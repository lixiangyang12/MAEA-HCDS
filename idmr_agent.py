"""
IDMR 智慧决策机器人 (DQN) - 纯NumPy实现
论文复现：缓解牛鞭效应的新途径：人机协同的智慧决策机器人（李勇等, 2022）

核心模块:
    1. QNetwork: 值网络 + 目标网络 (NumPy)
    2. ReplayBuffer: 经验回放池
    3. IDMRAgent: DQN智能体 + 人机协同机制
    4. train_idmr: 训练循环
    5. compare_with_paper: 与论文表3对比

状态空间: s_t = [S_{t-1}^3, WIP_{t-1}^3, q_{t-1}^2, Trans_{t-2}^3, q_{t-1}^3]  (5维)
动作空间: a_t in [11, 40]  (30个离散动作)
奖励函数: r_t = 完全满足顾客需求次数 / 订货次数
"""

import numpy as np
import random
from collections import deque
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False

from supply_chain_env import SupplyChainEnv, RationalAgent


# ============================================================
# 1. Q网络 (纯NumPy实现)
# ============================================================

class QNetwork:
    """
    DQN值网络 (纯NumPy实现)

    网络结构: state_dim -> 64 -> 64 -> action_dim (ReLU激活)
    使用He初始化和Adam优化器, 支持前向传播/反向传播/参数存取。
    """

    def __init__(self, state_dim=5, action_dim=30, hidden_dim=64, lr=1e-4):
        """
        初始化Q网络参数。

        Args:
            state_dim (int): 状态向量维度 (默认5)。
            action_dim (int): 动作空间大小 (默认30)。
            hidden_dim (int): 隐藏层神经元数 (默认64)。
            lr (float): Adam学习率 (默认1e-4)。
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.hidden_dim = hidden_dim
        self.lr = lr

        # He初始化
        scale1 = np.sqrt(2.0 / state_dim)
        scale2 = np.sqrt(2.0 / hidden_dim)
        scale3 = np.sqrt(2.0 / hidden_dim)

        self.W1 = np.random.randn(state_dim, hidden_dim) * scale1
        self.b1 = np.zeros(hidden_dim)
        self.W2 = np.random.randn(hidden_dim, hidden_dim) * scale2
        self.b2 = np.zeros(hidden_dim)
        self.W3 = np.random.randn(hidden_dim, action_dim) * scale3
        self.b3 = np.zeros(action_dim)

        # Adam优化器状态
        self._init_adam()

    def _init_adam(self):
        """初始化Adam优化器的一阶/二阶动量估计。"""
        self.m = {}
        self.v = {}
        self.t = 0
        beta1, beta2 = 0.9, 0.999
        for name in ['W1', 'b1', 'W2', 'b2', 'W3', 'b3']:
            self.m[name] = np.zeros_like(getattr(self, name))
            self.v[name] = np.zeros_like(getattr(self, name))

    def forward(self, x):
        """
        前向传播: 计算输入状态对应的Q值。

        Args:
            x (np.ndarray): 输入状态, shape=(batch, state_dim)。

        Returns:
            np.ndarray: Q值矩阵, shape=(batch, action_dim)。
        """
        self.x = x
        self.z1 = x @ self.W1 + self.b1
        self.a1 = np.maximum(0, self.z1)  # ReLU
        self.z2 = self.a1 @ self.W2 + self.b2
        self.a2 = np.maximum(0, self.z2)  # ReLU
        self.z3 = self.a2 @ self.W3 + self.b3
        return self.z3  # Q值

    def backward(self, grad_q, batch_size):
        """
        反向传播: 基于Q值梯度计算网络参数梯度。

        Args:
            grad_q (np.ndarray): Q值梯度, shape=(batch, action_dim)。
            batch_size (int): 批量大小, 用于梯度平均。

        Returns:
            dict: 各层参数梯度 {'W1','b1','W2','b2','W3','b3'}。
        """
        # grad_q: dL/dQ (batch, action_dim)
        grad_W3 = self.a2.T @ grad_q / batch_size
        grad_b3 = np.sum(grad_q, axis=0) / batch_size

        grad_a2 = grad_q @ self.W3.T
        grad_z2 = grad_a2 * (self.z2 > 0)  # ReLU梯度
        grad_W2 = self.a1.T @ grad_z2 / batch_size
        grad_b2 = np.sum(grad_z2, axis=0) / batch_size

        grad_a1 = grad_z2 @ self.W2.T
        grad_z1 = grad_a1 * (self.z1 > 0)  # ReLU梯度
        grad_W1 = self.x.T @ grad_z1 / batch_size
        grad_b1 = np.sum(grad_z1, axis=0) / batch_size

        return {'W1': grad_W1, 'b1': grad_b1,
                'W2': grad_W2, 'b2': grad_b2,
                'W3': grad_W3, 'b3': grad_b3}

    def adam_update(self, grads, beta1=0.9, beta2=0.999, eps=1e-8):
        """
        Adam优化器参数更新。

        Args:
            grads (dict): 各层参数梯度。
            beta1 (float): 一阶动量衰减率。
            beta2 (float): 二阶动量衰减率。
            eps (float): 数值稳定项。
        """
        self.t += 1
        for name in ['W1', 'b1', 'W2', 'b2', 'W3', 'b3']:
            g = grads[name]
            self.m[name] = beta1 * self.m[name] + (1 - beta1) * g
            self.v[name] = beta2 * self.v[name] + (1 - beta2) * (g ** 2)
            m_hat = self.m[name] / (1 - beta1 ** self.t)
            v_hat = self.v[name] / (1 - beta2 ** self.t)
            param = getattr(self, name)
            param -= self.lr * m_hat / (np.sqrt(v_hat) + eps)

    def get_params(self):
        """返回网络参数的深拷贝。"""
        return {'W1': self.W1.copy(), 'b1': self.b1.copy(),
                'W2': self.W2.copy(), 'b2': self.b2.copy(),
                'W3': self.W3.copy(), 'b3': self.b3.copy()}

    def load_params(self, params):
        """
        从字典加载网络参数。

        Args:
            params (dict): 参数字典, 键同 get_params()。
        """
        for name in ['W1', 'b1', 'W2', 'b2', 'W3', 'b3']:
            setattr(self, name, params[name].copy())


# ============================================================
# 2. 经验回放池
# ============================================================

class ReplayBuffer:
    """
    经验回放池 (Uniform Replay Buffer)

    存储 (s, a, r, s', done) 转换, 支持均匀随机采样。
    """

    def __init__(self, capacity=20000):
        """
        Args:
            capacity (int): 回放池最大容量。
        """
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        """
        Args:
            state: 当前状态。
            action: 执行的动作。
            reward: 获得的奖励。
            next_state: 下一状态。
            done (bool): 是否终止。
        """
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        """
        Args:
            batch_size (int): 采样批量大小。

        Returns:
            tuple: (states, actions, rewards, next_states, dones) 的NumPy数组。
        """
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            np.array(states, dtype=np.float32),
            np.array(actions, dtype=np.int64),
            np.array(rewards, dtype=np.float32),
            np.array(next_states, dtype=np.float32),
            np.array(dones, dtype=np.float32),
        )

    def __len__(self):
        return len(self.buffer)


# ============================================================
# 3. IDMR 智能体 (DQN + 人机协同)
# ============================================================

class IDMRAgent:
    """
    智慧决策机器人 (IDMR)

    人机协同三大机制:
        1. 传授经验: 用理性决策(SMA+OUT)作为参考
        2. 限制决策: ε-greedy探索，动作范围[11,40]
        3. 惩罚机制: IDMR库存>经典供应链均值时，强制a=0
    """

    def __init__(self, state_dim=5, action_min=11, action_max=40,
                 # DQN超参数 (论文附录表1)
                 lr=1e-4, gamma=0.9, batch_size=32,
                 replay_size=20000, replay_start=100,
                 epsilon_start=1.0, epsilon_end=0.01,
                 target_update_start=400, target_update_freq=10):
        """
        初始化IDMR智能体。

        Args:
            state_dim (int): 状态维度 (默认5)。
            action_min (int): 动作最小值 (默认11)。
            action_max (int): 动作最大值 (默认40)。
            lr (float): 学习率。
            gamma (float): 折扣因子。
            batch_size (int): 训练批量。
            replay_size (int): 回放池容量。
            replay_start (int): 开始训练的最小样本数。
            epsilon_start (float): ε初始值。
            epsilon_end (float): ε最终值。
            target_update_start (int): 目标网络开始更新步数。
            target_update_freq (int): 目标网络更新频率。
        """
        self.state_dim = state_dim
        self.action_min = action_min
        self.action_max = action_max
        self.action_dim = action_max - action_min + 1  # 30个动作

        # DQN组件 (NumPy实现)
        self.q_net = QNetwork(state_dim, self.action_dim, hidden_dim=64, lr=lr)
        self.target_net = QNetwork(state_dim, self.action_dim, hidden_dim=64, lr=lr)
        self.target_net.load_params(self.q_net.get_params())

        self.buffer = ReplayBuffer(capacity=replay_size)

        # 超参数
        self.gamma = gamma
        self.batch_size = batch_size
        self.replay_start = replay_start
        self.epsilon = epsilon_start
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.target_update_start = target_update_start
        self.target_update_freq = target_update_freq

        # 训练统计
        self.step_count = 0
        self.losses = []
        self.rewards = []

    def _epsilon_decay(self, total_steps):
        """线性衰减ε"""
        self.epsilon = max(
            self.epsilon_end,
            self.epsilon_start - (self.epsilon_start - self.epsilon_end) * self.step_count / total_steps
        )

    def get_state(self, env, k=3):
        """
        构建状态向量 (论文公式: 5维)
        s_t = [S_{t-1}^3, WIP_{t-1}^3, q_{t-1}^2, Trans_{t-2}^3, q_{t-1}^3]

        k=3 为分销商(IDMR所在节点)
        状态归一化: 各维度除以缩放因子，使值域在合理范围
        """
        node = env.nodes[k]
        upstream_node = env.nodes[k - 1] if k > 1 else None

        # S_{t-1}^3: 分销商上期库存 (归一化: /100)
        s_stock = node.net_stock / 100.0

        # WIP_{t-1}^3: 分销商上期在途库存 (归一化: /100)
        wip = (sum(node.pipeline) if node.pipeline else 0.0) / 100.0

        # q_{t-1}^2: 批发商上期订单 (归一化: /50)
        q_downstream = (upstream_node.order_placed if upstream_node else 0.0) / 50.0

        # Trans_{t-2}^3: 分销商前期运输货物 (归一化: /50)
        trans = (node.pipeline[0] if len(node.pipeline) > 0 else 0.0) / 50.0

        # q_{t-1}^3: 分销商上期订货量 (归一化: /50)
        q_self = node.order_placed / 50.0

        state = np.array([s_stock, wip, q_downstream, trans, q_self], dtype=np.float32)
        return state

    def select_action(self, state, force_zero=False):
        """
        ε-greedy动作选择

        参数:
            force_zero: 惩罚机制触发时，强制a=0
        """
        if force_zero:
            return 0  # 惩罚: 禁止订货

        if random.random() < self.epsilon:
            # 探索: 在[11,40]内随机
            return random.randint(self.action_min, self.action_max)
        else:
            # 利用: 选择Q值最大的动作
            q_values = self.q_net.forward(state.reshape(1, -1))
            action_idx = np.argmax(q_values)
            # 映射到实际动作值 [11, 40]
            return self.action_min + action_idx

    def store_transition(self, s, a, r, s_next, done):
        """
        存储经验转换到回放池。

        Args:
            s: 当前状态。
            a: 执行的动作。
            r: 获得的奖励。
            s_next: 下一状态。
            done (bool): 是否终止。
        """
        self.buffer.push(s, a, r, s_next, done)

    def update(self):
        """DQN梯度下降更新 (NumPy实现), 返回当前loss或None。"""
        if len(self.buffer) < self.replay_start:
            return None

        states, actions, rewards, next_states, dones = self.buffer.sample(self.batch_size)

        # 将原始动作值映射到动作索引 [0, 29]
        actions_idx = np.clip(actions - self.action_min, 0, self.action_dim - 1)

        # 当前Q值 (前向传播)
        q_all = self.q_net.forward(states)
        q_values = q_all[np.arange(self.batch_size), actions_idx]

        # 目标Q值 (target_net, 不计算梯度)
        next_q = self.target_net.forward(next_states)
        next_q_max = np.max(next_q, axis=1)
        target = rewards + self.gamma * next_q_max * (1 - dones)

        # 损失 = MSE
        td_error = q_values - target
        loss = np.mean(td_error ** 2)

        # 反向传播
        grad_q = np.zeros_like(q_all)
        grad_q[np.arange(self.batch_size), actions_idx] = 2.0 * td_error / self.batch_size

        grads = self.q_net.backward(grad_q, self.batch_size)
        self.q_net.adam_update(grads)

        # 目标网络更新
        self.step_count += 1
        if self.step_count >= self.target_update_start and self.step_count % self.target_update_freq == 0:
            self.target_net.load_params(self.q_net.get_params())

        self.losses.append(loss)
        return loss

    def save(self, path):
        """
        保存模型权重到文件。

        Args:
            path (str): 保存路径 (.pkl)。
        """
        import pickle
        with open(path, 'wb') as f:
            pickle.dump({
                'q_net': self.q_net.get_params(),
                'target_net': self.target_net.get_params(),
                'step_count': self.step_count,
                'epsilon': self.epsilon,
            }, f)

    def load(self, path):
        """
        从文件加载模型权重。

        Args:
            path (str): 模型文件路径 (.pkl)。
        """
        import pickle
        with open(path, 'rb') as f:
            ckpt = pickle.load(f)
        self.q_net.load_params(ckpt['q_net'])
        self.target_net.load_params(ckpt['target_net'])
        self.step_count = ckpt['step_count']
        self.epsilon = ckpt['epsilon']


# ============================================================
# 4. 仿真环境（分销商替换为IDMR）
# ============================================================

class IDMRSupplyChainEnv:
    """
    混合供应链环境:
        - 零售商(k=1): 理性决策 (SMA+OUT)
        - 批发商(k=2): 理性决策 (SMA+OUT)
        - 分销商(k=3): IDMR (DQN)
        - 制造商(k=4): 理性决策 (SMA+OUT)
    """

    def __init__(self, d=10, rho=0.5, sigma_eps=5.0, L=2, p=5, z=2,
                 C_L_rho=2.0, initial_inventory=10.0, K=4, seed=None, config=None):
        # ---- 工程化: 支持Config对象 ----
        if config is not None:
            sc = config.supply_chain
            ic = config.idmr
            d, rho, sigma_eps = sc.d, sc.rho, sc.sigma_eps
            L, p, z, C_L_rho = sc.L, sc.p, sc.z, sc.C_L_rho
            initial_inventory, K = sc.initial_inventory, sc.K
            self.penalty_threshold = ic.penalty_threshold
            self.holding_weight = ic.reward_holding_weight
            self.force_zero_on_penalty = ic.force_zero_on_penalty
            # 创新正向激励机制参数
            self.enable_inventory_bonus = ic.enable_inventory_bonus
            self.inventory_bonus_weight = ic.inventory_bonus_weight
            self.coverage_lower = ic.coverage_lower
            self.coverage_upper = ic.coverage_upper
            self.bonus_sma_window = ic.sma_window
            self.stockout_penalty_weight = ic.stockout_penalty_weight
            # 情绪模块参数
            self.enable_emotion = ic.enable_emotion
            self.emotion_alpha = ic.emotion_alpha
            self.emotion_gamma = ic.emotion_gamma
            self.emotion_w_stockout = ic.emotion_w_stockout
            self.emotion_w_match = ic.emotion_w_match
            self.emotion_w_excess = ic.emotion_w_excess
        else:
            self.penalty_threshold = 5.0
            self.holding_weight = 0.0001
            self.force_zero_on_penalty = True
            # 默认开启正向激励
            self.enable_inventory_bonus = True
            self.inventory_bonus_weight = 0.3
            self.coverage_lower = 0.8
            self.coverage_upper = 1.5
            self.bonus_sma_window = 5
            self.stockout_penalty_weight = 1.0
            # 默认开启情绪模块
            self.enable_emotion = True
            self.emotion_alpha = 0.7
            self.emotion_gamma = 2.0
            self.emotion_w_stockout = 1.0
            self.emotion_w_match = 0.5
            self.emotion_w_excess = 0.3

        # 初始化情绪状态管理器
        if self.enable_emotion:
            from emotion_module import EmotionState
            self.emotion = EmotionState(
                alpha=self.emotion_alpha,
                gamma=self.emotion_gamma,
                w_stockout=self.emotion_w_stockout,
                w_match=self.emotion_w_match,
                w_excess=self.emotion_w_excess,
            )
        else:
            self.emotion = None

        self.env = SupplyChainEnv(
            d=d, rho=rho, sigma_eps=sigma_eps,
            L=L, p=p, z=z, C_L_rho=C_L_rho,
            initial_inventory=initial_inventory, K=K, seed=seed,
        )
        self.L = L
        self.p = p
        self.z = z
        self.K = K

        # 理性决策Agent (用于k=1,2,4)
        self.rational = RationalAgent(L=L, p=p, z=z, C_L_rho=C_L_rho, sigma_eps=sigma_eps)
        for k in [1, 2, 4]:
            self.rational.init_node(k)

        # 经典供应链基准 (用于惩罚机制比较)
        # 修复: 运行Baseline获取分销商实际平均库存, 而非用initial_inventory
        self.classical_avg_inventory = {3: self._compute_classical_avg_inventory(
            d, rho, sigma_eps, L, p, z, C_L_rho, initial_inventory, K, seed)}

    def _compute_classical_avg_inventory(self, d, rho, sigma_eps, L, p, z,
                                          C_L_rho, initial_inventory, K, seed):
        """
        运行经典供应链Baseline, 计算分销商(k=3)的平均库存

        李勇论文惩罚机制: "当积压库存达到相同需求下经典多级供应链
        对应节点的平均库存时, 禁止向上游订货"
        → 惩罚阈值 = 经典供应链分销商的实际平均库存
        """
        from supply_chain_env import SupplyChainEnv, RationalAgent
        env = SupplyChainEnv(
            d=d, rho=rho, sigma_eps=sigma_eps, L=L, p=p, z=z,
            C_L_rho=C_L_rho, initial_inventory=initial_inventory, K=K,
            seed=seed,
        )
        agent = RationalAgent(L=L, p=p, z=z, C_L_rho=C_L_rho, sigma_eps=sigma_eps)
        for k in range(1, K + 1):
            agent.init_node(k)

        env.reset()
        ns_history_3 = []
        warmup = 2000  # 预热期, 取后2000步的平均库存

        for t in range(warmup):
            D_t = env._generate_demand()
            env.customer_demand_history.append(D_t)
            downstream_demand = {1: D_t}

            for k in range(1, env.K + 1):
                node = env.nodes[k]
                demand_k = downstream_demand.get(k, 0)
                arrived = node.pipeline[0] if len(node.pipeline) > 0 else 0.0
                node.net_stock += arrived
                if len(node.pipeline) > 0:
                    node.pipeline.popleft()

                q_t = agent.decide(k, node.net_stock, sum(node.pipeline), demand_k)
                q_t = max(0, q_t)
                node.order_placed = q_t
                node.order_history.append(q_t)
                downstream_demand[k + 1] = q_t

                fulfilled = min(max(node.net_stock, 0), demand_k)
                node.net_stock -= fulfilled
                node.demand_history.append(demand_k)
                node.pipeline.append(q_t)

                if k == 3:
                    ns_history_3.append(node.net_stock)

        avg_inv = float(np.mean(ns_history_3)) if ns_history_3 else initial_inventory
        print(f"  [惩罚机制] 经典供应链分销商平均库存={avg_inv:.2f} (预热{warmup}步)")
        return avg_inv

    def step(self, idmr_agent, total_steps):
        """
        执行一个仿真周期 (分销商=IDMR)
        """
        env = self.env

        # 生成需求
        D_t = env._generate_demand()
        env.customer_demand_history.append(D_t)

        # 按顺序决策
        downstream_demand = {1: D_t}
        orders = {}
        idmr_state = None
        idmr_action = None
        idmr_reward = 0
        idmr_next_state = None
        idmr_force_zero = False
        idmr_stockout = 0
        idmr_demand = 0
        idmr_fulfilled = 0
        idmr_ns_before = 0

        for k in range(1, env.K + 1):
            node = env.nodes[k]

            # Step 1: 收到上游货物
            arrived = node.pipeline[0] if len(node.pipeline) > 0 else 0.0
            node.net_stock += arrived
            if len(node.pipeline) > 0:
                node.pipeline.popleft()

            demand_k = downstream_demand.get(k, 0)

            if k == 3:
                # ===== IDMR 决策 (分销商) =====
                idmr_ns_before = node.net_stock
                idmr_demand = demand_k
                idmr_state = idmr_agent.get_state(env, k=3)

                # 惩罚机制: IDMR库存 > 阈值时禁止订货 (阈值放宽到3倍)
                if node.net_stock > self.classical_avg_inventory.get(3, 10) * self.penalty_threshold:
                    idmr_force_zero = True

                idmr_action = idmr_agent.select_action(idmr_state, force_zero=idmr_force_zero)
                q_t = max(0, idmr_action)
                orders[k] = q_t

            else:
                # ===== 理性决策 (k=1,2,4) =====
                q_t = self.rational.decide(k, node.net_stock, sum(node.pipeline), demand_k)
                q_t = max(0, q_t)
                orders[k] = q_t

            node.order_placed = q_t
            node.order_history.append(q_t)
            downstream_demand[k + 1] = q_t

            # 关键: 将订单放入自身pipeline, L期后变为收到的上游货物
            # (节点k向上游订货q_t, 上游当期发货, 经L期运输后到达节点k)
            node.pipeline.append(q_t)

            # Step 3: 满足下游需求
            fulfilled = min(max(node.net_stock, 0), demand_k)
            node.net_stock -= fulfilled
            stockout = max(0, demand_k - fulfilled)

            node.demand_history.append(demand_k)
            # 记录fulfilled历史, 用于正确计算SL
            if not hasattr(node, 'fulfilled_history'):
                from collections import deque as _dq
                node.fulfilled_history = _dq(maxlen=50000)
            node.fulfilled_history.append(fulfilled)

            # 记录IDMR的奖励和下一状态
            if k == 3:
                idmr_fulfilled = fulfilled
                idmr_stockout = stockout

                # ============================================================
                # 奖励函数 v5: 创新正向激励机制
                # ============================================================
                # 【理论背景 - 对冲"损失厌恶"导致的过度订货】
                # 传统啤酒游戏中,企业因害怕缺货担责(损失厌恶)而过度订货,
                # 导致上游牛鞭效应逐级放大。其根源在于:
                #   1. 缺货 = 刚性惩罚(担责/丢客户), 强激励避免缺货
                #   2. 库存积压 = 软约束(仅利润缩水), 弱激励,缺乏正向反馈
                # 这种不对称使决策者偏向"多订货保险",放大方差。
                #
                # 【创新机制 - 库存精准匹配正向激励】
                # 人为引入正向奖励: 当期末库存精准覆盖下期预测需求,
                # 且无过度积压时,给予正向奖励,对冲过度订货倾向。
                # 数学形式:
                #   奖励 = fill_rate                       # 服务水平收益
                #        + inventory_bonus                  # [新增] 库存精准匹配正向激励
                #        - stockout_penalty                  # [恢复] 缺货刚性惩罚
                #        - holding_penalty                   # 库存积压软惩罚
                # ============================================================

                # ---- 1. 服务水平收益 (fill_rate, 论文公式11稠密化) ----
                if demand_k > 0:
                    fill_rate = fulfilled / demand_k
                else:
                    fill_rate = 1.0

                # ---- 2. [创新] 库存精准匹配正向激励 ----
                # 当 NS_t 精准覆盖下期预测需求 D̂_{t+1} 时给予奖励
                # 触发条件: coverage_lower * D̂ <= NS_t <= coverage_upper * D̂
                # 这引导DQN学到"按需订货"而非"囤货保险"的策略
                inventory_bonus = 0.0
                match_factor = 0.0  # 用于情绪反馈
                excess_rate = 0.0   # 用于情绪反馈
                if self.enable_inventory_bonus:
                    # 用SMA预测下期需求 D̂_{t+1}
                    recent_demands = list(node.demand_history)[-self.bonus_sma_window:]
                    if len(recent_demands) >= 2:
                        forecast_next = np.mean(recent_demands)
                        ns_after = node.net_stock  # 发货后的期末库存
                        # 判定库存是否精准覆盖预测需求
                        lower_bound = self.coverage_lower * forecast_next
                        upper_bound = self.coverage_upper * forecast_next
                        if ns_after >= lower_bound and ns_after <= upper_bound:
                            # 库存精准匹配: 给予正向激励
                            # 匹配越精准(越接近1.0倍),奖励越高 (钟形曲线)
                            if forecast_next > 0:
                                match_ratio = ns_after / forecast_next
                                match_factor = max(0, 1.0 - abs(match_ratio - 1.0))
                                # 钟形奖励: 在match_ratio=1.0时最大, 偏离时衰减
                                deviation = abs(match_ratio - 1.0)
                                max_deviation = max(1.0 - self.coverage_lower,
                                                    self.coverage_upper - 1.0)
                                if max_deviation > 0:
                                    bonus_factor = 1.0 - (deviation / max_deviation)
                                else:
                                    bonus_factor = 1.0
                                inventory_bonus = self.inventory_bonus_weight * max(0, bonus_factor)
                        # 计算过度积压率 (用于情绪反馈)
                        if forecast_next > 0:
                            excess_rate = max(0, (ns_after - upper_bound) / forecast_next)

                # ---- 3. [恢复] 缺货刚性惩罚 (传统模型) ----
                # 缺货率 = stockout / demand, 与fill_rate互补但单独计算
                if demand_k > 0:
                    stockout_rate = stockout / demand_k
                else:
                    stockout_rate = 0.0

                # ---- 3.5 [情绪模块] 情绪调节奖励权重 ----
                # 情绪E_t演化: 受缺货(恐慌)和精准匹配(乐观)反馈驱动
                # 决策映射: 恐慌时放大缺货惩罚, 乐观时放大正向激励
                if self.emotion is not None:
                    # 情绪演化
                    self.emotion.update(
                        stockout_rate=stockout_rate,
                        match_factor=match_factor,
                        excess_rate=excess_rate,
                    )
                    # 情绪调节奖励权重
                    em_weights = self.emotion.get_reward_weights(
                        base_stockout_weight=self.stockout_penalty_weight,
                        base_bonus_weight=self.inventory_bonus_weight,
                    )
                    eff_stockout_weight = em_weights['stockout_weight']
                    eff_bonus_weight = em_weights['bonus_weight']
                    # 重算库存精准匹配奖励 (用情绪调节后的权重)
                    if match_factor > 0:
                        inventory_bonus = eff_bonus_weight * match_factor
                else:
                    eff_stockout_weight = self.stockout_penalty_weight

                stockout_penalty = eff_stockout_weight * stockout_rate

                # ---- 4. 库存积压软惩罚 (防止无界囤积) ----
                holding_penalty = self.holding_weight * max(0, node.net_stock)

                # ---- 综合奖励 ----
                # 正向: fill_rate + inventory_bonus (情绪调节)
                # 负向: - stockout_penalty (情绪调节) - holding_penalty
                idmr_reward = (fill_rate
                               + inventory_bonus
                               - stockout_penalty
                               - holding_penalty)

        # 获取IDMR下一状态
        idmr_next_state = idmr_agent.get_state(env, k=3)

        # 存储经验
        done = False
        idmr_agent.store_transition(idmr_state, idmr_action, idmr_reward, idmr_next_state, done)

        # DQN更新
        loss = idmr_agent.update()
        idmr_agent._epsilon_decay(total_steps)
        idmr_agent.rewards.append(idmr_reward)

        env.t += 1
        return {
            'demand': D_t,
            'orders': orders,
            'idmr_loss': loss,
            'idmr_reward': idmr_reward,
            'idmr_epsilon': idmr_agent.epsilon,
        }


# ============================================================
# 5. 训练循环
# ============================================================

def train_idmr(total_steps=20000, seed=42, verbose=True, config=None, logger=None):
    """
    训练IDMR智能体

    参数:
        total_steps: 训练步数 (论文=20000)
        seed: 随机种子
        verbose: 打印进度
        config: Config对象 (工程化配置, 若提供则覆盖参数)
        logger: Logger对象 (训练日志, 若提供则记录指标)
    """
    # ---- 工程化: 统一随机种子 ----
    if config is not None:
        from config import set_seed
        set_seed(config.seed)
        sc = config.supply_chain
        dq = config.dqn
        env = IDMRSupplyChainEnv(seed=config.seed, config=config)
        idmr = IDMRAgent(
            state_dim=dq.state_dim, action_min=dq.action_min, action_max=dq.action_max,
            lr=dq.learning_rate, gamma=dq.gamma, batch_size=dq.batch_size,
            replay_size=dq.replay_size, replay_start=dq.replay_start,
            epsilon_start=dq.epsilon_start, epsilon_end=dq.epsilon_end,
            target_update_start=dq.target_update_start, target_update_freq=dq.target_update_freq,
        )
        total_steps = config.training.total_steps
        log_interval = config.training.log_interval
    else:
        np.random.seed(seed)
        random.seed(seed)
        env = IDMRSupplyChainEnv(seed=seed)
        idmr = IDMRAgent(
            state_dim=5, action_min=11, action_max=40,
            lr=1e-3, gamma=0.9, batch_size=32,
            replay_size=20000, replay_start=100,
            epsilon_start=1.0, epsilon_end=0.01,
            target_update_start=400, target_update_freq=10,
        )
        log_interval = 2000

    # 训练记录
    episode_losses = []
    episode_rewards = []
    episode_bwe = []

    print("=" * 60)
    print("IDMR 训练开始 (DQN)")
    print(f"  总步数: {total_steps}")
    if config is not None:
        print(f"  状态维度: {dq.state_dim}, 动作范围: [{dq.action_min}, {dq.action_max}] (config)")
        print(f"  lr={dq.learning_rate}, gamma={dq.gamma}, batch={dq.batch_size}")
        print(f"  配置驱动: config.yaml (seed={config.seed})")
    else:
        print(f"  状态维度: 5, 动作范围: [11, 40] (论文设定)")
        print(f"  lr=1e-3, gamma=0.9, batch=32")
    print(f"  奖励: fill_rate + inventory_bonus - stockout_penalty - holding")
    print(f"  [创新] 正向激励: {'启用' if getattr(env, 'enable_inventory_bonus', False) else '关闭'}")
    print(f"  状态归一化: 已启用")
    print(f"  惩罚阈值: 5x经典库存")
    if logger:
        print(f"  日志: {logger.run_dir}")
    print("=" * 60)

    for step in range(1, total_steps + 1):
        result = env.step(idmr, total_steps)

        if result['idmr_loss'] is not None:
            episode_losses.append(result['idmr_loss'])
        episode_rewards.append(result['idmr_reward'])

        if verbose and step % log_interval == 0:
            avg_loss = np.mean(episode_losses[-log_interval:]) if episode_losses else 0
            avg_reward = np.mean(episode_rewards[-log_interval:])
            bwe = env.env.compute_bullwhip()
            episode_bwe.append(bwe.get(3, 0))
            print(f"  Step {step:>5d}/{total_steps} | "
                  f"Loss={avg_loss:.4f} | "
                  f"Reward={avg_reward:.3f} | "
                  f"eps={idmr.epsilon:.3f} | "
                  f"BWE_distr={bwe.get(3, 0):.1f}")
            # 日志记录
            if logger:
                logger.log_training(
                    step=step, loss=avg_loss, reward=avg_reward,
                    epsilon=idmr.epsilon, bwe_distributor=bwe.get(3, 0),
                    avg_reward_100=avg_reward, avg_loss_100=avg_loss,
                )

    print("=" * 60)
    print("训练完成!")
    return env, idmr, {
        'losses': episode_losses,
        'rewards': episode_rewards,
        'bwe_history': episode_bwe,
    }


# ============================================================
# 6. 评估与对比
# ============================================================

def evaluate(env, idmr, n_steps=1000):
    """评估训练后的IDMR表现"""
    print("\n[评估] 运行 %d 步..." % n_steps)

    # 运行评估
    for _ in range(n_steps):
        env.step(idmr, total_steps=1)
        idmr.epsilon = 0.01  # 评估时低探索

    # 计算指标
    bwe = env.env.compute_bullwhip()
    node_names = ["零售商", "批发商", "分销商(IDMR)", "制造商"]

    print("\n  方差比 (BWE):")
    for k in range(1, 5):
        print(f"    {node_names[k-1]}: {bwe[k]:.2f}")

    # 平均成本
    print("\n  平均成本:")
    for k in range(1, 5):
        orders = list(env.env.nodes[k].order_history)[-n_steps:]
        demands = list(env.env.nodes[k].demand_history)[-n_steps:]
        # 正确的SL = fulfilled / demand (论文公式6: 有货率)
        fulfilled_list = list(getattr(env.env.nodes[k], 'fulfilled_history', orders))[-n_steps:]
        avg_cost = np.mean(np.abs(orders)) * 0.5  # 简化成本
        sl = np.mean([f / d if d > 0 else 1.0
                      for f, d in zip(fulfilled_list, demands)])
        print(f"    {node_names[k-1]}: 成本={avg_cost:.2f}, SL={sl:.3f}")

    return bwe


def compare_with_paper(bwe_idmr, bwe_baseline):
    """与论文表3对比"""
    print("\n" + "=" * 60)
    print("与论文表3对比")
    print("=" * 60)

    # 论文表3数据 (近似值)
    paper_data = {
        'classic': {'BWE_distr': 789.41, 'BWE_manuf': 9160.60, 'SL': 0.977},
        'idmr': {'BWE_distr': '~50-100', 'BWE_manuf': '~500-1000', 'SL': '~0.95-0.99'},
    }

    print(f"\n  {'指标':<20} {'经典(基线)':<15} {'IDMR(本实现)':<15} {'论文IDMR':<15}")
    print(f"  {'-'*65}")
    print(f"  {'分销商BWE':<20} {bwe_baseline[3]:<15.2f} {bwe_idmr[3]:<15.2f} {paper_data['idmr']['BWE_distr']:<15}")
    print(f"  {'制造商BWE':<20} {bwe_baseline[4]:<15.2f} {bwe_idmr[4]:<15.2f} {paper_data['idmr']['BWE_manuf']:<15}")

    # 排查清单
    print("\n" + "=" * 60)
    print("排查清单 (如结果偏差较大):")
    print("=" * 60)
    checklist = [
        "1. 仿真周期: 论文20000步, 本实现可能不足",
        "2. 需求参数: 确认d=10, rho=0.5, eps~N(0,5)",
        "3. 状态归一化: 论文可能对状态做了归一化处理",
        "4. 奖励设计: 论文奖励=完全满足次数/订货次数, 确认一致",
        "5. 惩罚阈值: 论文惩罚机制的具体阈值需确认",
        "6. 网络结构: 论文可能使用不同隐藏层维度",
        "7. ε衰减: 论文衰减策略可能非线性",
        "8. 经验回放: 确认replay_start=100和target_update=400",
        "9. 动作映射: 确认[11,40]是否包含端点",
        "10. 多次运行: DQN有随机性, 需取多次平均",
    ]
    for item in checklist:
        print(f"  {item}")

    return checklist


# ============================================================
# 7. 可视化
# ============================================================

def plot_results(history, env, idmr):
    """绘制训练曲线和结果"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 子图1: Loss曲线
    ax1 = axes[0, 0]
    if history['losses']:
        losses = history['losses']
        window = min(100, len(losses) // 5)
        if window > 0:
            smoothed = np.convolve(losses, np.ones(window)/window, mode='valid')
            ax1.plot(smoothed, color='#00d4ff', linewidth=1.5)
        ax1.set_title('DQN Loss', fontsize=13, fontweight='bold')
        ax1.set_xlabel('Training Step')
        ax1.set_ylabel('MSE Loss')
        ax1.grid(True, alpha=0.3)

    # 子图2: 奖励曲线
    ax2 = axes[0, 1]
    rewards = history['rewards']
    window = min(100, len(rewards) // 5)
    if window > 0:
        smoothed = np.convolve(rewards, np.ones(window)/window, mode='valid')
        ax2.plot(smoothed, color='#ff6b9d', linewidth=1.5)
    ax2.set_title('IDMR Reward', fontsize=13, fontweight='bold')
    ax2.set_xlabel('Training Step')
    ax2.set_ylabel('Avg Reward')
    ax2.grid(True, alpha=0.3)

    # 子图3: BWE对比
    ax3 = axes[1, 0]
    bwe = env.env.compute_bullwhip()
    node_names = ['零售商', '批发商', '分销商\n(IDMR)', '制造商']
    colors = ['#00d4ff', '#ff6b9d', '#ffd93d', '#6bcf7f']
    bars = ax3.bar(range(1, 5), [bwe[k] for k in range(1, 5)], color=colors, edgecolor='white')
    ax3.set_title('BWE: IDMR vs Baseline', fontsize=13, fontweight='bold')
    ax3.set_xlabel('Supply Chain Node')
    ax3.set_ylabel('Variance Ratio (BWE)')
    ax3.set_xticks(range(1, 5))
    ax3.set_xticklabels(node_names)
    ax3.grid(True, alpha=0.3)
    for bar, val in zip(bars, [bwe[k] for k in range(1, 5)]):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                 f'{val:.1f}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 子图4: ε衰减
    ax4 = axes[1, 1]
    eps_history = [max(0.01, 1.0 - (1.0 - 0.01) * i / 20000) for i in range(20000)]
    ax4.plot(eps_history[:len(history['rewards'])], color='#6bcf7f', linewidth=1.5)
    ax4.set_title('Epsilon Decay', fontsize=13, fontweight='bold')
    ax4.set_xlabel('Training Step')
    ax4.set_ylabel('Epsilon')
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('idmr_training_results.png', dpi=150, bbox_inches='tight')
    print("\n图表已保存: idmr_training_results.png")


# ============================================================
# 8. 三大指标对比图 (方差比/平均成本/服务水平)
# ============================================================

def plot_three_metrics_comparison(idmr_env, baseline_env):
    """
    绘制理性决策 vs 智慧决策(IDMR) 三大指标对比图
    1. 方差比 (BWE)
    2. 平均成本
    3. 服务水平 (SL)
    分别保存为独立PNG
    """
    node_names = ['零售商', '批发商', '分销商\n(IDMR)', '制造商']
    node_names_short = ['零售商', '批发商', '分销商', '制造商']
    x = np.arange(4)
    width = 0.35

    # ===== 图1: 方差比对比 =====
    bwe_idmr = idmr_env.env.compute_bullwhip()
    bwe_base = baseline_env.compute_bullwhip()
    bwe_idmr_vals = [bwe_idmr[k] for k in range(1, 5)]
    bwe_base_vals = [bwe_base[k] for k in range(1, 5)]

    fig1, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width/2, bwe_base_vals, width,
                   label='理性决策', color='#5a7d9a', edgecolor='white', linewidth=1.2)
    bars2 = ax.bar(x + width/2, bwe_idmr_vals, width,
                   label='智慧决策(IDMR)', color='#ff6b9d', edgecolor='white', linewidth=1.2)
    ax.set_title('方差比对比：理性决策 vs 智慧决策', fontsize=15, fontweight='bold', pad=15)
    ax.set_xlabel('供应链节点', fontsize=12)
    ax.set_ylabel('方差比 (BWE = var(q)/var(D))', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(node_names)
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars1, bwe_base_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(bwe_base_vals)*0.02,
                f'{val:.1f}', ha='center', va='bottom', fontsize=9, color='#5a7d9a')
    for bar, val in zip(bars2, bwe_idmr_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(bwe_base_vals)*0.02,
                f'{val:.1f}', ha='center', va='bottom', fontsize=9, color='#ff6b9d', fontweight='bold')
    plt.tight_layout()
    plt.savefig('对比图1_方差比.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  [OK] 已保存: 对比图1_方差比.png")

    # ===== 图2: 平均成本对比 =====
    # 成本 = 库存成本 + 缺货成本 (库存成本=1/单位, 缺货成本=2/单位, 论文设定)
    n_eval = 1000
    cost_base_vals = []
    cost_idmr_vals = []
    for k in range(1, 5):
        # 基线: 用历史数据计算平均成本
        demands_b = list(baseline_env.nodes[k].demand_history)[-n_eval:]
        fulfilled_b = list(baseline_env.nodes[k].fulfilled_history)[-n_eval:]
        orders_b = list(baseline_env.nodes[k].order_history)[-n_eval:]
        # 平均成本: 库存成本 + 缺货成本 (近似: 用订单和满足量推算)
        # 库存 ≈ 订单 - 满足量 (累积), 缺货 = 需求 - 满足量
        stockouts_b = [max(0, d - f) for d, f in zip(demands_b, fulfilled_b)]
        avg_cost_b = np.mean([abs(o - f) * 1.0 + s * 2.0
                              for o, f, s in zip(orders_b, fulfilled_b, stockouts_b)])
        cost_base_vals.append(avg_cost_b)

        # IDMR
        demands_i = list(idmr_env.env.nodes[k].demand_history)[-n_eval:]
        fulfilled_i = list(getattr(idmr_env.env.nodes[k], 'fulfilled_history', demands_i))[-n_eval:]
        orders_i = list(idmr_env.env.nodes[k].order_history)[-n_eval:]
        stockouts_i = [max(0, d - f) for d, f in zip(demands_i, fulfilled_i)]
        avg_cost_i = np.mean([abs(o - f) * 1.0 + s * 2.0
                              for o, f, s in zip(orders_i, fulfilled_i, stockouts_i)])
        cost_idmr_vals.append(avg_cost_i)

    fig2, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width/2, cost_base_vals, width,
                   label='理性决策', color='#5a7d9a', edgecolor='white', linewidth=1.2)
    bars2 = ax.bar(x + width/2, cost_idmr_vals, width,
                   label='智慧决策(IDMR)', color='#ffd93d', edgecolor='white', linewidth=1.2)
    ax.set_title('平均成本对比：理性决策 vs 智慧决策', fontsize=15, fontweight='bold', pad=15)
    ax.set_xlabel('供应链节点', fontsize=12)
    ax.set_ylabel('平均成本 (库存成本 + 缺货成本)', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(node_names)
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars1, cost_base_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(cost_base_vals)*0.02,
                f'{val:.1f}', ha='center', va='bottom', fontsize=9, color='#5a7d9a')
    for bar, val in zip(bars2, cost_idmr_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(cost_base_vals)*0.02,
                f'{val:.1f}', ha='center', va='bottom', fontsize=9, color='#b8860b', fontweight='bold')
    plt.tight_layout()
    plt.savefig('对比图2_平均成本.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  [OK] 已保存: 对比图2_平均成本.png")

    # ===== 图3: 服务水平对比 =====
    sl_base_vals = []
    sl_idmr_vals = []
    for k in range(1, 5):
        # 基线 SL = fulfilled / demand
        demands_b = list(baseline_env.nodes[k].demand_history)[-n_eval:]
        fulfilled_b = list(baseline_env.nodes[k].fulfilled_history)[-n_eval:]
        sl_b = np.mean([f / d if d > 0 else 1.0 for f, d in zip(fulfilled_b, demands_b)])
        sl_base_vals.append(sl_b)

        # IDMR SL
        demands_i = list(idmr_env.env.nodes[k].demand_history)[-n_eval:]
        fulfilled_i = list(getattr(idmr_env.env.nodes[k], 'fulfilled_history', demands_i))[-n_eval:]
        sl_i = np.mean([f / d if d > 0 else 1.0 for f, d in zip(fulfilled_i, demands_i)])
        sl_idmr_vals.append(sl_i)

    fig3, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width/2, sl_base_vals, width,
                   label='理性决策', color='#5a7d9a', edgecolor='white', linewidth=1.2)
    bars2 = ax.bar(x + width/2, sl_idmr_vals, width,
                   label='智慧决策(IDMR)', color='#6bcf7f', edgecolor='white', linewidth=1.2)
    ax.set_title('服务水平对比：理性决策 vs 智慧决策', fontsize=15, fontweight='bold', pad=15)
    ax.set_xlabel('供应链节点', fontsize=12)
    ax.set_ylabel('服务水平 (SL = 有货率)', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(node_names)
    ax.set_ylim(0, 1.15)
    ax.axhline(y=0.977, color='red', linestyle='--', linewidth=1, alpha=0.7, label='理论目标SL=97.7% (z=2)')
    ax.legend(fontsize=11, loc='lower right')
    ax.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars1, sl_base_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{val:.1%}', ha='center', va='bottom', fontsize=9, color='#5a7d9a')
    for bar, val in zip(bars2, sl_idmr_vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{val:.1%}', ha='center', va='bottom', fontsize=9, color='#2e8b57', fontweight='bold')
    plt.tight_layout()
    plt.savefig('对比图3_服务水平.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("  [OK] 已保存: 对比图3_服务水平.png")

    # 打印汇总表
    print("\n" + "=" * 70)
    print("三大指标汇总 (最近1000周期均值)")
    print("=" * 70)
    print(f"  {'节点':<8} {'BWE(理性)':<12} {'BWE(IDMR)':<12} {'成本(理性)':<12} {'成本(IDMR)':<12} {'SL(理性)':<10} {'SL(IDMR)':<10}")
    print("  " + "-" * 66)
    for i, k in enumerate(range(1, 5)):
        print(f"  {node_names_short[i]:<8} {bwe_base_vals[i]:<12.2f} {bwe_idmr_vals[i]:<12.2f} "
              f"{cost_base_vals[i]:<12.2f} {cost_idmr_vals[i]:<12.2f} "
              f"{sl_base_vals[i]:<10.1%} {sl_idmr_vals[i]:<10.1%}")
    print("=" * 70)




if __name__ == "__main__":
    # ---- 工程化入口: 配置驱动 + 日志记录 + 随机种子 ----
    from config import load_config, set_seed
    from logger import Logger
    import dataclasses

    # 1. 加载配置
    cfg = load_config()

    # 2. 设置随机种子 (确保100%可复现)
    set_seed(cfg.seed)
    print(f"[工程化] 配置已加载: config.yaml (seed={cfg.seed})")
    print(f"[工程化] 随机种子已设置: Python + NumPy (可复现)")

    # 3. 初始化日志记录器
    with Logger(
        log_dir=cfg.logging.log_dir,
        use_csv=cfg.logging.use_csv,
        use_tensorboard=cfg.logging.use_tensorboard,
    ) as logger:
        # 记录配置快照
        config_dict = dataclasses.asdict(cfg)
        logger.log_config(config_dict)
        print(f"[工程化] 日志目录: {logger.run_dir}")

        # 4. 训练IDMR (配置驱动)
        env, idmr, history = train_idmr(
            total_steps=cfg.training.total_steps,
            seed=cfg.seed, verbose=True,
            config=cfg, logger=logger,
        )

        # 5. 保存模型
        if cfg.logging.save_model:
            idmr.save(cfg.logging.model_path)
            print(f"[工程化] 模型已保存: {cfg.logging.model_path}")

        # 6. 评估
        bwe_idmr = evaluate(env, idmr, n_steps=cfg.training.eval_steps)

        # 7. 记录评估指标到日志
        eval_metrics = {}
        for k in range(1, 5):
            demands = list(env.env.nodes[k].demand_history)[-cfg.training.eval_steps:]
            fulfilled = list(getattr(env.env.nodes[k], 'fulfilled_history', demands))[-cfg.training.eval_steps:]
            orders = list(env.env.nodes[k].order_history)[-cfg.training.eval_steps:]
            stockouts = [max(0, d - f) for d, f in zip(demands, fulfilled)]
            eval_metrics[k] = {
                'bwe': bwe_idmr.get(k, 0),
                'avg_cost': float(np.mean([abs(o-f)*1.0 + s*2.0
                             for o, f, s in zip(orders, fulfilled, stockouts)])),
                'service_level': float(np.mean([f/d if d > 0 else 1.0
                                  for f, d in zip(fulfilled, demands)])),
                'demand_mean': float(np.mean(demands)),
                'order_mean': float(np.mean(orders)),
            }
        logger.log_eval(step=cfg.training.total_steps, metrics=eval_metrics)

        # 8. 基线对比 (修复pipeline bug + 记录fulfilled)
        print("\n[基线] 运行理性决策仿真...")
        from supply_chain_env import SupplyChainEnv, RationalAgent
        baseline_env = SupplyChainEnv(seed=cfg.seed, config=cfg)
        baseline_agent = RationalAgent(
            L=cfg.supply_chain.L, p=cfg.supply_chain.p, z=cfg.supply_chain.z,
            C_L_rho=cfg.supply_chain.C_L_rho, sigma_eps=cfg.supply_chain.sigma_eps,
        )
        for k in range(1, 5):
            baseline_agent.init_node(k)
        for k in range(1, 5):
            baseline_env.nodes[k].fulfilled_history = deque(maxlen=50000)

        # 运行基线 (pipeline修复: 订单放入自身pipeline, L期后到货)
        for t in range(cfg.training.baseline_steps):
            D_t = baseline_env._generate_demand()
            baseline_env.customer_demand_history.append(D_t)
            downstream_demand = {1: D_t}
            for k in range(1, 5):
                node = baseline_env.nodes[k]
                arrived = node.pipeline[0] if len(node.pipeline) > 0 else 0.0
                node.net_stock += arrived
                if len(node.pipeline) > 0:
                    node.pipeline.popleft()
                demand_k = downstream_demand.get(k, 0)
                q_t = baseline_agent.decide(k, node.net_stock, sum(node.pipeline), demand_k)
                q_t = max(0, q_t)
                node.order_placed = q_t
                node.order_history.append(q_t)
                downstream_demand[k + 1] = q_t
                node.pipeline.append(q_t)
                fulfilled = min(max(node.net_stock, 0), demand_k)
                node.net_stock -= fulfilled
                node.demand_history.append(demand_k)
                node.fulfilled_history.append(fulfilled)
            baseline_env.t += 1

        bwe_baseline = baseline_env.compute_bullwhip()

        # 9. 对比分析
        compare_with_paper(bwe_idmr, bwe_baseline)

        # 10. 训练曲线图
        plot_results(history, env, idmr)

        # 11. 三大指标对比图
        plot_three_metrics_comparison(env, baseline_env)

        # 12. 保存实验摘要
        summary = {
            'best_reward': float(np.mean(history['rewards'][-1000:])),
            'final_bwe_distributor': float(bwe_idmr.get(3, 0)),
            'final_bwe_manufacturer': float(bwe_idmr.get(4, 0)),
            'final_sl_distributor': eval_metrics[3]['service_level'],
            'baseline_bwe_distributor': float(bwe_baseline.get(3, 0)),
            'baseline_bwe_manufacturer': float(bwe_baseline.get(4, 0)),
        }
        summary_path = logger.save_summary(summary)
        print(f"\n[工程化] 实验摘要已保存: {summary_path}")

    print("\n" + "=" * 60)
    print("IDMR 实验完成! (工程化重构版)")
    print("=" * 60)

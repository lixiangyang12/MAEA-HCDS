"""
多智能体供应链协同环境 (MARL Supply Chain Environment)
=======================================================

基于 PettingZoo AECEnv 实现, 将单智能体 DQN 升级为多智能体强化学习。

架构:
    - 4 个独立 Agent: 零售商 / 批发商 / 分销商 / 制造商
    - 每个 Agent 拥有:
        * 局部观测 (Local Observation)
        * 动作空间 (订货量)
        * 独立情绪模块 (EmotionState)
    - 协同机制 (Communication Channel):
        * Agent 之间可共享预测需求 / 库存水平 / 情绪标签
        * 缓解供应链信息不对称 (牛鞭效应根源)

执行顺序 (AECEnv 顺序决策):
    零售商 → 批发商 → 分销商 → 制造商
    (下游先决策, 订单逐级上传, 符合供应链物理流程)

依赖:
    pip install pettingzoo gymnasium numpy

使用示例:
    from marl_supply_chain_env import MARLSupplyChainEnv
    env = MARLSupplyChainEnv(config=None)  # 使用默认配置
    env.reset(seed=42)
    for agent in env.agent_iter():
        obs, reward, termination, truncation, info = env.last()
        action = env.action_space(agent).sample()
        env.step(action)

命名规范 (PettingZoo AECEnv):
    - self.agents        : 当前活跃 agent id 列表 (PettingZoo 规范, 基类维护)
    - self.agent_states  : {agent_id: SupplyChainAgent} 我们的 Agent 状态对象
"""

import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

# PettingZoo AECEnv (顺序决策环境)
from pettingzoo import AECEnv
from pettingzoo.utils import AgentSelector
from gymnasium import spaces


# ============================================================
# 1. 单个 Agent 的状态容器
# ============================================================

@dataclass
class SupplyChainAgent:
    """
    供应链单个 Agent 的内部状态

    维护:
        - 库存状态 (NS, WIP, pipeline)
        - 决策历史 (订单, 需求, 履约)
        - 情绪模块 (独立的 EmotionState 实例)
        - 局部观测构建
        - 协同信息广播缓冲区
    """
    agent_id: str             # 'retailer' / 'wholesaler' / 'distributor' / 'manufacturer'
    k: int                    # 层级 1=零售商 ... 4=制造商
    name: str                 # 中文名称

    # ---- 库存状态 ----
    net_stock: float = 0.0          # 净库存 NS
    pipeline: deque = field(default_factory=lambda: deque(maxlen=100))  # 在途货物 (L期后到达)

    # ---- 决策历史 ----
    order_placed: float = 0.0       # 本期向上游订货量
    incoming_demand: float = 0.0    # 本期收到下游订单
    fulfilled: float = 0.0          # 本期履约量
    stockout: float = 0.0           # 本期缺货量

    demand_history: deque = field(default_factory=lambda: deque(maxlen=10000))
    order_history: deque = field(default_factory=lambda: deque(maxlen=10000))
    fulfilled_history: deque = field(default_factory=lambda: deque(maxlen=10000))

    # ---- 情绪模块 (独立挂载) ----
    emotion: Optional[Any] = None    # EmotionState 实例 (由环境初始化时挂载)

    # ---- 协同信息广播缓冲 ----
    broadcast: Dict[str, Any] = field(default_factory=dict)
    # broadcast 可包含: 'forecast' (预测需求), 'inventory' (库存), 'emotion_label' (情绪)

    def reset(self, initial_inventory: float, L: int):
        """重置 Agent 到初始状态"""
        self.net_stock = initial_inventory
        self.pipeline = deque([0.0] * L, maxlen=L + 1)
        self.order_placed = 0.0
        self.incoming_demand = 0.0
        self.fulfilled = 0.0
        self.stockout = 0.0
        self.demand_history.clear()
        self.order_history.clear()
        self.fulfilled_history.clear()
        self.broadcast.clear()
        if self.emotion is not None:
            self.emotion.reset()

    def compute_bwe(self) -> float:
        """计算本节点的方差比 BWE = var(q) / var(D)"""
        if len(self.order_history) < 2 or len(self.demand_history) < 2:
            return 0.0
        var_q = float(np.var(list(self.order_history)))
        var_d = float(np.var(list(self.demand_history)))
        return var_q / var_d if var_d > 0 else 0.0


# ============================================================
# 2. 协同机制: 通信通道 (信息共享)
# ============================================================

class CommunicationChannel:
    """
    多智能体通信通道 (Information Sharing Channel)

    实现"协同机制", 允许 Agent 之间共享部分信息以缓解信息不对称。
    信息不对称是牛鞭效应的核心根源 (Lee et al., 1997)。

    共享模式 (可通过 config 配置):
        - 'forecast': 共享预测需求 (下游预测对上游可见)
        - 'inventory': 共享库存水平
        - 'emotion': 共享情绪标签 (用于协调决策)
        - 'none': 完全自私 (信息孤岛, 传统啤酒游戏)

    拓扑:
        - 'downstream_to_upstream': 仅下游→上游单向共享 (最符合实际)
        - 'all_to_all': 全互联共享 (理想协同)
        - 'none': 无通信
    """

    def __init__(self, topology: str = 'downstream_to_upstream',
                 share_modes: Optional[List[str]] = None):
        self.topology = topology  # 通信拓扑
        self.share_modes = share_modes or ['forecast']  # 默认仅共享预测
        # 共享信息池: {agent_id: {field: value}}
        self.shared_pool: Dict[str, Dict[str, Any]] = {}

    def broadcast(self, agent_id: str, info: Dict[str, Any]):
        """Agent 广播信息到共享池"""
        if agent_id not in self.shared_pool:
            self.shared_pool[agent_id] = {}
        for mode in self.share_modes:
            if mode in info:
                self.shared_pool[agent_id][mode] = info[mode]

    def reset(self):
        self.shared_pool.clear()


# ============================================================
# 3. PettingZoo AECEnv 多智能体供应链环境
# ============================================================

class MARLSupplyChainEnv(AECEnv):
    """
    多智能体供应链协同环境 (PettingZoo AECEnv)

    将四级供应链的每个节点定义为独立 Agent:
        - retailer (零售商, k=1)
        - wholesaler (批发商, k=2)
        - distributor (分销商, k=3)
        - manufacturer (制造商, k=4)

    每个 Agent 拥有独立:
        - 局部观测 (Local Observation)
        - 动作空间 (订货量)
        - 情绪模块 (EmotionState)

    协同机制:
        - CommunicationChannel 实现 Agent 间信息共享
        - 可共享: 预测需求 / 库存水平 / 情绪标签

    命名规范:
        - self.agents       : PettingZoo 活跃 agent id 列表 (基类规范)
        - self.agent_states : {agent_id: SupplyChainAgent} 我们的 Agent 状态对象
    """

    metadata = {"render_modes": [], "name": "marl_supply_chain_v1"}

    def __init__(self, config=None):
        """
        初始化 MARL 环境

        参数:
            config: 配置对象 (来自 config.py), 若 None 使用默认值
        """
        super().__init__()

        # ---- 解析配置 ----
        if config is not None:
            sc = config.supply_chain
            ic = config.idmr
            self.d = sc.d
            self.rho = sc.rho
            self.sigma_eps = sc.sigma_eps
            self.L = sc.L
            self.p = sc.p
            self.z = sc.z
            self.C_L_rho = sc.C_L_rho
            self.initial_inventory = sc.initial_inventory
            self.K = sc.K
            # 动作空间参数
            self.action_min = config.dqn.action_min
            self.action_max = config.dqn.action_max
            # 情绪参数
            self.enable_emotion = ic.enable_emotion
            self.emotion_alpha = ic.emotion_alpha
            self.emotion_gamma = ic.emotion_gamma
            self.emotion_w_stockout = ic.emotion_w_stockout
            self.emotion_w_match = ic.emotion_w_match
            self.emotion_w_excess = ic.emotion_w_excess
            # 奖励参数
            self.holding_weight = ic.reward_holding_weight
            self.stockout_penalty_weight = ic.stockout_penalty_weight
            self.enable_inventory_bonus = ic.enable_inventory_bonus
            self.inventory_bonus_weight = ic.inventory_bonus_weight
            self.coverage_lower = ic.coverage_lower
            self.coverage_upper = ic.coverage_upper
            self.bonus_sma_window = ic.sma_window
        else:
            # 默认参数 (与单智能体版本一致)
            self.d = 10
            self.rho = 0.5
            self.sigma_eps = 5.0
            self.L = 2
            self.p = 5
            self.z = 2
            self.C_L_rho = 2.0
            self.initial_inventory = 10.0
            self.K = 4
            self.action_min = 0
            self.action_max = 40
            # 情绪参数
            self.enable_emotion = True
            self.emotion_alpha = 0.7
            self.emotion_gamma = 2.0
            self.emotion_w_stockout = 1.0
            self.emotion_w_match = 0.5
            self.emotion_w_excess = 0.3
            # 奖励参数
            self.holding_weight = 0.0001
            self.stockout_penalty_weight = 1.0
            self.enable_inventory_bonus = True
            self.inventory_bonus_weight = 0.3
            self.coverage_lower = 0.8
            self.coverage_upper = 1.5
            self.bonus_sma_window = 5

        # ---- 仿真参数 ----
        self.total_periods = 20000  # 默认仿真周期
        self.max_cycles = self.total_periods

        # ---- Agent 定义 ----
        self.agent_ids = ['retailer', 'wholesaler', 'distributor', 'manufacturer']
        self.k_to_id = {1: 'retailer', 2: 'wholesaler',
                         3: 'distributor', 4: 'manufacturer'}
        self.id_to_k = {v: k for k, v in self.k_to_id.items()}
        self.agent_names = {'retailer': '零售商', 'wholesaler': '批发商',
                            'distributor': '分销商', 'manufacturer': '制造商'}

        # ---- 创建 Agent 状态对象 (独立于 PettingZoo 的 self.agents) ----
        self.agent_states: Dict[str, SupplyChainAgent] = {}
        for k in range(1, self.K + 1):
            aid = self.k_to_id[k]
            self.agent_states[aid] = SupplyChainAgent(
                agent_id=aid, k=k, name=self.agent_names[aid]
            )

        # ---- 为每个 Agent 挂载独立情绪模块 ----
        self._mount_emotion_modules()

        # ---- 协同机制: 通信通道 ----
        # 默认: 下游→上游单向共享预测需求
        self.comm_channel = CommunicationChannel(
            topology='downstream_to_upstream',
            share_modes=['forecast', 'inventory'],
        )

        # ---- 动态突发事件触发器 ----
        # 需求突变 / 供应中断 / 情绪传染
        from dynamic_events import DynamicEventTrigger
        self.event_trigger = DynamicEventTrigger(seed=42)
        # 是否启用动态事件 (可通过外部设置)
        self.enable_dynamic_events = True
        # 本周期事件记录 (供观测/info使用)
        self._current_cycle_events: Dict[str, Any] = {}

        # ---- PettingZoo 必需属性 ----
        self.possible_agents = list(self.agent_ids)
        self.agent_name_mapping = {aid: i for i, aid in enumerate(self.agent_ids)}

        # 动作空间: Discrete(action_max - action_min + 1) -> 订货量
        self._action_dim = self.action_max - self.action_min + 1
        self._action_spaces = {
            aid: spaces.Discrete(self._action_dim) for aid in self.agent_ids
        }

        # 观测空间: [NS, WIP, downstream_order, upstream_arrival,
        #            last_demand, emotion_E, shared_forecast, shared_inventory]
        self._obs_dim = 8
        self._observation_spaces = {
            aid: spaces.Box(low=-np.inf, high=np.inf,
                            shape=(self._obs_dim,), dtype=np.float32)
            for aid in self.agent_ids
        }

        # ---- 运行时状态 ----
        self.t = 0
        self.D_prev = self.d / (1 - self.rho)
        self.customer_demand_history: List[float] = []
        self.rewards: Dict[str, float] = {}
        self._cumulative_rewards: Dict[str, float] = {}
        self.terminations: Dict[str, bool] = {}
        self.truncations: Dict[str, bool] = {}
        self.infos: Dict[str, Dict[str, Any]] = {}
        self._agent_selector: Optional[AgentSelector] = None
        self.agent_selection: Optional[str] = None
        # self.agents 由基类维护 (活跃 agent id 列表), 初始化为空
        self.agents: List[str] = []

    # ============================================================
    # 情绪模块挂载 (核心: 每个 Agent 独立情绪)
    # ============================================================

    def _mount_emotion_modules(self):
        """
        为每个 Agent 挂载独立的 EmotionState 实例

        关键点:
            - 每个 Agent 的情绪参数可独立配置
            - 情绪演化相互独立 (零售商恐慌 ≠ 制造商恐慌)
            - 支持后续研究: 不同节点情绪敏感度差异化
        """
        if not self.enable_emotion:
            for aid in self.agent_ids:
                self.agent_states[aid].emotion = None
            return

        from emotion_module import EmotionState

        # 每个节点挂载独立情绪模块
        # 注: 可在此处对不同 agent 设置不同参数 (如制造商情绪更稳定)
        for aid in self.agent_ids:
            self.agent_states[aid].emotion = EmotionState(
                alpha=self.emotion_alpha,
                gamma=self.emotion_gamma,
                w_stockout=self.emotion_w_stockout,
                w_match=self.emotion_w_match,
                w_excess=self.emotion_w_excess,
            )

    # ============================================================
    # PettingZoo AECEnv 标准接口
    # ============================================================

    def observation_space(self, agent: str):
        return self._observation_spaces[agent]

    def action_space(self, agent: str):
        return self._action_spaces[agent]

    # ============================================================
    # 环境核心逻辑
    # ============================================================

    def _generate_demand(self) -> float:
        """生成顾客需求 AR(1): D_t = d + ρ·D_{t-1} + ε_t"""
        eps = self.rng.normal(0, self.sigma_eps)
        D_t = self.d + self.rho * self.D_prev + eps
        D_t = max(0, D_t)
        self.D_prev = D_t
        return D_t

    def _build_local_observation(self, agent_id: str) -> np.ndarray:
        """
        构建 Agent 的局部观测

        观测维度 (8维):
            [0] NS:                自身净库存 (归一化 /100)
            [1] WIP:               自身在途库存 (归一化 /100)
            [2] downstream_order:  下游订单 (归一化 /50)
            [3] upstream_arrival:  本期到货量 (归一化 /50)
            [4] last_demand:       上期需求 (归一化 /50)
            [5] emotion_E:         情绪状态 E_t ∈ [-1, 1]
            [6] shared_forecast:   下游共享的预测需求 (归一化 /50)
            [7] shared_inventory:  下游共享的库存水平 (归一化 /100)

        协同信息 ([6][7]) 来自 CommunicationChannel,
        若无共享则为 0 (信息不对称).
        """
        agent = self.agent_states[agent_id]
        k = agent.k

        # [0] 自身净库存
        ns = agent.net_stock / 100.0

        # [1] 在途库存
        wip = (sum(agent.pipeline) if agent.pipeline else 0.0) / 100.0

        # [2] 下游订单 (本期收到的需求)
        downstream_order = agent.incoming_demand / 50.0

        # [3] 本期到货 (pipeline 第一项)
        upstream_arrival = (agent.pipeline[0]
                            if len(agent.pipeline) > 0 else 0.0) / 50.0

        # [4] 上期需求
        last_demand = (list(agent.demand_history)[-1]
                       if len(agent.demand_history) > 0 else 0.0) / 50.0

        # [5] 情绪状态
        emotion_E = float(agent.emotion.E) if agent.emotion is not None else 0.0

        # [6][7] 协同信息: 从通信通道接收下游共享信息
        shared_forecast = 0.0
        shared_inventory = 0.0
        downstream_id = self.k_to_id.get(k - 1)  # k-1 为下游
        if downstream_id is not None:
            received = self.comm_channel.shared_pool.get(downstream_id, {})
            shared_forecast = received.get('forecast', 0.0) / 50.0
            shared_inventory = received.get('inventory', 0.0) / 100.0

        obs = np.array([
            ns, wip, downstream_order, upstream_arrival,
            last_demand, emotion_E, shared_forecast, shared_inventory
        ], dtype=np.float32)
        return obs

    def _compute_reward(self, agent_id: str) -> float:
        """
        计算 Agent 奖励 (受情绪调节)

        奖励 = fill_rate                       # 服务水平收益
             + inventory_bonus                  # [创新] 库存精准匹配正向激励 (情绪调节)
             - stockout_penalty                 # 缺货刚性惩罚 (情绪调节)
             - holding_penalty                  # 库存积压软惩罚

        情绪调节:
            恐慌(E<0): 放大缺货惩罚 → stockout_weight_eff = base·(1+|E|)
            乐观(E>0): 放大正向激励 → bonus_weight_eff = base·(1+E)
        """
        agent = self.agent_states[agent_id]
        demand = agent.incoming_demand
        fulfilled = agent.fulfilled
        stockout = agent.stockout
        ns_after = agent.net_stock

        # ---- 1. 服务水平收益 ----
        if demand > 0:
            fill_rate = fulfilled / demand
        else:
            fill_rate = 1.0

        # ---- 2. 库存精准匹配正向激励 ----
        inventory_bonus = 0.0
        match_factor = 0.0
        excess_rate = 0.0
        if self.enable_inventory_bonus:
            recent = list(agent.demand_history)[-self.bonus_sma_window:]
            if len(recent) >= 2:
                forecast_next = float(np.mean(recent))
                lower_b = self.coverage_lower * forecast_next
                upper_b = self.coverage_upper * forecast_next
                if ns_after >= lower_b and ns_after <= upper_b and forecast_next > 0:
                    match_ratio = ns_after / forecast_next
                    match_factor = max(0.0, 1.0 - abs(match_ratio - 1.0))
                    deviation = abs(match_ratio - 1.0)
                    max_dev = max(1.0 - self.coverage_lower,
                                  self.coverage_upper - 1.0)
                    bonus_factor = 1.0 - (deviation / max_dev) if max_dev > 0 else 1.0
                    inventory_bonus = self.inventory_bonus_weight * max(0, bonus_factor)
                if forecast_next > 0:
                    excess_rate = max(0.0, (ns_after - upper_b) / forecast_next)

        # ---- 3. 缺货率 ----
        stockout_rate = stockout / demand if demand > 0 else 0.0

        # ---- 3.5 情绪演化与权重调节 ----
        if agent.emotion is not None:
            agent.emotion.update(
                stockout_rate=stockout_rate,
                match_factor=match_factor,
                excess_rate=excess_rate,
            )
            em_w = agent.emotion.get_reward_weights(
                base_stockout_weight=self.stockout_penalty_weight,
                base_bonus_weight=self.inventory_bonus_weight,
            )
            eff_stockout_w = em_w['stockout_weight']
            eff_bonus_w = em_w['bonus_weight']
            if match_factor > 0:
                inventory_bonus = eff_bonus_w * match_factor
        else:
            eff_stockout_w = self.stockout_penalty_weight

        stockout_penalty = eff_stockout_w * stockout_rate
        holding_penalty = self.holding_weight * max(0, ns_after)

        reward = fill_rate + inventory_bonus - stockout_penalty - holding_penalty
        return float(reward)

    def _process_action(self, agent_id: str, action: int):
        """
        处理 Agent 动作 (订单流转 + 履约 + 情绪更新)

        事件顺序:
            1. 收到上游 L 期前的到货
            2. 满足下游需求 (履约/缺货)
            3. 记录向上游订货量
            4. 订单放入 pipeline (L 期后到自己)
            5. 广播协同信息 (预测/库存/情绪)
        """
        agent = self.agent_states[agent_id]
        k = agent.k

        # Step 1: 收到上游到货
        arrived = agent.pipeline[0] if len(agent.pipeline) > 0 else 0.0
        # 制造商(k=K)应用供应中断: 断供期间到货归零
        if self.enable_dynamic_events and k == self.K:
            arrived = self.event_trigger.apply_supply_disruption(arrived)
        agent.net_stock += arrived
        if len(agent.pipeline) > 0:
            agent.pipeline.popleft()

        # Step 2: 满足下游需求
        demand = agent.incoming_demand
        fulfilled = min(max(agent.net_stock, 0), demand)
        agent.net_stock -= fulfilled
        agent.fulfilled = fulfilled
        agent.stockout = max(0, demand - fulfilled)
        agent.demand_history.append(demand)
        agent.fulfilled_history.append(fulfilled)

        # Step 3: 记录订货量 (动作映射)
        # Discrete 动作 -> 连续订货量
        action_clipped = int(np.clip(action, 0, self._action_dim - 1))
        q_t = float(self.action_min + action_clipped)
        agent.order_placed = q_t
        agent.order_history.append(q_t)

        # Step 4: 订单放入 pipeline (L 期后到自己)
        agent.pipeline.append(q_t)

        # Step 5: 订单向上游传递 (上游的下游需求 = 本节点订单)
        if k < self.K:
            upstream_id = self.k_to_id[k + 1]
            self.agent_states[upstream_id].incoming_demand = q_t
        # 制造商上游无限, 不传递

        # Step 6: 广播协同信息
        # 预测下期需求 (SMA)
        if len(agent.demand_history) >= self.p:
            forecast = float(np.mean(list(agent.demand_history)[-self.p:]))
        else:
            forecast = demand
        # 情绪标签
        emotion_label = ''
        if agent.emotion is not None:
            em_w = agent.emotion.get_reward_weights(
                self.stockout_penalty_weight, self.inventory_bonus_weight)
            emotion_label = em_w['emotion_label']

        self.comm_channel.broadcast(agent_id, {
            'forecast': forecast,
            'inventory': agent.net_stock,
            'emotion_label': emotion_label,
        })

    # ============================================================
    # PettingZoo 标准接口: reset / step / last / observe
    # ============================================================

    def reset(self, seed: Optional[int] = None, options: Optional[Dict] = None):
        """
        重置环境

        参数:
            seed: 随机种子
            options: 可包含 'max_cycles' 覆盖默认仿真周期
        """
        # 注意: AECEnv.reset 不调用 super().reset() (PettingZoo 1.26 规范)
        self.rng = np.random.default_rng(seed)
        self.t = 0
        self.D_prev = self.d / (1 - self.rho)
        self.customer_demand_history = []

        if options is not None and 'max_cycles' in options:
            self.max_cycles = options['max_cycles']

        # 重置所有 Agent 状态对象
        for aid in self.agent_ids:
            self.agent_states[aid].reset(self.initial_inventory, self.L)

        # 重置通信通道
        self.comm_channel.reset()

        # 重置动态事件触发器
        if self.enable_dynamic_events:
            self.event_trigger.reset(seed=seed)
        self._current_cycle_events = {}

        # 重置 PettingZoo 状态
        self.agents = list(self.possible_agents)  # 活跃 agent id 列表
        self.rewards = {aid: 0.0 for aid in self.agents}
        self._cumulative_rewards = {aid: 0.0 for aid in self.agents}
        self.terminations = {aid: False for aid in self.agents}
        self.truncations = {aid: False for aid in self.agents}
        self.infos = {aid: {} for aid in self.agents}

        self._agent_selector = AgentSelector(self.agents)
        self.agent_selection = self._agent_selector.reset()

        # 生成第一期顾客需求 (零售商的下游需求)
        D_t = self._generate_demand()
        self.customer_demand_history.append(D_t)
        self.agent_states['retailer'].incoming_demand = D_t

    def step(self, action):
        """
        执行当前选中 Agent 的动作

        参数:
            action: Discrete 动作 (订货量索引)
        """
        if (self.terminations[self.agent_selection]
                or self.truncations[self.agent_selection]
                or not self.agents):
            self._was_dead_step(action)
            return

        current_agent = self.agent_selection

        # 处理动作 (订单流转 + 履约 + 情绪更新)
        self._process_action(current_agent, action)

        # 计算当前 Agent 的奖励
        reward = self._compute_reward(current_agent)
        self.rewards[current_agent] = reward
        self._cumulative_rewards[current_agent] += reward

        # 信息记录
        ag = self.agent_states[current_agent]
        self.infos[current_agent] = {
            't': self.t,
            'agent': current_agent,
            'order': ag.order_placed,
            'demand': ag.incoming_demand,
            'fulfilled': ag.fulfilled,
            'stockout': ag.stockout,
            'net_stock': ag.net_stock,
            'emotion_E': (float(ag.emotion.E)
                          if ag.emotion is not None else 0.0),
        }

        # 选择下一个 Agent
        if self._agent_selector is not None:
            self.agent_selection = self._agent_selector.next()

        # 一个完整周期 (4 个 agent 都决策完) 后推进时间
        if self._agent_selector is not None and self._agent_selector.is_last():
            self.t += 1

            # ---- 动态突发事件触发 ----
            if self.enable_dynamic_events:
                # 触发本周期事件 (需求突变/供应中断)
                self._current_cycle_events = self.event_trigger.step(self.t)
                # 情绪传染: 检查各节点严重缺货, 以概率传染上游
                contagions = self.event_trigger.apply_emotion_contagion(
                    self.agent_states, self.k_to_id, self.id_to_k)
                if contagions:
                    self._current_cycle_events['emotion_contagion'] = contagions

            # 生成下一期顾客需求 (应用需求突变)
            D_next = self._generate_demand()
            if self.enable_dynamic_events:
                D_next = self.event_trigger.apply_demand_shock(D_next)
            self.customer_demand_history.append(D_next)
            self.agent_states['retailer'].incoming_demand = D_next

            # 截断判断
            if self.t >= self.max_cycles:
                for aid in self.agents:
                    self.truncations[aid] = True

        self._accumulate_rewards()

    def _accumulate_rewards(self):
        """累积奖励 (PettingZoo 规范: 每步后其他 agent 奖励累积)"""
        # 简化: 仅当前 agent 获得奖励, 其他清零
        for aid in self.agents:
            if aid != self.agent_selection:
                self.rewards[aid] = 0.0

    def _was_dead_step(self, action):
        """处理已终止 agent 的 step (PettingZoo 规范)"""
        if action is not None:
            raise ValueError("when an agent is terminated/truncated, "
                             "action must be None")
        agent = self.agent_selection
        del self.terminations[agent]
        del self.truncations[agent]
        del self.rewards[agent]
        del self._cumulative_rewards[agent]
        del self.infos[agent]
        self.agents.remove(agent)
        if self.agents:
            self.agent_selection = self._agent_selector.next()
        else:
            self.agent_selection = None

    def last(self):
        """返回当前 agent 的 (obs, reward, termination, truncation, info)"""
        agent = self.agent_selection
        obs = self._build_local_observation(agent) if agent is not None else None
        return (obs,
                self.rewards.get(agent, 0.0) if agent is not None else 0.0,
                self.terminations.get(agent, False) if agent is not None else True,
                self.truncations.get(agent, False) if agent is not None else True,
                self.infos.get(agent, {}) if agent is not None else {})

    def observe(self, agent: str) -> np.ndarray:
        """返回指定 agent 的观测"""
        return self._build_local_observation(agent)

    def render(self):
        """打印当前环境状态"""
        print(f"\n=== t={self.t} ===")
        for aid in self.agent_ids:
            ag = self.agent_states[aid]
            E = float(ag.emotion.E) if ag.emotion is not None else 0.0
            print(f"  [{ag.name}] NS={ag.net_stock:.2f} WIP={sum(ag.pipeline):.2f} "
                  f"order={ag.order_placed:.2f} demand={ag.incoming_demand:.2f} "
                  f"fulfilled={ag.fulfilled:.2f} stockout={ag.stockout:.2f} "
                  f"E={E:+.3f}")

    def close(self):
        pass

    # ============================================================
    # 评估工具
    # ============================================================

    def compute_bullwhip(self) -> Dict[str, float]:
        """计算各节点方差比 BWE = var(q) / var(D)"""
        var_D = (float(np.var(self.customer_demand_history))
                 if len(self.customer_demand_history) > 1 else 0)
        bwe = {}
        for aid in self.agent_ids:
            ag = self.agent_states[aid]
            orders = list(ag.order_history)
            if len(orders) > 1:
                bwe[aid] = float(np.var(orders)) / var_D if var_D > 0 else 0.0
            else:
                bwe[aid] = 0.0
        return bwe

    def compute_service_levels(self) -> Dict[str, float]:
        """计算各节点平均服务水平 SL = mean(fulfilled/demand)"""
        sl = {}
        for aid in self.agent_ids:
            ag = self.agent_states[aid]
            if len(ag.fulfilled_history) > 0:
                fulfilled = np.array(list(ag.fulfilled_history))
                demands = np.array(list(ag.demand_history))
                mask = demands > 0
                if mask.sum() > 0:
                    sl[aid] = float(np.mean(fulfilled[mask] / demands[mask]))
                else:
                    sl[aid] = 1.0
            else:
                sl[aid] = 0.0
        return sl

    def get_emotion_stats(self) -> Dict[str, Dict]:
        """获取各 Agent 的情绪统计"""
        stats = {}
        for aid in self.agent_ids:
            ag = self.agent_states[aid]
            if ag.emotion is not None:
                stats[aid] = ag.emotion.get_stats()
            else:
                stats[aid] = {'current_emotion': 0.0, 'enabled': False}
        return stats


# ============================================================
# 自检: 验证 MARL 环境可运行
# ============================================================

if __name__ == '__main__':
    print("=" * 70)
    print("MARL 供应链协同环境 - 自检")
    print("=" * 70)

    # 创建环境 (使用默认配置)
    env = MARLSupplyChainEnv(config=None)
    # 提高事件概率以便观察 (默认概率很低)
    env.enable_dynamic_events = True
    env.event_trigger.demand_shock_prob = 0.15      # 15% 需求突变
    env.event_trigger.supply_disruption_prob = 0.10  # 10% 供应中断
    env.event_trigger.contagion_prob = 0.5           # 50% 情绪传染
    env.event_trigger.contagion_strength = 0.5
    print(f"\n[环境] Agent 列表: {env.possible_agents}")
    print(f"[环境] 动作空间: Discrete({env._action_dim}) (订货量 {env.action_min}~{env.action_max})")
    print(f"[环境] 观测维度: {env._obs_dim}")
    print(f"[环境] 情绪模块: {'启用' if env.enable_emotion else '关闭'}")
    print(f"[环境] 动态事件: {'启用' if env.enable_dynamic_events else '关闭'}")

    # 验证每个 Agent 挂载了独立情绪模块
    print("\n[验证] 各 Agent 情绪模块挂载:")
    for aid in env.agent_ids:
        ag = env.agent_states[aid]
        em_status = f"已挂载 (E_init={ag.emotion.E:.2f})" if ag.emotion else "未挂载"
        print(f"  {aid:12s} ({ag.name}): {em_status}")

    # 运行 15 个周期 (增加周期以观察动态事件)
    print("\n[运行] 模拟 15 个周期 (随机动作, 高事件概率):")
    env.reset(seed=42)
    cycle = 0
    contagion_total = 0
    for agent in env.agent_iter():
        obs, reward, term, trunc, info = env.last()
        if term or trunc:
            env.step(None)
            continue
        # 随机动作
        action = env.action_space(agent).sample()
        env.step(action)

        # 每周期结束打印状态 + 动态事件
        if info.get('t', 0) > cycle:
            cycle = info['t']
            # 统计本周期情绪传染
            conts = env._current_cycle_events.get('emotion_contagion', [])
            contagion_total += len(conts)
            if cycle <= 15:
                ev_flag = ''
                if env._current_cycle_events.get('demand_shock'):
                    mult = env._current_cycle_events.get('demand_multiplier', 1.0)
                    ev_flag += f' [需求突变x{mult:.1f}]'
                if env._current_cycle_events.get('supply_disruption'):
                    rem = env._current_cycle_events.get('disruption_remaining', 0)
                    ev_flag += f' [断供剩{rem}]'
                if conts:
                    ev_flag += f' [情绪传染x{len(conts)}]'
                print(f"\n  --- 周期 {cycle}{ev_flag} ---")
                for aid in env.agent_ids:
                    ag = env.agent_states[aid]
                    E = float(ag.emotion.E) if ag.emotion else 0.0
                    print(f"  {ag.name}: NS={ag.net_stock:.2f} order={ag.order_placed:.2f} "
                          f"fulfilled={ag.fulfilled:.2f} stockout={ag.stockout:.2f} E={E:+.3f}")
        if cycle >= 15:
            break

    # 评估指标
    print("\n[评估] 情绪统计:")
    em_stats = env.get_emotion_stats()
    for aid, st in em_stats.items():
        print(f"  {aid:12s}: E={st.get('current_emotion', 0):+.3f} "
              f"mean={st.get('mean_emotion', 0):+.3f} "
              f"vol={st.get('emotion_volatility', 0):.3f}")

    print("\n[评估] 动态事件统计:")
    ev_stats = env.event_trigger.get_stats()
    print(f"  需求突变次数: {ev_stats['demand_shock_count']}")
    print(f"  供应中断次数: {ev_stats['supply_disruption_count']}")
    print(f"  情绪传染次数: {ev_stats['contagion_count']} (本轮累计: {contagion_total})")
    print(f"  事件日志总数: {ev_stats['total_events']}")

    print("\n[评估] 协同信息池 (最后一周期):")
    for aid, info in env.comm_channel.shared_pool.items():
        print(f"  {aid:12s}: forecast={info.get('forecast', 0):.2f} "
              f"inventory={info.get('inventory', 0):.2f} "
              f"emotion={info.get('emotion_label', '-')}")

    print("\n" + "=" * 70)
    print("[OK] MARL 环境自检通过 (含动态事件)!")
    print("=" * 70)

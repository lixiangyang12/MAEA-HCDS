"""
持续学习 IDMR (Continual Learning IDMR)
=======================================

将"持续学习"机制集成到 IDMR 智慧决策机器人:

    1. 优先级经验回放 (PER):
       用 PrioritizedReplayBuffer 替代普通 ReplayBuffer,
       优先采样"情绪波动剧烈"或"严重缺货"的样本

    2. 情感增强价值网络:
       将情绪状态 E_t 作为第 6 维特征输入到 Q 网络,
       使机器人在面对类似情绪触发条件时能更快做出最优决策

    3. 弹性权重巩固 (EWC):
       在任务切换后, 对"旧任务重要参数"施加正则约束,
       防止学习新动态时发生灾难性遗忘

理论依据:
    - Schaul et al., 2015 (PER)
    - Kirkpatrick et al., 2017 (EWC)
    - 情感增强学习: 将情感状态作为强化学习的额外输入维度

设计原则:
    - 继承现有 IDMRAgent 和 IDMRSupplyChainEnv, 不破坏原代码
    - 通过开关 (use_per / emotion_augmented / use_ewc) 控制特性
    - 向后兼容: 关闭开关后行为与原版一致
"""

import numpy as np
import random
from typing import Dict, List, Optional, Any, Tuple

from idmr_agent import (
    IDMRAgent, IDMRSupplyChainEnv, QNetwork, train_idmr,
)
from prioritized_replay import PrioritizedReplayBuffer
from ewc import EWCRegularizer


# ============================================================
# 持续学习 IDMR 智能体 (扩展 IDMRAgent)
# ============================================================

class ContinualIDMRAgent(IDMRAgent):
    """
    持续学习 IDMR 智能体

    新增特性 (可通过开关控制):
        - emotion_augmented:  将情绪 E_t 加入 Q 网络输入 (state_dim 5→6)
        - use_per:            使用优先级经验回放 (含情绪权重)
        - use_ewc:            启用 EWC 正则化 (任务切换后)

    继承关系:
        ContinualIDMRAgent → IDMRAgent
        Q 网络: 共享 QNetwork 类, 但 state_dim=6 (启用 emotion_augmented)
    """

    def __init__(self,
                 state_dim: int = 6,           # 6 = 5(原状态) + 1(情绪)
                 action_min: int = 11,
                 action_max: int = 40,
                 # DQN 超参数
                 lr: float = 1e-3, gamma: float = 0.9, batch_size: int = 32,
                 replay_size: int = 20000, replay_start: int = 100,
                 epsilon_start: float = 1.0, epsilon_end: float = 0.01,
                 target_update_start: int = 400, target_update_freq: int = 10,
                 # 持续学习特性开关
                 emotion_augmented: bool = True,
                 use_per: bool = True,
                 use_ewc: bool = False,
                 # PER 参数
                 per_alpha: float = 0.6,
                 per_beta: float = 0.4,
                 per_beta_annealing: float = 0.0001,
                 per_emotion_weight: float = 0.3,
                 # EWC 参数
                 ewc_lambda: float = 400.0,
                 # 情绪感知噪声 (模拟机器人对情绪的误判)
                 emotion_noise_std: float = 0.0):
        """
        参数:
            emotion_augmented:    是否将情绪 E_t 加入 Q 网络输入
            use_per:              是否启用优先级经验回放
            use_ewc:              是否启用 EWC 正则化
            per_*:                PER 超参数
            ewc_lambda:           EWC 正则强度
            emotion_noise_std:    情绪感知噪声标准差 (σ_noise).
                                  机器人感知到的情绪 E_perceived = clip(E_true + N(0, σ), -1, 1).
                                  σ=0 表示完美感知; σ=0.15 表示典型误判水平.
                                  真实情绪仍用于环境动力学 (演化/传染) 和 PER 优先级,
                                  仅 Q 网络输入的第 6 维使用感知情绪.
        """
        # 调用父类初始化 (创建 q_net, target_net, buffer)
        super().__init__(
            state_dim=state_dim, action_min=action_min, action_max=action_max,
            lr=lr, gamma=gamma, batch_size=batch_size,
            replay_size=replay_size, replay_start=replay_start,
            epsilon_start=epsilon_start, epsilon_end=epsilon_end,
            target_update_start=target_update_start,
            target_update_freq=target_update_freq,
        )

        # 持续学习特性开关
        self.emotion_augmented = emotion_augmented
        self.use_per = use_per
        self.use_ewc = use_ewc
        # 情绪感知噪声 (模拟机器人误判情绪)
        self.emotion_noise_std = float(emotion_noise_std)
        # 统计: 累计感知误差 (供论文分析)
        self._perception_errors: List[float] = []

        # 替换为优先级经验回放池
        if self.use_per:
            self.per_buffer = PrioritizedReplayBuffer(
                capacity=replay_size,
                alpha=per_alpha,
                beta=per_beta,
                beta_annealing=per_beta_annealing,
                emotion_weight=per_emotion_weight,
            )
            # 屏蔽原 buffer 的使用
            self.buffer = None
        else:
            self.per_buffer = None

        # EWC 正则化器
        if self.use_ewc:
            self.ewc = EWCRegularizer()
            self.ewc_lambda = ewc_lambda
        else:
            self.ewc = None

        # 缓存最近一次的样本情绪信息 (用于 PER 更新)
        self._last_emotion_Es: Optional[np.ndarray] = None
        self._last_stockout_rates: Optional[np.ndarray] = None
        self._last_tree_indices: Optional[List[int]] = None
        self._last_is_weights: Optional[np.ndarray] = None

        # 训练统计
        self.ewc_losses = []
        self.task_id: int = 0  # 当前任务编号

    # ============================================================
    # 情感增强状态构建
    # ============================================================

    def get_state_with_emotion(self, env, k: int = 3, emotion_E: float = 0.0) -> np.ndarray:
        """
        构建情感增强状态向量 (6 维)

        s_t = [S, WIP, q_downstream, trans, q_self, E_perceived]

        其中 E_perceived 为机器人"感知"到的情绪 (可能含噪声误判):
            E_perceived = clip(E_true + N(0, σ_noise), -1, 1)

        注意:
            - 真实情绪 E_true 仍用于环境动力学 (演化方程/传染) 和 PER 优先级
            - 仅 Q 网络输入的第 6 维使用感知情绪, 模拟机器人对情绪的不完美感知
            - σ_noise=0 时退化为完美感知

        参数:
            env:       供应链环境
            k:         节点编号 (默认 k=3 分销商)
            emotion_E: 真实情绪值 E_true (由情绪模块计算)
        """
        if not self.emotion_augmented:
            # 关闭情绪增强时, 退化为父类的 5 维状态
            return self.get_state(env, k)

        node = env.nodes[k]
        upstream_node = env.nodes[k - 1] if k > 1 else None

        # 原 5 维状态 (与父类一致)
        s_stock = node.net_stock / 100.0
        wip = (sum(node.pipeline) if node.pipeline else 0.0) / 100.0
        q_downstream = (upstream_node.order_placed if upstream_node else 0.0) / 50.0
        trans = (node.pipeline[0] if len(node.pipeline) > 0 else 0.0) / 50.0
        q_self = node.order_placed / 50.0

        # 第 6 维: 情绪感知 (含噪声, 模拟机器人误判)
        true_emotion = float(emotion_E)
        if self.emotion_noise_std > 0:
            noise = float(np.random.normal(0.0, self.emotion_noise_std))
            perceived_emotion = float(np.clip(true_emotion + noise, -1.0, 1.0))
            # 记录感知误差 (供论文分析)
            self._perception_errors.append(perceived_emotion - true_emotion)
        else:
            perceived_emotion = true_emotion

        state = np.array([s_stock, wip, q_downstream, trans, q_self, perceived_emotion],
                         dtype=np.float32)
        return state

    # ============================================================
    # 经验存储 (含情绪元数据, 支持 PER)
    # ============================================================

    def store_transition_with_emotion(self, s, a, r, s_next, done,
                                        emotion_E: float = 0.0,
                                        stockout_rate: float = 0.0,
                                        is_contagion: bool = False):
        """
        存储经验 (含情绪元数据)

        若启用 PER: 使用优先级回放池, 优先级由 |TD| + 情绪权重 决定
        若未启用:   退化为父类普通存储
        """
        if self.use_per and self.per_buffer is not None:
            self.per_buffer.push(
                s, a, r, s_next, done,
                td_error=0.0,  # 新样本 TD=0, 后续训练时更新
                emotion_E=emotion_E,
                stockout_rate=stockout_rate,
                is_contagion=is_contagion,
            )
        else:
            # 退化为父类的普通存储
            super().store_transition(s, a, r, s_next, done)

    def __len__(self):
        if self.use_per and self.per_buffer is not None:
            return len(self.per_buffer)
        return len(self.buffer) if self.buffer else 0

    # ============================================================
    # DQN 更新 (集成 PER + EWC)
    # ============================================================

    def update(self):
        """
        DQN 梯度下降更新 (集成 PER 和 EWC)

        相比父类 update() 的改进:
            1. PER: 优先级采样 + IS 权重补偿 + 训练后更新优先级
            2. EWC: 在损失中加入正则项 L_ewc = λ * Σ F * (θ-θ*)²
        """
        # 检查回放池大小
        if self.use_per and self.per_buffer is not None:
            buffer_size = len(self.per_buffer)
        else:
            buffer_size = len(self.buffer) if self.buffer else 0
        if buffer_size < self.replay_start:
            return None

        # ---- 采样 ----
        if self.use_per and self.per_buffer is not None:
            (states, actions, rewards, next_states, dones,
             emotion_Es, stockout_rates, tree_indices, is_weights) = self.per_buffer.sample(self.batch_size)
        else:
            states, actions, rewards, next_states, dones = self.buffer.sample(self.batch_size)
            emotion_Es = np.zeros(self.batch_size, dtype=np.float32)
            stockout_rates = np.zeros(self.batch_size, dtype=np.float32)
            tree_indices = None
            is_weights = np.ones(self.batch_size, dtype=np.float32)

        # 动作索引
        actions_idx = np.clip(actions - self.action_min, 0, self.action_dim - 1)

        # ---- 前向传播 ----
        q_all = self.q_net.forward(states)
        q_values = q_all[np.arange(self.batch_size), actions_idx]

        # ---- 目标 Q 值 ----
        next_q = self.target_net.forward(next_states)
        next_q_max = np.max(next_q, axis=1)
        target = rewards + self.gamma * next_q_max * (1 - dones)

        # ---- TD 误差 ----
        td_error = q_values - target

        # ---- 损失 (PER 使用 IS 权重) ----
        # weighted MSE: L = mean(w_i * (q_i - target_i)²)
        loss = float(np.mean(is_weights * td_error ** 2))

        # ---- EWC 正则损失 ----
        ewc_loss = 0.0
        if self.use_ewc and self.ewc is not None and self.ewc.is_consolidated:
            ewc_loss = self.ewc.compute_ewc_loss(self.q_net)
            self.ewc_losses.append(ewc_loss)

        # ---- 反向传播 ----
        grad_q = np.zeros_like(q_all)
        # PER: 梯度乘以 IS 权重
        grad_q[np.arange(self.batch_size), actions_idx] = (
            2.0 * is_weights * td_error / self.batch_size
        )

        grads = self.q_net.backward(grad_q, self.batch_size)

        # EWC: 梯度合并
        if self.use_ewc and self.ewc is not None and self.ewc.is_consolidated:
            ewc_grads = self.ewc.compute_ewc_gradient(self.q_net)
            for name in ['W1', 'b1', 'W2', 'b2', 'W3', 'b3']:
                grads[name] = grads[name] + ewc_grads[name]

        # 参数更新
        self.q_net.adam_update(grads)

        # ---- PER: 更新样本优先级 ----
        if self.use_per and tree_indices is not None:
            self.per_buffer.update_priorities(
                tree_indices,
                td_errors=td_error.detach().numpy() if hasattr(td_error, 'detach')
                          else np.array(td_error),
                emotion_Es=emotion_Es,
                stockout_rates=stockout_rates,
            )

        # ---- 目标网络更新 ----
        self.step_count += 1
        if self.step_count >= self.target_update_start and \
                self.step_count % self.target_update_freq == 0:
            self.target_net.load_params(self.q_net.get_params())

        self.losses.append(loss)
        return loss

    # ============================================================
    # EWC 巩固接口
    # ============================================================

    def consolidate_knowledge(self, lambda_reg: float = 400.0,
                              n_samples: int = 200) -> bool:
        """
        在任务切换前调用: 保存当前参数为锚点, 计算 Fisher 矩阵

        参数:
            lambda_reg: EWC 正则强度
            n_samples:  Fisher 计算样本数
        """
        if not self.use_ewc or self.ewc is None:
            return False

        # 从回放池采样旧任务数据
        if self.use_per and self.per_buffer is not None and len(self.per_buffer) > 0:
            n = min(n_samples, len(self.per_buffer))
            (states, actions, _, _, _, _, _, _, _) = self.per_buffer.sample(n)
        elif self.buffer is not None and len(self.buffer) > 0:
            n = min(n_samples, len(self.buffer))
            states, actions, _, _, _ = self.buffer.sample(n)
        else:
            return False

        # 将原始动作值 [action_min, action_max] 映射到索引 [0, action_dim-1]
        # EWC 需要动作索引来定位 Q 网络输出维度
        actions_idx = np.clip(actions - self.action_min, 0, self.action_dim - 1)

        # 巩固
        self.ewc.consolidate(self.q_net, states, actions_idx,
                              lambda_reg=lambda_reg, n_samples=n_samples)
        self.task_id += 1
        return True

    def get_continual_stats(self) -> Dict[str, Any]:
        """获取持续学习统计信息"""
        stats = {
            'task_id': self.task_id,
            'emotion_augmented': self.emotion_augmented,
            'use_per': self.use_per,
            'use_ewc': self.use_ewc,
            'emotion_noise_std': self.emotion_noise_std,
            'buffer_size': len(self),
            'recent_loss': float(self.losses[-1]) if self.losses else 0.0,
        }
        # 情绪感知误差统计
        if self._perception_errors:
            errs = np.array(self._perception_errors)
            stats['perception_error_mean'] = float(np.mean(errs))
            stats['perception_error_std'] = float(np.std(errs))
            stats['perception_error_mae'] = float(np.mean(np.abs(errs)))
        if self.use_ewc and self.ewc is not None:
            stats['ewc_consolidated'] = self.ewc.is_consolidated
            if self.ewc.is_consolidated:
                stats['ewc_recent_loss'] = float(self.ewc_losses[-1]) if self.ewc_losses else 0.0
                stats.update(self.ewc.get_stats())
        return stats


# ============================================================
# 持续学习供应链环境 (扩展 IDMRSupplyChainEnv)
# ============================================================

class ContinualIDMRSupplyChainEnv(IDMRSupplyChainEnv):
    """
    持续学习供应链环境

    在原 IDMRSupplyChainEnv 基础上:
        1. 记录每步的情绪值和缺货率 (用于 PER 优先级)
        2. 支持任务切换 (动态修改需求参数 rho/sigma)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 任务上下文
        self.task_id: int = 0
        self.task_name: str = "stable_demand"
        # 当前周期的情绪和缺货率 (供 agent 存储经验时使用)
        self._current_emotion_E: float = 0.0
        self._current_stockout_rate: float = 0.0
        self._current_is_contagion: bool = False

    def switch_task(self, task_name: str,
                    rho: Optional[float] = None,
                    sigma_eps: Optional[float] = None):
        """
        切换任务 (动态修改需求参数)

        典型场景:
            Task 1: rho=0.5, sigma=5    (平稳需求)
            Task 2: rho=0.9, sigma=15   (高频波动需求)

        参数:
            task_name: 任务名称
            rho:       新需求自相关系数
            sigma_eps: 新需求噪声标准差
        """
        self.task_name = task_name
        self.task_id += 1
        if rho is not None:
            self.env.rho = rho
        if sigma_eps is not None:
            self.env.sigma_eps = sigma_eps
        # 重置需求序列的初始值
        self.env.D_prev = self.env.d / (1 - self.env.rho)

    def step(self, idmr_agent, total_steps: int):
        """
        重写 step: 记录情绪/缺货率, 并将情绪元数据传入存储
        """
        # 调用父类 step 完成基本仿真逻辑
        # 但需要拦截 store_transition 调用, 加入情绪信息
        # 这里用 "包装" 方式: 重写 store_transition 行为

        # 暂存原 store_transition
        original_store = idmr_agent.store_transition

        # 包装: 注入情绪信息
        def emotion_aware_store(s, a, r, s_next, done):
            # 调用持续学习版本的存储
            if hasattr(idmr_agent, 'store_transition_with_emotion'):
                idmr_agent.store_transition_with_emotion(
                    s, a, r, s_next, done,
                    emotion_E=self._current_emotion_E,
                    stockout_rate=self._current_stockout_rate,
                    is_contagion=self._current_is_contagion,
                )
            else:
                original_store(s, a, r, s_next, done)

        # 临时替换
        idmr_agent.store_transition = emotion_aware_store

        # 同时拦截 get_state: 注入情绪维度
        original_get_state = idmr_agent.get_state
        if hasattr(idmr_agent, 'emotion_augmented') and idmr_agent.emotion_augmented:
            def emotion_aware_get_state(env, k=3):
                return idmr_agent.get_state_with_emotion(env, k, self._current_emotion_E)
            idmr_agent.get_state = emotion_aware_get_state

        # 执行父类 step
        result = super().step(idmr_agent, total_steps)

        # 恢复
        idmr_agent.store_transition = original_store
        idmr_agent.get_state = original_get_state

        # 更新情绪/缺货率 (供下一周期使用)
        if self.emotion is not None:
            self._current_emotion_E = self.emotion.E
        # 缺货率从 result 中无法直接获取, 用库存状态近似
        node3 = self.env.nodes[3]
        if hasattr(node3, 'demand_history') and len(node3.demand_history) > 0:
            last_demand = list(node3.demand_history)[-1]
            last_fulfilled = list(getattr(node3, 'fulfilled_history', [0]))[-1] if \
                hasattr(node3, 'fulfilled_history') and len(node3.fulfilled_history) > 0 else 0
            if last_demand > 0:
                self._current_stockout_rate = max(0, (last_demand - last_fulfilled) / last_demand)
        # 重置 contagion 标志 (单周期有效)
        self._current_is_contagion = False

        return result

    def trigger_contagion_flag(self):
        """标记当前周期发生了情绪传染 (供 PER 优先级使用)"""
        self._current_is_contagion = True


# ============================================================
# 持续学习训练函数 (支持任务切换)
# ============================================================

def train_continual_idmr(total_steps: int = 10000,
                          seed: int = 42,
                          # 持续学习开关
                          emotion_augmented: bool = True,
                          use_per: bool = True,
                          use_ewc: bool = False,
                          # PER 参数
                          per_alpha: float = 0.6,
                          per_beta: float = 0.4,
                          per_emotion_weight: float = 0.3,
                          # EWC 参数
                          ewc_lambda: float = 400.0,
                          # 情绪感知噪声
                          emotion_noise_std: float = 0.0,
                          # 训练参数
                          lr: float = 1e-3,
                          verbose: bool = True) -> Tuple[ContinualIDMRSupplyChainEnv,
                                                          ContinualIDMRAgent,
                                                          Dict[str, Any]]:
    """
    训练持续学习 IDMR

    参数:
        total_steps: 总训练步数
        emotion_augmented: 是否启用情感增强状态
        use_per: 是否启用优先级经验回放
        use_ewc: 是否启用 EWC (任务切换前需调用 consolidate)
        emotion_noise_std: 情绪感知噪声标准差 (模拟机器人误判情绪)
        ...
    """
    np.random.seed(seed)
    random.seed(seed)

    # 创建环境和智能体
    env = ContinualIDMRSupplyChainEnv(seed=seed)
    agent = ContinualIDMRAgent(
        state_dim=6 if emotion_augmented else 5,
        action_min=11, action_max=40,
        lr=lr, gamma=0.9, batch_size=32,
        replay_size=20000, replay_start=100,
        epsilon_start=1.0, epsilon_end=0.01,
        target_update_start=400, target_update_freq=10,
        emotion_augmented=emotion_augmented,
        use_per=use_per,
        use_ewc=use_ewc,
        per_alpha=per_alpha,
        per_beta=per_beta,
        per_emotion_weight=per_emotion_weight,
        ewc_lambda=ewc_lambda,
        emotion_noise_std=emotion_noise_std,
    )

    print("=" * 70)
    print("持续学习 IDMR 训练")
    print(f"  总步数: {total_steps}")
    print(f"  特性: emotion_augmented={emotion_augmented}, "
          f"use_per={use_per}, use_ewc={use_ewc}")
    print(f"  PER: alpha={per_alpha}, beta={per_beta}, emotion_weight={per_emotion_weight}")
    if use_ewc:
        print(f"  EWC: lambda={ewc_lambda}")
    if emotion_noise_std > 0:
        print(f"  情绪感知噪声: σ_noise={emotion_noise_std} (模拟机器人误判情绪)")
    print("=" * 70)

    losses = []
    rewards = []

    for step in range(1, total_steps + 1):
        result = env.step(agent, total_steps)

        if result['idmr_loss'] is not None:
            losses.append(result['idmr_loss'])
        rewards.append(result['idmr_reward'])

        if verbose and step % 2000 == 0:
            avg_loss = np.mean(losses[-2000:]) if losses else 0
            avg_reward = np.mean(rewards[-2000:])
            stats = agent.get_continual_stats()
            ewc_str = f", EWC={stats.get('ewc_recent_loss', 0):.4f}" if use_ewc else ""
            print(f"  Step {step:>5d}/{total_steps} | "
                  f"Loss={avg_loss:.4f} | Reward={avg_reward:.3f} | "
                  f"eps={agent.epsilon:.3f} | "
                  f"Buf={stats['buffer_size']}{ewc_str}")

    return env, agent, {
        'losses': losses,
        'rewards': rewards,
        'final_stats': agent.get_continual_stats(),
    }


# ============================================================
# 自检
# ============================================================

if __name__ == '__main__':
    print("=" * 70)
    print("持续学习 IDMR - 自检")
    print("=" * 70)

    # 短期训练测试 (验证不崩溃)
    env, agent, history = train_continual_idmr(
        total_steps=500,
        seed=42,
        emotion_augmented=True,
        use_per=True,
        use_ewc=False,
        verbose=True,
    )
    print(f"\n训练完成, 损失样本数: {len(history['losses'])}")
    print(f"最终统计: {agent.get_continual_stats()}")

    # 测试 EWC 巩固
    print("\n【EWC 巩固测试】")
    agent.use_ewc = True
    agent.ewc = EWCRegularizer()
    ok = agent.consolidate_knowledge(lambda_reg=400.0, n_samples=100)
    print(f"  巩固成功: {ok}")
    print(f"  EWC 统计: {agent.ewc.get_stats() if agent.ewc else None}")

    # 继续训练 (启用 EWC)
    print("\n【启用 EWC 后继续训练 200 步】")
    for step in range(200):
        env.step(agent, total_steps=200)
    stats = agent.get_continual_stats()
    print(f"  EWC 最近损失: {stats.get('ewc_recent_loss', 'N/A')}")
    print(f"  缓冲池大小: {stats['buffer_size']}")

    print("\n[完成] 持续学习 IDMR 自检通过")

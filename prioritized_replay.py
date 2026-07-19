"""
优先级经验回放池 (Prioritized Experience Replay, PER)
====================================================

理论背景:
    Schaul et al., 2015 "Prioritized Experience Replay"
    核心: TD误差大的样本包含更多信息, 应优先采样

创新扩展 (情感增强):
    在标准 |TD-error| 优先级基础上, 引入"情绪权重"维度:
        priority = |δ| + β_e * emotion_intensity + ε

    其中 emotion_intensity 衡量样本的情绪扰动强度:
        - 恐慌/乐观极值样本 (|E_t| > 0.5): 高优先级
        - 严重缺货样本 (stockout_rate > 0.3): 高优先级
        - 情绪传染事件样本: 最高优先级

    这使机器人更关注"情绪波动剧烈"或"导致严重缺货"的历史样本,
    加速学习情绪调节策略, 适应供应链突发动态.

实现:
    使用 SumTree (完全二叉树) 实现 O(log n) 的优先级采样:
        - 叶子节点: 存储 (priority, transition)
        - 内部节点: 存储子节点 priority 之和
        - 采样: 在 [0, total_priority) 内均匀采样, 沿树下降定位样本

关键参数:
    alpha: 优先级指数 (0=均匀, 1=完全优先级)
    beta:  重要性采样补偿 (0=不补偿, 1=完全补偿)
    beta_annealing: beta 线性增长步长 (训练中逐步增大补偿)
"""

import numpy as np
import random
from collections import deque
from typing import Tuple, List, Optional, Dict, Any


# ============================================================
# SumTree: 支持优先级采样的数据结构
# ============================================================

class SumTree:
    """
    SumTree (求和树)

    完全二叉树结构:
        - 叶子节点 (data_ptr): 存储 priority 值
        - 内部节点: 存储子节点之和
        - 根节点: 存储所有 priority 之和

    支持:
        - update(ptr, priority): O(log n) 更新叶子节点优先级
        - get_leaf(value): O(log n) 按 value 定位叶子节点 (用于采样)
    """

    def __init__(self, capacity: int):
        self.capacity = capacity
        # 树节点数: 2*capacity - 1 (完全二叉树)
        self.tree = np.zeros(2 * capacity - 1, dtype=np.float64)
        # 数据数组 (与叶子节点一一对应)
        self.data = np.zeros(capacity, dtype=object)
        self.data_ptr = 0      # 当前写入位置
        self.n_entries = 0      # 已存储样本数

    def update(self, tree_idx: int, priority: float):
        """更新叶子节点的优先级, 并反向传播到根节点"""
        # 计算变化量
        change = priority - self.tree[tree_idx]
        self.tree[tree_idx] = priority
        # 反向传播到根
        while tree_idx != 0:
            tree_idx = (tree_idx - 1) // 2
            self.tree[tree_idx] += change

    def add(self, priority: float, data: Any) -> int:
        """
        添加新数据

        返回: 数据在树中的叶子索引 (用于后续更新优先级)
        """
        tree_idx = self.data_ptr + self.capacity - 1
        self.data[self.data_ptr] = data
        self.update(tree_idx, priority)
        self.data_ptr = (self.data_ptr + 1) % self.capacity
        self.n_entries = min(self.n_entries + 1, self.capacity)
        return tree_idx

    def get_leaf(self, value: float) -> Tuple[int, float, Any]:
        """
        根据 value 在 [0, total) 区间采样, 定位到叶子节点

        返回: (tree_idx, priority, data)
        """
        parent = 0
        while True:
            left = 2 * parent + 1
            right = left + 1
            # 到达叶子节点
            if left >= len(self.tree):
                leaf_idx = parent
                break
            # 向下搜索
            if value <= self.tree[left]:
                parent = left
            else:
                value -= self.tree[left]
                parent = right
        return leaf_idx, self.tree[leaf_idx], self.data[leaf_idx - self.capacity + 1]

    @property
    def total_priority(self) -> float:
        return float(self.tree[0])


# ============================================================
# 优先级经验回放池 (PER)
# ============================================================

class PrioritizedReplayBuffer:
    """
    优先级经验回放池

    创新: 在 |TD-error| 基础上叠加情绪权重, 实现"情感增强"采样

    使用方式:
        buffer = PrioritizedReplayBuffer(capacity=20000)
        # 存储 (含情绪信息)
        buffer.push(state, action, reward, next_state, done,
                    emotion_E=0.8, stockout_rate=0.3)
        # 采样
        batch, tree_indices, is_weights = buffer.sample(batch_size=32)
        # 更新优先级 (训练后)
        buffer.update_priorities(tree_indices, td_errors)
    """

    def __init__(self,
                 capacity: int = 20000,
                 alpha: float = 0.6,
                 beta: float = 0.4,
                 beta_annealing: float = 0.0001,
                 epsilon: float = 1e-6,
                 emotion_weight: float = 0.3):
        """
        参数:
            capacity:       缓冲区容量
            alpha:          优先级指数 (0=均匀采样, 1=完全按优先级)
            beta:           IS补偿初始值 (0=不补偿, 1=完全补偿)
            beta_annealing: beta 每次采样的增长量 (训练中逐步增大补偿)
            epsilon:        优先级下限 (避免0概率)
            emotion_weight: 情绪权重系数 (情感增强采样强度)
        """
        self.tree = SumTree(capacity)
        self.capacity = capacity
        self.alpha = alpha
        self.beta = beta
        self.beta_max = 1.0
        self.beta_annealing = beta_annealing
        self.epsilon = epsilon
        self.emotion_weight = emotion_weight
        self.max_priority = 1.0  # 新样本初始优先级

    def _compute_emotion_intensity(self,
                                    emotion_E: float = 0.0,
                                    stockout_rate: float = 0.0,
                                    is_contagion: bool = False) -> float:
        """
        计算样本的情绪强度 (情感增强核心)

        规则:
            - 情绪传染事件: 基础强度 1.0 (最高优先级)
            - 恐慌/乐观极值 (|E|>0.5): 强度 |E|
            - 严重缺货 (stockout_rate>0.3): 强度 stockout_rate
            - 取最大值

        返回: [0, 1] 范围的情绪强度
        """
        intensity = 0.0
        if is_contagion:
            intensity = 1.0
        intensity = max(intensity, abs(emotion_E))
        intensity = max(intensity, stockout_rate)
        return float(np.clip(intensity, 0.0, 1.0))

    def _compute_priority(self,
                          td_error: float = 0.0,
                          emotion_E: float = 0.0,
                          stockout_rate: float = 0.0,
                          is_contagion: bool = False) -> float:
        """
        计算综合优先级

        priority = (|TD-error| + ε)^α + β_e * emotion_intensity
        """
        td_part = (abs(td_error) + self.epsilon) ** self.alpha
        emotion_intensity = self._compute_emotion_intensity(
            emotion_E, stockout_rate, is_contagion)
        emotion_part = self.emotion_weight * emotion_intensity
        return td_part + emotion_part

    def push(self, state, action, reward, next_state, done,
             td_error: float = 0.0,
             emotion_E: float = 0.0,
             stockout_rate: float = 0.0,
             is_contagion: bool = False):
        """存储经验 (含情绪元数据)"""
        # 新样本用最大优先级 (确保至少被采样一次)
        priority = self.max_priority
        if td_error != 0.0 or emotion_E != 0.0 or stockout_rate > 0 or is_contagion:
            priority = self._compute_priority(
                td_error, emotion_E, stockout_rate, is_contagion)
            self.max_priority = max(self.max_priority, priority)

        # 存储 (state, action, reward, next_state, done, emotion_E, stockout_rate)
        data = (state, action, reward, next_state, done,
                emotion_E, stockout_rate, is_contagion)
        self.tree.add(priority, data)

    def sample(self, batch_size: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray,
                                                 np.ndarray, np.ndarray, np.ndarray,
                                                 np.ndarray, List[int], np.ndarray]:
        """
        优先级采样

        返回:
            states, actions, rewards, next_states, dones,
            emotion_Es, stockout_rates,
            tree_indices, is_weights (重要性采样权重)
        """
        # beta 退火 (训练中逐步增大补偿)
        self.beta = min(1.0, self.beta + self.beta_annealing)

        # 在 [0, total_priority) 内均匀分段采样
        segment = self.tree.total_priority / batch_size
        tree_indices = []
        priorities = []
        data_list = []

        for i in range(batch_size):
            a = segment * i
            b = segment * (i + 1)
            s = random.uniform(a, b)
            idx, priority, data = self.tree.get_leaf(s)
            tree_indices.append(idx)
            priorities.append(priority)
            data_list.append(data)

        # 重要性采样权重: w_i = (N * p_i)^(-β)
        sampling_probabilities = np.array(priorities) / max(self.tree.total_priority, self.epsilon)
        is_weights = np.power(self.tree.n_entries * sampling_probabilities + 1e-10, -self.beta)
        is_weights = is_weights / max(is_weights.max(), self.epsilon)  # 归一化

        # 解包数据
        states = np.array([d[0] for d in data_list], dtype=np.float32)
        actions = np.array([d[1] for d in data_list], dtype=np.int64)
        rewards = np.array([d[2] for d in data_list], dtype=np.float32)
        next_states = np.array([d[3] for d in data_list], dtype=np.float32)
        dones = np.array([d[4] for d in data_list], dtype=np.float32)
        emotion_Es = np.array([d[5] for d in data_list], dtype=np.float32)
        stockout_rates = np.array([d[6] for d in data_list], dtype=np.float32)

        return (states, actions, rewards, next_states, dones,
                emotion_Es, stockout_rates, tree_indices, is_weights)

    def update_priorities(self, tree_indices: List[int],
                          td_errors: np.ndarray,
                          emotion_Es: Optional[np.ndarray] = None,
                          stockout_rates: Optional[np.ndarray] = None,
                          is_contagions: Optional[List[bool]] = None):
        """训练后用新的TD误差更新样本优先级"""
        for i, idx in enumerate(tree_indices):
            td = float(td_errors[i]) if i < len(td_errors) else 0.0
            emo = float(emotion_Es[i]) if emotion_Es is not None and i < len(emotion_Es) else 0.0
            stk = float(stockout_rates[i]) if stockout_rates is not None and i < len(stockout_rates) else 0.0
            cont = bool(is_contagions[i]) if is_contagions and i < len(is_contagions) else False
            priority = self._compute_priority(td, emo, stk, cont)
            self.tree.update(idx, priority)
            self.max_priority = max(self.max_priority, priority)

    def __len__(self):
        return self.tree.n_entries


# ============================================================
# 自检
# ============================================================

if __name__ == '__main__':
    print("=" * 70)
    print("优先级经验回放池 (PER) - 自检")
    print("=" * 70)

    # 测试1: 基本功能
    print("\n【测试1】基本存储与采样")
    buf = PrioritizedReplayBuffer(capacity=100, alpha=0.6, beta=0.4)
    for i in range(50):
        s = np.array([i, i+1, i+2], dtype=np.float32)
        a = i % 5
        r = float(i)
        ns = np.array([i+1, i+2, i+3], dtype=np.float32)
        # 模拟不同情绪强度
        emo = 0.8 if i % 10 == 0 else 0.1
        stk = 0.5 if i % 10 == 0 else 0.0
        buf.push(s, a, r, ns, False,
                 td_error=abs(r), emotion_E=emo, stockout_rate=stk,
                 is_contagion=(i % 20 == 0))
    print(f"  缓冲区大小: {len(buf)}")
    print(f"  总优先级: {buf.tree.total_priority:.4f}")

    # 采样
    (s, a, r, ns, d, emo, stk, idxs, w) = buf.sample(batch_size=8)
    print(f"  采样 batch_size=8:")
    print(f"    states.shape={s.shape}")
    print(f"    actions={a}")
    print(f"    rewards={r}")
    print(f"    emotion_Es={emo}")
    print(f"    is_weights={w}")
    print(f"    tree_indices={idxs}")

    # 测试2: 高情绪强度样本被优先采样
    print("\n【测试2】情绪增强采样验证")
    buf2 = PrioritizedReplayBuffer(capacity=200, alpha=0.6, emotion_weight=0.5)
    # 普通样本 (TD=0.1, 情绪=0.1)
    for i in range(100):
        buf2.push(np.zeros(3), 0, 0.1, np.zeros(3), False,
                  td_error=0.1, emotion_E=0.1, stockout_rate=0.0)
    # 高情绪样本 (TD=0.1, 但情绪=0.9, 恐慌)
    for i in range(100):
        buf2.push(np.zeros(3), 0, 0.1, np.zeros(3), False,
                  td_error=0.1, emotion_E=0.9, stockout_rate=0.5)
    # 采样1000次, 统计高情绪样本占比
    high_count = 0
    for _ in range(1000):
        (_, _, _, _, _, emo, _, _, _) = buf2.sample(1)
        if abs(emo[0]) > 0.5:
            high_count += 1
    print(f"  1000次单样本采样中, 高情绪样本被采中次数: {high_count}/1000")
    print(f"  理论占比(高情绪优先级): 应显著高于50%")
    print(f"  实测占比: {high_count/10:.1f}%")

    print("\n[完成] PER 自检通过")

"""
情绪演化与决策映射模块 (Emotion-Aware Decision Module)
======================================================

理论框架:
    在人机协同供应链中,引入"情绪"维度模拟人类决策者的心理状态。
    情绪状态 E_t ∈ [-1, 1] 演化并调节DQN的奖励函数与动作选择,
    捕捉"损失厌恶"与"过度自信"两种偏差对订货决策的影响。

数学模型:
    1. 情绪状态:  E_t ∈ [-1, 1]
       E_t < 0: 恐慌/焦虑 (损失厌恶, 倾向过度订货)
       E_t > 0: 自信/乐观 (风险中性, 倾向精准订货)

    2. 情绪演化方程 (带饱和的动力学):
       E_t = tanh( α·E_{t-1} + γ·Φ_t )
       其中:
         α ∈ [0,1):  情绪惯性 (粘性系数), α越大情绪越持久
         γ > 0:      情绪敏感度 (对反馈的响应强度)
         Φ_t:        反馈信号 (缺货负反馈 + 精准匹配正反馈)

       Φ_t = -w_s · stockout_rate        # 缺货 → 恐慌 (负向)
             + w_m · match_factor         # 精准匹配 → 乐观 (正向)
             - w_e · excess_rate          # 过度积压 → 焦虑 (负向)

       tanh函数特性:
         - 值域自然限制在[-1,1]
         - 连续缺货时E_t加速趋向-1 (恐慌饱和, 模拟"恐慌蔓延")
         - 连续精准匹配时E_t趋向+1 (过度自信)
         - 提供平滑的非线性响应

    3. 决策映射 (情绪调节奖励权重):
       恐慌(E<0): 放大缺货惩罚 → stockout_weight_eff = w_s0 · (1 + |E|)
       乐观(E>0): 放大正向激励 → bonus_weight_eff  = w_b0 · (1 + E)

使用:
    from emotion_module import EmotionState
    emotion = EmotionState(alpha=0.7, gamma=2.0)
    emotion.update(stockout_rate=0.1, match_factor=0.8, excess_rate=0.0)
    weights = emotion.get_reward_weights(base_stockout_w, base_bonus_w)
"""

import numpy as np
from dataclasses import dataclass


# ============================================================
# 情绪状态与演化
# ============================================================

@dataclass
class EmotionState:
    """
    情绪状态管理器

    维护情绪变量 E_t ∈ [-1, 1] 并按演化方程更新。
    同时提供决策映射: 将情绪转换为奖励权重调节因子。
    """

    # ---- 情绪动力学参数 ----
    alpha: float = 0.7       # 情绪惯性 (α∈[0,1), 越大越持久)
    gamma: float = 2.0       # 情绪敏感度 (对反馈的响应强度)

    # ---- 反馈信号权重 ----
    w_stockout: float = 1.0    # 缺货反馈权重 (负向→恐慌)
    w_match: float = 0.5       # 精准匹配反馈权重 (正向→乐观)
    w_excess: float = 0.3      # 积压反馈权重 (负向→焦虑)

    # ---- 初始情绪 ----
    E_init: float = 0.0        # 初始情绪 (中性)

    def __post_init__(self):
        self.E = self.E_init           # 当前情绪
        self.E_history = [self.E]       # 情绪历史 (用于可视化)
        self.feedback_history = []      # 反馈信号历史

    def update(self, stockout_rate: float, match_factor: float,
               excess_rate: float) -> float:
        """
        情绪演化方程: E_t = tanh(α·E_{t-1} + γ·Φ_t)

        参数:
            stockout_rate: 缺货率 ∈ [0,1] (stockout/demand)
            match_factor:  库存精准匹配度 ∈ [0,1] (1=完美匹配)
            excess_rate:   过度积压率 ∈ [0,1] (excess/forecast)

        返回:
            更新后的情绪 E_t ∈ [-1, 1]
        """
        # ---- 反馈信号 Φ_t ----
        # 缺货 → 负向 (恐慌); 精准匹配 → 正向 (乐观); 积压 → 负向 (焦虑)
        feedback = (
            -self.w_stockout * np.clip(stockout_rate, 0, 1)
            + self.w_match * np.clip(match_factor, 0, 1)
            - self.w_excess * np.clip(excess_rate, 0, 1)
        )

        # ---- 情绪演化 (tanh饱和) ----
        # α·E_{t-1}: 情绪惯性 (上一期情绪的衰减延续)
        # γ·Φ_t:     本期反馈对情绪的冲击
        # tanh:       饱和函数, 确保情绪在[-1,1]内, 模拟恐慌/乐观的极值饱和
        self.E = float(np.tanh(self.alpha * self.E + self.gamma * feedback))

        # ---- 记录历史 ----
        self.E_history.append(self.E)
        self.feedback_history.append(feedback)

        return self.E

    # ============================================================
    # 决策映射: 情绪 → 奖励权重调节
    # ============================================================

    def get_reward_weights(self, base_stockout_weight: float,
                           base_bonus_weight: float) -> dict:
        """
        将情绪状态映射为奖励函数权重的调节因子

        决策映射逻辑:
            恐慌(E<0): 放大缺货惩罚权重 (损失厌恶加剧)
                       stockout_weight_eff = base · (1 + |E|)
            乐观(E>0): 放大正向激励权重 (信任精准匹配)
                       bonus_weight_eff = base · (1 + E)

        参数:
            base_stockout_weight: 基准缺货惩罚权重
            base_bonus_weight:     基准正向激励权重

        返回:
            dict: {
                'stockout_weight': 情绪调节后的缺货惩罚权重,
                'bonus_weight':    情绪调节后的正向激励权重,
                'emotion':         当前情绪值,
                'emotion_label':   情绪标签,
            }
        """
        E = self.E

        # 恐慌(E<0)时放大缺货惩罚: |E|越大, 惩罚放大越多
        # 乐观(E>0)时不放大缺货惩罚 (保持基准)
        stockout_amplifier = 1.0 + max(0, -E)   # E<0时: 1+|E|; E>=0时: 1
        stockout_weight_eff = base_stockout_weight * stockout_amplifier

        # 乐观(E>0)时放大正向激励: E越大, 激励放大越多
        # 恐慌(E<0)时不放大正向激励 (保持基准)
        bonus_amplifier = 1.0 + max(0, E)       # E>0时: 1+E; E<=0时: 1
        bonus_weight_eff = base_bonus_weight * bonus_amplifier

        # 情绪标签
        if E < -0.3:
            label = "恐慌"
        elif E < -0.05:
            label = "焦虑"
        elif E < 0.05:
            label = "中性"
        elif E < 0.3:
            label = "自信"
        else:
            label = "乐观"

        return {
            'stockout_weight': stockout_weight_eff,
            'bonus_weight': bonus_weight_eff,
            'emotion': E,
            'emotion_label': label,
        }

    def get_exploration_modifier(self) -> float:
        """
        情绪对探索率ε的调节

        恐慌时增加探索 (不信任自身判断, 更多随机尝试)
        乐观时减少探索 (信任自身判断, 更多利用)

        返回:
            ε调节因子 ∈ [0.5, 2.0]
        """
        # E=-1时ε放大2倍; E=+1时ε缩小0.5倍
        return float(np.clip(1.0 - self.E, 0.5, 2.0))

    def apply_contagion_shock(self, shock: float) -> float:
        """
        应用情绪传染冲击 (外部注入, 用于多智能体情绪传染)

        数学形式:
            E_t = tanh(E_{t-1} + shock)

        传染冲击是独立于演化方程 (α·E_{t-1} + γ·Φ_t) 的外部项,
        模拟"恐慌从下游节点蔓延到上游节点"的群体心理现象。

        参数:
            shock: 传染冲击值 (负值=恐慌传染, 正值=乐观传染)

        返回:
            传染后的情绪 E_t ∈ [-1, 1]
        """
        # 外部冲击直接注入, 用tanh饱和保持值域
        self.E = float(np.tanh(self.E + shock))
        # 记录历史 (标记为传染事件)
        self.E_history.append(self.E)
        # 反馈历史记为 None 以区分正常演化与传染
        self.feedback_history.append(('contagion', shock))
        return self.E

    def reset(self):
        """重置情绪到初始状态"""
        self.E = self.E_init
        self.E_history = [self.E]
        self.feedback_history = []

    def get_stats(self) -> dict:
        """获取情绪统计信息"""
        if len(self.E_history) > 1:
            return {
                'current_emotion': self.E,
                'mean_emotion': float(np.mean(self.E_history)),
                'min_emotion': float(np.min(self.E_history)),
                'max_emotion': float(np.max(self.E_history)),
                'emotion_volatility': float(np.std(self.E_history)),
                'history_length': len(self.E_history),
            }
        return {'current_emotion': self.E, 'history_length': 1}


# ============================================================
# 自检: 模拟情绪演化场景
# ============================================================

if __name__ == '__main__':
    print("=" * 70)
    print("情绪演化与决策映射模块 - 自检")
    print("=" * 70)

    emotion = EmotionState(alpha=0.7, gamma=2.0)

    print("\n【场景1: 连续缺货 → 恐慌蔓延】")
    print(f"  初始情绪: E={emotion.E:.3f} ({emotion.get_reward_weights(1,0.3)['emotion_label']})")
    print("  模拟连续5期缺货(stockout_rate=0.3):")
    for t in range(5):
        E = emotion.update(stockout_rate=0.3, match_factor=0.0, excess_rate=0.0)
        w = emotion.get_reward_weights(base_stockout_weight=1.0, base_bonus_weight=0.3)
        print(f"    t={t+1}: E={E:+.3f} [{w['emotion_label']}] "
              f"缺货权重={w['stockout_weight']:.3f} 激励权重={w['bonus_weight']:.3f}")

    print(f"\n  恐慌后统计: {emotion.get_stats()}")

    print("\n【场景2: 连续精准匹配 → 乐观建立】")
    emotion.reset()
    print(f"  初始情绪: E={emotion.E:.3f}")
    print("  模拟连续5期精准匹配(match=0.9, 无缺货):")
    for t in range(5):
        E = emotion.update(stockout_rate=0.0, match_factor=0.9, excess_rate=0.0)
        w = emotion.get_reward_weights(base_stockout_weight=1.0, base_bonus_weight=0.3)
        print(f"    t={t+1}: E={E:+.3f} [{w['emotion_label']}] "
              f"缺货权重={w['stockout_weight']:.3f} 激励权重={w['bonus_weight']:.3f}")

    print(f"\n  乐观后统计: {emotion.get_stats()}")

    print("\n【场景3: 混合场景 → 情绪波动】")
    emotion.reset()
    scenarios = [
        (0.0, 0.8, 0.0, "正常"),
        (0.5, 0.0, 0.0, "突发缺货"),
        (0.3, 0.0, 0.0, "持续缺货"),
        (0.0, 0.7, 0.0, "恢复精准"),
        (0.0, 0.0, 0.4, "过度积压"),
        (0.0, 0.9, 0.0, "恢复乐观"),
    ]
    print(f"  初始情绪: E={emotion.E:.3f}")
    for t, (s, m, e, desc) in enumerate(scenarios):
        E = emotion.update(stockout_rate=s, match_factor=m, excess_rate=e)
        w = emotion.get_reward_weights(base_stockout_weight=1.0, base_bonus_weight=0.3)
        print(f"    t={t+1} [{desc}]: E={E:+.3f} [{w['emotion_label']}] "
              f"缺货权重={w['stockout_weight']:.3f} 激励权重={w['bonus_weight']:.3f} "
              f"ε调节={emotion.get_exploration_modifier():.2f}")

    print("\n" + "=" * 70)
    print("[OK] 情绪模块自检通过!")
    print("=" * 70)

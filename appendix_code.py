"""
论文附录代码 (Appendix Code) — 精简版
=====================================

提取论文两个核心模型的数学实现, 精简至 30 行以内,
适合作为顶级期刊论文附录 (Appendix) 展示。

包含:
    A.1 情绪演化方程 (Emotion Evolution Equation)
    A.2 正向激励奖励函数 (Positive Incentive Reward Function)

理论依据:
    - Kahneman & Tversky (1979): 损失厌恶系数 2.25 (本实现 w_s:w_m = 2:1)
    - Lee et al. (1997): 牛鞭效应方差比 BWE = var(q)/var(D)
"""

import numpy as np


def emotion_evolution(E_prev, stockout_rate, match_factor, excess_rate,
                       alpha=0.7, gamma=2.0, w_s=1.0, w_m=0.5, w_e=0.3):
    """A.1 情绪演化: E_t = tanh(α·E_{t-1} + γ·Φ_t), Φ_t = -w_s·s + w_m·m - w_e·e"""
    Phi = -w_s * np.clip(stockout_rate, 0, 1) + w_m * np.clip(match_factor, 0, 1) \
          - w_e * np.clip(excess_rate, 0, 1)
    E_t = float(np.tanh(alpha * E_prev + gamma * Phi))   # E_t ∈ [-1, 1]
    w_stockout_eff = 1.0 + max(0.0, -E_t)                  # 恐慌放大缺货惩罚
    w_bonus_eff = 1.0 + max(0.0, E_t)                      # 乐观放大正向激励
    return E_t, w_stockout_eff, w_bonus_eff


def positive_incentive(net_stock, demand_forecast, w_bonus=0.3,
                        cov_lo=0.8, cov_hi=1.5):
    """A.2 正向激励: 库存精准覆盖预测需求时给予钟形奖励"""
    if demand_forecast <= 0:
        return 0.0, 0.0
    ratio = net_stock / demand_forecast                      # 覆盖率
    if ratio < cov_lo or ratio > cov_hi:
        return 0.0, 0.0                                      # 区外无奖励
    match = max(0.0, 1.0 - abs(ratio - 1.0))                # 匹配度 ∈ [0,1]
    bonus = w_bonus * match                                  # 钟形奖励
    return float(bonus), float(match)


# ============================================================
# 验证用例 (Appendix 自检, 非论文内容)
# ============================================================

if __name__ == '__main__':
    # A.1 情绪演化: 模拟一次缺货事件
    E, ws, wb = emotion_evolution(E_prev=0.0, stockout_rate=0.5,
                                   match_factor=0.3, excess_rate=0.0)
    print(f"A.1 情绪演化: E_t={E:.4f}, 缺货权重={ws:.2f}, 激励权重={wb:.2f}")

    # A.2 正向激励: 库存精准匹配场景
    bonus, match = positive_incentive(net_stock=22, demand_forecast=20)
    print(f"A.2 正向激励: bonus={bonus:.4f}, match={match:.4f}")

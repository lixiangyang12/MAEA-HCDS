"""
Exp_1b 20000周期剥离实验: 单智能体IDMR + 情绪机制（无协同）
============================================================
剥离实验（Ablation Study）设计:
  - Exp_1:   单智能体IDMR（无情绪、无协同）
  - Exp_1b:  单智能体IDMR + 情绪机制（无协同）← 本脚本
  - Exp_2:   多智能体 + 情绪机制 + 协同通信

Exp_1b配置:
  - 仅分销商(k=3)部署IDMR（DQN + 人机协同），其余节点理性决策
  - 启用情绪演化方程（tanh饱和动力学, α=0.7, γ=2.0）
  - 启用库存精准匹配正向激励（情绪正反馈信号所需）
  - 禁用多智能体协同通信
  - 无动态突发事件（与Exp_1环境一致，AR(1)需求自然波动）

对比逻辑:
  - Exp_1 vs Exp_1b: 隔离情绪机制的独立效应（H1: 损失厌恶放大）
  - Exp_1b vs Exp_2: 隔离协同通信的独立效应（H3: 协同鲁棒性）

输出:
  - p0_results/exp1b_20k.json (Exp_1b实验汇总数据)
  - p0_results/exp1b_20k_timeseries.json (Exp_1b时序数据)
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.size'] = 11

# ============================================================
# 配置参数（与实验设计方案表4-3完全对标）
# ============================================================
TOTAL_PERIODS = 20000
TRAIN_STEPS = 10000
SEED = 42
D = 10; RHO = 0.5; SIGMA_EPS = 5.0; L = 2; P = 5; Z = 2; C_L_RHO = 2.0
INITIAL_INVENTORY = 10.0; K = 4
H = 1.0; B = 2.0  # 单位库存成本/单位缺货成本

NODE_NAMES = ['零售商', '批发商', '分销商', '制造商']

# 路径
EXP1B_JSON = os.path.join('p0_results', 'exp1b_20k.json')
EXP1B_TS_JSON = os.path.join('p0_results', 'exp1b_20k_timeseries.json')
FIG_DIR = 'svg_figures_exp2'
os.makedirs('p0_results', exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)


# ============================================================
# 1. 运行Exp_1b: 单智能体IDMR + 情绪机制（无协同）
# ============================================================

def run_exp1b_20k():
    """
    运行Exp_1b: 单智能体IDMR + 情绪机制（无协同）

    设计要点:
      1. 仅分销商(k=3)部署IDMR（DQN + 人机协同），其余节点理性决策
      2. 启用情绪演化方程（tanh饱和动力学）
      3. 启用库存精准匹配正向激励（情绪正反馈信号所需）
      4. 禁用多智能体协同通信
      5. 无动态突发事件（与Exp_1环境一致）
    """
    from idmr_agent import train_idmr
    from config import load_config, set_seed

    print("\n" + "=" * 70)
    print(f"[Exp_1b] 单智能体IDMR + 情绪机制（无协同）({TOTAL_PERIODS}周期)")
    print("=" * 70)

    # 加载配置并覆盖Exp_1b参数
    cfg = load_config()
    cfg.idmr.enable_emotion = True             # 启用情绪模块
    cfg.idmr.enable_inventory_bonus = True      # 启用正向激励（情绪正反馈所需）
    cfg.idmr.penalty_threshold = 1.0            # 与Exp_1一致（经典平均库存阈值）
    cfg.training.total_steps = TRAIN_STEPS      # 训练步数
    cfg.training.eval_steps = TOTAL_PERIODS     # 评估周期
    cfg.training.baseline_steps = TOTAL_PERIODS
    set_seed(SEED)

    print(f"  情绪模块: 启用 (alpha={cfg.idmr.emotion_alpha}, gamma={cfg.idmr.emotion_gamma})")
    print(f"  正向激励: 启用 (权重={cfg.idmr.inventory_bonus_weight})")
    print(f"  协同机制: 禁用")
    print(f"  动态事件: 无（AR(1)需求自然波动）")
    print(f"  惩罚阈值: {cfg.idmr.penalty_threshold}x经典平均库存")
    print(f"  训练步数: {TRAIN_STEPS}, 评估周期: {TOTAL_PERIODS}")

    # 训练IDMR（情绪模块参与奖励调节）
    env, idmr, history = train_idmr(
        total_steps=TRAIN_STEPS, seed=SEED,
        config=cfg, verbose=True,
    )

    print(f"\n  训练完成，开始{TOTAL_PERIODS}周期评估...")

    # ============================================================
    # 评估: 20000周期连续仿真，记录详细数据
    # ============================================================
    order_history = {k: [] for k in range(1, 5)}
    demand_history = {k: [] for k in range(1, 5)}
    fulfilled_history = {k: [] for k in range(1, 5)}
    netstock_history = {k: [] for k in range(1, 5)}
    cost_history = {k: [] for k in range(1, 5)}
    sl_history = {k: [] for k in range(1, 5)}
    emotion_history = {k: [] for k in range(1, 5)}  # 仅k=3有情绪
    reward_history = []
    emotion_label_history = []  # 分销商情绪标签

    inner_env = env.env  # SupplyChainEnv

    for t in range(TOTAL_PERIODS):
        result = env.step(idmr, total_steps=1)
        idmr.epsilon = 0.01  # 评估时低探索
        reward_history.append(result['idmr_reward'])

        # 提取各节点数据
        for k in range(1, 5):
            node = inner_env.nodes[k]
            orders = list(node.order_history)
            demands = list(node.demand_history)
            fulfilled_list = list(getattr(node, 'fulfilled_history', orders))

            q_t = orders[-1]
            d_t = demands[-1]
            f_t = fulfilled_list[-1]
            ns_t = node.net_stock
            stockout = max(0, d_t - f_t)

            holding_cost = max(0, ns_t) * H
            stockout_cost = stockout * B

            order_history[k].append(float(q_t))
            demand_history[k].append(float(d_t))
            fulfilled_history[k].append(float(f_t))
            netstock_history[k].append(float(ns_t))
            cost_history[k].append(float(holding_cost + stockout_cost))
            sl_history[k].append(float(f_t / d_t if d_t > 0 else 1.0))

            # 情绪状态（仅分销商k=3有IDMR情绪模块）
            if k == 3 and env.emotion is not None:
                emotion_history[k].append(float(env.emotion.E))
            else:
                emotion_history[k].append(0.0)

        # 记录分销商情绪标签
        if env.emotion is not None:
            weights = env.emotion.get_reward_weights(
                base_stockout_weight=cfg.idmr.stockout_penalty_weight,
                base_bonus_weight=cfg.idmr.inventory_bonus_weight,
            )
            emotion_label_history.append(weights['emotion_label'])

        if (t + 1) % 5000 == 0:
            avg_r = np.mean(reward_history[-5000:])
            E_3 = emotion_history[3][-1] if emotion_history[3] else 0.0
            print(f"    周期 {t+1}/{TOTAL_PERIODS} | "
                  f"avg_reward={avg_r:.3f} | E_distr={E_3:+.3f}")

    print(f"\n  评估完成: {TOTAL_PERIODS}周期")

    # ============================================================
    # 计算指标
    # ============================================================
    demand_hist = demand_history[1]  # 零售商需求 = 顾客需求
    var_D = float(np.var(demand_hist)) if len(demand_hist) > 1 else 1.0

    bwe = {}; avg_cost = {}; sl = {}; emotion_var = {}
    demand_mean = {}; order_mean = {}

    for k in range(1, 5):
        orders = order_history[k]
        bwe[k] = float(np.var(orders)) / var_D if var_D > 0 else 0.0
        avg_cost[k] = float(np.mean(cost_history[k]))
        sl[k] = float(np.mean(sl_history[k]))
        emotion_var[k] = float(np.var(emotion_history[k])) if emotion_history[k] else 0.0
        demand_mean[k] = float(np.mean(demand_history[k]))
        order_mean[k] = float(np.mean(order_history[k]))

    total_cost = sum(avg_cost.values())

    # 情绪统计（仅分销商）
    emo_distr = emotion_history[3]
    emo_stats = {
        'mean': float(np.mean(emo_distr)) if emo_distr else 0.0,
        'std': float(np.std(emo_distr)) if emo_distr else 0.0,
        'min': float(np.min(emo_distr)) if emo_distr else 0.0,
        'max': float(np.max(emo_distr)) if emo_distr else 0.0,
        'panic_ratio': float(np.mean(np.array(emo_distr) < -0.3)) if emo_distr else 0.0,
        'anxiety_ratio': float(np.mean((np.array(emo_distr) >= -0.3) & (np.array(emo_distr) < -0.05))) if emo_distr else 0.0,
        'neutral_ratio': float(np.mean((np.array(emo_distr) >= -0.05) & (np.array(emo_distr) <= 0.05))) if emo_distr else 0.0,
        'confident_ratio': float(np.mean((np.array(emo_distr) > 0.05) & (np.array(emo_distr) <= 0.3))) if emo_distr else 0.0,
        'optimistic_ratio': float(np.mean(np.array(emo_distr) > 0.3)) if emo_distr else 0.0,
    }

    # 过度订货比例（订货量超过需求均值）
    overorder_ratio = {}
    for k in range(1, 5):
        orders = np.array(order_history[k])
        d_mean = demand_mean[k]
        overorder_ratio[k] = float(np.mean(orders > d_mean)) if len(orders) > 0 else 0.0

    # 打印结果
    print(f"\n  Exp_1b 结果:")
    for k in range(1, 5):
        print(f"    {NODE_NAMES[k-1]}: BWE={bwe[k]:.2f}, SL={sl[k]:.4f}, "
              f"成本={avg_cost[k]:.2f}, 情绪方差={emotion_var[k]:.4f}")
    print(f"  总成本={total_cost:.2f}")
    print(f"\n  分销商情绪统计:")
    print(f"    均值={emo_stats['mean']:+.4f}, 标准差={emo_stats['std']:.4f}")
    print(f"    恐慌占比={emo_stats['panic_ratio']*100:.2f}%, "
          f"焦虑占比={emo_stats['anxiety_ratio']*100:.2f}%, "
          f"中性占比={emo_stats['neutral_ratio']*100:.2f}%")
    print(f"    自信占比={emo_stats['confident_ratio']*100:.2f}%, "
          f"乐观占比={emo_stats['optimistic_ratio']*100:.2f}%")
    print(f"  过度订货比例: "
          f"零售商={overorder_ratio[1]*100:.1f}%, "
          f"批发商={overorder_ratio[2]*100:.1f}%, "
          f"分销商={overorder_ratio[3]*100:.1f}%, "
          f"制造商={overorder_ratio[4]*100:.1f}%")

    # ============================================================
    # 保存结果
    # ============================================================
    result = {
        'name': 'Exp_1b (单智能体IDMR+情绪, 无协同)',
        'bwe': {str(k): bwe[k] for k in range(1, 5)},
        'avg_cost': {str(k): avg_cost[k] for k in range(1, 5)},
        'sl': {str(k): sl[k] for k in range(1, 5)},
        'total_cost': total_cost,
        'demand_mean': {str(k): demand_mean[k] for k in range(1, 5)},
        'order_mean': {str(k): order_mean[k] for k in range(1, 5)},
        'emotion_variance': {str(k): emotion_var[k] for k in range(1, 5)},
        'emotion_stats_distributor': emo_stats,
        'overorder_ratio': {str(k): overorder_ratio[k] for k in range(1, 5)},
        'var_D': var_D,
        'config': {
            'enable_emotion': True,
            'enable_inventory_bonus': True,
            'enable_coordination': False,
            'dynamic_events': False,
            'penalty_threshold': 1.0,
            'train_steps': TRAIN_STEPS,
            'eval_periods': TOTAL_PERIODS,
            'emotion_alpha': cfg.idmr.emotion_alpha,
            'emotion_gamma': cfg.idmr.emotion_gamma,
        },
    }

    # 时序数据
    ts_data = {
        'order_history': {str(k): order_history[k] for k in range(1, 5)},
        'demand_history': {str(k): demand_history[k] for k in range(1, 5)},
        'fulfilled_history': {str(k): fulfilled_history[k] for k in range(1, 5)},
        'netstock_history': {str(k): netstock_history[k] for k in range(1, 5)},
        'cost_history': {str(k): cost_history[k] for k in range(1, 5)},
        'sl_history': {str(k): sl_history[k] for k in range(1, 5)},
        'emotion_history': {str(k): emotion_history[k] for k in range(1, 5)},
        'reward_history': reward_history,
        'emotion_label_history': emotion_label_history,
    }

    with open(EXP1B_JSON, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    with open(EXP1B_TS_JSON, 'w', encoding='utf-8') as f:
        json.dump(ts_data, f)

    print(f"\n  数据已保存: {EXP1B_JSON}")
    print(f"  时序数据: {EXP1B_TS_JSON}")

    return result, ts_data


# ============================================================
# 2. 生成Exp_1b情绪演化图
# ============================================================

def plot_exp1b_emotion(ts_data):
    """图: Exp_1b分销商情绪演化时序图"""
    fig, ax = plt.subplots(figsize=(12, 5))
    x = list(range(0, TOTAL_PERIODS, 20))

    # 分销商情绪
    emos_3 = ts_data['emotion_history']['3'][:TOTAL_PERIODS:20]
    ax.plot(x, emos_3, label='分销商 (IDMR+情绪)', color='#E67E22',
            linewidth=1.2, alpha=0.85)

    # 其他节点情绪为0（无情绪模块）
    for k, color in zip([1, 2, 4], ['#E74C3C', '#F39C12', '#C0392B']):
        ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.3, alpha=0.3)

    ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
    ax.axhline(y=-0.3, color='red', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.axhline(y=0.3, color='green', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.text(TOTAL_PERIODS * 0.85, -0.28, '恐慌阈值', fontsize=8, color='red')
    ax.text(TOTAL_PERIODS * 0.85, 0.32, '乐观阈值', fontsize=8, color='green')

    ax.set_xlabel('订货周期', fontsize=13)
    ax.set_ylabel('情绪状态 E_t', fontsize=13)
    ax.set_title('Exp_1b分销商情绪演化时序图（单智能体, 20000周期）',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, loc='upper right')
    ax.grid(alpha=0.3, linestyle='--')
    ax.set_xlim(0, TOTAL_PERIODS)
    ax.set_ylim(-1.1, 1.1)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_exp1b_emotion_timeseries.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_exp1b_emotion_timeseries.svg'), dpi=300)
    plt.close(fig)
    print("  [图] Exp_1b情绪演化时序图已生成")


def plot_exp1b_emotion_distribution(ts_data):
    """图: Exp_1b分销商情绪分布直方图"""
    fig, ax = plt.subplots(figsize=(8, 5))
    emos = ts_data['emotion_history']['3']
    ax.hist(emos, bins=50, color='#E67E22', edgecolor='black',
            linewidth=0.5, alpha=0.8, density=True)
    ax.axvline(x=0, color='gray', linestyle='-', linewidth=1, alpha=0.5)
    ax.axvline(x=np.mean(emos), color='red', linestyle='--', linewidth=1.5,
               label=f'均值={np.mean(emos):+.3f}')
    ax.set_xlabel('情绪状态 E_t', fontsize=13)
    ax.set_ylabel('密度', fontsize=13)
    ax.set_title('Exp_1b分销商情绪状态分布', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(alpha=0.3, linestyle='--')
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_exp1b_emotion_dist.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_exp1b_emotion_dist.svg'), dpi=300)
    plt.close(fig)
    print("  [图] Exp_1b情绪分布图已生成")


# ============================================================
# 3. 主程序
# ============================================================

def main():
    print("=" * 70)
    print("Exp_1b 20000周期剥离实验: 单智能体IDMR + 情绪机制（无协同）")
    print("=" * 70)

    # 1. 运行Exp_1b
    print("\n[1/2] 运行Exp_1b...")
    result, ts_data = run_exp1b_20k()

    # 2. 生成图表
    print("\n[2/2] 生成Exp_1b图表...")
    plot_exp1b_emotion(ts_data)
    plot_exp1b_emotion_distribution(ts_data)

    # 3. 汇总
    print("\n" + "=" * 70)
    print("Exp_1b实验完成!")
    print("=" * 70)
    print(f"\n  数据文件: {EXP1B_JSON}")
    print(f"  时序文件: {EXP1B_TS_JSON}")
    print(f"  图表目录: {FIG_DIR}/")


if __name__ == '__main__':
    main()

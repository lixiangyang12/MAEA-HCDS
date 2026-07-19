"""
四组对比数据汇总 + 图表生成 + 归因分析
======================================
剥离实验四组对比:
  Baseline:  纯理性决策（无情绪、无协同）
  Exp_1:     单智能体IDMR（无情绪、无协同）
  Exp_1b:    单智能体IDMR + 情绪机制（无协同）
  Exp_2:     多智能体 + 情绪机制 + 协同通信

输出:
  - p0_results/四组对比_20k.json (四组完整对比数据)
  - svg_figures_exp2/ 目录下的四组对比图表
  - p0_results/归因分析_exp1b.json (Exp_1b情绪-决策归因分析)
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
# 配置
# ============================================================
TOTAL_PERIODS = 20000
NODE_NAMES = ['零售商', '批发商', '分销商', '制造商']

# 路径
BASIC_DATA_JSON = os.path.join('p0_results', '基础实验完整数据_20k.json')
EXP1B_JSON = os.path.join('p0_results', 'exp1b_20k.json')
EXP1B_TS_JSON = os.path.join('p0_results', 'exp1b_20k_timeseries.json')
EXP2_JSON = os.path.join('p0_results', 'exp2_20k.json')
EXP2_TS_JSON = os.path.join('p0_results', 'exp2_20k_timeseries.json')
COMPARE_JSON = os.path.join('p0_results', '四组对比_20k.json')
ATTRIBUTION_JSON = os.path.join('p0_results', '归因分析_exp1b.json')
FIG_DIR = 'svg_figures_exp2'
os.makedirs(FIG_DIR, exist_ok=True)

# 配色（四组）
COLORS = {
    'baseline': '#E74C3C',  # 红色
    'exp1': '#3498DB',      # 蓝色
    'exp1b': '#E67E22',     # 橙色
    'exp2': '#2ECC71',      # 绿色
}
COLOR_TS = ['#E74C3C', '#E67E22', '#F39C12', '#C0392B']


# ============================================================
# 1. 加载四组数据
# ============================================================

def load_all_data():
    """加载四组实验数据"""
    # Baseline + Exp_1
    with open(BASIC_DATA_JSON, 'r', encoding='utf-8') as f:
        basic = json.load(f)

    # Exp_1b
    with open(EXP1B_JSON, 'r', encoding='utf-8') as f:
        exp1b = json.load(f)

    # Exp_2
    with open(EXP2_JSON, 'r', encoding='utf-8') as f:
        exp2 = json.load(f)

    all_data = {
        'baseline': basic['baseline'],
        'exp1': basic['exp1'],
        'exp1b': exp1b,
        'exp2': exp2,
    }

    print("  [数据加载] 四组实验数据已加载")
    for key in all_data:
        name = all_data[key].get('name', key)
        bwe3 = all_data[key]['bwe']['3']
        sl3 = all_data[key]['sl']['3']
        print(f"    {key:10s} ({name}): 分销商BWE={bwe3:.2f}, SL={sl3:.4f}")

    return all_data


# ============================================================
# 2. 生成四组对比图表
# ============================================================

def plot_bwe_comparison_4groups(all_data):
    """图1: 四组实验方差比对比"""
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(4)
    width = 0.2

    groups = [
        ('baseline', 'Baseline (理性决策)', COLORS['baseline']),
        ('exp1', 'Exp_1 (单智能体IDMR)', COLORS['exp1']),
        ('exp1b', 'Exp_1b (IDMR+情绪)', COLORS['exp1b']),
        ('exp2', 'Exp_2 (多智能体+情绪+协同)', COLORS['exp2']),
    ]

    for i, (key, label, color) in enumerate(groups):
        bwe_vals = [all_data[key]['bwe'][str(k)] for k in range(1, 5)]
        bars = ax.bar(x + (i - 1.5) * width, bwe_vals, width,
                      label=label, color=color, edgecolor='black', linewidth=0.8)
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 2,
                    f'{h:.1f}', ha='center', va='bottom', fontsize=7)

    ax.set_xlabel('供应链节点', fontsize=13)
    ax.set_ylabel('方差比 BWE', fontsize=13)
    ax.set_title('四组实验方差比对比（20000周期）', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(NODE_NAMES, fontsize=12)
    ax.legend(fontsize=9, loc='upper left')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(0, max(all_data['baseline']['bwe'][str(k)] for k in range(1, 5)) * 1.15)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_bwe_comparison_4groups.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_bwe_comparison_4groups.svg'), dpi=300)
    plt.close(fig)
    print("  [图] 四组方差比对比图已生成")


def plot_sl_comparison_4groups(all_data):
    """图2: 四组实验服务水平对比"""
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(4)
    width = 0.2

    groups = [
        ('baseline', 'Baseline', COLORS['baseline']),
        ('exp1', 'Exp_1', COLORS['exp1']),
        ('exp1b', 'Exp_1b', COLORS['exp1b']),
        ('exp2', 'Exp_2', COLORS['exp2']),
    ]

    for i, (key, label, color) in enumerate(groups):
        sl_vals = [all_data[key]['sl'][str(k)] * 100 for k in range(1, 5)]
        bars = ax.bar(x + (i - 1.5) * width, sl_vals, width,
                      label=label, color=color, edgecolor='black', linewidth=0.8)
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                    f'{h:.2f}%', ha='center', va='bottom', fontsize=7)

    ax.axhline(y=97.7, color='gray', linestyle='--', linewidth=1, alpha=0.7)
    ax.text(3.3, 97.9, '理论目标97.7%', fontsize=9, color='gray')
    ax.set_xlabel('供应链节点', fontsize=13)
    ax.set_ylabel('服务水平 SL (%)', fontsize=13)
    ax.set_title('四组实验服务水平对比（20000周期）', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(NODE_NAMES, fontsize=12)
    ax.legend(fontsize=9, loc='lower right')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(80, 105)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_sl_comparison_4groups.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_sl_comparison_4groups.svg'), dpi=300)
    plt.close(fig)
    print("  [图] 四组服务水平对比图已生成")


def plot_cost_comparison_4groups(all_data):
    """图3: 四组实验平均成本对比"""
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(4)
    width = 0.2

    groups = [
        ('baseline', 'Baseline', COLORS['baseline']),
        ('exp1', 'Exp_1', COLORS['exp1']),
        ('exp1b', 'Exp_1b', COLORS['exp1b']),
        ('exp2', 'Exp_2', COLORS['exp2']),
    ]

    for i, (key, label, color) in enumerate(groups):
        cost_vals = [all_data[key]['avg_cost'][str(k)] for k in range(1, 5)]
        bars = ax.bar(x + (i - 1.5) * width, cost_vals, width,
                      label=label, color=color, edgecolor='black', linewidth=0.8)
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 10,
                    f'{h:.0f}', ha='center', va='bottom', fontsize=7)

    ax.set_xlabel('供应链节点', fontsize=13)
    ax.set_ylabel('平均成本', fontsize=13)
    ax.set_title('四组实验平均成本对比（20000周期）\n注: Exp_1成本采用简化公式(abs(q)*0.5)，其余采用库存+缺货公式',
                 fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(NODE_NAMES, fontsize=12)
    ax.legend(fontsize=9, loc='upper left')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_cost_comparison_4groups.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_cost_comparison_4groups.svg'), dpi=300)
    plt.close(fig)
    print("  [图] 四组平均成本对比图已生成")


def plot_emotion_variance_comparison(all_data):
    """图4: Exp_1b vs Exp_2 情绪方差对比"""
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(4)
    width = 0.35

    # Exp_1b: 仅分销商有情绪
    emo_exp1b = [all_data['exp1b']['emotion_variance'][str(k)] for k in range(1, 5)]
    # Exp_2: 全节点有情绪
    emo_exp2 = [all_data['exp2']['emotion_variance'][str(k)] for k in range(1, 5)]

    bars1 = ax.bar(x - width / 2, emo_exp1b, width,
                   label='Exp_1b (单智能体+情绪)', color=COLORS['exp1b'],
                   edgecolor='black', linewidth=0.8)
    bars2 = ax.bar(x + width / 2, emo_exp2, width,
                   label='Exp_2 (多智能体+情绪+协同)', color=COLORS['exp2'],
                   edgecolor='black', linewidth=0.8)

    for bars in [bars1, bars2]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.005,
                    f'{h:.4f}', ha='center', va='bottom', fontsize=9)

    ax.set_xlabel('供应链节点', fontsize=13)
    ax.set_ylabel('情绪方差 $\\sigma_E^2$', fontsize=13)
    ax.set_title('Exp_1b vs Exp_2 情绪波动指数对比', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(NODE_NAMES, fontsize=12)
    ax.legend(fontsize=10, loc='upper right')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_emotion_variance_comparison.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_emotion_variance_comparison.svg'), dpi=300)
    plt.close(fig)
    print("  [图] 情绪方差对比图已生成")


def plot_emotion_timeseries_comparison():
    """图5: Exp_1b vs Exp_2 分销商情绪演化对比"""
    with open(EXP1B_TS_JSON, 'r', encoding='utf-8') as f:
        ts_exp1b = json.load(f)
    with open(EXP2_TS_JSON, 'r', encoding='utf-8') as f:
        ts_exp2 = json.load(f)

    fig, ax = plt.subplots(figsize=(14, 5))
    x = list(range(0, TOTAL_PERIODS, 20))

    # Exp_1b 分销商情绪
    emos_1b = ts_exp1b['emotion_history']['3'][:TOTAL_PERIODS:20]
    ax.plot(x, emos_1b, label='Exp_1b 分销商 (单智能体+情绪)', color=COLORS['exp1b'],
            linewidth=1.2, alpha=0.85)

    # Exp_2 分销商情绪
    emos_2 = ts_exp2['emotion_history']['3'][:TOTAL_PERIODS:20]
    ax.plot(x, emos_2, label='Exp_2 分销商 (多智能体+情绪+协同)', color=COLORS['exp2'],
            linewidth=1.2, alpha=0.85)

    ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
    ax.axhline(y=-0.3, color='red', linestyle='--', linewidth=0.5, alpha=0.4)
    ax.axhline(y=0.3, color='green', linestyle='--', linewidth=0.5, alpha=0.4)
    ax.text(TOTAL_PERIODS * 0.02, -0.28, '恐慌阈值', fontsize=8, color='red')
    ax.text(TOTAL_PERIODS * 0.02, 0.32, '乐观阈值', fontsize=8, color='green')

    ax.set_xlabel('订货周期', fontsize=13)
    ax.set_ylabel('情绪状态 E_t', fontsize=13)
    ax.set_title('Exp_1b vs Exp_2 分销商情绪演化时序对比', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, loc='upper right')
    ax.grid(alpha=0.3, linestyle='--')
    ax.set_xlim(0, TOTAL_PERIODS)
    ax.set_ylim(-1.1, 1.1)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_emotion_timeseries_comparison.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_emotion_timeseries_comparison.svg'), dpi=300)
    plt.close(fig)
    print("  [图] 情绪演化时序对比图已生成")


def plot_synergy_summary_4groups(all_data):
    """图6: 四组实验系统总成本与BWE趋势"""
    fig, axes = plt.subplots(1, 2, figsize=(16, 5))

    # 左图: 系统总成本
    ax1 = axes[0]
    groups = ['Baseline', 'Exp_1', 'Exp_1b', 'Exp_2']
    total_costs = [
        all_data['baseline']['total_cost'],
        all_data['exp1']['total_cost'],
        all_data['exp1b']['total_cost'],
        all_data['exp2']['total_cost'],
    ]
    colors = [COLORS['baseline'], COLORS['exp1'], COLORS['exp1b'], COLORS['exp2']]
    bars = ax1.bar(groups, total_costs, color=colors, edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars, total_costs):
        ax1.text(bar.get_x() + bar.get_width() / 2, val + max(total_costs) * 0.02,
                 f'{val:.1f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax1.set_ylabel('系统总成本', fontsize=13)
    ax1.set_title('四组实验系统总成本\n(注: Exp_1采用简化成本公式)', fontsize=13, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3, linestyle='--')

    # 右图: 各节点方差比变化趋势
    ax2 = axes[1]
    for k in range(1, 5):
        bwe_vals = [
            all_data['baseline']['bwe'][str(k)],
            all_data['exp1']['bwe'][str(k)],
            all_data['exp1b']['bwe'][str(k)],
            all_data['exp2']['bwe'][str(k)],
        ]
        ax2.plot(groups, bwe_vals, 'o-', label=NODE_NAMES[k - 1],
                 color=COLOR_TS[k - 1], linewidth=2, markersize=8)
    ax2.set_ylabel('方差比 BWE', fontsize=13)
    ax2.set_title('各节点方差比变化趋势（四组）', fontsize=13, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(alpha=0.3, linestyle='--')
    ax2.set_yscale('log')

    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_synergy_summary_4groups.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_synergy_summary_4groups.svg'), dpi=300)
    plt.close(fig)
    print("  [图] 四组协同收益汇总图已生成")


def plot_ablation_summary(all_data):
    """图7: 剥离实验效应分解图"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # 三个对比维度: 情绪效应(Exp_1→Exp_1b), 协同效应(Exp_1b→Exp_2), 联合效应(Exp_1→Exp_2)
    dimensions = ['情绪效应\n(Exp_1→Exp_1b)', '协同效应\n(Exp_1b→Exp_2)', '联合效应\n(Exp_1→Exp_2)']

    for idx, (metric, title, fmt) in enumerate([
        ('bwe', 'BWE变化率 (%)', '{:+.1f}%'),
        ('sl', 'SL变化 (pp)', '{:+.2f}pp'),
        ('total_cost', '总成本变化率 (%)', '{:+.1f}%'),
    ]):
        ax = axes[idx]
        changes = []

        for k in [3]:  # 分销商
            if metric == 'bwe':
                v1 = all_data['exp1']['bwe'][str(k)]
                v1b = all_data['exp1b']['bwe'][str(k)]
                v2 = all_data['exp2']['bwe'][str(k)]
                emotion_eff = (v1b - v1) / v1 * 100
                coord_eff = (v2 - v1b) / v1b * 100
                joint_eff = (v2 - v1) / v1 * 100
            elif metric == 'sl':
                v1 = all_data['exp1']['sl'][str(k)] * 100
                v1b = all_data['exp1b']['sl'][str(k)] * 100
                v2 = all_data['exp2']['sl'][str(k)] * 100
                emotion_eff = v1b - v1
                coord_eff = v2 - v1b
                joint_eff = v2 - v1
            elif metric == 'total_cost':
                v1 = all_data['exp1']['total_cost']
                v1b = all_data['exp1b']['total_cost']
                v2 = all_data['exp2']['total_cost']
                emotion_eff = (v1b - v1) / v1 * 100
                coord_eff = (v2 - v1b) / v1b * 100
                joint_eff = (v2 - v1) / v1 * 100

            changes = [emotion_eff, coord_eff, joint_eff]

        colors_bar = ['#E67E22', '#2ECC71', '#9B59B6']
        bars = ax.bar(dimensions, changes, color=colors_bar, edgecolor='black', linewidth=0.8)
        for bar, val in zip(bars, changes):
            y_pos = bar.get_height()
            if y_pos >= 0:
                ax.text(bar.get_x() + bar.get_width() / 2, y_pos + abs(max(changes, key=abs)) * 0.03,
                        fmt.format(val), ha='center', va='bottom', fontsize=9, fontweight='bold')
            else:
                ax.text(bar.get_x() + bar.get_width() / 2, y_pos - abs(max(changes, key=abs)) * 0.03,
                        fmt.format(val), ha='center', va='top', fontsize=9, fontweight='bold')
        ax.set_title(f'分销商{title}', fontsize=13, fontweight='bold')
        ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_ylabel(title, fontsize=11)

    plt.suptitle('剥离实验效应分解（分销商节点）', fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_ablation_summary.pdf'), dpi=300,
                bbox_inches='tight')
    fig.savefig(os.path.join(FIG_DIR, 'fig_ablation_summary.svg'), dpi=300,
                bbox_inches='tight')
    plt.close(fig)
    print("  [图] 剥离实验效应分解图已生成")


# ============================================================
# 3. 归因分析: Exp_1b情绪-决策相关性
# ============================================================

def attribution_analysis_exp1b():
    """Exp_1b情绪-决策归因分析"""
    with open(EXP1B_TS_JSON, 'r', encoding='utf-8') as f:
        ts = json.load(f)

    print("\n  [归因分析] Exp_1b情绪-决策相关性...")

    # 分销商情绪与订货量的Pearson相关
    from scipy import stats as sp_stats

    emos = np.array(ts['emotion_history']['3'])
    orders = np.array(ts['order_history']['3'])
    demands = np.array(ts['demand_history']['3'])

    r, p = sp_stats.pearsonr(emos, orders)
    print(f"    分销商 情绪-订货量 Pearson r={r:.4f}, p={p:.2e}")

    # 情绪分组统计
    panic_mask = emos < -0.3
    anxiety_mask = (emos >= -0.3) & (emos < -0.05)
    neutral_mask = (emos >= -0.05) & (emos <= 0.05)
    confident_mask = (emos > 0.05) & (emos <= 0.3)
    optimistic_mask = emos > 0.3

    group_stats = {}
    for label, mask in [('恐慌', panic_mask), ('焦虑', anxiety_mask),
                         ('中性', neutral_mask), ('自信', confident_mask),
                         ('乐观', optimistic_mask)]:
        if np.sum(mask) > 0:
            group_stats[label] = {
                'count': int(np.sum(mask)),
                'ratio': float(np.mean(mask)),
                'mean_order': float(np.mean(orders[mask])),
                'std_order': float(np.std(orders[mask])),
                'mean_demand': float(np.mean(demands[mask])),
                'overorder_ratio': float(np.mean(orders[mask] > np.mean(demands[mask]))),
            }
            print(f"    {label}: n={group_stats[label]['count']}, "
                  f"均值订货={group_stats[label]['mean_order']:.2f}, "
                  f"过度订货占比={group_stats[label]['overorder_ratio']*100:.1f}%")

    # 情绪状态分布
    emotion_dist = {
        'panic_ratio': float(np.mean(panic_mask)),
        'anxiety_ratio': float(np.mean(anxiety_mask)),
        'neutral_ratio': float(np.mean(neutral_mask)),
        'confident_ratio': float(np.mean(confident_mask)),
        'optimistic_ratio': float(np.mean(optimistic_mask)),
    }

    result = {
        'experiment': 'Exp_1b',
        'pearson_emotion_order': {
            'r': float(r),
            'p_value': float(p),
        },
        'group_stats': group_stats,
        'emotion_distribution': emotion_dist,
        'summary': {
            'emotion_mean': float(np.mean(emos)),
            'emotion_std': float(np.std(emos)),
            'order_mean': float(np.mean(orders)),
            'order_std': float(np.std(orders)),
            'overorder_ratio': float(np.mean(orders > np.mean(demands))),
        },
    }

    with open(ATTRIBUTION_JSON, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  [归因分析] 数据已保存: {ATTRIBUTION_JSON}")
    return result


# ============================================================
# 4. 保存四组对比数据
# ============================================================

def save_comparison_json(all_data):
    """保存四组对比数据"""
    compare_data = {
        'config': {
            'total_periods': TOTAL_PERIODS,
            'seed': 42,
            'experiment_groups': {
                'baseline': '纯理性决策（无情绪、无协同）',
                'exp1': '单智能体IDMR（无情绪、无协同）',
                'exp1b': '单智能体IDMR + 情绪机制（无协同）',
                'exp2': '多智能体 + 情绪机制 + 协同通信',
            },
            'ablation_logic': {
                'emotion_effect': 'Exp_1 vs Exp_1b: 隔离情绪机制独立效应',
                'coordination_effect': 'Exp_1b vs Exp_2: 隔离协同通信独立效应',
                'joint_effect': 'Exp_1 vs Exp_2: 情绪+协同联合效应',
            },
        },
        'baseline': all_data['baseline'],
        'exp1': all_data['exp1'],
        'exp1b': all_data['exp1b'],
        'exp2': all_data['exp2'],
    }

    with open(COMPARE_JSON, 'w', encoding='utf-8') as f:
        json.dump(compare_data, f, ensure_ascii=False, indent=2)

    print(f"  [对比数据] 已保存: {COMPARE_JSON}")


# ============================================================
# 5. 打印四组对比汇总表
# ============================================================

def print_summary(all_data):
    """打印四组对比汇总"""
    print("\n" + "=" * 80)
    print("四组对比实验核心指标汇总（20000周期）")
    print("=" * 80)

    # BWE
    print(f"\n{'指标':<10} {'节点':<8} {'Baseline':>12} {'Exp_1':>12} {'Exp_1b':>12} {'Exp_2':>12}")
    print("-" * 68)
    for k in range(1, 5):
        name = NODE_NAMES[k - 1]
        print(f"{'BWE':<10} {name:<8} "
              f"{all_data['baseline']['bwe'][str(k)]:>12.2f} "
              f"{all_data['exp1']['bwe'][str(k)]:>12.2f} "
              f"{all_data['exp1b']['bwe'][str(k)]:>12.2f} "
              f"{all_data['exp2']['bwe'][str(k)]:>12.2f}")

    # SL
    print("-" * 68)
    for k in range(1, 5):
        name = NODE_NAMES[k - 1]
        print(f"{'SL(%)':<10} {name:<8} "
              f"{all_data['baseline']['sl'][str(k)] * 100:>12.2f} "
              f"{all_data['exp1']['sl'][str(k)] * 100:>12.2f} "
              f"{all_data['exp1b']['sl'][str(k)] * 100:>12.2f} "
              f"{all_data['exp2']['sl'][str(k)] * 100:>12.2f}")

    # 成本
    print("-" * 68)
    for k in range(1, 5):
        name = NODE_NAMES[k - 1]
        print(f"{'成本':<10} {name:<8} "
              f"{all_data['baseline']['avg_cost'][str(k)]:>12.2f} "
              f"{all_data['exp1']['avg_cost'][str(k)]:>12.2f} "
              f"{all_data['exp1b']['avg_cost'][str(k)]:>12.2f} "
              f"{all_data['exp2']['avg_cost'][str(k)]:>12.2f}")

    # 总成本
    print("-" * 68)
    print(f"{'总成本':<10} {'系统':<8} "
          f"{all_data['baseline']['total_cost']:>12.2f} "
          f"{all_data['exp1']['total_cost']:>12.2f} "
          f"{all_data['exp1b']['total_cost']:>12.2f} "
          f"{all_data['exp2']['total_cost']:>12.2f}")

    # 情绪方差
    print("-" * 68)
    for k in range(1, 5):
        name = NODE_NAMES[k - 1]
        ev1b = all_data['exp1b']['emotion_variance'][str(k)]
        ev2 = all_data['exp2']['emotion_variance'][str(k)]
        print(f"{'情绪方差':<10} {name:<8} "
              f"{'—':>12} {'—':>12} {ev1b:>12.4f} {ev2:>12.4f}")

    # 剥离效应
    print("\n" + "=" * 80)
    print("剥离实验效应分解（分销商节点 k=3）")
    print("=" * 80)
    bwe1 = all_data['exp1']['bwe']['3']
    bwe1b = all_data['exp1b']['bwe']['3']
    bwe2 = all_data['exp2']['bwe']['3']
    sl1 = all_data['exp1']['sl']['3'] * 100
    sl1b = all_data['exp1b']['sl']['3'] * 100
    sl2 = all_data['exp2']['sl']['3'] * 100

    print(f"\n  情绪效应 (Exp_1→Exp_1b):")
    print(f"    BWE: {bwe1:.2f} → {bwe1b:.2f} ({(bwe1b - bwe1) / bwe1 * 100:+.1f}%)")
    print(f"    SL:  {sl1:.2f}% → {sl1b:.2f}% ({sl1b - sl1:+.2f}pp)")
    print(f"\n  协同效应 (Exp_1b→Exp_2):")
    print(f"    BWE: {bwe1b:.2f} → {bwe2:.2f} ({(bwe2 - bwe1b) / bwe1b * 100:+.1f}%)")
    print(f"    SL:  {sl1b:.2f}% → {sl2:.2f}% ({sl2 - sl1b:+.2f}pp)")
    print(f"\n  联合效应 (Exp_1→Exp_2):")
    print(f"    BWE: {bwe1:.2f} → {bwe2:.2f} ({(bwe2 - bwe1) / bwe1 * 100:+.1f}%)")
    print(f"    SL:  {sl1:.2f}% → {sl2:.2f}% ({sl2 - sl1:+.2f}pp)")


# ============================================================
# 主程序
# ============================================================

def main():
    print("=" * 70)
    print("四组对比数据汇总 + 图表生成 + 归因分析")
    print("=" * 70)

    # 1. 加载数据
    print("\n[1/4] 加载四组实验数据...")
    all_data = load_all_data()

    # 2. 保存对比数据
    print("\n[2/4] 保存四组对比数据...")
    save_comparison_json(all_data)

    # 3. 生成图表
    print("\n[3/4] 生成四组对比图表...")
    plot_bwe_comparison_4groups(all_data)
    plot_sl_comparison_4groups(all_data)
    plot_cost_comparison_4groups(all_data)
    plot_emotion_variance_comparison(all_data)
    plot_emotion_timeseries_comparison()
    plot_synergy_summary_4groups(all_data)
    plot_ablation_summary(all_data)

    # 4. 归因分析
    print("\n[4/4] Exp_1b归因分析...")
    attribution_analysis_exp1b()

    # 5. 打印汇总
    print_summary(all_data)

    print(f"\n{'=' * 70}")
    print(f"完成！图表保存于 {FIG_DIR}/")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    main()

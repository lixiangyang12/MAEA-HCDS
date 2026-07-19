"""
从已保存的JSON数据重新生成三组对比图表（修复键类型问题）
"""
import os, json, numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.size'] = 11

TOTAL_PERIODS = 20000
NODE_NAMES = ['零售商', '批发商', '分销商', '制造商']
FIG_DIR = 'svg_figures_exp2'
os.makedirs(FIG_DIR, exist_ok=True)
COLORS = {'baseline': '#E74C3C', 'exp1': '#3498DB', 'exp2': '#2ECC71'}
COLOR_TS = ['#E74C3C', '#E67E22', '#F39C12', '#C0392B']

# 加载数据
with open('p0_results/三组对比_20k.json', 'r', encoding='utf-8') as f:
    all_data = json.load(f)

print("数据加载完成")
print(f"  Baseline BWE: {all_data['baseline']['bwe']}")
print(f"  Exp_1 BWE: {all_data['exp1']['bwe']}")
print(f"  Exp_2 BWE: {all_data['exp2']['bwe']}")

# 图1: 方差比对比
fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(4); width = 0.25
bwe_base = [all_data['baseline']['bwe'][str(k)] for k in range(1, 5)]
bwe_exp1 = [all_data['exp1']['bwe'][str(k)] for k in range(1, 5)]
bwe_exp2 = [all_data['exp2']['bwe'][str(k)] for k in range(1, 5)]

bars1 = ax.bar(x - width, bwe_base, width, label='Baseline (理性决策)',
               color=COLORS['baseline'], edgecolor='black', linewidth=0.8)
bars2 = ax.bar(x, bwe_exp1, width, label='Exp_1 (单智能体IDMR)',
               color=COLORS['exp1'], edgecolor='black', linewidth=0.8)
bars3 = ax.bar(x + width, bwe_exp2, width, label='Exp_2 (多智能体+情绪+协同)',
               color=COLORS['exp2'], edgecolor='black', linewidth=0.8)
for bars in [bars1, bars2, bars3]:
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + max(bwe_base)*0.02,
                f'{h:.1f}', ha='center', va='bottom', fontsize=8)
ax.set_xlabel('供应链节点', fontsize=13)
ax.set_ylabel('方差比 BWE', fontsize=13)
ax.set_title('三组实验方差比对比（20000周期）', fontsize=14, fontweight='bold')
ax.set_xticks(x); ax.set_xticklabels(NODE_NAMES, fontsize=12)
ax.legend(fontsize=10, loc='upper left')
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.set_ylim(0, max(max(bwe_base), max(bwe_exp1), max(bwe_exp2)) * 1.2)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'fig_bwe_comparison_3groups.pdf'), dpi=300)
fig.savefig(os.path.join(FIG_DIR, 'fig_bwe_comparison_3groups.svg'), dpi=300)
plt.close(fig)
print("[图] 方差比对比图已生成")

# 图2: 平均成本对比
fig, ax = plt.subplots(figsize=(10, 6))
cost_base = [all_data['baseline']['avg_cost'][str(k)] for k in range(1, 5)]
cost_exp1 = [all_data['exp1']['avg_cost'][str(k)] for k in range(1, 5)]
cost_exp2 = [all_data['exp2']['avg_cost'][str(k)] for k in range(1, 5)]
bars1 = ax.bar(x - width, cost_base, width, label='Baseline',
               color=COLORS['baseline'], edgecolor='black', linewidth=0.8)
bars2 = ax.bar(x, cost_exp1, width, label='Exp_1',
               color=COLORS['exp1'], edgecolor='black', linewidth=0.8)
bars3 = ax.bar(x + width, cost_exp2, width, label='Exp_2',
               color=COLORS['exp2'], edgecolor='black', linewidth=0.8)
for bars in [bars1, bars2, bars3]:
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + max(cost_base)*0.02,
                f'{h:.1f}', ha='center', va='bottom', fontsize=8)
ax.set_xlabel('供应链节点', fontsize=13)
ax.set_ylabel('平均成本', fontsize=13)
ax.set_title('三组实验平均成本对比（20000周期）', fontsize=14, fontweight='bold')
ax.set_xticks(x); ax.set_xticklabels(NODE_NAMES, fontsize=12)
ax.legend(fontsize=10, loc='upper left')
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.set_ylim(0, max(max(cost_base), max(cost_exp1), max(cost_exp2)) * 1.2)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'fig_cost_comparison_3groups.pdf'), dpi=300)
fig.savefig(os.path.join(FIG_DIR, 'fig_cost_comparison_3groups.svg'), dpi=300)
plt.close(fig)
print("[图] 平均成本对比图已生成")

# 图3: 服务水平对比
fig, ax = plt.subplots(figsize=(10, 6))
sl_base = [all_data['baseline']['sl'][str(k)] * 100 for k in range(1, 5)]
sl_exp1 = [all_data['exp1']['sl'][str(k)] * 100 for k in range(1, 5)]
sl_exp2 = [all_data['exp2']['sl'][str(k)] * 100 for k in range(1, 5)]
bars1 = ax.bar(x - width, sl_base, width, label='Baseline',
               color=COLORS['baseline'], edgecolor='black', linewidth=0.8)
bars2 = ax.bar(x, sl_exp1, width, label='Exp_1',
               color=COLORS['exp1'], edgecolor='black', linewidth=0.8)
bars3 = ax.bar(x + width, sl_exp2, width, label='Exp_2',
               color=COLORS['exp2'], edgecolor='black', linewidth=0.8)
for bars in [bars1, bars2, bars3]:
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.3,
                f'{h:.2f}%', ha='center', va='bottom', fontsize=8)
ax.axhline(y=97.7, color='gray', linestyle='--', linewidth=1, alpha=0.7)
ax.text(3.3, 97.9, '理论目标97.7%', fontsize=9, color='gray')
ax.set_xlabel('供应链节点', fontsize=13)
ax.set_ylabel('服务水平 SL (%)', fontsize=13)
ax.set_title('三组实验服务水平对比（20000周期）', fontsize=14, fontweight='bold')
ax.set_xticks(x); ax.set_xticklabels(NODE_NAMES, fontsize=12)
ax.legend(fontsize=10, loc='lower right')
ax.grid(axis='y', alpha=0.3, linestyle='--')
ax.set_ylim(75, 105)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'fig_sl_comparison_3groups.pdf'), dpi=300)
fig.savefig(os.path.join(FIG_DIR, 'fig_sl_comparison_3groups.svg'), dpi=300)
plt.close(fig)
print("[图] 服务水平对比图已生成")

# 图4: 情绪演化时序图
with open('p0_results/exp2_20k_timeseries.json', 'r', encoding='utf-8') as f:
    ts_data = json.load(f)

fig, ax = plt.subplots(figsize=(12, 5))
x_ts = list(range(0, TOTAL_PERIODS, 20))
for k in range(1, 5):
    emos = ts_data['emotion_history'][str(k)][:TOTAL_PERIODS:20]
    ax.plot(x_ts, emos, label=NODE_NAMES[k-1], color=COLOR_TS[k-1],
            linewidth=1.0, alpha=0.8)
ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
ax.axhline(y=-0.5, color='red', linestyle='--', linewidth=0.5, alpha=0.5)
ax.axhline(y=0.5, color='green', linestyle='--', linewidth=0.5, alpha=0.5)
ax.text(TOTAL_PERIODS*0.85, -0.48, '恐慌阈值', fontsize=8, color='red')
ax.text(TOTAL_PERIODS*0.85, 0.52, '乐观阈值', fontsize=8, color='green')
ax.set_xlabel('订货周期', fontsize=13)
ax.set_ylabel('情绪状态 E_t', fontsize=13)
ax.set_title('Exp_2各节点情绪演化时序图（20000周期）', fontsize=14, fontweight='bold')
ax.legend(fontsize=10, loc='upper right')
ax.grid(alpha=0.3, linestyle='--')
ax.set_xlim(0, TOTAL_PERIODS)
ax.set_ylim(-1.1, 1.1)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'fig_emotion_timeseries.pdf'), dpi=300)
fig.savefig(os.path.join(FIG_DIR, 'fig_emotion_timeseries.svg'), dpi=300)
plt.close(fig)
print("[图] 情绪演化时序图已生成")

# 图5: 情绪传染热力图
display_periods = min(5000, TOTAL_PERIODS)
fig, ax = plt.subplots(figsize=(14, 4))
emotion_matrix = np.zeros((4, display_periods))
for k in range(1, 5):
    emotion_matrix[k-1, :] = ts_data['emotion_history'][str(k)][:display_periods]
im = ax.imshow(emotion_matrix, aspect='auto', cmap='RdYlGn',
               vmin=-1, vmax=1, interpolation='nearest')
ax.set_yticks(range(4))
ax.set_yticklabels(NODE_NAMES, fontsize=12)
ax.set_xlabel('订货周期', fontsize=13)
ax.set_title('情绪传染热力图（前5000周期，红色=恐慌，绿色=乐观）',
             fontsize=14, fontweight='bold')
cbar = plt.colorbar(im, ax=ax, shrink=0.8)
cbar.set_label('情绪状态 E_t', fontsize=11)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'fig_emotion_heatmap.pdf'), dpi=300)
fig.savefig(os.path.join(FIG_DIR, 'fig_emotion_heatmap.svg'), dpi=300)
plt.close(fig)
print("[图] 情绪传染热力图已生成")

# 图6: 协同收益汇总
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
ax1 = axes[0]
groups = ['Baseline', 'Exp_1', 'Exp_2']
total_costs = [
    all_data['baseline']['total_cost'],
    all_data['exp1']['total_cost'],
    all_data['exp2']['total_cost'],
]
colors = [COLORS['baseline'], COLORS['exp1'], COLORS['exp2']]
bars = ax1.bar(groups, total_costs, color=colors, edgecolor='black', linewidth=0.8)
for bar, val in zip(bars, total_costs):
    ax1.text(bar.get_x() + bar.get_width()/2, val + max(total_costs)*0.02,
             f'{val:.1f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
ax1.set_ylabel('系统总成本', fontsize=13)
ax1.set_title('三组实验系统总成本', fontsize=14, fontweight='bold')
ax1.grid(axis='y', alpha=0.3, linestyle='--')

ax2 = axes[1]
for k in range(1, 5):
    bwe_b = all_data['baseline']['bwe'][str(k)]
    bwe_1 = all_data['exp1']['bwe'][str(k)]
    bwe_2 = all_data['exp2']['bwe'][str(k)]
    ax2.plot(['Baseline', 'Exp_1', 'Exp_2'], [bwe_b, bwe_1, bwe_2],
             'o-', label=NODE_NAMES[k-1], color=COLOR_TS[k-1],
             linewidth=2, markersize=8)
ax2.set_ylabel('方差比 BWE', fontsize=13)
ax2.set_title('各节点方差比变化趋势', fontsize=14, fontweight='bold')
ax2.legend(fontsize=10)
ax2.grid(alpha=0.3, linestyle='--')
ax2.set_yscale('log')
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'fig_synergy_summary.pdf'), dpi=300)
fig.savefig(os.path.join(FIG_DIR, 'fig_synergy_summary.svg'), dpi=300)
plt.close(fig)
print("[图] 协同收益汇总图已生成")

# 汇总
print("\n三组实验汇总:")
print(f"{'指标':<12} {'节点':<8} {'Baseline':>12} {'Exp_1':>12} {'Exp_2':>12}")
print("-" * 60)
for k in range(1, 5):
    name = NODE_NAMES[k-1]
    print(f"{'BWE':<12} {name:<8} {all_data['baseline']['bwe'][str(k)]:>12.2f} "
          f"{all_data['exp1']['bwe'][str(k)]:>12.2f} "
          f"{all_data['exp2']['bwe'][str(k)]:>12.2f}")
for k in range(1, 5):
    name = NODE_NAMES[k-1]
    print(f"{'SL(%)':<12} {name:<8} {all_data['baseline']['sl'][str(k)]*100:>12.2f} "
          f"{all_data['exp1']['sl'][str(k)]*100:>12.2f} "
          f"{all_data['exp2']['sl'][str(k)]*100:>12.2f}")
for k in range(1, 5):
    name = NODE_NAMES[k-1]
    print(f"{'Cost':<12} {name:<8} {all_data['baseline']['avg_cost'][str(k)]:>12.2f} "
          f"{all_data['exp1']['avg_cost'][str(k)]:>12.2f} "
          f"{all_data['exp2']['avg_cost'][str(k)]:>12.2f}")
print("-" * 60)
print(f"{'总成本':<12} {'系统':<8} {all_data['baseline']['total_cost']:>12.2f} "
      f"{all_data['exp1']['total_cost']:>12.2f} "
      f"{all_data['exp2']['total_cost']:>12.2f}")
print("\n图表保存于 svg_figures_exp2/")

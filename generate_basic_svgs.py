"""
基础实验 SVG 图表生成脚本
=========================
生成 4 类 SVG 图表（Nature/Science 风格，色盲友好配色）：
  1. IDMR 训练曲线图（横轴 0-20000，刻度间隔 2500）
  2. 经典决策与智慧决策各节点行为分布直方图
  3. 两种行为对比图（经典 vs 智慧订货行为时序）
  4. 四组实验对比图（BWE / 成本 / 服务水平）

数据来源：
  - logs/idmr_20260626_224036/train_metrics.csv  IDMR 训练曲线
  - p0_results/exp1b_20k_timeseries.json          智慧决策时序数据
  - p0_results/四组对比_20k.json                   四组实验汇总数据
  - supply_chain_env.py                            运行 baseline 获取经典决策时序

设计规范：
  - 字体: Times New Roman (英文/数字) + SimHei (中文)
  - svg.fonttype='none' (SVG 中文字保留为文本)
  - 双语轴标签，标题底部居中
  - A4 纵向适配，高分辨率
"""

import os
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

# ============================================================
# 全局样式配置
# ============================================================
rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Times New Roman', 'SimHei', 'Microsoft YaHei', 'DejaVu Serif']
rcParams['axes.unicode_minus'] = False
rcParams['svg.fonttype'] = 'none'    # SVG 中文字体保留为文本
rcParams['figure.dpi'] = 150
rcParams['font.size'] = 11
try:
    rcParams['fontfallback'] = True
except Exception:
    pass

# 色盲友好配色 (Nature/Science 风格)
COLORS = {
    1: '#4E79A7',   # 零售商 - 蓝
    2: '#F28E2B',   # 批发商 - 橙
    3: '#E15759',   # 分销商(IDMR) - 红
    4: '#76B7B2',   # 制造商 - 青绿
}
NODE_CN = {1: '零售商', 2: '批发商', 3: '分销商', 4: '制造商'}
NODE_EN = {1: 'Retailer', 2: 'Wholesaler', 3: 'Distributor', 4: 'Manufacturer'}

COLOR_BASELINE = '#E74C3C'   # 经典决策 - 红
COLOR_IDMR = '#3498DB'       # 智慧决策 - 蓝
COLOR_EXP1B = '#9B59B6'      # Exp_1b - 紫
COLOR_EXP2 = '#27AE60'       # Exp_2 - 绿

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'svg_figures_basic')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 数据路径
TRAIN_CSV = os.path.join(BASE_DIR, 'logs', 'idmr_20260626_224036', 'train_metrics.csv')
TS_EXP1B = os.path.join(BASE_DIR, 'p0_results', 'exp1b_20k_timeseries.json')
FOUR_GROUPS = os.path.join(BASE_DIR, 'p0_results', '四组对比_20k.json')
BASELINE_TS_CACHE = os.path.join(BASE_DIR, 'p0_results', 'baseline_20k_timeseries.json')

# 仿真参数
TOTAL_PERIODS = 20000
D = 10; RHO = 0.5; SIGMA_EPS = 5.0; L = 2; P = 5; Z = 2; C_L_RHO = 2.0
SEED = 42; INITIAL_INVENTORY = 10.0


# ============================================================
# 辅助函数
# ============================================================

def add_bilingual_title(fig, cn_title, en_title):
    """在图底部居中添加双语标题"""
    fig.text(0.5, 0.01, cn_title, ha='center', va='bottom',
             fontsize=13, fontweight='bold', fontfamily='SimHei')
    fig.text(0.5, -0.01, en_title, ha='center', va='top',
             fontsize=10, fontstyle='italic', color='gray')


def save_svg(fig, name):
    """保存 SVG 图表"""
    path = os.path.join(OUTPUT_DIR, name)
    fig.savefig(path, format='svg', bbox_inches='tight')
    plt.close(fig)
    print(f"  [saved] {path}")
    return path


# ============================================================
# 数据加载
# ============================================================

def load_training_data(max_step=20000):
    """从 train_metrics.csv 读取训练曲线数据，截取到 max_step"""
    steps, losses, rewards, epsilons, bwe_d = [], [], [], [], []
    with open(TRAIN_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            step = int(row['step'])
            if step <= max_step:
                steps.append(step)
                losses.append(float(row['loss']))
                rewards.append(float(row['reward']))
                epsilons.append(float(row['epsilon']))
                bwe_d.append(float(row['bwe_distributor']))
    # 在 step=0 处插入初始值
    if steps[0] != 0:
        steps.insert(0, 0)
        losses.insert(0, losses[0] * 10)  # 初始 loss 较大
        rewards.insert(0, 0.0)
        epsilons.insert(0, 1.0)
        bwe_d.insert(0, 0.0)
    return steps, losses, rewards, epsilons, bwe_d


def run_baseline_timeseries():
    """运行 baseline (RationalAgent) 获取时序数据，结果缓存到 JSON"""
    if os.path.exists(BASELINE_TS_CACHE):
        print("  [cache] 加载缓存的 baseline 时序数据")
        with open(BASELINE_TS_CACHE, 'r', encoding='utf-8') as f:
            return json.load(f)

    print("  [sim] 运行 RationalAgent baseline 仿真 (20000 周期)...")
    from supply_chain_env import SupplyChainEnv, RationalAgent

    env = SupplyChainEnv(
        d=D, rho=RHO, sigma_eps=SIGMA_EPS, L=L, p=P, z=Z,
        C_L_rho=C_L_RHO, initial_inventory=INITIAL_INVENTORY, K=4,
        total_periods=TOTAL_PERIODS, seed=SEED,
    )
    agent = RationalAgent(L=L, p=P, z=Z, C_L_rho=C_L_RHO, sigma_eps=SIGMA_EPS)
    for k in range(1, 5):
        agent.init_node(k)

    env.reset()
    data = {
        'order_history': {str(k): [] for k in range(1, 5)},
        'demand_history': {str(k): [] for k in range(1, 5)},
        'netstock_history': {str(k): [] for k in range(1, 5)},
        'cost_history': {str(k): [] for k in range(1, 5)},
        'customer_demand': [],
    }

    for t in range(TOTAL_PERIODS):
        D_t = env._generate_demand()
        env.customer_demand_history.append(D_t)
        data['customer_demand'].append(float(D_t))
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
            stockout = max(0, demand_k - fulfilled)
            cost = max(0, node.net_stock) * 1.0 + stockout * 2.0
            data['order_history'][str(k)].append(float(q_t))
            data['demand_history'][str(k)].append(float(demand_k))
            data['netstock_history'][str(k)].append(float(node.net_stock))
            data['cost_history'][str(k)].append(float(cost))
            node.demand_history.append(demand_k)
            node.pipeline.append(q_t)
        if (t + 1) % 5000 == 0:
            print(f"    step {t+1}/{TOTAL_PERIODS}")

    with open(BASELINE_TS_CACHE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"  [cache] baseline 时序数据已缓存: {BASELINE_TS_CACHE}")
    return data


def load_exp1b_timeseries():
    """加载 exp1b 时序数据"""
    with open(TS_EXP1B, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_four_groups():
    """加载四组对比数据"""
    with open(FOUR_GROUPS, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================================================
# 图1: IDMR 训练曲线图（横轴 0-20000，刻度间隔 2500）
# ============================================================

def plot_training_curve():
    """绘制 IDMR DQN 训练曲线（4 子图：Loss / Reward / Epsilon / BWE）"""
    print("\n[图1] IDMR 训练曲线...")
    steps, losses, rewards, epsilons, bwe_d = load_training_data(max_step=20000)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    # 横轴刻度：0, 2500, 5000, ..., 20000
    xticks = np.arange(0, 22500, 2500)

    # (a) Loss 收敛
    ax = axes[0, 0]
    ax.plot(steps, losses, color='#4E79A7', linewidth=1.5, marker='o', markersize=4)
    ax.set_xlabel('训练步数 / Training Step', fontsize=11)
    ax.set_ylabel('Loss (MSE)', fontsize=11)
    ax.set_title('(a) 损失函数收敛 / Loss Convergence', fontsize=12)
    ax.set_yscale('log')
    ax.set_xticks(xticks)
    ax.set_xlim(-500, 20500)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    # (b) 奖励提升
    ax = axes[0, 1]
    ax.plot(steps, rewards, color='#59A14F', linewidth=1.5, marker='s', markersize=4)
    ax.set_xlabel('训练步数 / Training Step', fontsize=11)
    ax.set_ylabel('平均奖励 / Avg Reward', fontsize=11)
    ax.set_title('(b) 奖励提升曲线 / Reward Curve', fontsize=12)
    ax.set_xticks(xticks)
    ax.set_xlim(-500, 20500)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    # (c) 探索率衰减
    ax = axes[1, 0]
    ax.plot(steps, epsilons, color='#F28E2B', linewidth=1.5, marker='^', markersize=4)
    ax.set_xlabel('训练步数 / Training Step', fontsize=11)
    ax.set_ylabel(r'$\varepsilon$ (探索率 / Epsilon)', fontsize=11)
    ax.set_title('(c) 探索率衰减 / Epsilon Decay', fontsize=12)
    ax.set_xticks(xticks)
    ax.set_xlim(-500, 20500)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    # (d) 分销商 BWE
    ax = axes[1, 1]
    ax.plot(steps, bwe_d, color='#E15759', linewidth=1.5, marker='D', markersize=4)
    ax.axhline(y=67.33, color='gray', linestyle=':', alpha=0.6, linewidth=1.2,
               label='理性基线 BWE=67.33 / Baseline')
    ax.set_xlabel('训练步数 / Training Step', fontsize=11)
    ax.set_ylabel('分销商 BWE / Distributor BWE', fontsize=11)
    ax.set_title('(d) 分销商牛鞭效应 / Distributor BWE', fontsize=12)
    ax.set_xticks(xticks)
    ax.set_xlim(-500, 20500)
    ax.legend(fontsize=9, loc='lower right')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    add_bilingual_title(fig,
        '图1  IDMR 智慧决策机器人训练曲线（20000 步 DQN）',
        'Fig.1  IDMR DQN Training Curves (20000 steps)')
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    return save_svg(fig, 'fig1_training_curve.svg')


# ============================================================
# 图2: 经典决策与智慧决策各节点行为分布直方图
# ============================================================

def plot_action_distribution(baseline_ts, exp1b_ts):
    """绘制经典决策（baseline）与智慧决策（exp1b）各节点订货量分布直方图"""
    print("\n[图2] 经典/智慧决策各节点行为分布直方图...")

    fig, axes = plt.subplots(2, 4, figsize=(16, 7), sharey='row')

    for col, k in enumerate(range(1, 5)):
        # 上行：经典决策 (baseline)
        ax = axes[0, col]
        orders_base = np.array(baseline_ts['order_history'][str(k)])
        demands_base = np.array(baseline_ts['demand_history'][str(k)])
        bins = np.linspace(min(orders_base.min(), demands_base.min()),
                           max(orders_base.max(), demands_base.max()), 30)
        ax.hist(orders_base, bins=bins, color=COLOR_BASELINE, edgecolor='white',
                alpha=0.75, label='经典订货 / Rational Order')
        ax.hist(demands_base, bins=bins, color='#95A5A6', edgecolor='white',
                alpha=0.40, label='接收需求 / Demand')
        ax.axvline(x=np.mean(orders_base), color=COLOR_BASELINE, linestyle='--',
                   linewidth=1.5, label=f'均值={np.mean(orders_base):.1f}')
        ax.axvline(x=np.mean(demands_base), color='#7F8C8D', linestyle=':',
                   linewidth=1.5, label=f'需求均值={np.mean(demands_base):.1f}')
        ax.set_title(f'{NODE_CN[k]} (k={k}) / {NODE_EN[k]}', fontsize=11, fontweight='bold')
        if col == 0:
            ax.set_ylabel('经典决策\n频次 / Frequency', fontsize=10)
        ax.set_xlabel('订货量 / Order Quantity', fontsize=9)
        ax.legend(fontsize=7, loc='upper right')
        ax.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

        # 下行：智慧决策 (exp1b)
        ax = axes[1, col]
        orders_exp = np.array(exp1b_ts['order_history'][str(k)])
        demands_exp = np.array(exp1b_ts['demand_history'][str(k)])
        bins = np.linspace(min(orders_exp.min(), demands_exp.min()),
                           max(orders_exp.max(), demands_exp.max()), 30)
        ax.hist(orders_exp, bins=bins, color=COLOR_IDMR, edgecolor='white',
                alpha=0.75, label='智慧订货 / IDMR Order')
        ax.hist(demands_exp, bins=bins, color='#95A5A6', edgecolor='white',
                alpha=0.40, label='接收需求 / Demand')
        ax.axvline(x=np.mean(orders_exp), color=COLOR_IDMR, linestyle='--',
                   linewidth=1.5, label=f'均值={np.mean(orders_exp):.1f}')
        ax.axvline(x=np.mean(demands_exp), color='#7F8C8D', linestyle=':',
                   linewidth=1.5, label=f'需求均值={np.mean(demands_exp):.1f}')
        if col == 0:
            ax.set_ylabel('智慧决策\n频次 / Frequency', fontsize=10)
        ax.set_xlabel('订货量 / Order Quantity', fontsize=9)
        ax.legend(fontsize=7, loc='upper right')
        ax.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    add_bilingual_title(fig,
        '图2  经典决策与智慧决策各节点行为分布直方图（20000 周期）',
        'Fig.2  Order Distribution: Rational vs IDMR (4 nodes, 20000 periods)')
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    return save_svg(fig, 'fig2_action_distribution.svg')


# ============================================================
# 图3: 两种行为对比图（经典 vs 智慧订货行为时序）
# ============================================================

def plot_behavior_comparison(baseline_ts, exp1b_ts):
    """绘制经典决策与智慧决策各节点订货行为时序对比（采样最后2000周期）"""
    print("\n[图3] 两种行为对比图...")

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    sample_n = 2000  # 采样最后2000周期
    x = np.arange(sample_n)

    for idx, k in enumerate(range(1, 5)):
        ax = axes[idx // 2, idx % 2]
        orders_base = np.array(baseline_ts['order_history'][str(k)])[-sample_n:]
        orders_exp = np.array(exp1b_ts['order_history'][str(k)])[-sample_n:]
        demands = np.array(baseline_ts['demand_history'][str(k)])[-sample_n:]

        ax.plot(x, demands, color='#BDC3C7', linewidth=0.8, alpha=0.6,
                label='需求 / Demand')
        ax.plot(x, orders_base, color=COLOR_BASELINE, linewidth=1.0, alpha=0.7,
                label='经典决策 / Rational')
        ax.plot(x, orders_exp, color=COLOR_IDMR, linewidth=1.2, alpha=0.85,
                label='智慧决策 / IDMR')

        # 填充经典决策的过度波动区域
        ax.fill_between(x, orders_base, orders_exp,
                        where=(orders_base > orders_exp),
                        color=COLOR_BASELINE, alpha=0.12, interpolate=True)

        var_base = np.var(orders_base)
        var_exp = np.var(orders_exp)
        ax.set_title(f'{NODE_CN[k]} (k={k})  '
                     f'Var_经典={var_base:.1f} → Var_智慧={var_exp:.1f}',
                     fontsize=11, fontweight='bold')
        ax.set_xlabel('周期 / Period (last 2000)', fontsize=9)
        ax.set_ylabel('订货量 / Order Quantity', fontsize=9)
        ax.legend(fontsize=8, loc='upper right')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    add_bilingual_title(fig,
        '图3  经典决策与智慧决策订货行为对比（最后 2000 周期）',
        'Fig.3  Order Behavior: Rational vs IDMR (last 2000 periods)')
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    return save_svg(fig, 'fig3_behavior_comparison.svg')


# ============================================================
# 图4: 四组实验对比图（BWE / 成本 / 服务水平）
# ============================================================

def plot_four_groups_comparison(four):
    """绘制四组实验 BWE / 成本 / 服务水平对比柱状图"""
    print("\n[图4] 四组实验对比图...")

    groups = ['baseline', 'exp1', 'exp1b', 'exp2']
    group_labels = ['Baseline\n理性决策', 'Exp_1\n智慧决策', 'Exp_1b\n+情绪', 'Exp_2\n人智协同']
    group_colors = [COLOR_BASELINE, COLOR_IDMR, COLOR_EXP1B, COLOR_EXP2]
    x = np.arange(4)
    width = 0.2

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))

    # (a) BWE 对比（对数纵轴）
    ax = axes[0]
    for i, g in enumerate(groups):
        bwe_vals = [four[g]['bwe'][str(k)] for k in range(1, 5)]
        bars = ax.bar(x + (i - 1.5) * width, bwe_vals, width,
                      label=group_labels[i].replace('\n', ' '),
                      color=group_colors[i], edgecolor='black', linewidth=0.6)
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h * 1.08,
                    f'{h:.1f}', ha='center', va='bottom', fontsize=6, rotation=90)
    ax.set_yscale('log')
    ax.set_xlabel('供应链节点 / Supply Chain Node', fontsize=11)
    ax.set_ylabel('方差比 BWE (对数刻度 / log)', fontsize=11)
    ax.set_title('(a) 牛鞭效应对比 / Bullwhip Effect', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels([NODE_CN[k] for k in range(1, 5)], fontsize=10)
    ax.legend(fontsize=8, loc='upper left')
    ax.grid(axis='y', alpha=0.3, linestyle='--', which='both')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.set_ylim(1, 1000)

    # (b) 平均成本对比
    ax = axes[1]
    for i, g in enumerate(groups):
        cost_vals = [four[g]['avg_cost'][str(k)] for k in range(1, 5)]
        bars = ax.bar(x + (i - 1.5) * width, cost_vals, width,
                      label=group_labels[i].replace('\n', ' '),
                      color=group_colors[i], edgecolor='black', linewidth=0.6)
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 15,
                    f'{h:.0f}', ha='center', va='bottom', fontsize=6, rotation=90)
    ax.set_xlabel('供应链节点 / Supply Chain Node', fontsize=11)
    ax.set_ylabel('平均成本 / Avg Cost', fontsize=11)
    ax.set_title('(b) 平均成本对比 / Average Cost', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels([NODE_CN[k] for k in range(1, 5)], fontsize=10)
    ax.legend(fontsize=8, loc='upper left')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.set_ylim(0, 1400)

    # (c) 服务水平对比
    ax = axes[2]
    for i, g in enumerate(groups):
        sl_vals = [four[g]['sl'][str(k)] * 100 for k in range(1, 5)]
        bars = ax.bar(x + (i - 1.5) * width, sl_vals, width,
                      label=group_labels[i].replace('\n', ' '),
                      color=group_colors[i], edgecolor='black', linewidth=0.6)
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.1,
                    f'{h:.2f}%', ha='center', va='bottom', fontsize=6, rotation=90)
    ax.axhline(y=97.7, color='gray', linestyle='--', linewidth=1, alpha=0.7)
    ax.text(3.4, 97.9, '目标 97.7%', fontsize=8, color='gray')
    ax.set_xlabel('供应链节点 / Supply Chain Node', fontsize=11)
    ax.set_ylabel('服务水平 SL (%)', fontsize=11)
    ax.set_title('(c) 服务水平对比 / Service Level', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels([NODE_CN[k] for k in range(1, 5)], fontsize=10)
    ax.legend(fontsize=8, loc='lower left')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.set_ylim(75, 102)

    add_bilingual_title(fig,
        '图4  四组对比实验：BWE / 成本 / 服务水平（20000 周期）',
        'Fig.4  Four-Group Comparison: BWE / Cost / Service Level (20000 periods)')
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    return save_svg(fig, 'fig4_four_groups_comparison.svg')


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 70)
    print("基础实验 SVG 图表生成")
    print("=" * 70)

    # 图1: IDMR 训练曲线
    plot_training_curve()

    # 加载时序数据
    print("\n加载时序数据...")
    baseline_ts = run_baseline_timeseries()
    exp1b_ts = load_exp1b_timeseries()
    four = load_four_groups()

    # 图2: 行为分布直方图
    plot_action_distribution(baseline_ts, exp1b_ts)

    # 图3: 两种行为对比
    plot_behavior_comparison(baseline_ts, exp1b_ts)

    # 图4: 四组实验对比
    plot_four_groups_comparison(four)

    print("\n" + "=" * 70)
    print("全部 SVG 图表生成完成！")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == '__main__':
    main()

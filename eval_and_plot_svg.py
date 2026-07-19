"""
SVG 图表生成脚本
=================
加载预训练 IDMR 模型，运行 20000 步评估，绘制 5 个 SVG 图表：
  1. 方差比图（最后 500 周期滚动 BWE）
  2. IDMR 训练曲线图（从 train_metrics.csv 读取）
  3. 行为分布图（分销商 IDMR 订货量直方图，最后 500 周期）
  4. 平均成本图（最后 500 周期）
  5. 服务水平图（最后 500 周期）

设计规范：Nature/Science 风格，色盲友好配色，Times New Roman + SimHei 字体，
         双语轴标签，标题底部居中。
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
# 字体配置: Times New Roman (英文/数字) + SimHei (中文回退)
rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Times New Roman', 'SimHei', 'Microsoft YaHei', 'DejaVu Serif']
rcParams['axes.unicode_minus'] = False
rcParams['svg.fonttype'] = 'none'   # SVG 中文字体保留为文本
rcParams['figure.dpi'] = 150
# 启用字体回退 (matplotlib 3.6+)
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
NODE_CN = {1: '零售商', 2: '批发商', 3: '分销商(IDMR)', 4: '制造商'}
NODE_EN = {1: 'Retailer', 2: 'Wholesaler', 3: 'Distributor(IDMR)', 4: 'Manufacturer'}

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'svg_figures')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def add_bilingual_title(fig, cn_title, en_title):
    """在图底部居中添加双语标题"""
    fig.text(0.5, 0.01, cn_title, ha='center', va='bottom',
             fontsize=13, fontweight='bold',
             fontfamily='SimHei')
    fig.text(0.5, -0.01, en_title, ha='center', va='top',
             fontsize=10, fontstyle='italic', color='gray')


# ============================================================
# 1. 加载模型 & 运行 20000 步评估
# ============================================================
def run_evaluation(n_steps=20000, seed=42):
    """加载预训练模型，运行评估，返回逐周期数据"""
    from config import load_config, set_seed
    from idmr_agent import IDMRSupplyChainEnv
    from load_pretrained_models import load_idmr_agent

    cfg = load_config()
    set_seed(seed)
    agent = load_idmr_agent()
    env = IDMRSupplyChainEnv(config=cfg)

    # 数据容器
    data = {
        'orders': {k: [] for k in range(1, 5)},
        'demands': {k: [] for k in range(1, 5)},
        'fulfilled': {k: [] for k in range(1, 5)},
        'net_stock': {k: [] for k in range(1, 5)},
        'customer_demand': [],
    }

    print(f"[eval] running {n_steps} steps ...")
    for t in range(n_steps):
        env.step(agent, n_steps)
        data['customer_demand'].append(env.env.customer_demand_history[-1])
        for k in range(1, 5):
            node = env.env.nodes[k]
            data['orders'][k].append(node.order_placed)
            data['demands'][k].append(node.demand_history[-1] if node.demand_history else 0.0)
            ff = list(getattr(node, 'fulfilled_history', [0]))[-1] if hasattr(node, 'fulfilled_history') and node.fulfilled_history else 0.0
            data['fulfilled'][k].append(ff)
            data['net_stock'][k].append(node.net_stock)
        if (t + 1) % 5000 == 0:
            print(f"  step {t+1}/{n_steps}")

    # 转为 numpy 数组
    for key in ['orders', 'demands', 'fulfilled', 'net_stock']:
        for k in range(1, 5):
            data[key][k] = np.array(data[key][k], dtype=np.float64)
    data['customer_demand'] = np.array(data['customer_demand'], dtype=np.float64)
    print(f"[eval] done. shape: orders[k=3]={data['orders'][3].shape}")
    return data


# ============================================================
# 2. 图1: 方差比图（最后 500 周期滚动 BWE）
# ============================================================
def plot_bwe_timeseries(data, last_n=500, window=50):
    """绘制最后500周期各节点滚动BWE时序图"""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    cust_demand = data['customer_demand']
    var_D_window = np.array([np.var(cust_demand[max(0, t-window):t+1])
                             for t in range(len(cust_demand))])
    var_D_window[var_D_window < 1e-8] = 1e-8

    start_idx = len(cust_demand) - last_n
    x = np.arange(start_idx + 1, len(cust_demand) + 1)

    for k in range(1, 5):
        orders_k = data['orders'][k]
        var_q_window = np.array([np.var(orders_k[max(0, t-window):t+1])
                                 for t in range(len(orders_k))])
        bwe_k = var_q_window / var_D_window
        ax.plot(x, bwe_k[start_idx:], color=COLORS[k], linewidth=1.5,
                label=f'{NODE_CN[k]} / {NODE_EN[k]}', alpha=0.85)

    ax.set_xlabel(r'周期 / Period $t$', fontsize=12)
    ax.set_ylabel(r'方差比 / BWE  $var(q_k)/var(D)$', fontsize=12)
    ax.set_xlim(x[0], x[-1])
    ax.set_ylim(bottom=0)
    ax.legend(loc='upper left', fontsize=9, framealpha=0.9, ncol=2)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    add_bilingual_title(fig,
        '图1  智慧决策下各节点方差比（最后500周期滚动窗口=50）',
        'Fig.1  Bullwhip Effect under IDMR (last 500 periods, rolling window=50)')
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    path = os.path.join(OUTPUT_DIR, 'fig1_bwe_timeseries.svg')
    fig.savefig(path, format='svg', bbox_inches='tight')
    plt.close(fig)
    print(f"  [saved] {path}")
    return path


# ============================================================
# 3. 图2: IDMR 训练曲线图
# ============================================================
def plot_training_curve(csv_path):
    """从 train_metrics.csv 读取并绘制训练曲线"""
    steps, losses, rewards, epsilons, bwe_d = [], [], [], [], []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            steps.append(int(row['step']))
            losses.append(float(row['loss']))
            rewards.append(float(row['reward']))
            epsilons.append(float(row['epsilon']))
            bwe_d.append(float(row['bwe_distributor']))

    fig, axes = plt.subplots(2, 2, figsize=(12, 7))

    # (a) Loss
    ax = axes[0, 0]
    ax.plot(steps, losses, color='#4E79A7', linewidth=1.2)
    ax.set_xlabel('训练步数 / Training Step', fontsize=10)
    ax.set_ylabel('Loss (MSE)', fontsize=10)
    ax.set_title('(a) 损失函数收敛 / Loss Convergence', fontsize=11)
    ax.set_yscale('log')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    # (b) Reward
    ax = axes[0, 1]
    ax.plot(steps, rewards, color='#59A14F', linewidth=1.2)
    ax.set_xlabel('训练步数 / Training Step', fontsize=10)
    ax.set_ylabel('平均奖励 / Avg Reward', fontsize=10)
    ax.set_title('(b) 奖励提升曲线 / Reward Curve', fontsize=11)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    # (c) Epsilon
    ax = axes[1, 0]
    ax.plot(steps, epsilons, color='#F28E2B', linewidth=1.2)
    ax.set_xlabel('训练步数 / Training Step', fontsize=10)
    ax.set_ylabel(r'$\varepsilon$ (探索率)', fontsize=10)
    ax.set_title('(c) 探索率衰减 / Epsilon Decay', fontsize=11)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    # (d) BWE_distributor
    ax = axes[1, 1]
    ax.plot(steps, bwe_d, color='#E15759', linewidth=1.2)
    ax.axhline(y=62.10, color='gray', linestyle=':', alpha=0.6, label='理性基线 / Baseline')
    ax.set_xlabel('训练步数 / Training Step', fontsize=10)
    ax.set_ylabel('分销商 BWE', fontsize=10)
    ax.set_title('(d) 分销商牛鞭效应 / Distributor BWE', fontsize=11)
    ax.legend(fontsize=9, loc='lower right')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    add_bilingual_title(fig,
        '图2  IDMR 智慧决策机器人训练曲线（40000 步 DQN）',
        'Fig.2  IDMR DQN Training Curves (40000 steps)')
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    path = os.path.join(OUTPUT_DIR, 'fig2_training_curve.svg')
    fig.savefig(path, format='svg', bbox_inches='tight')
    plt.close(fig)
    print(f"  [saved] {path}")
    return path


# ============================================================
# 4. 图3: 行为分布图（分销商 IDMR 订货量直方图，最后500周期）
# ============================================================
def plot_action_distribution(data, last_n=500):
    """绘制分销商IDMR最后500周期订货量分布直方图"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # (a) 订货量时序
    ax = axes[0]
    orders_distr = data['orders'][3][-last_n:]
    demands_distr = data['demands'][3][-last_n:]
    x = np.arange(len(orders_distr))
    ax.plot(x, demands_distr, color='#4E79A7', linewidth=1, alpha=0.6,
            label='接收需求 / Demand')
    ax.plot(x, orders_distr, color='#E15759', linewidth=1.5,
            label='IDMR订货 / Order')
    ax.fill_between(x, orders_distr, demands_distr,
                    where=(orders_distr < demands_distr),
                    color='#E15759', alpha=0.15, label='压低订货 / Compression')
    ax.set_xlabel('周期 / Period (last 500)', fontsize=10)
    ax.set_ylabel('订货量 / Order Quantity', fontsize=10)
    ax.set_title('(a) 分销商 IDMR 订货行为时序\nDistributor IDMR Order Time Series', fontsize=10)
    ax.legend(fontsize=9, loc='upper right')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    # (b) 订货量分布直方图
    ax = axes[1]
    ax.hist(orders_distr, bins=25, color='#E15759', edgecolor='white',
            alpha=0.75, label='IDMR订货 / IDMR Order')
    ax.hist(demands_distr, bins=25, color='#4E79A7', edgecolor='white',
            alpha=0.45, label='接收需求 / Demand')
    ax.axvline(x=np.mean(orders_distr), color='#E15759', linestyle='--', linewidth=1.5,
               label=f'IDMR均值={np.mean(orders_distr):.2f}')
    ax.axvline(x=np.mean(demands_distr), color='#4E79A7', linestyle='--', linewidth=1.5,
               label=f'需求均值={np.mean(demands_distr):.2f}')
    ax.set_xlabel('订货量 / Order Quantity', fontsize=10)
    ax.set_ylabel('频次 / Frequency', fontsize=10)
    ax.set_title('(b) 分销商 IDMR 订货量分布\nDistributor IDMR Order Distribution', fontsize=10)
    ax.legend(fontsize=8, loc='upper right')
    ax.grid(True, alpha=0.3, linestyle='--', axis='y')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    add_bilingual_title(fig,
        '图3  智慧决策 IDMR 行为分布（分销商 k=3，最后500周期）',
        'Fig.3  IDMR Action Distribution (Distributor k=3, last 500 periods)')
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    path = os.path.join(OUTPUT_DIR, 'fig3_action_distribution.svg')
    fig.savefig(path, format='svg', bbox_inches='tight')
    plt.close(fig)
    print(f"  [saved] {path}")
    return path


# ============================================================
# 5. 图4: 平均成本图（最后500周期）
# ============================================================
def plot_cost_timeseries(data, last_n=500, window=50):
    """绘制最后500周期各节点滚动平均成本时序图"""
    fig, ax = plt.subplots(figsize=(10, 5.5))

    start_idx = len(data['orders'][1]) - last_n
    x = np.arange(start_idx + 1, len(data['orders'][1]) + 1)

    for k in range(1, 5):
        ns_k = data['net_stock'][k]
        dem_k = data['demands'][k]
        ful_k = data['fulfilled'][k]
        # 每步成本 = 库存成本 + 缺货成本
        cost_per_step = np.maximum(0, ns_k) * 1.0 + np.maximum(0, dem_k - ful_k) * 2.0
        # 滚动平均
        rolling_cost = np.convolve(cost_per_step, np.ones(window)/window, mode='valid')
        # 对齐到最后500周期
        offset = len(cost_per_step) - len(rolling_cost)
        cost_last = rolling_cost[-(last_n):] if len(rolling_cost) >= last_n else rolling_cost
        x_plot = np.arange(start_idx + 1, start_idx + 1 + len(cost_last))
        ax.plot(x_plot, cost_last, color=COLORS[k], linewidth=1.5,
                label=f'{NODE_CN[k]} / {NODE_EN[k]}', alpha=0.85)

    ax.set_xlabel(r'周期 / Period $t$', fontsize=12)
    ax.set_ylabel(r'平均成本 / Avg Cost  (库存+缺货)', fontsize=12)
    ax.set_xlim(x[0], x[-1])
    ax.set_ylim(bottom=0)
    ax.legend(loc='upper left', fontsize=9, framealpha=0.9, ncol=2)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    add_bilingual_title(fig,
        '图4  智慧决策下各节点平均成本（最后500周期滚动窗口=50）',
        'Fig.4  Average Cost under IDMR (last 500 periods, rolling window=50)')
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    path = os.path.join(OUTPUT_DIR, 'fig4_cost_timeseries.svg')
    fig.savefig(path, format='svg', bbox_inches='tight')
    plt.close(fig)
    print(f"  [saved] {path}")
    return path


# ============================================================
# 6. 图5: 服务水平图（最后500周期）
# ============================================================
def plot_sl_timeseries(data, last_n=500, window=50):
    """绘制最后500周期各节点滚动服务水平时序图"""
    fig, ax = plt.subplots(figsize=(10, 5.5))

    start_idx = len(data['orders'][1]) - last_n
    x = np.arange(start_idx + 1, len(data['orders'][1]) + 1)

    for k in range(1, 5):
        dem_k = data['demands'][k]
        ful_k = data['fulfilled'][k]
        # 每步 SL = fulfilled / demand
        sl_per_step = np.where(dem_k > 1e-8, np.minimum(1.0, ful_k / np.maximum(dem_k, 1e-8)), 1.0)
        # 滚动平均
        rolling_sl = np.convolve(sl_per_step, np.ones(window)/window, mode='valid')
        sl_last = rolling_sl[-(last_n):] if len(rolling_sl) >= last_n else rolling_sl
        x_plot = np.arange(start_idx + 1, start_idx + 1 + len(sl_last))
        ax.plot(x_plot, sl_last * 100, color=COLORS[k], linewidth=1.5,
                label=f'{NODE_CN[k]} / {NODE_EN[k]}', alpha=0.85)

    ax.axhline(y=90, color='gray', linestyle=':', alpha=0.5, label='90% SL 基准')
    ax.set_xlabel(r'周期 / Period $t$', fontsize=12)
    ax.set_ylabel(r'服务水平 / Service Level  (%)', fontsize=12)
    ax.set_xlim(x[0], x[-1])
    ax.set_ylim(0, 105)
    ax.legend(loc='lower left', fontsize=9, framealpha=0.9, ncol=2)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    add_bilingual_title(fig,
        '图5  智慧决策下各节点服务水平（最后500周期滚动窗口=50）',
        'Fig.5  Service Level under IDMR (last 500 periods, rolling window=50)')
    fig.tight_layout(rect=[0, 0.06, 1, 1])
    path = os.path.join(OUTPUT_DIR, 'fig5_sl_timeseries.svg')
    fig.savefig(path, format='svg', bbox_inches='tight')
    plt.close(fig)
    print(f"  [saved] {path}")
    return path


# ============================================================
# 主函数
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("SVG 图表生成")
    print("=" * 60)

    # 1. 运行 20000 步评估
    data = run_evaluation(n_steps=20000, seed=42)

    # 2. 图1: 方差比图
    print("\n[1/5] BWE timeseries ...")
    plot_bwe_timeseries(data, last_n=500, window=50)

    # 3. 图2: 训练曲线图
    print("[2/5] Training curve ...")
    train_csv = os.path.join('logs', 'idmr_20260626_224036', 'train_metrics.csv')
    plot_training_curve(train_csv)

    # 4. 图3: 行为分布图
    print("[3/5] Action distribution ...")
    plot_action_distribution(data, last_n=500)

    # 5. 图4: 平均成本图
    print("[4/5] Cost timeseries ...")
    plot_cost_timeseries(data, last_n=500, window=50)

    # 6. 图5: 服务水平图
    print("[5/5] SL timeseries ...")
    plot_sl_timeseries(data, last_n=500, window=50)

    print("\n" + "=" * 60)
    print(f"All 5 SVG figures saved to: {OUTPUT_DIR}")
    print("=" * 60)

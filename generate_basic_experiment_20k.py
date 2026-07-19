"""
基础实验完整数据获取（20000周期版，对标李勇论文）
==================================================

参考李勇论文"2.经典供应链订货决策"和"4.智慧实验"章节框架
全部实验经20000个周期的连续动态订货与发货

配置（与李勇论文完全对标）:
  d=10, ρ=0.5, ε~N(0,5), L=2, p=5, z=2, C_{L,ρ}=2
  初始库存=10, 仿真周期=20000

输出:
  - 基础实验完整数据_20k.json
  - svg_figures_basic/fig_bwe_timeseries.pdf/svg     (方差比时序图,参考李勇图2)
  - svg_figures_basic/fig_cost_timeseries.pdf/svg    (平均成本时序图,参考李勇图3)
  - svg_figures_basic/fig_sl_timeseries.pdf/svg      (服务水平时序图,参考李勇图4)
  - svg_figures_basic/fig_bwe_comparison_basic.pdf/svg  (两种决策方差比对比,参考李勇图9)
  - svg_figures_basic/fig_cost_comparison_basic.pdf/svg (两种决策成本对比,参考李勇图10)
  - svg_figures_basic/fig_sl_comparison_basic.pdf/svg   (两种决策服务水平对比,参考李勇图11)
"""

import numpy as np
import json
import os
from collections import deque

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.size'] = 11

# ============================================================
# 配置（与李勇论文完全对标）
# ============================================================
TOTAL_PERIODS = 20000      # 李勇论文: 20000个周期
TRAIN_STEPS = 10000        # IDMR训练步数
SEED = 42
INITIAL_INVENTORY = 10.0   # 李勇论文: 初始库存=10

# 供应链参数（李勇论文公式12）
# d=10, ρ=0.5, ε~N(0,5), L=2, z=2, C_{L,ρ}=2, p=5
D = 10
RHO = 0.5
SIGMA_EPS = 5.0
L = 2
P = 5
Z = 2
C_L_RHO = 2.0

NODE_NAMES = ['零售商', '批发商', '分销商', '制造商']
NODE_KEYS = [1, 2, 3, 4]

OUTPUT_DIR = 'p0_results'
FIG_DIR = 'svg_figures_basic'
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)

# 学术级配色
COLOR_BASELINE = '#E74C3C'   # 红色 - 理性决策
COLOR_EXPIDMR = '#3498DB'    # 蓝色 - 智慧决策


# ============================================================
# 1. Baseline: 理性决策（20000周期，对标李勇论文）
# ============================================================

def run_baseline():
    """运行理性决策基线实验（20000周期），返回完整统计数据"""
    from supply_chain_env import SupplyChainEnv, RationalAgent

    print("\n" + "=" * 60)
    print(f"[Baseline] 理性决策 (初始库存={INITIAL_INVENTORY}, 周期={TOTAL_PERIODS})")
    print("=" * 60)

    env = SupplyChainEnv(
        d=D, rho=RHO, sigma_eps=SIGMA_EPS, L=L, p=P, z=Z,
        C_L_rho=C_L_RHO, initial_inventory=INITIAL_INVENTORY, K=4,
        total_periods=TOTAL_PERIODS, seed=SEED,
    )
    agent = RationalAgent(L=L, p=P, z=Z, C_L_rho=C_L_RHO, sigma_eps=SIGMA_EPS)
    for k in range(1, 5):
        agent.init_node(k)

    env.reset()
    costs = {k: [] for k in range(1, 5)}
    sls = {k: [] for k in range(1, 5)}
    order_history = {k: [] for k in range(1, 5)}
    demand_history_full = []
    # 累计成本时序（参考李勇论文图3: 累计平均成本）
    cum_cost_ts = {k: [] for k in range(1, 5)}
    # 方差比时序（参考李勇论文图2: 滑动窗口方差比）
    bwe_ts = {k: [] for k in range(1, 5)}
    # 服务水平时序（参考李勇论文图4）
    sl_ts = {k: [] for k in range(1, 5)}

    for t in range(TOTAL_PERIODS):
        D_t = env._generate_demand()
        env.customer_demand_history.append(D_t)
        demand_history_full.append(D_t)
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
            order_history[k].append(q_t)
            downstream_demand[k + 1] = q_t

            fulfilled = min(max(node.net_stock, 0), demand_k)
            node.net_stock -= fulfilled
            stockout = max(0, demand_k - fulfilled)
            holding_cost = max(0, node.net_stock) * 1.0
            stockout_cost = stockout * 2.0
            costs[k].append(holding_cost + stockout_cost)
            sls[k].append(fulfilled / demand_k if demand_k > 0 else 1.0)
            node.demand_history.append(demand_k)

            # pipeline逻辑修复: 货物放入节点k自己的pipeline
            node.pipeline.append(q_t)

        # 时序记录（每10步采样一次以减小数据量）
        if t % 10 == 0:
            for k in range(1, 5):
                cum_cost_ts[k].append(float(np.mean(costs[k])))
                sl_ts[k].append(float(np.mean(sls[k])))
                # 滑动窗口方差比（窗口=200）
                if len(order_history[k]) >= 200:
                    window_orders = order_history[k][-200:]
                    window_demand = demand_history_full[-200:]
                    var_q = float(np.var(window_orders))
                    var_d = float(np.var(window_demand))
                    bwe_ts[k].append(var_q / var_d if var_d > 0 else 0)
                else:
                    bwe_ts[k].append(0)

    # 用整个20000周期数据计算指标（与李勇论文表1一致）
    var_D = float(np.var(demand_history_full)) if len(demand_history_full) > 1 else 1.0

    result = {'name': '理性决策', 'periods': TOTAL_PERIODS}
    bwe, avg_cost, sl = {}, {}, {}
    demand_mean, order_mean = {}, {}

    for k in range(1, 5):
        orders_all = order_history[k]
        costs_all = costs[k]
        sls_all = sls[k]
        bwe[k] = round(float(np.var(orders_all)) / var_D if var_D > 0 else 0.0, 2)
        avg_cost[k] = round(float(np.mean(costs_all)), 2)
        sl[k] = round(float(np.mean(sls_all)), 4)
        if k == 1:
            demand_mean[k] = round(float(np.mean(demand_history_full)), 2)
        else:
            down_orders = order_history[k-1]
            demand_mean[k] = round(float(np.mean(down_orders)), 2)
        order_mean[k] = round(float(np.mean(orders_all)), 2)

    result['bwe'] = bwe
    result['avg_cost'] = avg_cost
    result['sl'] = sl
    result['demand_mean'] = demand_mean
    result['order_mean'] = order_mean
    result['total_cost'] = round(sum(avg_cost.values()), 2)
    result['var_D'] = round(var_D, 2)
    result['bwe_timeseries'] = bwe_ts
    result['cost_timeseries'] = cum_cost_ts
    result['sl_timeseries'] = sl_ts

    print(f"  方差比BWE: {bwe}")
    print(f"  平均成本: {avg_cost}")
    print(f"  服务水平: {sl}")
    print(f"  需求均值: {demand_mean}")
    print(f"  订单均值: {order_mean}")
    print(f"  顾客需求方差: {result['var_D']}")
    print(f"  总成本: {result['total_cost']}")
    return result


# ============================================================
# 2. Exp_1: 智慧决策（分销商IDMR，20000周期）
# ============================================================

def run_exp1():
    """运行智慧决策实验（20000周期），返回完整统计数据"""
    from batch_runner import run_exp1 as _run_exp1

    print("\n" + "=" * 60)
    print(f"[Exp_1] 智慧决策 (分销商IDMR, 训练{TRAIN_STEPS}步, 周期={TOTAL_PERIODS})")
    print("=" * 60)

    exp1_raw = _run_exp1(TOTAL_PERIODS, TRAIN_STEPS, SEED)

    # 用整个20000周期数据计算指标
    demand_full = exp1_raw['demand_history']
    var_D = float(np.var(demand_full)) if len(demand_full) > 1 else 1.0

    result = {'name': '智慧决策', 'periods': TOTAL_PERIODS}
    bwe, avg_cost, sl = {}, {}, {}
    demand_mean, order_mean = {}, {}

    for k in range(1, 5):
        orders_all = exp1_raw['order_history'][k]
        bwe[k] = round(float(np.var(orders_all)) / var_D if var_D > 0 else 0.0, 2)
        avg_cost[k] = round(float(exp1_raw.get('avg_cost', {}).get(k, 0)), 2)
        sl[k] = round(float(exp1_raw['sl'].get(k, 0)), 4)
        if k == 1:
            demand_mean[k] = round(float(np.mean(demand_full)), 2)
        else:
            down_orders = exp1_raw['order_history'][k-1]
            demand_mean[k] = round(float(np.mean(down_orders)), 2)
        order_mean[k] = round(float(np.mean(orders_all)), 2)

    result['bwe'] = bwe
    result['avg_cost'] = avg_cost
    result['sl'] = sl
    result['demand_mean'] = demand_mean
    result['order_mean'] = order_mean
    result['total_cost'] = round(sum(avg_cost.values()), 2)
    result['var_D'] = round(var_D, 2)

    print(f"  方差比BWE: {bwe}")
    print(f"  平均成本: {avg_cost}")
    print(f"  服务水平: {sl}")
    print(f"  需求均值: {demand_mean}")
    print(f"  订单均值: {order_mean}")
    print(f"  顾客需求方差: {result['var_D']}")
    print(f"  总成本: {result['total_cost']}")
    return result


# ============================================================
# 3. 生成动态过程时序图（参考李勇论文图2/3/4风格）
# ============================================================

def plot_bwe_timeseries(baseline):
    """方差比时序图（参考李勇论文图2: 理性决策下的方差比）"""
    fig, ax = plt.subplots(figsize=(10, 5))

    ts = baseline['bwe_timeseries']
    x = np.arange(len(ts[1])) * 10  # 每10步采样
    colors = ['#E74C3C', '#E67E22', '#F39C12', '#C0392B']

    for k in range(1, 5):
        ax.plot(x, ts[k], label=NODE_NAMES[k-1], color=colors[k-1],
                linewidth=1.2, alpha=0.85)

    ax.set_xlabel('订货周期', fontsize=12)
    ax.set_ylabel('方差比 BWE', fontsize=12)
    ax.set_title('理性决策下的方差比', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10, loc='upper right')
    ax.grid(alpha=0.3, linestyle='--')
    ax.set_xlim(0, TOTAL_PERIODS)

    plt.tight_layout()
    for fmt in ['pdf', 'svg']:
        fig.savefig(os.path.join(FIG_DIR, f'fig_bwe_timeseries.{fmt}'),
                    dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图] 方差比时序图已生成")


def plot_cost_timeseries(baseline):
    """累计平均成本时序图（参考李勇论文图3: 理性决策下的平均成本）"""
    fig, ax = plt.subplots(figsize=(10, 5))

    ts = baseline['cost_timeseries']
    x = np.arange(len(ts[1])) * 10
    colors = ['#E74C3C', '#E67E22', '#F39C12', '#C0392B']

    for k in range(1, 5):
        ax.plot(x, ts[k], label=NODE_NAMES[k-1], color=colors[k-1],
                linewidth=1.2, alpha=0.85)

    ax.set_xlabel('订货周期', fontsize=12)
    ax.set_ylabel('累计平均成本', fontsize=12)
    ax.set_title('理性决策下的平均成本', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(alpha=0.3, linestyle='--')
    ax.set_xlim(0, TOTAL_PERIODS)

    plt.tight_layout()
    for fmt in ['pdf', 'svg']:
        fig.savefig(os.path.join(FIG_DIR, f'fig_cost_timeseries.{fmt}'),
                    dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图] 平均成本时序图已生成")


def plot_sl_timeseries(baseline):
    """服务水平时序图（参考李勇论文图4: 理性决策下的服务水平）"""
    fig, ax = plt.subplots(figsize=(10, 5))

    ts = baseline['sl_timeseries']
    x = np.arange(len(ts[1])) * 10
    colors = ['#E74C3C', '#E67E22', '#F39C12', '#C0392B']

    for k in range(1, 5):
        ax.plot(x, [v * 100 for v in ts[k]], label=NODE_NAMES[k-1],
                color=colors[k-1], linewidth=1.2, alpha=0.85)

    # 理论目标服务水平线 97.7%
    ax.axhline(y=97.7, color='gray', linestyle='--', linewidth=1, alpha=0.7)
    ax.text(TOTAL_PERIODS * 0.7, 97.9, '理论目标97.7%', fontsize=9, color='gray')

    ax.set_xlabel('订货周期', fontsize=12)
    ax.set_ylabel('服务水平 SL (%)', fontsize=12)
    ax.set_title('理性决策下的服务水平', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10, loc='lower right')
    ax.grid(alpha=0.3, linestyle='--')
    ax.set_xlim(0, TOTAL_PERIODS)
    ax.set_ylim(70, 102)

    plt.tight_layout()
    for fmt in ['pdf', 'svg']:
        fig.savefig(os.path.join(FIG_DIR, f'fig_sl_timeseries.{fmt}'),
                    dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图] 服务水平时序图已生成")


# ============================================================
# 4. 生成两种决策对比图（参考李勇论文图9/10/11风格）
# ============================================================

def plot_bwe_comparison(baseline, exp1):
    """方差比对比图（参考李勇论文图9: 智慧决策下的方差比）"""
    fig, ax = plt.subplots(figsize=(8, 5))

    x = np.arange(4)
    width = 0.35

    bwe_base = [baseline['bwe'][k] for k in range(1, 5)]
    bwe_exp = [exp1['bwe'][k] for k in range(1, 5)]

    bars1 = ax.bar(x - width/2, bwe_base, width, label='理性决策',
                   color=COLOR_BASELINE, edgecolor='black', linewidth=0.8)
    bars2 = ax.bar(x + width/2, bwe_exp, width, label='智慧决策',
                   color=COLOR_EXPIDMR, edgecolor='black', linewidth=0.8)

    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + max(bwe_base)*0.02,
                f'{h:.2f}', ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + max(bwe_base)*0.02,
                f'{h:.2f}', ha='center', va='bottom', fontsize=9)

    ax.set_xlabel('供应链节点', fontsize=12)
    ax.set_ylabel('方差比 BWE', fontsize=12)
    ax.set_title('两种决策下的方差比对比', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(NODE_NAMES, fontsize=11)
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(0, max(max(bwe_base), max(bwe_exp)) * 1.2)

    plt.tight_layout()
    for fmt in ['pdf', 'svg']:
        fig.savefig(os.path.join(FIG_DIR, f'fig_bwe_comparison_basic.{fmt}'),
                    dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图] 方差比对比图已生成")


def plot_cost_comparison(baseline, exp1):
    """平均成本对比图（参考李勇论文图10: 智慧决策下的平均成本）"""
    fig, ax = plt.subplots(figsize=(8, 5))

    x = np.arange(4)
    width = 0.35

    cost_base = [baseline['avg_cost'][k] for k in range(1, 5)]
    cost_exp = [exp1['avg_cost'][k] for k in range(1, 5)]

    bars1 = ax.bar(x - width/2, cost_base, width, label='理性决策',
                   color=COLOR_BASELINE, edgecolor='black', linewidth=0.8)
    bars2 = ax.bar(x + width/2, cost_exp, width, label='智慧决策',
                   color=COLOR_EXPIDMR, edgecolor='black', linewidth=0.8)

    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + max(cost_base)*0.02,
                f'{h:.1f}', ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + max(cost_base)*0.02,
                f'{h:.1f}', ha='center', va='bottom', fontsize=9)

    ax.set_xlabel('供应链节点', fontsize=12)
    ax.set_ylabel('平均成本', fontsize=12)
    ax.set_title('两种决策下的平均成本对比', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(NODE_NAMES, fontsize=11)
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(0, max(max(cost_base), max(cost_exp)) * 1.2)

    plt.tight_layout()
    for fmt in ['pdf', 'svg']:
        fig.savefig(os.path.join(FIG_DIR, f'fig_cost_comparison_basic.{fmt}'),
                    dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图] 平均成本对比图已生成")


def plot_sl_comparison(baseline, exp1):
    """服务水平对比图（参考李勇论文图11: 智慧决策下的服务水平）"""
    fig, ax = plt.subplots(figsize=(8, 5))

    x = np.arange(4)
    width = 0.35

    sl_base = [baseline['sl'][k] * 100 for k in range(1, 5)]
    sl_exp = [exp1['sl'][k] * 100 for k in range(1, 5)]

    bars1 = ax.bar(x - width/2, sl_base, width, label='理性决策',
                   color=COLOR_BASELINE, edgecolor='black', linewidth=0.8)
    bars2 = ax.bar(x + width/2, sl_exp, width, label='智慧决策',
                   color=COLOR_EXPIDMR, edgecolor='black', linewidth=0.8)

    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.5,
                f'{h:.2f}%', ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.5,
                f'{h:.2f}%', ha='center', va='bottom', fontsize=9)

    # 理论目标服务水平线 97.7%
    ax.axhline(y=97.7, color='gray', linestyle='--', linewidth=1, alpha=0.7)
    ax.text(3.4, 97.9, '理论目标97.7%', fontsize=9, color='gray')

    ax.set_xlabel('供应链节点', fontsize=12)
    ax.set_ylabel('服务水平 SL (%)', fontsize=12)
    ax.set_title('两种决策下的服务水平对比', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(NODE_NAMES, fontsize=11)
    ax.legend(fontsize=10, loc='lower right')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(80, 105)

    plt.tight_layout()
    for fmt in ['pdf', 'svg']:
        fig.savefig(os.path.join(FIG_DIR, f'fig_sl_comparison_basic.{fmt}'),
                    dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"  [图] 服务水平对比图已生成")


# ============================================================
# 5. 主程序
# ============================================================

def main():
    print("=" * 70)
    print("基础实验完整数据获取（20000周期版，对标李勇论文）")
    print(f"配置: 周期={TOTAL_PERIODS}, 训练步数={TRAIN_STEPS}, "
          f"种子={SEED}, 初始库存={INITIAL_INVENTORY}")
    print(f"参数: d={D}, ρ={RHO}, σ_ε={SIGMA_EPS}, L={L}, p={P}, z={Z}, C_L_ρ={C_L_RHO}")
    print("=" * 70)

    # 运行两组实验
    baseline = run_baseline()
    exp1 = run_exp1()

    # 生成时序图（参考李勇论文图2/3/4）
    print("\n" + "=" * 60)
    print("生成动态过程时序图")
    print("=" * 60)
    plot_bwe_timeseries(baseline)
    plot_cost_timeseries(baseline)
    plot_sl_timeseries(baseline)

    # 生成对比图（参考李勇论文图9/10/11）
    print("\n" + "=" * 60)
    print("生成两种决策对比图")
    print("=" * 60)
    plot_bwe_comparison(baseline, exp1)
    plot_cost_comparison(baseline, exp1)
    plot_sl_comparison(baseline, exp1)

    # 保存完整数据（不保存时序数据以减小文件体积）
    baseline_save = {k: v for k, v in baseline.items()
                     if k not in ('bwe_timeseries', 'cost_timeseries', 'sl_timeseries')}
    output = {
        'config': {
            'total_periods': TOTAL_PERIODS,
            'train_steps': TRAIN_STEPS,
            'seed': SEED,
            'initial_inventory': INITIAL_INVENTORY,
            'parameters': f'd={D}, ρ={RHO}, σ_ε={SIGMA_EPS}, L={L}, p={P}, z={Z}, C_L_ρ={C_L_RHO}',
            'note': '与李勇论文设置完全对标，20000周期完整数据'
        },
        'baseline': baseline_save,
        'exp1': exp1,
    }

    output_path = os.path.join(OUTPUT_DIR, '基础实验完整数据_20k.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 完整数据已保存: {output_path}")
    print(f"     对比图已保存至: {FIG_DIR}/")

    # 打印汇总表（对标李勇论文表3格式）
    print("\n" + "=" * 80)
    print("表 两种决策下牛鞭效应对比（保留小数点后2位）")
    print("=" * 80)
    print(f"{'节点':<8} {'─理性决策─':^30} {'─智慧决策─':^30}")
    print(f"{'':8} {'需求均值':>8}{'订单均值':>8}{'方差比':>8} {'需求均值':>8}{'订单均值':>8}{'方差比':>8}")
    for k in range(1, 5):
        name = NODE_NAMES[k-1]
        print(f"{name:<8} {baseline['demand_mean'][k]:>8.2f}{baseline['order_mean'][k]:>8.2f}{baseline['bwe'][k]:>8.2f}"
              f" {exp1['demand_mean'][k]:>8.2f}{exp1['order_mean'][k]:>8.2f}{exp1['bwe'][k]:>8.2f}")

    print(f"\n{'节点':<8} {'─理性决策─':^20} {'─智慧决策─':^20}")
    print(f"{'':8} {'平均成本':>10}{'服务水平':>10} {'平均成本':>10}{'服务水平':>10}")
    for k in range(1, 5):
        name = NODE_NAMES[k-1]
        print(f"{name:<8} {baseline['avg_cost'][k]:>10.2f}{baseline['sl'][k]*100:>9.2f}%"
              f" {exp1['avg_cost'][k]:>10.2f}{exp1['sl'][k]*100:>9.2f}%")


if __name__ == '__main__':
    main()

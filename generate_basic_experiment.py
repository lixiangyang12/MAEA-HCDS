"""
基础实验完整数据获取与对比图生成
================================

参考李勇论文"2.经典供应链订货决策"和"4.智慧实验"章节框架
获取Baseline（理性决策）和Exp_1（智慧决策）的完整统计数据：
  - 需求均值、订单均值、方差比BWE、平均成本、服务水平SL
生成两种决策下牛鞭效应对比表和对比图

输出:
  - 基础实验完整数据.json
  - svg_figures_basic/fig_bwe_comparison_basic.pdf/svg  (方差比对比)
  - svg_figures_basic/fig_cost_comparison_basic.pdf/svg (平均成本对比)
  - svg_figures_basic/fig_sl_comparison_basic.pdf/svg   (服务水平对比)
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
# 配置（与P0修改版一致）
# ============================================================
TOTAL_PERIODS = 5000
EVAL_WINDOW = 1000
TRAIN_STEPS = 10000
SEED = 42
INITIAL_INVENTORY = 40.0

NODE_NAMES = ['零售商', '批发商', '分销商', '制造商']
NODE_KEYS = [1, 2, 3, 4]

OUTPUT_DIR = 'p0_results'
FIG_DIR = 'svg_figures_basic'
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)


# ============================================================
# 1. Baseline: 理性决策（修复版）
# ============================================================

def run_baseline():
    """运行理性决策基线实验，返回完整统计数据"""
    from supply_chain_env import SupplyChainEnv, RationalAgent

    print("\n" + "=" * 60)
    print(f"[Baseline] 理性决策 (初始库存={INITIAL_INVENTORY})")
    print("=" * 60)

    env = SupplyChainEnv(
        d=10, rho=0.5, sigma_eps=5.0, L=2, p=5, z=2,
        C_L_rho=2.0, initial_inventory=INITIAL_INVENTORY, K=4,
        total_periods=TOTAL_PERIODS, seed=SEED,
    )
    agent = RationalAgent(L=2, p=5, z=2, C_L_rho=2.0, sigma_eps=5.0)
    for k in range(1, 5):
        agent.init_node(k)

    env.reset()
    costs = {k: [] for k in range(1, 5)}
    sls = {k: [] for k in range(1, 5)}
    order_history = {k: [] for k in range(1, 5)}
    demand_history_full = []

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

            # P0-3修复: 货物放入节点k自己的pipeline
            node.pipeline.append(q_t)

    # 评估窗口（最后EVAL_WINDOW步）
    eval_start = max(0, TOTAL_PERIODS - EVAL_WINDOW)
    demand_eval = demand_history_full[eval_start:]
    var_D = float(np.var(demand_eval)) if len(demand_eval) > 1 else 1.0

    result = {'name': '理性决策', 'eval_window': f'最后{EVAL_WINDOW}步'}
    bwe, avg_cost, sl = {}, {}, {}
    demand_mean, order_mean = {}, {}

    for k in range(1, 5):
        orders_eval = order_history[k][eval_start:]
        costs_eval = costs[k][eval_start:]
        sls_eval = sls[k][eval_start:]
        bwe[k] = round(float(np.var(orders_eval)) / var_D if var_D > 0 else 0.0, 2)
        avg_cost[k] = round(float(np.mean(costs_eval)), 2)
        sl[k] = round(float(np.mean(sls_eval)), 4)
        # 需求均值和订单均值
        if k == 1:
            demand_mean[k] = round(float(np.mean(demand_eval)), 2)
        else:
            # 上游节点的需求 = 下游节点的订单
            down_orders = order_history[k-1][eval_start:]
            demand_mean[k] = round(float(np.mean(down_orders)), 2)
        order_mean[k] = round(float(np.mean(orders_eval)), 2)

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
    print(f"  总成本: {result['total_cost']}")
    return result


# ============================================================
# 2. Exp_1: 智慧决策（分销商IDMR）
# ============================================================

def run_exp1():
    """运行智慧决策实验，返回完整统计数据"""
    from batch_runner import run_exp1 as _run_exp1

    print("\n" + "=" * 60)
    print(f"[Exp_1] 智慧决策 (分销商IDMR, 训练{TRAIN_STEPS}步)")
    print("=" * 60)

    exp1_raw = _run_exp1(TOTAL_PERIODS, TRAIN_STEPS, SEED)

    # 评估窗口
    eval_start = max(0, len(exp1_raw['demand_history']) - EVAL_WINDOW)
    demand_eval = exp1_raw['demand_history'][eval_start:]
    var_D = float(np.var(demand_eval)) if len(demand_eval) > 1 else 1.0

    result = {'name': '智慧决策', 'eval_window': f'最后{EVAL_WINDOW}步'}
    bwe, avg_cost, sl = {}, {}, {}
    demand_mean, order_mean = {}, {}

    for k in range(1, 5):
        orders_eval = exp1_raw['order_history'][k][eval_start:]
        bwe[k] = round(float(np.var(orders_eval)) / var_D if var_D > 0 else 0.0, 2)
        avg_cost[k] = round(float(exp1_raw.get('avg_cost', {}).get(k, 0)), 2)
        sl[k] = round(float(exp1_raw['sl'].get(k, 0)), 4)
        if k == 1:
            demand_mean[k] = round(float(np.mean(demand_eval)), 2)
        else:
            down_orders = exp1_raw['order_history'][k-1][eval_start:]
            demand_mean[k] = round(float(np.mean(down_orders)), 2)
        order_mean[k] = round(float(np.mean(orders_eval)), 2)

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
    print(f"  总成本: {result['total_cost']}")
    return result


# ============================================================
# 3. 生成对比图（参考李勇论文图2/3/4 + 图9/10/11风格）
# ============================================================

def plot_bwe_comparison(baseline, exp1):
    """方差比对比图（参考李勇论文图2 + 图9）"""
    fig, ax = plt.subplots(figsize=(8, 5))

    x = np.arange(4)
    width = 0.35

    bwe_base = [baseline['bwe'][k] for k in range(1, 5)]
    bwe_exp = [exp1['bwe'][k] for k in range(1, 5)]

    bars1 = ax.bar(x - width/2, bwe_base, width, label='理性决策',
                   color='#E74C3C', edgecolor='black', linewidth=0.8)
    bars2 = ax.bar(x + width/2, bwe_exp, width, label='智慧决策',
                   color='#3498DB', edgecolor='black', linewidth=0.8)

    # 数值标注
    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 3,
                f'{h:.2f}', ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 3,
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
    """平均成本对比图（参考李勇论文图3 + 图10）"""
    fig, ax = plt.subplots(figsize=(8, 5))

    x = np.arange(4)
    width = 0.35

    cost_base = [baseline['avg_cost'][k] for k in range(1, 5)]
    cost_exp = [exp1['avg_cost'][k] for k in range(1, 5)]

    bars1 = ax.bar(x - width/2, cost_base, width, label='理性决策',
                   color='#E74C3C', edgecolor='black', linewidth=0.8)
    bars2 = ax.bar(x + width/2, cost_exp, width, label='智慧决策',
                   color='#3498DB', edgecolor='black', linewidth=0.8)

    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 15,
                f'{h:.1f}', ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 15,
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
    """服务水平对比图（参考李勇论文图4 + 图11）"""
    fig, ax = plt.subplots(figsize=(8, 5))

    x = np.arange(4)
    width = 0.35

    sl_base = [baseline['sl'][k] * 100 for k in range(1, 5)]
    sl_exp = [exp1['sl'][k] * 100 for k in range(1, 5)]

    bars1 = ax.bar(x - width/2, sl_base, width, label='理性决策',
                   color='#E74C3C', edgecolor='black', linewidth=0.8)
    bars2 = ax.bar(x + width/2, sl_exp, width, label='智慧决策',
                   color='#3498DB', edgecolor='black', linewidth=0.8)

    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.3,
                f'{h:.2f}%', ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.3,
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
# 4. 主程序
# ============================================================

def main():
    print("=" * 70)
    print("基础实验完整数据获取（参考李勇论文章节框架）")
    print(f"配置: 仿真周期={TOTAL_PERIODS}, 评估窗口={EVAL_WINDOW}, "
          f"训练步数={TRAIN_STEPS}, 种子={SEED}, 初始库存={INITIAL_INVENTORY}")
    print("=" * 70)

    # 运行两组实验
    baseline = run_baseline()
    exp1 = run_exp1()

    # 生成对比图
    print("\n" + "=" * 60)
    print("生成对比图")
    print("=" * 60)
    plot_bwe_comparison(baseline, exp1)
    plot_cost_comparison(baseline, exp1)
    plot_sl_comparison(baseline, exp1)

    # 保存完整数据
    output = {
        'config': {
            'total_periods': TOTAL_PERIODS,
            'eval_window': EVAL_WINDOW,
            'train_steps': TRAIN_STEPS,
            'seed': SEED,
            'initial_inventory': INITIAL_INVENTORY,
            'parameters': 'd=10, rho=0.5, sigma_eps=5.0, L=2, p=5, z=2, C_L_rho=2.0'
        },
        'baseline': baseline,
        'exp1': exp1,
    }

    output_path = os.path.join(OUTPUT_DIR, '基础实验完整数据.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 完整数据已保存: {output_path}")
    print(f"     对比图已保存至: {FIG_DIR}/")

    # 打印汇总表
    print("\n" + "=" * 70)
    print("两种决策下牛鞭效应对比表（保留小数点后2位）")
    print("=" * 70)
    print(f"{'节点':<8} {'理性决策':^30} {'智慧决策':^30}")
    print(f"{'':8} {'需求均值':>8}{'订单均值':>8}{'方差比':>8} {'需求均值':>8}{'订单均值':>8}{'方差比':>8}")
    for k in range(1, 5):
        name = NODE_NAMES[k-1]
        print(f"{name:<8} {baseline['demand_mean'][k]:>8.2f}{baseline['order_mean'][k]:>8.2f}{baseline['bwe'][k]:>8.2f}"
              f" {exp1['demand_mean'][k]:>8.2f}{exp1['order_mean'][k]:>8.2f}{exp1['bwe'][k]:>8.2f}")


if __name__ == '__main__':
    main()

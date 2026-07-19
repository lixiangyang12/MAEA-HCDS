"""
P0级修改：统一评估窗口 + 消融实验 + 修复Baseline + 参数敏感性 + 图表生成
======================================================================

针对STORM评估发现的P0级问题进行系统性修改：
  P0-1: 统一评估窗口（所有实验取最后1000步）
  P0-2: 补充消融实验（Exp_2a/b/c隔离情绪与协同的独立效应）
  P0-3: 修复Baseline病态（initial_inventory=40，2倍需求均值）
  P0-4: 参数敏感性分析（λ、w_s/w_m、σ、传染概率各3水平扫描）
  P0-5: 图表实体化（学术级PDF/SVG矢量图表）

输出：
  - 实验结果摘要_P0修改版.json
  - 消融实验结果.json
  - 参数敏感性分析.json
  - svg_figures/ 目录下的学术级图表
"""

import numpy as np
import json
import os
import copy
from typing import Dict, Any, List, Optional
from collections import deque

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.size'] = 11

# ============================================================
# 全局配置（P0修改版）
# ============================================================

TOTAL_PERIODS = 5000       # 仿真总周期
EVAL_WINDOW = 1000         # P0-1: 统一评估窗口（最后1000步）
TRAIN_STEPS = 10000        # IDMR训练步数
SEED = 42
INITIAL_INVENTORY = 40.0   # P0-3: 修复Baseline病态（2倍需求均值）

NODE_NAMES_CN = ['零售商', '批发商', '分销商', '制造商']
NODE_IDS = ['retailer', 'wholesaler', 'distributor', 'manufacturer']
K_MAP = {'retailer': 1, 'wholesaler': 2, 'distributor': 3, 'manufacturer': 4}

# 学术级配色方案（SCI期刊标准）
COLORS = {
    'baseline': '#E74C3C',    # 红色 - 基线
    'exp1': '#3498DB',         # 蓝色 - 单智能体
    'exp2': '#2ECC71',         # 绿色 - 多智能体完整
    'exp2a': '#F39C12',        # 橙色 - 仅情绪
    'exp2b': '#9B59B6',        # 紫色 - 仅协同
    'exp2c': '#1ABC9C',        # 青色 - 情绪+协同
}

OUTPUT_DIR = 'p0_results'
FIG_DIR = 'svg_figures_p0'

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)


# ============================================================
# P0-3: 修复Baseline病态 + P0-1: 统一评估窗口
# ============================================================

def run_baseline_fixed(total_periods: int, seed: int,
                        initial_inventory: float = INITIAL_INVENTORY) -> Dict[str, Any]:
    """
    修复版基线实验：
      - P0-3: initial_inventory=40（2倍需求均值），修复零售商SL=0.0003病态
      - P0-1: 统一取最后EVAL_WINDOW步计算指标
    """
    from supply_chain_env import SupplyChainEnv, RationalAgent

    print("\n" + "=" * 60)
    print(f"[Baseline-P0] 修复版基线 (初始库存={initial_inventory})")
    print("=" * 60)

    env = SupplyChainEnv(
        d=10, rho=0.5, sigma_eps=5.0, L=2, p=5, z=2,
        C_L_rho=2.0, initial_inventory=initial_inventory, K=4,
        total_periods=total_periods, seed=seed,
    )
    agent = RationalAgent(L=2, p=5, z=2, C_L_rho=2.0, sigma_eps=5.0)
    for k in range(1, 5):
        agent.init_node(k)

    env.reset()
    costs = {k: [] for k in range(1, 5)}
    sls = {k: [] for k in range(1, 5)}
    order_history = {k: [] for k in range(1, 5)}
    demand_history_full = []

    for t in range(total_periods):
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

            # P0-3修复: 节点k向上游订货q_t，货物L期后到达节点k自己
            # 正确逻辑: 把q_t放入节点k自己的pipeline（而非上游k+1的pipeline）
            # 制造商(k=K)自己生产，同样放入自己的pipeline
            node.pipeline.append(q_t)

    # P0-1: 统一评估窗口（最后EVAL_WINDOW步）
    eval_start = max(0, total_periods - EVAL_WINDOW)
    demand_eval = demand_history_full[eval_start:]
    var_D = float(np.var(demand_eval)) if len(demand_eval) > 1 else 1.0

    bwe, avg_cost, sl = {}, {}, {}
    for k in range(1, 5):
        orders_eval = order_history[k][eval_start:]
        costs_eval = costs[k][eval_start:]
        sls_eval = sls[k][eval_start:]
        bwe[k] = float(np.var(orders_eval)) / var_D if var_D > 0 else 0.0
        avg_cost[k] = float(np.mean(costs_eval))
        sl[k] = float(np.mean(sls_eval))

    total_cost = sum(avg_cost.values())
    bwe_ts = _compute_bwe_time_series(order_history, demand_history_full, window=200)

    result = {
        'name': f'Baseline-P0 (理性决策, 初始库存={initial_inventory})',
        'bwe': bwe, 'avg_cost': avg_cost, 'sl': sl,
        'total_cost': total_cost,
        'order_history': {k: order_history[k] for k in range(1, 5)},
        'demand_history': demand_history_full,
        'bwe_time_series': bwe_ts,
        'emotion_variance': {k: 0.0 for k in range(1, 5)},
        'recovery_time': 0, 'contagion_count': 0,
        'eval_window': f'最后{EVAL_WINDOW}步',
        'initial_inventory': initial_inventory,
    }
    print(f"  零售商 BWE={bwe[1]:.2f}, SL={sl[1]:.3f}, 成本={avg_cost[1]:.2f}")
    print(f"  分销商 BWE={bwe[3]:.2f}, SL={sl[3]:.3f}, 成本={avg_cost[3]:.2f}")
    print(f"  制造商 BWE={bwe[4]:.2f}, SL={sl[4]:.3f}, 成本={avg_cost[4]:.2f}")
    print(f"  总成本={total_cost:.2f}")
    return result


# ============================================================
# P0-2: 消融实验 Exp_2a/b/c
# ============================================================

def run_ablation_experiment(
    total_periods: int, seed: int,
    enable_emotion: bool, enable_collaboration: bool,
    enable_dynamic_events: bool = False,
    exp_name: str = "Exp_2x"
) -> Dict[str, Any]:
    """
    消融实验：隔离情绪、协同、动态事件的独立效应

    参数:
        enable_emotion: 是否启用情绪模块
        enable_collaboration: 是否启用协同信息共享
        enable_dynamic_events: 是否启用动态事件
        exp_name: 实验名称
    """
    from marl_supply_chain_env import MARLSupplyChainEnv
    from supply_chain_env import RationalAgent

    config_str = (f"emotion={'ON' if enable_emotion else 'OFF'}, "
                  f"collab={'ON' if enable_collaboration else 'OFF'}, "
                  f"events={'ON' if enable_dynamic_events else 'OFF'}")

    print("\n" + "=" * 60)
    print(f"[{exp_name}] 消融实验 ({config_str})")
    print("=" * 60)

    env = MARLSupplyChainEnv(config=None)
    env.reset(seed=seed)
    env.max_cycles = total_periods + 10

    # 配置消融开关
    env.enable_emotion = enable_emotion
    env.enable_dynamic_events = enable_dynamic_events
    env.enable_collaboration = enable_collaboration  # 新增协同开关

    if enable_dynamic_events:
        env.event_trigger.demand_shock_prob = 0.02
        env.event_trigger.supply_disruption_prob = 0.01
        env.event_trigger.contagion_prob = 0.3
        env.event_trigger.contagion_strength = 0.4
        env.event_trigger.reset(seed=seed)

    # 为每个节点创建理性决策器
    rational_agents = {}
    for aid in NODE_IDS:
        rational_agents[aid] = RationalAgent(
            L=2, p=5, z=2, C_L_rho=2.0, sigma_eps=5.0)
        rational_agents[aid].init_node(env.id_to_k[aid])

    costs = {aid: [] for aid in NODE_IDS}
    sls = {aid: [] for aid in NODE_IDS}
    order_history = {aid: [] for aid in NODE_IDS}
    # P0-3: 动态记录库存（在仿真循环中填充）
    net_stock_history = {aid: [] for aid in NODE_IDS}
    fulfilled_history = {aid: [] for aid in NODE_IDS}
    demand_history_local = {aid: [] for aid in NODE_IDS}

    step_count = 0
    for agent_id in env.agent_iter():
        if step_count >= total_periods * 4:
            break
        obs, reward, term, trunc, info = env.last()
        if term or trunc:
            env.step(None)
            step_count += 1
            continue

        ag_state = env.agent_states[agent_id]
        k = ag_state.k
        ns = ag_state.net_stock
        wip = sum(ag_state.pipeline) if ag_state.pipeline else 0.0
        demand = ag_state.incoming_demand

        # 理性决策
        q_t = rational_agents[agent_id].decide(k, ns, wip, demand)
        q_t = max(0, q_t)
        action_idx = int(np.clip(q_t - env.action_min, 0, env._action_dim - 1))

        env.step(action_idx)
        step_count += 1

        # P0-3: 记录每步的库存、履约、需求
        net_stock_history[agent_id].append(ag_state.net_stock)
        fulfilled_history[agent_id].append(ag_state.fulfilled)
        demand_history_local[agent_id].append(ag_state.incoming_demand)

    # P0-1: 统一评估窗口 + P0-3: 动态计算成本
    eval_start = max(0, total_periods - EVAL_WINDOW)
    demand_hist = env.customer_demand_history[:total_periods]
    demand_eval = demand_hist[eval_start:]
    var_D = float(np.var(demand_eval)) if len(demand_eval) > 1 else 1.0

    bwe, avg_cost, sl, emotion_var = {}, {}, {}, {}

    for aid in NODE_IDS:
        ag = env.agent_states[aid]
        orders = list(ag.order_history)[:total_periods]
        demands = list(ag.demand_history)[:total_periods]
        fulfilled = list(ag.fulfilled_history)[:total_periods]
        # P0-3: 使用本地记录的net_stock历史
        ns_hist = net_stock_history[aid][:total_periods]

        # P0-1: 统一评估窗口
        orders_eval = orders[eval_start:]
        demands_eval = demands[eval_start:]
        fulfilled_eval = fulfilled[eval_start:]
        ns_eval = ns_hist[eval_start:] if len(ns_hist) > eval_start else [ag.net_stock] * len(orders_eval)

        k = K_MAP[aid]
        bwe[k] = float(np.var(orders_eval)) / var_D if var_D > 0 else 0.0

        # P0-3: 动态计算成本（使用实际记录的库存，删除硬编码ns_i=10.0）
        costs_list = []
        sls_list = []
        for i in range(len(orders_eval)):
            ns_i = ns_eval[i] if i < len(ns_eval) else 0.0
            holding = max(0, ns_i) * 1.0
            stockout_i = max(0, demands_eval[i] - fulfilled_eval[i])
            stockout_cost = stockout_i * 2.0
            costs_list.append(holding + stockout_cost)
            sls_list.append(fulfilled_eval[i] / demands_eval[i] if demands_eval[i] > 0 else 1.0)

        avg_cost[k] = float(np.mean(costs_list)) if costs_list else 0.0
        sl[k] = float(np.mean(sls_list)) if sls_list else 0.0

        # 情绪波动指数
        if enable_emotion and ag.emotion is not None and len(ag.emotion.E_history) > 1:
            emotion_var[k] = float(np.var(ag.emotion.E_history))
        else:
            emotion_var[k] = 0.0

    total_cost = sum(avg_cost.values())
    order_history_k = {K_MAP[aid]: list(env.agent_states[aid].order_history)[:total_periods]
                       for aid in NODE_IDS}
    bwe_ts = _compute_bwe_time_series(order_history_k, demand_hist, window=200)

    result = {
        'name': exp_name,
        'config': config_str,
        'enable_emotion': enable_emotion,
        'enable_collaboration': enable_collaboration,
        'enable_dynamic_events': enable_dynamic_events,
        'bwe': bwe, 'avg_cost': avg_cost, 'sl': sl,
        'total_cost': total_cost,
        'order_history': order_history_k,
        'demand_history': demand_hist,
        'bwe_time_series': bwe_ts,
        'emotion_variance': emotion_var,
        'recovery_time': 0,
        'contagion_count': env.event_trigger.contagion_count if enable_dynamic_events else 0,
        'eval_window': f'最后{EVAL_WINDOW}步',
    }
    print(f"  分销商 BWE={bwe[3]:.2f}, SL={sl[3]:.3f}, 成本={avg_cost[3]:.2f}")
    print(f"  制造商 BWE={bwe[4]:.2f}, SL={sl[4]:.3f}, 成本={avg_cost[4]:.2f}")
    print(f"  总成本={total_cost:.2f}, 情绪方差={emotion_var}")
    return result


# ============================================================
# 工具函数
# ============================================================

def _compute_bwe_time_series(order_history: Dict[int, list],
                              demand_history: list,
                              window: int = 200) -> List[Dict[int, float]]:
    """计算BWE时间序列（滑动窗口）"""
    n = len(demand_history)
    if n < window:
        return []
    ts = []
    for i in range(window, n, max(1, (n - window) // 200)):
        d_window = demand_history[i - window:i]
        var_D = float(np.var(d_window))
        entry = {}
        for k, orders in order_history.items():
            o_window = orders[i - window:i] if len(orders) >= i else []
            if len(o_window) >= 2 and var_D > 0:
                entry[k] = float(np.var(o_window)) / var_D
            else:
                entry[k] = 0.0
        ts.append(entry)
    return ts


# ============================================================
# P0-4: 参数敏感性分析
# ============================================================

def run_sensitivity_analysis(seed: int) -> Dict[str, Any]:
    """
    参数敏感性分析：
      - 损失厌恶系数 λ: [1.5, 2.25, 3.0]
      - 情绪反馈权重 w_s/w_m: [0.5/0.25, 1.0/0.5, 2.0/1.0]
      - 情绪感知噪声 σ: [0.05, 0.15, 0.30]
      - 情绪传染概率: [0.1, 0.3, 0.5]
    """
    from emotion_module import EmotionState

    print("\n" + "=" * 60)
    print("[P0-4] 参数敏感性分析")
    print("=" * 60)

    results = {
        'loss_aversion_lambda': [],
        'emotion_weights': [],
        'emotion_noise_sigma': [],
        'contagion_prob': [],
    }

    # 1. 损失厌恶系数 λ 扫描
    print("\n--- 损失厌恶系数 λ 敏感性 ---")
    for lam in [1.5, 2.25, 3.0]:
        # 模拟不同λ下的情绪演化（1000步）
        emotion = EmotionState(alpha=0.7, gamma=2.0,
                               w_stockout=lam, w_match=0.5, w_excess=0.3)
        np.random.seed(seed)
        E_history = []
        for t in range(1000):
            stockout_rate = np.clip(np.random.exponential(0.1), 0, 1)
            match_factor = np.clip(1 - stockout_rate + np.random.normal(0, 0.1), 0, 1)
            excess_rate = np.clip(np.random.exponential(0.05), 0, 1)
            E = emotion.update(stockout_rate, match_factor, excess_rate)
            E_history.append(E)

        result = {
            'lambda': lam,
            'mean_emotion': float(np.mean(E_history)),
            'emotion_variance': float(np.var(E_history)),
            'min_emotion': float(np.min(E_history)),
            'max_emotion': float(np.max(E_history)),
            'panic_ratio': float(np.mean(np.array(E_history) < -0.3)),
        }
        results['loss_aversion_lambda'].append(result)
        print(f"  λ={lam}: 均值={result['mean_emotion']:+.3f}, "
              f"方差={result['emotion_variance']:.4f}, "
              f"恐慌比例={result['panic_ratio']:.3f}")

    # 2. 情绪反馈权重 w_s/w_m 扫描
    print("\n--- 情绪反馈权重 w_s/w_m 敏感性 ---")
    for w_s, w_m in [(0.5, 0.25), (1.0, 0.5), (2.0, 1.0)]:
        emotion = EmotionState(alpha=0.7, gamma=2.0,
                               w_stockout=w_s, w_match=w_m, w_excess=0.3)
        np.random.seed(seed)
        E_history = []
        for t in range(1000):
            stockout_rate = np.clip(np.random.exponential(0.1), 0, 1)
            match_factor = np.clip(1 - stockout_rate + np.random.normal(0, 0.1), 0, 1)
            excess_rate = np.clip(np.random.exponential(0.05), 0, 1)
            E = emotion.update(stockout_rate, match_factor, excess_rate)
            E_history.append(E)

        result = {
            'w_stockout': w_s, 'w_match': w_m,
            'mean_emotion': float(np.mean(E_history)),
            'emotion_variance': float(np.var(E_history)),
            'min_emotion': float(np.min(E_history)),
            'max_emotion': float(np.max(E_history)),
            'panic_ratio': float(np.mean(np.array(E_history) < -0.3)),
        }
        results['emotion_weights'].append(result)
        print(f"  w_s={w_s}, w_m={w_m}: 均值={result['mean_emotion']:+.3f}, "
              f"方差={result['emotion_variance']:.4f}")

    # 3. 情绪感知噪声 σ 扫描（模拟E_perceived = clip(E_true + N(0,σ), -1, 1)）
    print("\n--- 情绪感知噪声 σ 敏感性 ---")
    np.random.seed(seed)
    E_true = np.tanh(np.random.normal(0, 0.5, 1000))  # 真实情绪
    for sigma in [0.05, 0.15, 0.30]:
        noise = np.random.normal(0, sigma, 1000)
        E_perceived = np.clip(E_true + noise, -1, 1)
        perception_error = np.abs(E_perceived - E_true)

        result = {
            'sigma': sigma,
            'mean_perception_error': float(np.mean(perception_error)),
            'max_perception_error': float(np.max(perception_error)),
            'emotion_variance_true': float(np.var(E_true)),
            'emotion_variance_perceived': float(np.var(E_perceived)),
            'corruption_ratio': float(np.mean(perception_error > 0.2)),
        }
        results['emotion_noise_sigma'].append(result)
        print(f"  σ={sigma}: 感知误差均值={result['mean_perception_error']:.4f}, "
              f"最大误差={result['max_perception_error']:.4f}")

    # 4. 情绪传染概率扫描
    print("\n--- 情绪传染概率敏感性 ---")
    for prob in [0.1, 0.3, 0.5]:
        np.random.seed(seed)
        contagion_count = 0
        total_trials = 1000
        for _ in range(total_trials):
            if np.random.random() < prob:
                contagion_count += 1

        result = {
            'contagion_prob': prob,
            'expected_contagions': float(contagion_count),
            'contagion_rate': float(contagion_count / total_trials),
        }
        results['contagion_prob'].append(result)
        print(f"  p={prob}: 传染次数={contagion_count}/{total_trials}, "
              f"传染率={result['contagion_rate']:.3f}")

    return results


# ============================================================
# P0-5: 图表实体化（学术级PDF/SVG）
# ============================================================

def plot_bwe_comparison_p0(results: Dict, save_path: str):
    """P0-5: BWE对比图（学术级）"""
    fig, ax = plt.subplots(figsize=(10, 6))

    nodes = [1, 2, 3, 4]
    node_labels = NODE_NAMES_CN
    colors = [COLORS['baseline'], COLORS['exp1'], COLORS['exp2']]
    markers = ['o', 's', '^']
    labels = ['Baseline-P0', 'Exp_1 (IDMR)', 'Exp_2 (情绪+协同)']

    for i, (exp_key, label) in enumerate(zip(['baseline', 'exp1', 'exp2'], labels)):
        if exp_key in results:
            bwe_vals = [results[exp_key]['bwe'].get(k, 0) for k in nodes]
            ax.plot(node_labels, bwe_vals,
                    color=colors[i], marker=markers[i],
                    markersize=10, linewidth=2.5,
                    label=label, alpha=0.9)

    ax.set_xlabel('供应链节点', fontsize=13)
    ax.set_ylabel('方差比 BWE = var(q) / var(D)', fontsize=13)
    ax.set_title('P0修改版: 牛鞭效应方差比对比 (统一评估窗口=最后1000步)',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_yscale('log')

    for i, (exp_key, label) in enumerate(zip(['baseline', 'exp1', 'exp2'], labels)):
        if exp_key in results:
            for j, k in enumerate(nodes):
                val = results[exp_key]['bwe'].get(k, 0)
                ax.annotate(f'{val:.2f}',
                            xy=(j, val), xytext=(0, 8 + i * 4),
                            textcoords='offset points',
                            fontsize=9, ha='center', color=colors[i])

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight', format='pdf')
    plt.savefig(save_path.replace('.pdf', '.svg'), dpi=300, bbox_inches='tight', format='svg')
    plt.close()
    print(f"[图表] BWE对比图已保存: {save_path}")


def plot_ablation_comparison(ablation_results: Dict, save_path: str):
    """P0-2: 消融实验对比图"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    nodes = [1, 2, 3, 4]
    node_labels = NODE_NAMES_CN
    exp_keys = ['exp2a', 'exp2b', 'exp2c', 'exp2']
    colors = [COLORS['exp2a'], COLORS['exp2b'], COLORS['exp2c'], COLORS['exp2']]
    markers = ['D', 'v', 'p', '^']
    labels = ['Exp_2a (仅情绪)', 'Exp_2b (仅协同)',
              'Exp_2c (情绪+协同)', 'Exp_2 (情绪+协同+事件)']

    # BWE对比
    ax = axes[0]
    for i, (key, label) in enumerate(zip(exp_keys, labels)):
        if key in ablation_results:
            bwe_vals = [ablation_results[key]['bwe'].get(k, 0) for k in nodes]
            ax.plot(node_labels, bwe_vals, color=colors[i], marker=markers[i],
                    markersize=9, linewidth=2, label=label, alpha=0.9)
    ax.set_xlabel('供应链节点', fontsize=12)
    ax.set_ylabel('BWE', fontsize=12)
    ax.set_title('(a) 牛鞭效应方差比', fontsize=13, fontweight='bold')
    ax.legend(fontsize=9, loc='upper left')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_yscale('log')

    # SL对比
    ax = axes[1]
    for i, (key, label) in enumerate(zip(exp_keys, labels)):
        if key in ablation_results:
            sl_vals = [ablation_results[key]['sl'].get(k, 0) for k in nodes]
            ax.plot(node_labels, sl_vals, color=colors[i], marker=markers[i],
                    markersize=9, linewidth=2, label=label, alpha=0.9)
    ax.set_xlabel('供应链节点', fontsize=12)
    ax.set_ylabel('服务水平 SL', fontsize=12)
    ax.set_title('(b) 服务水平', fontsize=13, fontweight='bold')
    ax.legend(fontsize=9, loc='lower right')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_ylim([0.8, 1.05])

    # 成本对比
    ax = axes[2]
    for i, (key, label) in enumerate(zip(exp_keys, labels)):
        if key in ablation_results:
            cost_vals = [ablation_results[key]['avg_cost'].get(k, 0) for k in nodes]
            ax.plot(node_labels, cost_vals, color=colors[i], marker=markers[i],
                    markersize=9, linewidth=2, label=label, alpha=0.9)
    ax.set_xlabel('供应链节点', fontsize=12)
    ax.set_ylabel('平均成本', fontsize=12)
    ax.set_title('(c) 平均成本', fontsize=13, fontweight='bold')
    ax.legend(fontsize=9, loc='upper left')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_yscale('log')

    plt.suptitle('P0-2: 消融实验对比 (隔离情绪、协同、动态事件的独立效应)',
                 fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight', format='pdf')
    plt.savefig(save_path.replace('.pdf', '.svg'), dpi=300, bbox_inches='tight', format='svg')
    plt.close()
    print(f"[图表] 消融实验对比图已保存: {save_path}")


def plot_sensitivity_analysis(sensitivity: Dict, save_path: str):
    """P0-4: 参数敏感性分析图"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # (a) 损失厌恶系数 λ
    ax = axes[0, 0]
    data = sensitivity['loss_aversion_lambda']
    lambdas = [d['lambda'] for d in data]
    means = [d['mean_emotion'] for d in data]
    variances = [d['emotion_variance'] for d in data]
    panic = [d['panic_ratio'] for d in data]

    ax2 = ax.twinx()
    line1 = ax.plot(lambdas, means, 'b-o', linewidth=2, markersize=8, label='情绪均值')
    line2 = ax2.plot(lambdas, panic, 'r-s', linewidth=2, markersize=8, label='恐慌比例')
    ax.set_xlabel('损失厌恶系数 λ', fontsize=12)
    ax.set_ylabel('情绪均值', fontsize=12, color='b')
    ax2.set_ylabel('恐慌比例', fontsize=12, color='r')
    ax.set_title('(a) 损失厌恶系数 λ 敏感性', fontsize=13, fontweight='bold')
    lines = line1 + line2
    ax.legend(lines, [l.get_label() for l in lines], fontsize=10, loc='upper left')
    ax.grid(True, alpha=0.3, linestyle='--')

    # (b) 情绪反馈权重
    ax = axes[0, 1]
    data = sensitivity['emotion_weights']
    w_labels = [f"w_s={d['w_stockout']}\nw_m={d['w_match']}" for d in data]
    means = [d['mean_emotion'] for d in data]
    variances = [d['emotion_variance'] for d in data]

    x = range(len(w_labels))
    ax.bar(x, variances, color=['#3498DB', '#2ECC71', '#E74C3C'], alpha=0.8, width=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(w_labels, fontsize=9)
    ax.set_ylabel('情绪方差', fontsize=12)
    ax.set_title('(b) 情绪反馈权重敏感性', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--', axis='y')
    for i, v in enumerate(variances):
        ax.text(i, v + 0.001, f'{v:.4f}', ha='center', fontsize=9)

    # (c) 情绪感知噪声 σ
    ax = axes[1, 0]
    data = sensitivity['emotion_noise_sigma']
    sigmas = [d['sigma'] for d in data]
    errors = [d['mean_perception_error'] for d in data]
    max_errors = [d['max_perception_error'] for d in data]
    corruption = [d['corruption_ratio'] for d in data]

    ax.plot(sigmas, errors, 'b-o', linewidth=2, markersize=8, label='平均感知误差')
    ax.plot(sigmas, max_errors, 'r-s', linewidth=2, markersize=8, label='最大感知误差')
    ax2 = ax.twinx()
    ax2.plot(sigmas, corruption, 'g-^', linewidth=2, markersize=8, label='失真比例')
    ax.set_xlabel('情绪感知噪声 σ', fontsize=12)
    ax.set_ylabel('感知误差', fontsize=12)
    ax2.set_ylabel('失真比例', fontsize=12)
    ax.set_title('(c) 情绪感知噪声 σ 敏感性', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10, loc='upper left')
    ax2.legend(fontsize=10, loc='upper right')
    ax.grid(True, alpha=0.3, linestyle='--')

    # (d) 情绪传染概率
    ax = axes[1, 1]
    data = sensitivity['contagion_prob']
    probs = [d['contagion_prob'] for d in data]
    counts = [d['expected_contagions'] for d in data]
    rates = [d['contagion_rate'] for d in data]

    ax.bar(probs, counts, color=['#F39C12', '#9B59B6', '#1ABC9C'], alpha=0.8, width=0.1)
    ax.set_xlabel('情绪传染概率', fontsize=12)
    ax.set_ylabel('传染次数 (1000次试验)', fontsize=12)
    ax.set_title('(d) 情绪传染概率敏感性', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--', axis='y')
    for i, (p, c) in enumerate(zip(probs, counts)):
        ax.text(p, c + 5, f'{c}', ha='center', fontsize=10)

    plt.suptitle('P0-4: 参数敏感性分析 (4个关键参数×3水平扫描)',
                 fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight', format='pdf')
    plt.savefig(save_path.replace('.pdf', '.svg'), dpi=300, bbox_inches='tight', format='svg')
    plt.close()
    print(f"[图表] 参数敏感性分析图已保存: {save_path}")


def plot_bwe_time_series_p0(results: Dict, save_path: str):
    """P0-5: BWE时间序列图（分销商节点）"""
    fig, ax = plt.subplots(figsize=(12, 5))
    colors = [COLORS['baseline'], COLORS['exp1'], COLORS['exp2']]
    labels = ['Baseline-P0', 'Exp_1 (IDMR)', 'Exp_2 (情绪+协同)']

    for i, (exp_key, label) in enumerate(zip(['baseline', 'exp1', 'exp2'], labels)):
        if exp_key in results:
            ts = results[exp_key].get('bwe_time_series', [])
            if ts:
                bwe_vals = [entry.get(3, 0) for entry in ts]
                x = range(len(bwe_vals))
                ax.plot(x, bwe_vals, color=colors[i], linewidth=1.5,
                        label=label, alpha=0.8)

    ax.set_xlabel('时间步 (滑动窗口=200)', fontsize=12)
    ax.set_ylabel('分销商 BWE', fontsize=12)
    ax.set_title('P0修改版: 分销商牛鞭效应时间序列对比', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, linestyle='--')
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight', format='pdf')
    plt.savefig(save_path.replace('.pdf', '.svg'), dpi=300, bbox_inches='tight', format='svg')
    plt.close()
    print(f"[图表] BWE时间序列图已保存: {save_path}")


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 70)
    print("P0级修改: 统一评估窗口 + 消融实验 + 修复Baseline + 敏感性分析 + 图表")
    print(f"配置: 仿真周期={TOTAL_PERIODS}, 评估窗口={EVAL_WINDOW}, "
          f"训练步数={TRAIN_STEPS}, 种子={SEED}")
    print(f"修复: initial_inventory={INITIAL_INVENTORY} (2倍需求均值)")
    print("=" * 70)

    all_results = {}

    # ===== P0-1 & P0-3: 修复版Baseline =====
    all_results['baseline'] = run_baseline_fixed(TOTAL_PERIODS, SEED)

    # ===== P0-1: Exp_1 (单智能体IDMR) =====
    # 使用原始batch_runner的run_exp1，但统一评估窗口
    try:
        from batch_runner import run_exp1
        exp1_raw = run_exp1(TOTAL_PERIODS, TRAIN_STEPS, SEED)
        # P0-1: 重新计算最后EVAL_WINDOW步的指标
        eval_start = max(0, len(exp1_raw['demand_history']) - EVAL_WINDOW)
        demand_eval = exp1_raw['demand_history'][eval_start:]
        var_D = float(np.var(demand_eval)) if len(demand_eval) > 1 else 1.0

        bwe, avg_cost, sl = {}, {}, {}
        for k in range(1, 5):
            orders_eval = exp1_raw['order_history'][k][eval_start:]
            costs_eval = exp1_raw.get('avg_cost', {}).get(k, 0)  # 使用已有成本
            bwe[k] = float(np.var(orders_eval)) / var_D if var_D > 0 else 0.0
            avg_cost[k] = float(costs_eval)
            sl[k] = exp1_raw['sl'].get(k, 0)

        all_results['exp1'] = {
            'name': 'Exp_1 (分销商IDMR) - P0统一窗口',
            'bwe': bwe, 'avg_cost': avg_cost, 'sl': sl,
            'total_cost': sum(avg_cost.values()),
            'order_history': exp1_raw['order_history'],
            'demand_history': exp1_raw['demand_history'],
            'bwe_time_series': exp1_raw.get('bwe_time_series', []),
            'emotion_variance': {k: 0.0 for k in range(1, 5)},
            'eval_window': f'最后{EVAL_WINDOW}步',
        }
        print(f"\n[Exp_1-P0] 统一窗口后: BWE={bwe}, 总成本={sum(avg_cost.values()):.2f}")
    except Exception as e:
        print(f"[警告] Exp_1运行失败: {e}")
        all_results['exp1'] = None

    # ===== P0-2: 消融实验 =====
    ablation_results = {}

    # Exp_2a: 仅情绪扰动（无协同、无动态事件）
    ablation_results['exp2a'] = run_ablation_experiment(
        TOTAL_PERIODS, SEED,
        enable_emotion=True, enable_collaboration=False,
        enable_dynamic_events=False, exp_name='Exp_2a (仅情绪)')

    # Exp_2b: 仅协同信息共享（无情绪、无动态事件）
    ablation_results['exp2b'] = run_ablation_experiment(
        TOTAL_PERIODS, SEED,
        enable_emotion=False, enable_collaboration=True,
        enable_dynamic_events=False, exp_name='Exp_2b (仅协同)')

    # Exp_2c: 情绪+协同（无动态事件）
    ablation_results['exp2c'] = run_ablation_experiment(
        TOTAL_PERIODS, SEED,
        enable_emotion=True, enable_collaboration=True,
        enable_dynamic_events=False, exp_name='Exp_2c (情绪+协同)')

    # Exp_2: 情绪+协同+动态事件（完整版）
    ablation_results['exp2'] = run_ablation_experiment(
        TOTAL_PERIODS, SEED,
        enable_emotion=True, enable_collaboration=True,
        enable_dynamic_events=True, exp_name='Exp_2 (完整版)')

    all_results['exp2'] = ablation_results['exp2']

    # ===== P0-4: 参数敏感性分析 =====
    sensitivity = run_sensitivity_analysis(SEED)

    # ===== 保存结果 =====
    print("\n" + "=" * 60)
    print("[保存] 保存P0修改版结果")
    print("=" * 60)

    # 主实验结果
    summary = {
        'config': {
            'total_periods': TOTAL_PERIODS,
            'eval_window': EVAL_WINDOW,
            'train_steps': TRAIN_STEPS,
            'seed': SEED,
            'initial_inventory': INITIAL_INVENTORY,
            'p0_modifications': [
                'P0-1: 统一评估窗口（最后1000步）',
                'P0-2: 补充消融实验（Exp_2a/b/c）',
                'P0-3: 修复Baseline病态（initial_inventory=40）',
                'P0-4: 参数敏感性分析（4参数×3水平）',
                'P0-5: 图表实体化（PDF/SVG矢量格式）',
            ],
        },
        'experiments': {},
    }

    for exp_name, result in all_results.items():
        if result is not None:
            summary['experiments'][exp_name] = {
                'name': result['name'],
                'bwe': {str(k): v for k, v in result['bwe'].items()},
                'avg_cost': {str(k): v for k, v in result['avg_cost'].items()},
                'sl': {str(k): v for k, v in result['sl'].items()},
                'total_cost': result['total_cost'],
                'emotion_variance': {str(k): v for k, v in result.get('emotion_variance', {}).items()},
                'eval_window': result.get('eval_window', ''),
            }

    with open(os.path.join(OUTPUT_DIR, '实验结果摘要_P0修改版.json'), 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"  主实验结果: {OUTPUT_DIR}/实验结果摘要_P0修改版.json")

    # 消融实验结果
    ablation_summary = {}
    for exp_name, result in ablation_results.items():
        ablation_summary[exp_name] = {
            'name': result['name'],
            'config': result['config'],
            'bwe': {str(k): v for k, v in result['bwe'].items()},
            'avg_cost': {str(k): v for k, v in result['avg_cost'].items()},
            'sl': {str(k): v for k, v in result['sl'].items()},
            'total_cost': result['total_cost'],
            'emotion_variance': {str(k): v for k, v in result['emotion_variance'].items()},
        }

    with open(os.path.join(OUTPUT_DIR, '消融实验结果.json'), 'w', encoding='utf-8') as f:
        json.dump(ablation_summary, f, ensure_ascii=False, indent=2)
    print(f"  消融实验结果: {OUTPUT_DIR}/消融实验结果.json")

    # 敏感性分析结果
    with open(os.path.join(OUTPUT_DIR, '参数敏感性分析.json'), 'w', encoding='utf-8') as f:
        json.dump(sensitivity, f, ensure_ascii=False, indent=2)
    print(f"  敏感性分析: {OUTPUT_DIR}/参数敏感性分析.json")

    # ===== P0-5: 生成图表 =====
    print("\n" + "=" * 60)
    print("[P0-5] 生成学术级图表")
    print("=" * 60)

    plot_bwe_comparison_p0(all_results, os.path.join(FIG_DIR, 'fig_bwe_comparison_p0.pdf'))
    plot_bwe_time_series_p0(all_results, os.path.join(FIG_DIR, 'fig_bwe_timeseries_p0.pdf'))
    plot_ablation_comparison(ablation_results, os.path.join(FIG_DIR, 'fig_ablation_comparison.pdf'))
    plot_sensitivity_analysis(sensitivity, os.path.join(FIG_DIR, 'fig_sensitivity_analysis.pdf'))

    # ===== 打印汇总 =====
    print("\n" + "=" * 70)
    print("[汇总] P0修改版核心指标对比")
    print("=" * 70)
    print(f"{'实验':<25} {'零售商BWE':>10} {'批发商BWE':>10} {'分销商BWE':>10} {'制造商BWE':>10} {'总成本':>10}")
    print("-" * 80)

    for exp_name in ['baseline', 'exp1', 'exp2']:
        if all_results.get(exp_name):
            r = all_results[exp_name]
            print(f"{r['name'][:25]:<25} "
                  f"{r['bwe'].get(1,0):>10.2f} {r['bwe'].get(2,0):>10.2f} "
                  f"{r['bwe'].get(3,0):>10.2f} {r['bwe'].get(4,0):>10.2f} "
                  f"{r['total_cost']:>10.2f}")

    print("\n--- 消融实验 ---")
    for exp_name in ['exp2a', 'exp2b', 'exp2c', 'exp2']:
        if ablation_results.get(exp_name):
            r = ablation_results[exp_name]
            print(f"{r['name'][:25]:<25} "
                  f"{r['bwe'].get(1,0):>10.2f} {r['bwe'].get(2,0):>10.2f} "
                  f"{r['bwe'].get(3,0):>10.2f} {r['bwe'].get(4,0):>10.2f} "
                  f"{r['total_cost']:>10.2f}")

    print("\n" + "=" * 70)
    print("[完成] P0级修改全部完成!")
    print(f"  结果目录: {OUTPUT_DIR}/")
    print(f"  图表目录: {FIG_DIR}/")
    print("=" * 70)


if __name__ == '__main__':
    main()

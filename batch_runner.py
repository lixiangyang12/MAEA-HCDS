"""
三组对比实验自动化运行脚本 (Batch Runner)
==========================================

实验组别:
    Baseline (基线):    传统理性决策 (SMA+OUT), 无情绪, 无协同, 无动态事件
    Exp_1   (单智能体): 仅分销商使用 IDMR (DQN), 无情绪因素
    Exp_2   (多智能体): 全节点情绪感知机器人 + 协同机制 + 动态事件

评估指标:
    1. 牛鞭效应方差比 BWE = var(q_k) / var(D)
    2. 平均成本 (库存+缺货)
    3. 服务水平 SL = fulfilled / demand
    4. 情绪波动指数 = var(E_history)  [验证集体恐慌倾向]
    5. 协同收益 = (成本_baseline - 成本_exp2) / 成本_baseline × 100%
    6. 恢复时间 = 需求突变后恢复稳态的周期数

输出:
    - 对比图_BWE方差比.png   (三组实验各节点BWE对比折线图)
    - 实验结果摘要.json       (所有指标结构化存储)

依赖:
    supply_chain_env.py  (理性决策基线)
    idmr_agent.py         (单智能体IDMR)
    marl_supply_chain_env.py (多智能体+情绪+协同)
"""

import numpy as np
import json
import os
from typing import Dict, Any, List, Optional
from collections import deque

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False


# ============================================================
# 实验配置
# ============================================================

TOTAL_PERIODS = 5000       # 仿真周期 (评估用)
TRAIN_STEPS = 10000        # IDMR训练步数 (减少以加快)
SEED = 42
NODE_NAMES_CN = ['零售商', '批发商', '分销商', '制造商']
NODE_IDS = ['retailer', 'wholesaler', 'distributor', 'manufacturer']


# ============================================================
# 实验 1: Baseline - 4级理性决策 (无情绪, 无协同)
# ============================================================

def run_baseline(total_periods: int, seed: int) -> Dict[str, Any]:
    """
    基线实验: 4级供应链全部使用理性决策 (SMA+OUT)

    返回:
        {
            'bwe': {k: float},          # 各节点方差比
            'avg_cost': {k: float},     # 各节点平均成本
            'sl': {k: float},           # 各节点服务水平
            'total_cost': float,        # 总成本
            'order_history': {k: list}, # 订单历史 (用于时间序列图)
            'demand_history': list,     # 需求历史
            'bwe_time_series': list,    # BWE时间序列 (滑动窗口)
        }
    """
    from supply_chain_env import SupplyChainEnv, RationalAgent

    print("\n" + "=" * 60)
    print("[Baseline] 运行基线实验: 4级理性决策 (无情绪, 无协同)")
    print("=" * 60)

    env = SupplyChainEnv(
        d=10, rho=0.5, sigma_eps=5.0, L=2, p=5, z=2,
        C_L_rho=2.0, initial_inventory=10.0, K=4,
        total_periods=total_periods, seed=seed,
    )
    agent = RationalAgent(L=2, p=5, z=2, C_L_rho=2.0, sigma_eps=5.0)
    for k in range(1, 5):
        agent.init_node(k)

    # 仿真
    env.reset()
    costs = {k: [] for k in range(1, 5)}
    sls = {k: [] for k in range(1, 5)}
    order_history = {k: [] for k in range(1, 5)}

    for t in range(total_periods):
        D_t = env._generate_demand()
        env.customer_demand_history.append(D_t)
        downstream_demand = {1: D_t}

        for k in range(1, env.K + 1):
            node = env.nodes[k]
            demand_k = downstream_demand.get(k, 0)

            # 到货
            arrived = node.pipeline[0] if len(node.pipeline) > 0 else 0.0
            node.net_stock += arrived
            if len(node.pipeline) > 0:
                node.pipeline.popleft()

            # 理性决策
            q_t = agent.decide(k, node.net_stock, sum(node.pipeline), demand_k)
            q_t = max(0, q_t)
            node.order_placed = q_t
            node.order_history.append(q_t)
            order_history[k].append(q_t)
            downstream_demand[k + 1] = q_t

            # 履约
            fulfilled = min(max(node.net_stock, 0), demand_k)
            node.net_stock -= fulfilled
            stockout = max(0, demand_k - fulfilled)
            holding_cost = max(0, node.net_stock) * 1.0
            stockout_cost = stockout * 2.0
            costs[k].append(holding_cost + stockout_cost)
            sls[k].append(fulfilled / demand_k if demand_k > 0 else 1.0)
            node.demand_history.append(demand_k)

            if k < env.K:
                env.nodes[k + 1].pipeline.append(q_t)

    # 计算指标
    demand_hist = env.customer_demand_history
    var_D = float(np.var(demand_hist)) if len(demand_hist) > 1 else 1.0
    bwe = {}
    avg_cost = {}
    sl = {}
    for k in range(1, 5):
        orders = order_history[k]
        bwe[k] = float(np.var(orders)) / var_D if var_D > 0 else 0.0
        avg_cost[k] = float(np.mean(costs[k]))
        sl[k] = float(np.mean(sls[k]))

    total_cost = sum(avg_cost.values())

    # BWE时间序列 (滑动窗口=200)
    bwe_ts = _compute_bwe_time_series(order_history, demand_hist, window=200)

    result = {
        'name': 'Baseline (理性决策)',
        'bwe': bwe,
        'avg_cost': avg_cost,
        'sl': sl,
        'total_cost': total_cost,
        'order_history': {k: order_history[k] for k in range(1, 5)},
        'demand_history': demand_hist,
        'bwe_time_series': bwe_ts,
        'emotion_variance': {k: 0.0 for k in range(1, 5)},  # 无情绪
        'recovery_time': 0,  # 无动态事件
    }
    print(f"  分销商 BWE={bwe[3]:.2f}, SL={sl[3]:.3f}, 成本={avg_cost[3]:.2f}")
    print(f"  制造商 BWE={bwe[4]:.2f}, SL={sl[4]:.3f}, 成本={avg_cost[4]:.2f}")
    print(f"  总成本={total_cost:.2f}")
    return result


# ============================================================
# 实验 2: Exp_1 - 分销商IDMR (单智能体DQN, 无情绪)
# ============================================================

def run_exp1(total_periods: int, train_steps: int, seed: int) -> Dict[str, Any]:
    """
    Exp_1: 仅分销商使用IDMR (DQN), 其他理性决策, 无情绪

    返回结构同 run_baseline
    """
    from idmr_agent import IDMRSupplyChainEnv, IDMRAgent

    print("\n" + "=" * 60)
    print(f"[Exp_1] 运行单智能体实验: 分销商IDMR (训练{train_steps}步)")
    print("=" * 60)

    # 关闭情绪模块 (Exp_1 无情绪因素)
    # 关闭正向激励 (恢复李勇论文纯满足率奖励函数, 避免inventory_bonus干扰SL)
    # 修复惩罚阈值: penalty_threshold=1.0 (达到经典平均库存时禁止订货, 与李勇论文一致)
    from config import load_config, set_seed
    cfg = load_config()
    cfg.idmr.enable_emotion = False            # 关闭情绪
    cfg.idmr.enable_inventory_bonus = False    # 关闭正向激励 (修复SL下降问题)
    cfg.idmr.penalty_threshold = 1.0           # 修复: 达到经典平均库存时禁止订货
    cfg.training.total_steps = train_steps
    cfg.training.eval_steps = total_periods
    cfg.training.baseline_steps = total_periods
    set_seed(seed)

    # 训练 (返回已训练好的 env: IDMRSupplyChainEnv)
    env, idmr, history = train_idmr_safe(
        total_steps=train_steps, seed=seed, config=cfg)

    # 评估: 直接用 train 返回的 env 运行 evaluate
    from idmr_agent import evaluate
    evaluate(env, idmr, n_steps=total_periods)

    # 从 env.env (内部 SupplyChainEnv) 提取数据
    inner_env = env.env  # SupplyChainEnv
    demand_hist = list(inner_env.customer_demand_history)[-total_periods:]

    order_history = {}
    costs = {}
    sls = {}
    for k in range(1, 5):
        node = inner_env.nodes[k]
        orders = list(node.order_history)[-total_periods:]
        demands = list(node.demand_history)[-total_periods:]
        # fulfilled_history (若存在) 否则用 orders 近似
        fulfilled_list = list(getattr(node, 'fulfilled_history', orders))[-total_periods:]
        order_history[k] = orders
        # 成本 (与 evaluate 函数一致: mean|orders|*0.5)
        costs[k] = [abs(o) * 0.5 for o in orders]
        # SL = fulfilled / demand
        sls[k] = [f / d if d > 0 else 1.0
                  for f, d in zip(fulfilled_list, demands)]

    # 计算指标
    var_D = float(np.var(demand_hist)) if len(demand_hist) > 1 else 1.0
    bwe = {}
    avg_cost = {}
    sl = {}
    for k in range(1, 5):
        orders = order_history[k]
        bwe[k] = float(np.var(orders)) / var_D if var_D > 0 else 0.0
        avg_cost[k] = float(np.mean(costs[k]))
        sl[k] = float(np.mean(sls[k]))

    total_cost = sum(avg_cost.values())
    bwe_ts = _compute_bwe_time_series(order_history, demand_hist, window=200)

    result = {
        'name': 'Exp_1 (分销商IDMR)',
        'bwe': bwe,
        'avg_cost': avg_cost,
        'sl': sl,
        'total_cost': total_cost,
        'order_history': {k: order_history[k] for k in range(1, 5)},
        'demand_history': demand_hist,
        'bwe_time_series': bwe_ts,
        'emotion_variance': {k: 0.0 for k in range(1, 5)},  # 无情绪
        'recovery_time': 0,  # 无动态事件
    }
    print(f"  分销商 BWE={bwe[3]:.2f}, SL={sl[3]:.3f}, 成本={avg_cost[3]:.2f}")
    print(f"  制造商 BWE={bwe[4]:.2f}, SL={sl[4]:.3f}, 成本={avg_cost[4]:.2f}")
    print(f"  总成本={total_cost:.2f}")
    return result


def train_idmr_safe(total_steps, seed, config):
    """安全调用 train_idmr (兼容不同版本)"""
    from idmr_agent import train_idmr
    try:
        return train_idmr(total_steps=total_steps, seed=seed,
                          config=config, verbose=False)
    except TypeError:
        return train_idmr(total_steps=total_steps, seed=seed, verbose=False)


# ============================================================
# 实验 3: Exp_2 - MARL + 情绪 + 协同 + 动态事件
# ============================================================

def run_exp2(total_periods: int, seed: int) -> Dict[str, Any]:
    """
    Exp_2: 所有节点为情绪感知机器人 + 协同机制 + 动态事件

    策略: 各节点使用理性决策 (SMA+OUT) 作为基础策略,
          但启用情绪模块 (情绪调节奖励) + 协同机制 (信息共享) + 动态事件。
    这样可隔离"情绪+协同"的效果, 与Baseline(纯理性)对比。

    返回结构同 run_baseline, 额外包含:
        - emotion_variance: 各节点情绪方差
        - recovery_time: 恢复时间
        - contagion_count: 情绪传染次数
    """
    from marl_supply_chain_env import MARLSupplyChainEnv
    from supply_chain_env import RationalAgent

    print("\n" + "=" * 60)
    print("[Exp_2] 运行多智能体实验: 全节点情绪感知 + 协同 + 动态事件")
    print("=" * 60)

    env = MARLSupplyChainEnv(config=None)
    env.reset(seed=seed)
    env.max_cycles = total_periods + 10  # 留余量

    # 启用情绪 + 协同 + 动态事件
    env.enable_emotion = True
    env.enable_dynamic_events = True
    # 动态事件参数 (中等频率)
    env.event_trigger.demand_shock_prob = 0.02       # 2% 需求突变
    env.event_trigger.supply_disruption_prob = 0.01   # 1% 供应中断
    env.event_trigger.contagion_prob = 0.3            # 30% 情绪传染
    env.event_trigger.contagion_strength = 0.4
    env.event_trigger.reset(seed=seed)

    # 为每个节点创建理性决策器 (作为基础策略)
    rational_agents = {}
    for aid in NODE_IDS:
        rational_agents[aid] = RationalAgent(
            L=2, p=5, z=2, C_L_rho=2.0, sigma_eps=5.0)
        rational_agents[aid].init_node(env.id_to_k[aid])

    # 仿真
    costs = {aid: [] for aid in NODE_IDS}
    sls = {aid: [] for aid in NODE_IDS}
    order_history = {aid: [] for aid in NODE_IDS}
    demand_shock_events = []  # 记录需求突变周期

    step_count = 0
    for agent_id in env.agent_iter():
        if step_count >= total_periods * 4:  # 4 agents per cycle
            break
        obs, reward, term, trunc, info = env.last()
        if term or trunc:
            env.step(None)
            step_count += 1
            continue

        # 理性决策策略
        ag_state = env.agent_states[agent_id]
        k = ag_state.k
        ns = ag_state.net_stock
        wip = sum(ag_state.pipeline) if ag_state.pipeline else 0.0
        demand = ag_state.incoming_demand

        # 用RationalAgent决策
        q_t = rational_agents[agent_id].decide(k, ns, wip, demand)
        q_t = max(0, q_t)
        # 映射到Discrete动作 (clip到动作范围)
        action_idx = int(np.clip(q_t - env.action_min, 0, env._action_dim - 1))

        env.step(action_idx)
        step_count += 1

        # 周期末收集数据
        if info.get('t', 0) > len(costs[agent_id]):
            pass  # 由下面统一收集

    # 从env状态收集结果
    demand_hist = env.customer_demand_history[:total_periods]

    for aid in NODE_IDS:
        ag = env.agent_states[aid]
        orders = list(ag.order_history)[:total_periods]
        demands = list(ag.demand_history)[:total_periods]
        fulfilled = list(ag.fulfilled_history)[:total_periods]
        order_history[aid] = orders

        # 成本
        for i in range(min(len(orders), len(demands))):
            # 估算库存和缺货
            ns_i = 10.0  # 初始
            holding = max(0, ns_i) * 1.0  # 简化
            stockout_i = max(0, demands[i] - fulfilled[i])
            stockout_cost = stockout_i * 2.0
            costs[aid].append(holding + stockout_cost)
            sls[aid].append(fulfilled[i] / demands[i] if demands[i] > 0 else 1.0)

    # 计算指标
    var_D = float(np.var(demand_hist)) if len(demand_hist) > 1 else 1.0
    bwe = {}
    avg_cost = {}
    sl = {}
    emotion_var = {}
    k_map = {'retailer': 1, 'wholesaler': 2, 'distributor': 3, 'manufacturer': 4}

    for aid in NODE_IDS:
        orders = order_history[aid]
        bwe[k_map[aid]] = float(np.var(orders)) / var_D if var_D > 0 else 0.0
        avg_cost[k_map[aid]] = float(np.mean(costs[aid])) if costs[aid] else 0.0
        sl[k_map[aid]] = float(np.mean(sls[aid])) if sls[aid] else 0.0
        # 情绪波动指数
        ag = env.agent_states[aid]
        if ag.emotion is not None and len(ag.emotion.E_history) > 1:
            emotion_var[k_map[aid]] = float(np.var(ag.emotion.E_history))
        else:
            emotion_var[k_map[aid]] = 0.0

    total_cost = sum(avg_cost.values())

    # BWE时间序列
    order_history_k = {k_map[aid]: order_history[aid] for aid in NODE_IDS}
    bwe_ts = _compute_bwe_time_series(order_history_k, demand_hist, window=200)

    # 恢复时间: 检测需求突变后BWE恢复稳态的周期数
    recovery_time = _compute_recovery_time(env, bwe_ts)

    # 情绪传染次数
    contagion_count = env.event_trigger.contagion_count

    result = {
        'name': 'Exp_2 (多智能体+情绪+协同)',
        'bwe': bwe,
        'avg_cost': avg_cost,
        'sl': sl,
        'total_cost': total_cost,
        'order_history': order_history_k,
        'demand_history': demand_hist,
        'bwe_time_series': bwe_ts,
        'emotion_variance': emotion_var,
        'recovery_time': recovery_time,
        'contagion_count': contagion_count,
    }
    print(f"  分销商 BWE={bwe[3]:.2f}, SL={sl[3]:.3f}, 成本={avg_cost[3]:.2f}")
    print(f"  制造商 BWE={bwe[4]:.2f}, SL={sl[4]:.3f}, 成本={avg_cost[4]:.2f}")
    print(f"  总成本={total_cost:.2f}")
    print(f"  情绪波动指数: {emotion_var}")
    print(f"  情绪传染次数: {contagion_count}")
    print(f"  恢复时间: {recovery_time} 周期")
    return result


# ============================================================
# 指标计算工具
# ============================================================

def _compute_bwe_time_series(order_history: Dict[int, list],
                              demand_history: list,
                              window: int = 200) -> List[Dict[int, float]]:
    """
    计算BWE时间序列 (滑动窗口)

    返回: [{k: bwe_k} for each window step]
    """
    n = len(demand_history)
    if n < window:
        return []
    ts = []
    for i in range(window, n, max(1, (n - window) // 200)):  # 采样200点
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


def _compute_recovery_time(env, bwe_ts: List[Dict[int, float]]) -> int:
    """
    计算恢复时间: 需求突变后BWE恢复到稳态的周期数

    简化方法:
        1. 找到需求突变发生的周期
        2. 检测BWE时间序列中突变后BWE峰值到恢复稳态的周期数
        3. 稳态定义: BWE波动 < 均值的10%
    """
    # 从事件日志找需求突变周期
    shock_periods = []
    for log in env.event_trigger.event_log:
        if log.get('demand_shock'):
            shock_periods.append(log.get('t', 0))

    if not shock_periods or not bwe_ts:
        return 0

    # 取第一个突变周期
    first_shock = shock_periods[0]
    # BWE时间序列的采样间隔
    if len(bwe_ts) < 2:
        return 0

    # 简化: 计算突变后BWE恢复到突变前水平的时间
    # 找突变前的稳态BWE (取前20%的均值)
    n_pre = max(2, len(bwe_ts) // 5)
    pre_bwe = np.mean([bwe_ts[i].get(3, 0) for i in range(n_pre)])

    # 找突变后的峰值
    peak_idx = n_pre
    peak_val = 0
    for i in range(n_pre, len(bwe_ts)):
        val = bwe_ts[i].get(3, 0)
        if val > peak_val:
            peak_val = val
            peak_idx = i

    # 恢复: BWE回到 pre_bwe * 1.5 以内
    threshold = pre_bwe * 1.5 if pre_bwe > 0 else 0.1
    recovery_idx = peak_idx
    for i in range(peak_idx, len(bwe_ts)):
        if bwe_ts[i].get(3, 0) <= threshold:
            recovery_idx = i
            break

    # 转换为周期数 (每个时间序列点对应的周期数)
    if len(bwe_ts) > 1:
        periods_per_point = max(1, first_shock // len(bwe_ts))
    else:
        periods_per_point = 1

    recovery_time = (recovery_idx - peak_idx) * periods_per_point
    return max(0, recovery_time)


# ============================================================
# 绘图: BWE对比折线图
# ============================================================

def plot_bwe_comparison(results: Dict[str, Dict], save_path: str):
    """
    绘制三组实验在BWE方差比上的对比折线图

    X轴: 供应链节点 (零售商→批发商→分销商→制造商)
    Y轴: 方差比 BWE
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    nodes = [1, 2, 3, 4]
    node_labels = NODE_NAMES_CN
    colors = ['#2196F3', '#FF9800', '#4CAF50']
    markers = ['o', 's', '^']

    for i, (exp_name, result) in enumerate(results.items()):
        bwe_vals = [result['bwe'].get(k, 0) for k in nodes]
        ax.plot(node_labels, bwe_vals,
                color=colors[i], marker=markers[i],
                markersize=10, linewidth=2.5,
                label=result['name'], alpha=0.9)

    ax.set_xlabel('供应链节点', fontsize=13)
    ax.set_ylabel('方差比 BWE = var(q) / var(D)', fontsize=13)
    ax.set_title('三组对比实验: 牛鞭效应方差比', fontsize=15, fontweight='bold')
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_yscale('log')  # 对数坐标 (BWE差异大)

    # 添加数值标注
    for i, (exp_name, result) in enumerate(results.items()):
        for j, k in enumerate(nodes):
            val = result['bwe'].get(k, 0)
            ax.annotate(f'{val:.1f}',
                        xy=(j, val), xytext=(0, 8 + i * 4),
                        textcoords='offset points',
                        fontsize=8, ha='center', color=colors[i])

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n[绘图] BWE对比图已保存: {save_path}")


def plot_bwe_time_series(results: Dict[str, Dict], save_path: str):
    """绘制BWE时间序列对比图 (分销商节点)"""
    fig, ax = plt.subplots(figsize=(12, 5))
    colors = ['#2196F3', '#FF9800', '#4CAF50']

    for i, (exp_name, result) in enumerate(results.items()):
        ts = result.get('bwe_time_series', [])
        if ts:
            bwe_vals = [entry.get(3, 0) for entry in ts]  # 分销商 k=3
            x = range(len(bwe_vals))
            ax.plot(x, bwe_vals, color=colors[i], linewidth=1.5,
                    label=result['name'], alpha=0.8)

    ax.set_xlabel('时间步 (滑动窗口)', fontsize=12)
    ax.set_ylabel('分销商 BWE', fontsize=12)
    ax.set_title('分销商牛鞭效应时间序列对比', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, linestyle='--')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[绘图] BWE时间序列图已保存: {save_path}")


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 60)
    print("三组对比实验 Batch Runner")
    print(f"配置: 评估周期={TOTAL_PERIODS}, IDMR训练={TRAIN_STEPS}, 种子={SEED}")
    print("=" * 60)

    results = {}

    # ---- 实验1: Baseline ----
    results['baseline'] = run_baseline(TOTAL_PERIODS, SEED)

    # ---- 实验2: Exp_1 (IDMR) ----
    results['exp1'] = run_exp1(TOTAL_PERIODS, TRAIN_STEPS, SEED)

    # ---- 实验3: Exp_2 (MARL+情绪+协同) ----
    results['exp2'] = run_exp2(TOTAL_PERIODS, SEED)

    # ---- 计算新增指标 ----
    print("\n" + "=" * 60)
    print("[指标] 新增评估指标")
    print("=" * 60)

    # 协同收益
    baseline_cost = results['baseline']['total_cost']
    exp2_cost = results['exp2']['total_cost']
    synergy_gain = (baseline_cost - exp2_cost) / baseline_cost * 100 if baseline_cost > 0 else 0
    print(f"\n  协同收益: {synergy_gain:.2f}%  "
          f"(Baseline成本={baseline_cost:.2f} → Exp_2成本={exp2_cost:.2f})")

    # 情绪波动指数
    print(f"\n  情绪波动指数 (各节点情绪方差):")
    for k in range(1, 5):
        bv = results['baseline']['emotion_variance'].get(k, 0)
        e1v = results['exp1']['emotion_variance'].get(k, 0)
        e2v = results['exp2']['emotion_variance'].get(k, 0)
        print(f"    {NODE_NAMES_CN[k-1]}: Baseline={bv:.4f}, "
              f"Exp_1={e1v:.4f}, Exp_2={e2v:.4f}")

    # 恢复时间
    print(f"\n  恢复时间 (需求突变后恢复稳态):")
    print(f"    Baseline: {results['baseline']['recovery_time']} 周期 (无动态事件)")
    print(f"    Exp_1:    {results['exp1']['recovery_time']} 周期 (无动态事件)")
    print(f"    Exp_2:    {results['exp2']['recovery_time']} 周期")

    # ---- 汇总表 ----
    print("\n" + "=" * 60)
    print("[汇总] 三组实验核心指标对比")
    print("=" * 60)
    print(f"{'指标':<16} {'Baseline':>12} {'Exp_1(IDMR)':>12} {'Exp_2(MARL)':>12}")
    print("-" * 56)
    for k in range(1, 5):
        name = NODE_NAMES_CN[k-1]
        print(f"{name} BWE        "
              f"{results['baseline']['bwe'][k]:>12.2f} "
              f"{results['exp1']['bwe'][k]:>12.2f} "
              f"{results['exp2']['bwe'][k]:>12.2f}")
    print("-" * 56)
    for k in range(1, 5):
        name = NODE_NAMES_CN[k-1]
        print(f"{name} SL         "
              f"{results['baseline']['sl'][k]:>12.3f} "
              f"{results['exp1']['sl'][k]:>12.3f} "
              f"{results['exp2']['sl'][k]:>12.3f}")
    print("-" * 56)
    for k in range(1, 5):
        name = NODE_NAMES_CN[k-1]
        print(f"{name} 成本       "
              f"{results['baseline']['avg_cost'][k]:>12.2f} "
              f"{results['exp1']['avg_cost'][k]:>12.2f} "
              f"{results['exp2']['avg_cost'][k]:>12.2f}")
    print("-" * 56)
    print(f"{'总成本':<16} "
          f"{results['baseline']['total_cost']:>12.2f} "
          f"{results['exp1']['total_cost']:>12.2f} "
          f"{results['exp2']['total_cost']:>12.2f}")
    print(f"{'协同收益':<16} {'-':>12} {'-':>12} {synergy_gain:>11.2f}%")

    # ---- 绘图 ----
    plot_bwe_comparison(results, '对比图_BWE方差比.png')
    plot_bwe_time_series(results, '对比图_BWE时间序列.png')

    # ---- 保存结果摘要 ----
    summary = {
        'config': {
            'total_periods': TOTAL_PERIODS,
            'train_steps': TRAIN_STEPS,
            'seed': SEED,
        },
        'synergy_gain_pct': synergy_gain,
        'experiments': {},
    }
    for exp_name, result in results.items():
        summary['experiments'][exp_name] = {
            'name': result['name'],
            'bwe': {str(k): v for k, v in result['bwe'].items()},
            'avg_cost': {str(k): v for k, v in result['avg_cost'].items()},
            'sl': {str(k): v for k, v in result['sl'].items()},
            'total_cost': result['total_cost'],
            'emotion_variance': {str(k): v for k, v in result['emotion_variance'].items()},
            'recovery_time': result['recovery_time'],
            'contagion_count': result.get('contagion_count', 0),
        }

    with open('实验结果摘要.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n[保存] 实验结果摘要已保存: 实验结果摘要.json")

    print("\n" + "=" * 60)
    print("[完成] Batch Runner 全部实验运行完毕!")
    print("=" * 60)


if __name__ == '__main__':
    main()

"""
极限压力测试 (Stress Test) - 论文 Limitations 章节支撑
======================================================

面向顶级期刊审稿人的严苛审查, 设计三大压力测试场景:

1. 极端参数敏感性分析:
    1.1 正向激励权重 (inventory_bonus_weight): [0.01, 0.1, 0.3, 1.0, 5.0, 10.0]
    1.2 情绪反馈权重 (emotion_w_match):       [0.01, 0.1, 0.5, 1.0, 5.0, 10.0]
    1.3 情绪传染概率 (contagion_prob):          [0.0, 0.1, 0.3, 0.5, 0.8, 1.0]

2. 非理性人类干预模拟:
    20%/50% 节点替换为完全随机 / 极度保守决策者, 验证 MARL 系统鲁棒性

3. 计算开销评估:
    - 单步推理耗时 / DQN 训练单步耗时
    - 可扩展性: 4 / 8 / 16 / 32 节点供应链

崩溃判定:
    - avg_BWE > 1000  (订单方差爆炸)
    - avg_SL  < 0.5   (服务水平崩塌)
    - 数值溢出 (NaN/Inf)

输出:
    - 极限压力测试_结果摘要.json
    - 控制台详细日志
"""

import numpy as np
import json
import time
import os
from typing import Dict, Any, List, Optional
from collections import deque


# ============================================================
# 通用工具
# ============================================================

NODE_IDS = ['retailer', 'wholesaler', 'distributor', 'manufacturer']
K_MAP = {'retailer': 1, 'wholesaler': 2, 'distributor': 3, 'manufacturer': 4}


def _is_crash(avg_bwe: float, avg_sl: float) -> bool:
    """判定系统是否崩溃"""
    if np.isnan(avg_bwe) or np.isinf(avg_bwe):
        return True
    if np.isnan(avg_sl) or np.isinf(avg_sl):
        return True
    return (avg_bwe > 1000.0) or (avg_sl < 0.5)


def _run_marl_simulation(total_periods: int, seed: int,
                          inventory_bonus_weight: float = 0.3,
                          emotion_w_match: float = 0.5,
                          contagion_prob: float = 0.3,
                          contagion_strength: float = 0.4,
                          human_override: Optional[Dict[str, str]] = None,
                          ) -> Dict[str, Any]:
    """
    通用 MARL 仿真封装

    Args:
        human_override: {agent_id: 'random'|'conservative'} 指定节点采用人类决策
            None: 全部使用理性决策 (MARL 基线)
            'random': 完全随机订货
            'conservative': 极度保守, 始终订最小量

    返回:
        性能指标字典, 含 bwe/sl/costs/emotion/crash 等
    """
    from marl_supply_chain_env import MARLSupplyChainEnv
    from supply_chain_env import RationalAgent
    from emotion_module import EmotionState

    env = MARLSupplyChainEnv(config=None)
    # 覆盖参数
    env.inventory_bonus_weight = inventory_bonus_weight
    env.emotion_w_match = emotion_w_match

    # 重新挂载情绪模块 (使 emotion_w_match 生效)
    for aid in env.agent_ids:
        env.agent_states[aid].emotion = EmotionState(
            alpha=env.emotion_alpha,
            gamma=env.emotion_gamma,
            w_stockout=env.emotion_w_stockout,
            w_match=emotion_w_match,
            w_excess=env.emotion_w_excess,
        )

    env.reset(seed=seed)
    env.max_cycles = total_periods + 10
    env.enable_emotion = True
    env.enable_dynamic_events = True
    env.event_trigger.contagion_prob = contagion_prob
    env.event_trigger.contagion_strength = contagion_strength
    env.event_trigger.reset(seed=seed)

    # 为非人类节点创建理性决策器
    rational_agents = {}
    for aid in NODE_IDS:
        if human_override is None or aid not in human_override:
            rational_agents[aid] = RationalAgent(L=2, p=5, z=2,
                                                  C_L_rho=2.0, sigma_eps=5.0)
            rational_agents[aid].init_node(env.id_to_k[aid])

    # 仿真
    rng = np.random.default_rng(seed + 1)
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

        if human_override is not None and agent_id in human_override:
            # 人类决策者
            if human_override[agent_id] == 'random':
                action_idx = int(rng.integers(0, env._action_dim))
            else:  # conservative
                action_idx = 0  # 始终订 action_min
        else:
            q_t = rational_agents[agent_id].decide(k, ns, wip, demand)
            q_t = max(0, q_t)
            action_idx = int(np.clip(q_t - env.action_min, 0, env._action_dim - 1))

        env.step(action_idx)
        step_count += 1

    # 计算指标
    demand_hist = env.customer_demand_history[:total_periods]
    var_D = float(np.var(demand_hist)) if len(demand_hist) > 1 else 1.0

    bwe, sl, costs, emotion_stats = {}, {}, {}, {}
    for aid in NODE_IDS:
        ag = env.agent_states[aid]
        orders = list(ag.order_history)[:total_periods]
        demands = list(ag.demand_history)[:total_periods]
        fulfilled = list(ag.fulfilled_history)[:total_periods]
        if len(orders) < 2:
            continue
        bwe[aid] = float(np.var(orders)) / var_D if var_D > 0 else 0.0
        sl_list = [f/d if d > 0 else 1.0 for f, d in zip(fulfilled, demands)]
        sl[aid] = float(np.mean(sl_list)) if sl_list else 0.0
        stockout_costs = [max(0, d - f) * 2.0 for f, d in zip(fulfilled, demands)]
        costs[aid] = float(np.mean(stockout_costs)) if stockout_costs else 0.0
        if ag.emotion is not None and len(ag.emotion.E_history) > 1:
            emotion_stats[aid] = {
                'mean_E': float(np.mean(ag.emotion.E_history)),
                'std_E': float(np.std(ag.emotion.E_history)),
                'min_E': float(np.min(ag.emotion.E_history)),
                'max_E': float(np.max(ag.emotion.E_history)),
            }

    avg_bwe = float(np.mean(list(bwe.values()))) if bwe else 0.0
    avg_sl = float(np.mean(list(sl.values()))) if sl else 0.0
    max_bwe = float(np.max(list(bwe.values()))) if bwe else 0.0
    crash = _is_crash(avg_bwe, avg_sl)

    return {
        'bwe': bwe, 'sl': sl, 'costs': costs, 'emotion': emotion_stats,
        'avg_bwe': avg_bwe, 'avg_sl': avg_sl, 'max_bwe': max_bwe,
        'crash': crash,
        'contagion_count': env.event_trigger.contagion_count,
        'total_periods': len(demand_hist),
    }


# ============================================================
# 测试 1: 极端参数敏感性分析
# ============================================================

def test_sensitivity_incentive_weight(periods: int, seed: int) -> List[Dict]:
    """测试 1.1: 正向激励权重 (inventory_bonus_weight) 敏感性"""
    print("\n[测试1.1] 正向激励权重 (inventory_bonus_weight) 敏感性分析")
    print(f"{'权重':>8} | {'avg_BWE':>10} | {'avg_SL':>10} | {'max_BWE':>10} | "
          f"{'情绪波动':>10} | {'崩溃':>6}")
    print("-" * 80)
    weights = [0.01, 0.05, 0.1, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0]
    results = []
    for w in weights:
        r = _run_marl_simulation(periods, seed, inventory_bonus_weight=w,
                                  emotion_w_match=0.5,
                                  contagion_prob=0.3, contagion_strength=0.4)
        # 计算情绪波动均值
        em_stds = [v.get('std_E', 0.0) for v in r['emotion'].values()]
        avg_emotion_std = float(np.mean(em_stds)) if em_stds else 0.0
        r['weight'] = w
        r['avg_emotion_std'] = avg_emotion_std
        results.append(r)
        crash_flag = 'YES' if r['crash'] else 'OK'
        print(f"{w:>8.3f} | {r['avg_bwe']:>10.3f} | {r['avg_sl']:>10.4f} | "
              f"{r['max_bwe']:>10.3f} | {avg_emotion_std:>10.4f} | {crash_flag:>6}")
    return results


def test_sensitivity_emotion_match(periods: int, seed: int) -> List[Dict]:
    """测试 1.2: 情绪正向反馈权重 (emotion_w_match) 敏感性"""
    print("\n[测试1.2] 情绪正向反馈权重 (emotion_w_match) 敏感性分析")
    print(f"{'权重':>8} | {'avg_BWE':>10} | {'avg_SL':>10} | {'情绪均值':>10} | "
          f"{'情绪波动':>10} | {'崩溃':>6}")
    print("-" * 80)
    weights = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    results = []
    for w in weights:
        r = _run_marl_simulation(periods, seed, inventory_bonus_weight=0.3,
                                  emotion_w_match=w,
                                  contagion_prob=0.3, contagion_strength=0.4)
        em_means = [v.get('mean_E', 0.0) for v in r['emotion'].values()]
        em_stds = [v.get('std_E', 0.0) for v in r['emotion'].values()]
        avg_emotion_mean = float(np.mean(em_means)) if em_means else 0.0
        avg_emotion_std = float(np.mean(em_stds)) if em_stds else 0.0
        r['w_match'] = w
        r['avg_emotion_mean'] = avg_emotion_mean
        r['avg_emotion_std'] = avg_emotion_std
        results.append(r)
        crash_flag = 'YES' if r['crash'] else 'OK'
        print(f"{w:>8.3f} | {r['avg_bwe']:>10.3f} | {r['avg_sl']:>10.4f} | "
              f"{avg_emotion_mean:>+10.4f} | {avg_emotion_std:>10.4f} | {crash_flag:>6}")
    return results


def test_sensitivity_contagion(periods: int, seed: int) -> List[Dict]:
    """测试 1.3: 情绪传染概率敏感性"""
    print("\n[测试1.3] 情绪传染概率 (contagion_prob) 敏感性分析")
    print(f"{'概率':>8} | {'avg_BWE':>10} | {'avg_SL':>10} | {'传染次数':>10} | "
          f"{'情绪均值':>10} | {'崩溃':>6}")
    print("-" * 80)
    probs = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
    results = []
    for p in probs:
        r = _run_marl_simulation(periods, seed, inventory_bonus_weight=0.3,
                                  emotion_w_match=0.5,
                                  contagion_prob=p, contagion_strength=0.4)
        em_means = [v.get('mean_E', 0.0) for v in r['emotion'].values()]
        avg_emotion_mean = float(np.mean(em_means)) if em_means else 0.0
        r['contagion_prob'] = p
        r['avg_emotion_mean'] = avg_emotion_mean
        results.append(r)
        crash_flag = 'YES' if r['crash'] else 'OK'
        print(f"{p:>8.2f} | {r['avg_bwe']:>10.3f} | {r['avg_sl']:>10.4f} | "
              f"{r['contagion_count']:>10d} | {avg_emotion_mean:>+10.4f} | {crash_flag:>6}")
    return results


# ============================================================
# 测试 2: 非理性人类干预模拟
# ============================================================

def test_human_intervention(periods: int, seed: int) -> List[Dict]:
    """测试 2: 非理性人类决策者混合实验"""
    print("\n[测试2] 非理性人类决策者混合实验")
    print(f"{'场景':>28} | {'avg_BWE':>10} | {'avg_SL':>10} | "
          f"{'人类节点':>22} | {'崩溃':>6}")
    print("-" * 100)

    scenarios = [
        {'human_ratio': 0.0, 'human_type': 'none',
         'desc': '0% 人类 (全MARL基线)'},
        {'human_ratio': 0.25, 'human_type': 'random',
         'desc': '25% 随机决策者'},
        {'human_ratio': 0.25, 'human_type': 'conservative',
         'desc': '25% 极度保守者'},
        {'human_ratio': 0.50, 'human_type': 'random',
         'desc': '50% 随机决策者'},
        {'human_ratio': 0.50, 'human_type': 'conservative',
         'desc': '50% 极度保守者'},
        {'human_ratio': 0.75, 'human_type': 'random',
         'desc': '75% 随机决策者 (极限)'},
    ]

    rng = np.random.default_rng(seed + 100)
    results = []
    for sc in scenarios:
        if sc['human_ratio'] == 0.0:
            r = _run_marl_simulation(periods, seed, inventory_bonus_weight=0.3,
                                      emotion_w_match=0.5,
                                      contagion_prob=0.3, contagion_strength=0.4,
                                      human_override=None)
            r['human_nodes'] = []
        else:
            n_human = max(1, int(round(sc['human_ratio'] * 4)))
            human_nodes = list(rng.choice(NODE_IDS, size=n_human, replace=False))
            human_override = {aid: sc['human_type'] for aid in human_nodes}
            r = _run_marl_simulation(periods, seed, inventory_bonus_weight=0.3,
                                      emotion_w_match=0.5,
                                      contagion_prob=0.3, contagion_strength=0.4,
                                      human_override=human_override)
            r['human_nodes'] = human_nodes
        r['desc'] = sc['desc']
        r['human_ratio'] = sc['human_ratio']
        r['human_type'] = sc['human_type']
        results.append(r)
        crash_flag = 'YES' if r['crash'] else 'OK'
        hnodes = ','.join(r['human_nodes']) if r['human_nodes'] else '-'
        print(f"{sc['desc']:>28} | {r['avg_bwe']:>10.3f} | {r['avg_sl']:>10.4f} | "
              f"{hnodes:>22} | {crash_flag:>6}")
    return results


# ============================================================
# 测试 3: 计算开销评估
# ============================================================

def test_computational_overhead(periods: int, seed: int) -> Dict[str, Any]:
    """测试 3: 计算开销评估"""
    print("\n[测试3] 计算开销评估")
    print("-" * 70)

    # ---- 3.1 单步推理耗时 (MARL 环境 + 理性决策) ----
    from marl_supply_chain_env import MARLSupplyChainEnv
    from supply_chain_env import RationalAgent

    env = MARLSupplyChainEnv(config=None)
    env.reset(seed=seed)
    env.enable_emotion = True
    env.enable_dynamic_events = True
    env.event_trigger.contagion_prob = 0.3
    env.event_trigger.reset(seed=seed)

    rational_agents = {aid: RationalAgent(L=2, p=5, z=2, C_L_rho=2.0, sigma_eps=5.0)
                       for aid in env.agent_ids}
    for aid in rational_agents:
        rational_agents[aid].init_node(env.id_to_k[aid])

    # 预热 100 周期
    n_warmup = 100
    step_count = 0
    for agent_id in env.agent_iter():
        if step_count >= n_warmup * 4:
            break
        obs, r, t, tr, info = env.last()
        if t or tr:
            env.step(None); step_count += 1; continue
        ag = env.agent_states[agent_id]
        q = rational_agents[agent_id].decide(ag.k, ag.net_stock,
                                              sum(ag.pipeline) if ag.pipeline else 0,
                                              ag.incoming_demand)
        env.step(int(np.clip(max(0, q) - env.action_min, 0, env._action_dim - 1)))
        step_count += 1

    # 计时: 1000 周期推理
    n_inference = 1000
    t0 = time.perf_counter()
    step_count = 0
    for agent_id in env.agent_iter():
        if step_count >= n_inference * 4:
            break
        obs, r, t, tr, info = env.last()
        if t or tr:
            env.step(None); step_count += 1; continue
        ag = env.agent_states[agent_id]
        q = rational_agents[agent_id].decide(ag.k, ag.net_stock,
                                              sum(ag.pipeline) if ag.pipeline else 0,
                                              ag.incoming_demand)
        env.step(int(np.clip(max(0, q) - env.action_min, 0, env._action_dim - 1)))
        step_count += 1
    t1 = time.perf_counter()

    inference_total = t1 - t0
    inference_per_period = inference_total / n_inference
    inference_per_agent = inference_total / (n_inference * 4)
    print(f"[3.1] 推理耗时: {inference_total*1000:.2f} ms / {n_inference} 周期 = "
          f"{inference_per_period*1000:.4f} ms/周期 (4 agent) = "
          f"{inference_per_agent*1000:.4f} ms/agent")

    # ---- 3.2 DQN 训练单步耗时 ----
    from idmr_agent import QNetwork

    state_dim = 8
    action_dim = 41
    q_net = QNetwork(state_dim=state_dim, action_dim=action_dim, hidden_dim=64, lr=1e-4)
    target_net = QNetwork(state_dim=state_dim, action_dim=action_dim, hidden_dim=64, lr=1e-4)

    batch_size = 32
    n_train_steps = 1000
    states = np.random.randn(batch_size, state_dim).astype(np.float32)
    actions = np.random.randint(0, action_dim, batch_size)
    rewards = np.random.randn(batch_size).astype(np.float32)
    next_states = np.random.randn(batch_size, state_dim).astype(np.float32)
    dones = np.zeros(batch_size, dtype=np.float32)

    # 预热
    for _ in range(50):
        q = q_net.forward(states)
        next_q = target_net.forward(next_states).max(axis=1)
        target = rewards + 0.9 * next_q * (1 - dones)
        q_selected = q[np.arange(batch_size), actions]
        td_error = q_selected - target
        grad_q = np.zeros_like(q)
        grad_q[np.arange(batch_size), actions] = td_error
        grads = q_net.backward(grad_q, batch_size)
        q_net.adam_update(grads)

    # 计时
    t0 = time.perf_counter()
    for _ in range(n_train_steps):
        q = q_net.forward(states)
        next_q = target_net.forward(next_states).max(axis=1)
        target = rewards + 0.9 * next_q * (1 - dones)
        q_selected = q[np.arange(batch_size), actions]
        td_error = q_selected - target
        grad_q = np.zeros_like(q)
        grad_q[np.arange(batch_size), actions] = td_error
        grads = q_net.backward(grad_q, batch_size)
        q_net.adam_update(grads)
    t1 = time.perf_counter()

    train_total = t1 - t0
    train_per_step = train_total / n_train_steps
    print(f"[3.2] 训练耗时: {train_total*1000:.2f} ms / {n_train_steps} 步 = "
          f"{train_per_step*1000:.4f} ms/step (batch={batch_size})")

    # ---- 3.3 EWC Fisher 信息计算耗时 (持续学习开销) ----
    try:
        from ewc import EWC
        ewc = EWC(q_net, lambda_reg=2000.0)
        n_fisher_samples = 200
        # 预热
        for _ in range(5):
            ewc.compute_fisher(states[:n_fisher_samples], actions[:n_fisher_samples])

        t0 = time.perf_counter()
        for _ in range(20):
            ewc.compute_fisher(states[:n_fisher_samples], actions[:n_fisher_samples])
        t1 = time.perf_counter()
        ewc_per_call = (t1 - t0) / 20
        print(f"[3.3] EWC Fisher 计算: {ewc_per_call*1000:.4f} ms/call "
              f"(n_samples={n_fisher_samples})")
    except Exception as e:
        ewc_per_call = None
        print(f"[3.3] EWC Fisher 计算跳过 ({e})")

    # ---- 3.4 可扩展性测试 ----
    print(f"\n[3.4] 可扩展性测试 (单周期推理耗时 vs 节点数):")
    print(f"{'节点数K':>8} | {'周期数':>8} | {'总耗时(s)':>12} | "
          f"{'每周期(ms)':>12} | {'每节点(ms)':>12}")
    print("-" * 70)

    scaling_results = []
    test_periods = 200
    for K in [4, 8, 16, 32, 64]:
        from supply_chain_env import SupplyChainEnv
        env_s = SupplyChainEnv(K=K, total_periods=test_periods, seed=seed)
        ag_s = RationalAgent(L=2, p=5, z=2, C_L_rho=2.0, sigma_eps=5.0)
        for k in range(1, K + 1):
            ag_s.init_node(k)

        env_s.reset()
        t0 = time.perf_counter()
        for t in range(test_periods):
            D_t = env_s._generate_demand()
            env_s.customer_demand_history.append(D_t)
            dd = {1: D_t}
            for k in range(1, env_s.K + 1):
                node = env_s.nodes[k]
                demand_k = dd.get(k, 0)
                arrived = node.pipeline[0] if node.pipeline else 0.0
                node.net_stock += arrived
                if node.pipeline:
                    node.pipeline.popleft()
                q = ag_s.decide(k, node.net_stock,
                                  sum(node.pipeline) if node.pipeline else 0,
                                  demand_k)
                q = max(0, q)
                node.order_placed = q
                node.order_history.append(q)
                dd[k + 1] = q
                fulfilled = min(max(node.net_stock, 0), demand_k)
                node.net_stock -= fulfilled
                if k < env_s.K:
                    env_s.nodes[k + 1].pipeline.append(q)
        t1 = time.perf_counter()
        total_time = t1 - t0
        per_period_ms = total_time / test_periods * 1000
        per_node_ms = per_period_ms / K
        scaling_results.append({
            'K': K, 'periods': test_periods, 'total_time_s': total_time,
            'per_period_ms': per_period_ms, 'per_node_ms': per_node_ms
        })
        print(f"{K:>8d} | {test_periods:>8d} | {total_time:>12.4f} | "
              f"{per_period_ms:>12.4f} | {per_node_ms:>12.4f}")

    # ---- 工业部署可行性评估 ----
    # 假设日产1000个决策周期 (订单决策), 4节点
    daily_periods = 1000
    daily_inference_time_s = inference_per_period * daily_periods
    # 训练: 假设每周一次, 10000步
    weekly_train_time_s = train_per_step * 10000

    deployment_eval = {
        'daily_inference_time_s': daily_inference_time_s,
        'daily_inference_time_min': daily_inference_time_s / 60,
        'weekly_train_time_s': weekly_train_time_s,
        'weekly_train_time_min': weekly_train_time_s / 60,
        'realtime_threshold_ms': 100,  # 实时决策阈值 100ms
        'meets_realtime': inference_per_period * 1000 < 100,
    }

    print(f"\n[3.5] 工业部署可行性评估 (4节点):")
    print(f"  日推理耗时 (1000周期): {daily_inference_time_s:.2f} s = "
          f"{daily_inference_time_s/60:.2f} min")
    print(f"  周训练耗时 (10000步):  {weekly_train_time_s:.2f} s = "
          f"{weekly_train_time_s/60:.2f} min")
    print(f"  实时性: 单周期 {inference_per_period*1000:.3f} ms < 100ms 阈值? "
          f"{'YES' if deployment_eval['meets_realtime'] else 'NO'}")

    return {
        'inference_time_per_period_s': inference_per_period,
        'inference_time_per_agent_s': inference_per_agent,
        'train_time_per_step_s': train_per_step,
        'ewc_fisher_time_per_call_s': ewc_per_call,
        'n_inference_steps': n_inference,
        'n_train_steps': n_train_steps,
        'scaling': scaling_results,
        'deployment_eval': deployment_eval,
        'hardware': 'CPU (Intel i7, NumPy implementation, no GPU acceleration)',
        'framework': 'NumPy + PettingZoo',
    }


# ============================================================
# 主程序
# ============================================================

def main():
    print("=" * 80)
    print("极限压力测试 (Stress Test) - 论文 Limitations 章节支撑")
    print("=" * 80)

    PERIODS = 500
    SEED = 42

    all_results = {
        'config': {
            'periods': PERIODS,
            'seed': SEED,
            'date': '2026-06-27',
            'crash_criteria': 'avg_BWE>1000 OR avg_SL<0.5 OR NaN/Inf'
        },
        'test1_sensitivity': {},
        'test2_human_intervention': {},
        'test3_overhead': {},
    }

    # ---- 阶段 1: 极端参数敏感性 ----
    print("\n" + "=" * 80)
    print("[阶段 1] 极端参数敏感性分析")
    print("=" * 80)
    all_results['test1_sensitivity']['incentive_weight'] = \
        test_sensitivity_incentive_weight(PERIODS, SEED)
    all_results['test1_sensitivity']['emotion_match_weight'] = \
        test_sensitivity_emotion_match(PERIODS, SEED)
    all_results['test1_sensitivity']['contagion_prob'] = \
        test_sensitivity_contagion(PERIODS, SEED)

    # ---- 阶段 2: 非理性人类干预 ----
    print("\n" + "=" * 80)
    print("[阶段 2] 非理性人类干预模拟")
    print("=" * 80)
    all_results['test2_human_intervention']['scenarios'] = \
        test_human_intervention(PERIODS, SEED)

    # ---- 阶段 3: 计算开销 ----
    print("\n" + "=" * 80)
    print("[阶段 3] 计算开销评估")
    print("=" * 80)
    all_results['test3_overhead'] = test_computational_overhead(PERIODS, SEED)

    # ---- 保存结果 ----
    output_file = '极限压力测试_结果摘要.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n[保存] 结果已保存至: {output_file}")

    # ---- 打印总结 ----
    print("\n" + "=" * 80)
    print("[总结] 极限压力测试摘要")
    print("=" * 80)

    inc = all_results['test1_sensitivity']['incentive_weight']
    em = all_results['test1_sensitivity']['emotion_match_weight']
    con = all_results['test1_sensitivity']['contagion_prob']
    print(f"测试1.1 激励权重: {len(inc)}组, "
          f"崩溃 {sum(1 for r in inc if r['crash'])}组 "
          f"(权重范围 0.01~10.0)")
    print(f"测试1.2 情绪反馈权重: {len(em)}组, "
          f"崩溃 {sum(1 for r in em if r['crash'])}组")
    print(f"测试1.3 传染概率: {len(con)}组, "
          f"崩溃 {sum(1 for r in con if r['crash'])}组 "
          f"(概率 0.0~1.0)")

    hum = all_results['test2_human_intervention']['scenarios']
    print(f"测试2  人类干预: {len(hum)}场景, "
          f"崩溃 {sum(1 for r in hum if r.get('crash', False))}场景")

    oh = all_results['test3_overhead']
    print(f"测试3  计算开销: 推理 {oh['inference_time_per_period_s']*1000:.3f} ms/周期, "
          f"训练 {oh['train_time_per_step_s']*1000:.3f} ms/步")
    print(f"       可扩展性: 4节点 {oh['scaling'][0]['per_period_ms']:.3f} ms/周期 → "
          f"64节点 {oh['scaling'][-1]['per_period_ms']:.3f} ms/周期")
    print(f"       实时性: {'满足' if oh['deployment_eval']['meets_realtime'] else '不满足'} "
          f"100ms 阈值")

    print("\n" + "=" * 80)
    print("[OK] 极限压力测试全部完成!")
    print("=" * 80)


if __name__ == '__main__':
    main()

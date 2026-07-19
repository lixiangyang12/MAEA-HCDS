"""
快速诊断测试 V2: 测试全节点平滑 + 动态事件配置
"""
import os
import numpy as np
from marl_supply_chain_env import MARLSupplyChainEnv
from supply_chain_env import RationalAgent

NODE_IDS = ['retailer', 'wholesaler', 'distributor', 'manufacturer']
K_MAP = {'retailer': 1, 'wholesaler': 2, 'distributor': 3, 'manufacturer': 4}
K = 4
H = 1.0
P_SMA = 5
Z_SAFETY = 2
C_L_RHO = 2.0
SIM_PERIODS = 5000
SEED = 42


def run_single_sim(params, mode='baseline', alpha=0.85, smooth_all=False,
                   cautious_k=0.0, optimistic_k=0.0, dynamic_events=False):
    """运行单次仿真, 可配置全节点平滑和动态事件"""
    sigma_eps = params['sigma_eps']
    L_val = params['L']
    w_s = params['w_s']

    env = MARLSupplyChainEnv(config=None)
    env.sigma_eps = sigma_eps
    env.L = L_val
    env.reset(seed=SEED)

    if mode == 'exp2':
        env.enable_emotion = True
        env.enable_dynamic_events = dynamic_events
        env.enable_coordination = True
    else:
        env.enable_emotion = False
        env.enable_dynamic_events = dynamic_events
        env.enable_coordination = False

    rational_agents = {}
    for aid in NODE_IDS:
        rational_agents[aid] = RationalAgent(
            L=L_val, p=P_SMA, z=Z_SAFETY,
            C_L_rho=C_L_RHO, sigma_eps=sigma_eps)
        rational_agents[aid].init_node(env.id_to_k[aid])

    order_hist = {aid: [] for aid in NODE_IDS}
    demand_hist = {aid: [] for aid in NODE_IDS}
    cost_hist = {aid: [] for aid in NODE_IDS}
    sl_hist = {aid: [] for aid in NODE_IDS}
    prev_orders = {}

    step_count = 0
    for agent_id in env.agent_iter():
        if step_count >= SIM_PERIODS * K:
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

        q_t = rational_agents[agent_id].decide(k, ns, wip, demand)
        q_t = max(0, q_t)

        # 情绪调节
        if mode == 'exp2' and env.enable_emotion and ag_state.emotion is not None:
            E_t = ag_state.emotion.E
            if E_t < 0 and env.enable_dynamic_events:
                q_t = q_t * (1.0 + 0.5 * abs(E_t))
            elif E_t < 0 and cautious_k > 0:
                q_t = q_t * (1.0 + cautious_k * abs(E_t))
            elif E_t > 0 and optimistic_k > 0:
                if q_t > demand:
                    excess = q_t - demand
                    q_t = demand + excess * (1.0 - optimistic_k * E_t)

        # 订单平滑
        smooth_condition = (mode == 'exp2' and env.enable_coordination)
        if smooth_all:
            smooth_condition = smooth_condition and (k >= 1)
        else:
            smooth_condition = smooth_condition and (k > 1)

        if smooth_condition:
            prev_q = prev_orders.get(agent_id, q_t)
            q_t = alpha * q_t + (1 - alpha) * prev_q
        prev_orders[agent_id] = q_t

        action_min = env.action_min if hasattr(env, 'action_min') else 0
        action_dim = env._action_dim if hasattr(env, '_action_dim') else 41
        q_clipped = int(np.clip(q_t, action_min, action_min + action_dim - 1))
        action_idx = q_clipped - action_min

        env.step(action_idx)
        step_count += 1

        actual_q = ag_state.order_placed
        actual_demand = ag_state.incoming_demand
        actual_fulfilled = getattr(ag_state, 'last_fulfilled',
                                   min(max(ns, 0), actual_demand))
        actual_ns = ag_state.net_stock

        order_hist[agent_id].append(actual_q)
        demand_hist[agent_id].append(actual_demand)

        holding_cost = max(0, actual_ns) * H
        stockout = max(0, actual_demand - actual_fulfilled)
        stockout_cost = stockout * w_s
        cost_hist[agent_id].append(holding_cost + stockout_cost)

        sl = actual_fulfilled / actual_demand if actual_demand > 0 else 1.0
        sl_hist[agent_id].append(sl)

    demand_retail = demand_hist['retailer'][:SIM_PERIODS]
    var_D = float(np.var(demand_retail)) if len(demand_retail) > 1 else 1.0

    bwe = {}; avg_cost = {}; sl = {}
    for aid in NODE_IDS:
        kk = K_MAP[aid]
        orders = order_hist[aid][:SIM_PERIODS]
        bwe[kk] = float(np.var(orders)) / var_D if var_D > 0 else 0.0
        avg_cost[kk] = float(np.mean(cost_hist[aid][:SIM_PERIODS]))
        sl[kk] = float(np.mean(sl_hist[aid][:SIM_PERIODS]))

    total_cost = sum(avg_cost.values())
    avg_sl = sum(sl.values()) / K
    system_bwe = sum(bwe.values()) / K

    return {
        'total_cost': total_cost,
        'avg_sl': avg_sl,
        'system_bwe': system_bwe,
        'sl_per_node': {str(k): f"{v*100:.1f}%" for k, v in sl.items()},
    }


# 测试参数组合
test_cases = [
    {'name': '低σ_ε低L', 'params': {'w_s': 2.0, 'sigma_eps': 3, 'L': 1}},
    {'name': '默认参数',  'params': {'w_s': 2.0, 'sigma_eps': 5, 'L': 2}},
    {'name': '高σ_ε高L', 'params': {'w_s': 2.0, 'sigma_eps': 10, 'L': 3}},
]

# 测试配置 V2
configs = [
    {'name': 'Baseline',                              'mode': 'baseline', 'alpha': 0.85, 'smooth_all': False, 'ck': 0.0, 'ok': 0.0, 'de': False},
    {'name': '全节点平滑α=0.85',                      'mode': 'exp2',    'alpha': 0.85, 'smooth_all': True,  'ck': 0.0, 'ok': 0.0, 'de': False},
    {'name': '全节点平滑α=0.9',                       'mode': 'exp2',    'alpha': 0.9,  'smooth_all': True,  'ck': 0.0, 'ok': 0.0, 'de': False},
    {'name': '全节点平滑α=0.85+谨慎0.1+乐观0.05',     'mode': 'exp2',    'alpha': 0.85, 'smooth_all': True,  'ck': 0.1, 'ok': 0.05, 'de': False},
    {'name': '全节点平滑α=0.9+谨慎0.1+乐观0.05',      'mode': 'exp2',    'alpha': 0.9,  'smooth_all': True,  'ck': 0.1, 'ok': 0.05, 'de': False},
]

print("=" * 120)
print("快速诊断测试 V2: 全节点平滑 + 情绪调节")
print("=" * 120)

for tc in test_cases:
    print(f"\n{'='*120}")
    print(f"参数组合: {tc['name']}  (w_s={tc['params']['w_s']}, σ_ε={tc['params']['sigma_eps']}, L={tc['params']['L']})")
    print(f"{'='*120}")
    print(f"{'配置':<40} {'成本':>8} {'成本差':>8} {'SL':>8} {'SL差':>8} {'BWE':>8} {'SL_零售':>8} {'SL_批发':>8} {'SL_分销':>8} {'SL_制造':>8}")
    print("-" * 120)

    base_result = None
    for cfg in configs:
        result = run_single_sim(
            tc['params'], mode=cfg['mode'], alpha=cfg['alpha'],
            smooth_all=cfg['smooth_all'], cautious_k=cfg['ck'],
            optimistic_k=cfg['ok'], dynamic_events=cfg['de'])

        if cfg['name'] == 'Baseline':
            base_result = result

        cost_diff = ""
        sl_diff = ""
        if base_result is not None and cfg['name'] != 'Baseline':
            cd = (result['total_cost'] - base_result['total_cost']) / base_result['total_cost'] * 100
            sd = (result['avg_sl'] - base_result['avg_sl']) * 100
            cost_diff = f"{cd:+.1f}%"
            sl_diff = f"{sd:+.1f}pp"

        sl_nodes = result['sl_per_node']
        print(f"{cfg['name']:<40} {result['total_cost']:>8.1f} {cost_diff:>8} "
              f"{result['avg_sl']*100:>7.2f}% {sl_diff:>8} {result['system_bwe']:>8.2f} "
              f"{sl_nodes['1']:>8} {sl_nodes['2']:>8} {sl_nodes['3']:>8} {sl_nodes['4']:>8}")

print(f"\n{'='*120}")
print("诊断完成")

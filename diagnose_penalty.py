"""
诊断脚本：检查Baseline中分销商的实际平均库存
验证惩罚阈值是否过低
"""
import numpy as np
from supply_chain_env import SupplyChainEnv, RationalAgent

TOTAL_PERIODS = 20000
SEED = 42
INITIAL_INVENTORY = 10.0

env = SupplyChainEnv(
    d=10, rho=0.5, sigma_eps=5.0, L=2, p=5, z=2,
    C_L_rho=2.0, initial_inventory=INITIAL_INVENTORY, K=4,
    total_periods=TOTAL_PERIODS, seed=SEED,
)
agent = RationalAgent(L=2, p=5, z=2, C_L_rho=2.0, sigma_eps=5.0)
for k in range(1, 5):
    agent.init_node(k)

env.reset()
ns_history = {k: [] for k in range(1, 5)}
costs = {k: [] for k in range(1, 5)}

for t in range(TOTAL_PERIODS):
    D_t = env._generate_demand()
    env.customer_demand_history.append(D_t)
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
        holding_cost = max(0, node.net_stock) * 1.0
        stockout_cost = stockout * 2.0
        costs[k].append(holding_cost + stockout_cost)
        ns_history[k].append(node.net_stock)
        node.demand_history.append(demand_k)
        node.pipeline.append(q_t)

print("=" * 70)
print("Baseline各节点平均库存（用于验证惩罚阈值）")
print("=" * 70)
for k in range(1, 5):
    ns_arr = np.array(ns_history[k])
    print(f"  节点{k}: 平均NS={np.mean(ns_arr):.2f}, "
          f"最大NS={np.max(ns_arr):.2f}, 最小NS={np.min(ns_arr):.2f}, "
          f"平均成本={np.mean(costs[k]):.2f}")

print(f"\n当前惩罚阈值: classical_avg_inventory[3]={INITIAL_INVENTORY} "
      f"× penalty_threshold=5.0 = {INITIAL_INVENTORY * 5.0}")
print(f"实际分销商平均库存: {np.mean(ns_history[3]):.2f}")
print(f"惩罚触发比例: {np.mean(np.array(ns_history[3]) > INITIAL_INVENTORY * 5.0) * 100:.1f}%")
print(f"\n问题: 惩罚阈值({INITIAL_INVENTORY * 5.0})远低于实际平均库存({np.mean(ns_history[3]):.2f})")
print(f"     → IDMR库存经常超过阈值 → force_zero频繁触发 → 订货为0 → 缺货 → SL下降")

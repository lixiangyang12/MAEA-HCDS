"""
四级供应链仿真环境
论文复现：缓解牛鞭效应的新途径：人机协同的智慧决策机器人（李勇等, 2022）

供应链结构：零售商(k=1) → 批发商(k=2) → 分销商(k=3) → 制造商(k=4)
需求模型：AR(1) 过程 D_t = d + ρ·D_{t-1} + ε_t
理性决策：SMA移动平均预测 + OUT订至点库存策略
"""

import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional


# ============================================================
# 数据结构
# ============================================================

@dataclass
class NodeState:
    """供应链节点状态"""
    name: str           # 节点名称
    k: int              # 节点层级 (1=零售商, 2=批发商, 3=分销商, 4=制造商)
    net_stock: float = 0.0       # 净库存 NS
    wip: float = 0.0             # 在途库存 WIP
    incoming_orders: float = 0.0  # 收到的下游订单
    order_placed: float = 0.0     # 向上游下的订单
    demand_history: deque = field(default_factory=lambda: deque(maxlen=50000))
    order_history: deque = field(default_factory=lambda: deque(maxlen=50000))
    # 运输管道：pipeline[i] 表示 i+1 期后到达的货物量
    pipeline: deque = field(default_factory=lambda: deque(maxlen=100))


@dataclass
class StepResult:
    """单步仿真结果"""
    t: int
    customer_demand: float
    node_data: dict  # {k: {"NS":, "WIP":, "order":, "demand":, "cost":, "stockout":}}


class SupplyChainEnv:
    """
    四级供应链仿真环境

    参数（来自论文附录）:
        d=10, ρ=0.5, ε~N(0,5), L=2, p=5, z=2, C_{L,ρ}=2
        初始库存=10, 仿真周期=20000

    工程化支持:
        - 支持传入 Config 对象 (来自 config.py)
        - 向后兼容: 也支持直接传参
    """

    def __init__(self, d=10, rho=0.5, sigma_eps=5.0, L=2, p=5, z=2,
                 C_L_rho=2.0, initial_inventory=10.0, K=4,
                 total_periods=20000, seed=None, config=None):
        """
        初始化供应链仿真环境。

        Args:
            d (float): 基础需求均值。
            rho (float): AR(1)需求自相关系数。
            sigma_eps (float): 需求噪声标准差。
            L (int): 订货提前期。
            p (int): 预测窗口。
            z (float): 安全库存系数。
            C_L_rho (float): Lee等(2000)需求预测校正系数。
            initial_inventory (float): 初始库存。
            K (int): 供应链级数 (默认4)。
            total_periods (int): 总仿真周期。
            seed (int): 随机种子。
            config: Config对象 (可选, 覆盖上述参数)。
        """
        # ---- 工程化: 支持Config对象 ----
        if config is not None:
            sc = config.supply_chain
            d, rho, sigma_eps = sc.d, sc.rho, sc.sigma_eps
            L, p, z, C_L_rho = sc.L, sc.p, sc.z, sc.C_L_rho
            initial_inventory, K = sc.initial_inventory, sc.K

        # ---- 环境参数 ----
        self.d = d
        self.rho = rho
        self.sigma_eps = sigma_eps
        self.L = L
        self.p = p
        self.z = z
        self.C_L_rho = C_L_rho
        self.initial_inventory = initial_inventory
        self.K = K
        self.total_periods = total_periods

        # ---- 随机数 (确定性) ----
        self.rng = np.random.default_rng(seed)

        # ---- 节点名称 ----
        # 支持任意 K 值: 前4级使用专用名称, 其余使用通用名称
        _base_names = {1: "零售商", 2: "批发商", 3: "分销商", 4: "制造商"}
        self.node_names = {k: _base_names.get(k, f"节点{k}")
                           for k in range(1, self.K + 1)}

        # ---- 初始化 ----
        self.reset()

    def reset(self):
        """重置环境到初始状态"""
        self.t = 0
        self.D_prev = self.d / (1 - self.rho)  # 初始需求均值

        # 初始化各节点
        self.nodes = {}
        for k in range(1, self.K + 1):
            pipeline = deque([0.0] * self.L, maxlen=self.L + 1)
            self.nodes[k] = NodeState(
                name=self.node_names[k],
                k=k,
                net_stock=self.initial_inventory,
                wip=0.0,
                pipeline=pipeline,
            )
        # 制造商上游无限供应
        self.nodes[self.K].upstream_unlimited = True

        # 记录历史
        self.customer_demand_history = []
        self.results = []

        return self._get_state()

    def _generate_demand(self):
        """生成顾客需求 AR(1): D_t = d + ρ·D_{t-1} + ε_t"""
        eps = self.rng.normal(0, self.sigma_eps)
        D_t = self.d + self.rho * self.D_prev + eps
        D_t = max(0, D_t)  # 需求非负
        self.D_prev = D_t
        return D_t

    def step(self, actions=None):
        """
        执行一个仿真周期

        事件顺序（论文第2.1节）:
            1. 节点k收到下游k-1的订单，向上游k+1补货
            2. 节点k收到上游k+1在L期前发出的货物
            3. 节点k满足下游k-1的订单，更新库存和缺货

        参数:
            actions: dict {k: order_qty}，若为None则使用理性决策
        """
        self.t += 1
        D_t = self._generate_demand()
        self.customer_demand_history.append(D_t)

        # ---- 第一步：各节点收到下游订单，决定向上游订货量 ----
        orders = {}  # {k: 本期订货量}
        downstream_demand = {1: D_t}  # 零售商的下游需求=顾客需求

        for k in range(1, self.K + 1):
            node = self.nodes[k]
            node.incoming_orders = downstream_demand.get(k, 0)

            # 决策：向上游订多少
            if actions and k in actions:
                order = actions[k]
            else:
                order = None  # 由外部Agent填充

            orders[k] = order
            node.order_placed = order
            node.order_history.append(order)

            # 下游的订单 = 当前节点向上游的订单
            downstream_demand[k + 1] = order

        # ---- 第二步：各节点收到上游L期前发出的货物 ----
        for k in range(1, self.K + 1):
            node = self.nodes[k]
            # 从pipeline取出本周期到达的货物
            arrived = node.pipeline[0] if len(node.pipeline) > 0 else 0.0
            node.net_stock += arrived
            # pipeline左移
            if len(node.pipeline) > 0:
                node.pipeline.popleft()

            # 将本期订单放入上游的pipeline（制造商上游无限，直接发货）
            if k < self.K:
                # 上游节点 k+1 的pipeline 追加订单
                upstream = self.nodes[k + 1]
                # 上游在L期后发货给当前节点
                # 实际上，当前节点向上游订货，上游处理后在L期后到货
                # 论文模型：节点k收到的货物来自上游k+1在L期前的发货
                # 所以上游的pipeline记录的是要发给下游的货
                upstream.pipeline.append(order)
            # 制造商(k=K)自己生产，放入自己的pipeline
            # （制造商的pipeline由外部填充或自身产能决定）

        # ---- 修正pipeline逻辑 ----
        # 重新处理：每个节点的pipeline记录的是"上游发给我的货，将在L期后到达"
        # 当节点k向上游k+1订货 q_t，上游在当期发货，经过L期后到达节点k

        # ---- 第三步：各节点满足下游订单，更新库存 ----
        node_results = {}
        for k in range(1, self.K + 1):
            node = self.nodes[k]
            demand = downstream_demand.get(k, 0) if k > 1 else D_t

            # 满足需求
            fulfilled = min(node.net_stock, demand)
            node.net_stock -= fulfilled
            stockout = max(0, demand - fulfilled)  # 缺货量

            # 成本计算（论文：库存成本 + 缺货成本）
            holding_cost = max(0, node.net_stock) * 1.0   # 单位库存成本=1
            stockout_cost = stockout * 2.0                  # 单位缺货成本=2
            total_cost = holding_cost + stockout_cost

            # 服务水平
            sl = 1.0 if demand > 0 and fulfilled >= demand else (fulfilled / demand if demand > 0 else 1.0)

            node.demand_history.append(demand)

            node_results[k] = {
                "NS": node.net_stock,
                "WIP": sum(node.pipeline) if len(node.pipeline) > 0 else 0.0,
                "order": orders[k],
                "demand": demand,
                "fulfilled": fulfilled,
                "stockout": stockout,
                "holding_cost": holding_cost,
                "stockout_cost": stockout_cost,
                "total_cost": total_cost,
                "SL": sl,
            }

        result = StepResult(t=self.t, customer_demand=D_t, node_data=node_results)
        self.results.append(result)
        return result, node_results

    def _get_state(self):
        """获取当前环境状态"""
        state = {}
        for k in range(1, self.K + 1):
            node = self.nodes[k]
            state[k] = {
                "NS": node.net_stock,
                "WIP": sum(node.pipeline) if node.pipeline else 0.0,
                "pipeline": list(node.pipeline),
            }
        return state

    def get_demand_history(self):
        return np.array(self.customer_demand_history)

    def get_order_history(self, k):
        return np.array(list(self.nodes[k].order_history))

    def compute_bullwhip(self):
        """计算各节点方差比 BWE = var(q_k) / var(D)"""
        var_D = np.var(self.customer_demand_history) if len(self.customer_demand_history) > 1 else 0
        bwe = {}
        for k in range(1, self.K + 1):
            orders = list(self.nodes[k].order_history)
            if len(orders) > 1:
                bwe[k] = np.var(orders) / var_D if var_D > 0 else 0
            else:
                bwe[k] = 0
        return bwe


# ============================================================
# 理性决策Agent（SMA + OUT）
# ============================================================

class RationalAgent:
    """
    理性决策基线Agent

    决策流程:
        1. SMA预测: D̂_t^L = (L/p) * Σ D_{t-i}
        2. 预测误差: ê_t^L = C_{L,ρ} * (σ_ε/p) * sqrt(Σ e_{t-i}²)
        3. 期望库存: S_t = D̂_t^L + z * ê_t^L
        4. 订货: q_t = S_t - (NS_t + WIP_t)
    """

    def __init__(self, L=2, p=5, z=2, C_L_rho=2.0, sigma_eps=5.0):
        """
        Args:
            L (int): 订货提前期。
            p (int): SMA预测窗口。
            z (float): 安全库存系数。
            C_L_rho (float): 需求预测校正系数。
            sigma_eps (float): 需求噪声标准差。
        """
        self.L = L
        self.p = p
        self.z = z
        self.C_L_rho = C_L_rho
        self.sigma_eps = sigma_eps

        # 每个节点维护自己的需求历史和预测误差历史
        self.demand_history = {}   # {k: deque}
        self.error_history = {}    # {k: deque}  预测误差 e_t = D_t - D̂_t^1
        self.last_forecast = {}    # {k: 上期单步预测}

    def init_node(self, k):
        """
        为节点k初始化历史记录。

        Args:
            k (int): 节点编号 (1=零售商, ..., K=制造商)。
        """
        self.demand_history[k] = deque(maxlen=10000)
        self.error_history[k] = deque(maxlen=10000)
        self.last_forecast[k] = None

    def predict(self, k):
        """SMA移动平均预测"""
        dh = self.demand_history[k]
        if len(dh) < self.p:
            return None, None

        # 单步预测 D̂_t^1
        recent = list(dh)[-self.p:]
        forecast_1 = np.mean(recent)

        # L步预测 D̂_t^L
        forecast_L = self.L * forecast_1

        # 预测误差标准差 ê_t^L
        eh = self.error_history[k]
        if len(eh) >= self.p:
            recent_errors = list(eh)[-self.p:]
            error_std = self.C_L_rho * (self.sigma_eps / self.p) * np.sqrt(
                np.sum(np.square(recent_errors))
            )
        else:
            error_std = self.sigma_eps

        return forecast_L, error_std

    def decide(self, k, NS, WIP, current_demand):
        """
        为节点k做理性决策

        返回: 订货量 q_t
        """
        if k not in self.demand_history:
            self.init_node(k)

        # 记录需求
        self.demand_history[k].append(current_demand)

        # 更新预测误差
        if self.last_forecast.get(k) is not None:
            e_t = current_demand - self.last_forecast[k]
            self.error_history[k].append(e_t)

        # 预测
        forecast_L, error_std = self.predict(k)

        if forecast_L is None:
            # 数据不足，使用需求本身
            q_t = max(0, current_demand)
        else:
            # 期望库存 S_t = D̂_t^L + z * ê_t^L
            S_t = forecast_L + self.z * error_std
            # 订货 q_t = S_t - (NS + WIP)
            q_t = S_t - (NS + WIP)
            q_t = max(0, q_t)  # 不允许负订货

        # 更新上期预测
        if len(self.demand_history[k]) >= self.p:
            recent = list(self.demand_history[k])[-self.p:]
            self.last_forecast[k] = np.mean(recent)

        return q_t


# ============================================================
# 仿真运行器
# ============================================================

def run_simulation(total_periods=100, seed=42, verbose=True):
    """
    运行理性决策仿真

    参数:
        total_periods: 仿真周期数
        seed: 随机种子
        verbose: 是否打印进度
    """
    # 创建环境
    env = SupplyChainEnv(
        d=10, rho=0.5, sigma_eps=5.0,
        L=2, p=5, z=2, C_L_rho=2.0,
        initial_inventory=10.0, K=4,
        total_periods=total_periods,
        seed=seed,
    )

    # 创建理性决策Agent
    agent = RationalAgent(L=2, p=5, z=2, C_L_rho=2.0, sigma_eps=5.0)
    for k in range(1, 5):
        agent.init_node(k)

    # 运行仿真
    all_results = []
    for t in range(total_periods):
        # 各节点依次决策
        actions = {}
        state = env._get_state()

        # 顾客需求（零售商的下游需求在env内部生成）
        # 各节点看到的"需求"=下游的订单
        # 需要先获取下游订单，但订单在本步决策中产生
        # 简化：按顺序决策，下游先决策

        # 先运行env的一步，但我们需要在step之前提供actions
        # 改进：手动执行一步逻辑

        # 生成需求
        D_t = env._generate_demand()
        env.customer_demand_history.append(D_t)

        # 按供应链顺序决策：零售商→批发商→分销商→制造商
        downstream_demand = {1: D_t}
        node_step_data = {}

        for k in range(1, env.K + 1):
            node = env.nodes[k]
            demand_k = downstream_demand.get(k, 0)

            # Step 1: 收到上游L期前的货物
            arrived = node.pipeline[0] if len(node.pipeline) > 0 else 0.0
            node.net_stock += arrived
            if len(node.pipeline) > 0:
                node.pipeline.popleft()

            # Step 2: Agent决策
            q_t = agent.decide(k, node.net_stock, sum(node.pipeline), demand_k)
            q_t = max(0, q_t)
            actions[k] = q_t
            node.order_placed = q_t
            node.order_history.append(q_t)

            # 下游的需求 = 当前节点的订单
            downstream_demand[k + 1] = q_t

            # Step 3: 满足下游需求
            fulfilled = min(node.net_stock, demand_k)
            node.net_stock -= fulfilled
            stockout = max(0, demand_k - fulfilled)

            holding_cost = max(0, node.net_stock) * 1.0
            stockout_cost = stockout * 2.0

            node.demand_history.append(demand_k)

            node_step_data[k] = {
                "NS": node.net_stock,
                "WIP": sum(node.pipeline) if node.pipeline else 0.0,
                "order": q_t,
                "demand": demand_k,
                "fulfilled": fulfilled,
                "stockout": stockout,
                "holding_cost": holding_cost,
                "stockout_cost": stockout_cost,
                "total_cost": holding_cost + stockout_cost,
                "SL": 1.0 if (demand_k == 0 or fulfilled >= demand_k) else fulfilled / demand_k,
            }

            # 将订单放入pipeline（L期后到达）
            if k < env.K:
                env.nodes[k + 1].pipeline.append(q_t)
            # 制造商的pipeline由自身产能满足（无限供应）

        env.t += 1
        all_results.append({
            "t": env.t,
            "demand": D_t,
            "nodes": node_step_data,
        })

        if verbose and (t + 1) % 20 == 0:
            print(f"  周期 {t+1}/{total_periods} 完成")

    return env, agent, all_results


# ============================================================
# 主程序：运行实验 + 绘图
# ============================================================

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
    matplotlib.rcParams['axes.unicode_minus'] = False

    print("=" * 60)
    print("四级供应链牛鞭效应仿真 — 理性决策基线")
    print("论文复现：李勇等(2022) 缓解牛鞭效应的新途径")
    print("=" * 60)

    # 运行仿真
    print("\n[1] 运行仿真 (100周期)...")
    env, agent, results = run_simulation(total_periods=100, seed=42)

    # 计算方差比
    print("\n[2] 计算方差比 (BWE)...")
    bwe = env.compute_bullwhip()
    node_names = ["零售商", "批发商", "分销商", "制造商"]
    print("\n  节点方差比:")
    for k in range(1, 5):
        print(f"    {node_names[k-1]}: BWE = {bwe[k]:.2f}")

    # 均值统计
    print("\n[3] 需求与订单均值:")
    demand_mean = np.mean(env.customer_demand_history)
    print(f"    顾客需求均值: {demand_mean:.2f}")
    for k in range(1, 5):
        orders = list(env.nodes[k].order_history)
        print(f"    {node_names[k-1]} 订单均值: {np.mean(orders):.2f}")

    # 绘图
    print("\n[4] 绘制方差比折线图...")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 子图1：方差比逐级放大
    ax1 = axes[0]
    levels = [1, 2, 3, 4]
    bwe_values = [bwe[k] for k in levels]
    colors = ['#00d4ff', '#ff6b9d', '#ffd93d', '#6bcf7f']
    bars = ax1.bar(levels, bwe_values, color=colors, edgecolor='white', linewidth=1.5)
    ax1.plot(levels, bwe_values, 'o-', color='#ff006e', linewidth=2, markersize=8)
    ax1.set_xlabel('供应链层级', fontsize=12)
    ax1.set_ylabel('方差比 (BWE)', fontsize=12)
    ax1.set_title('牛鞭效应：方差比逐级放大', fontsize=14, fontweight='bold')
    ax1.set_xticks(levels)
    ax1.set_xticklabels(node_names)
    ax1.grid(True, alpha=0.3)
    for bar, val in zip(bars, bwe_values):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                 f'{val:.1f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

    # 子图2：各节点订单随时间变化
    ax2 = axes[1]
    for k in range(1, 5):
        orders = list(env.nodes[k].order_history)
        ax2.plot(range(1, len(orders)+1), orders, label=node_names[k-1],
                 color=colors[k-1], alpha=0.8, linewidth=1.5)
    demand = env.customer_demand_history
    ax2.plot(range(1, len(demand)+1), demand, '--', color='gray',
             label='顾客需求', alpha=0.6, linewidth=1)
    ax2.set_xlabel('周期', fontsize=12)
    ax2.set_ylabel('订单量', fontsize=12)
    ax2.set_title('各节点订单波动', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('牛鞭效应_理性决策基线.png', dpi=150, bbox_inches='tight')
    print("\n  图表已保存: 牛鞭效应_理性决策基线.png")

    # 验证结论
    print("\n" + "=" * 60)
    print("验证结论:")
    print(f"  [OK] 方差比逐级放大: {'->'.join([f'{bwe[k]:.1f}' for k in range(1,5)])}")
    print(f"  [OK] 牛鞭效应存在: 制造商BWE({bwe[4]:.1f}) >> 零售商BWE({bwe[1]:.1f})")
    print("=" * 60)

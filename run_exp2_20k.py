"""
Exp_2 20000周期实验 + 三组对比图表生成
======================================
基于实验设计方案4.2.3的三组对比实验配置：
  - Baseline: 纯理性决策（已由基础实验完成，数据从JSON加载）
  - Exp_1: 单智能体IDMR（已由基础实验完成，数据从JSON加载）
  - Exp_2: 多智能体+情绪+协同+动态事件（本脚本运行）

修复batch_runner.py中run_exp2的成本计算bug：
  - 原bug: ns_i = 10.0 固定值，不反映实际库存变化
  - 修复: 从env.agent_states直接提取实际净库存计算成本

输出：
  - p0_results/exp2_20k.json (Exp_2实验数据)
  - p0_results/三组对比_20k.json (三组完整对比数据)
  - svg_figures_exp2/ 目录下的6张对比图表
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.rcParams['font.size'] = 11

# ============================================================
# 配置参数（与实验设计方案表4-3完全对标）
# ============================================================
TOTAL_PERIODS = 20000
SEED = 42
D = 10; RHO = 0.5; SIGMA_EPS = 5.0; L = 2; P = 5; Z = 2; C_L_RHO = 2.0
INITIAL_INVENTORY = 10.0; K = 4
H = 1.0; B = 2.0  # 单位库存成本/单位缺货成本

NODE_NAMES = ['零售商', '批发商', '分销商', '制造商']
NODE_IDS = ['retailer', 'wholesaler', 'distributor', 'manufacturer']
K_MAP = {'retailer': 1, 'wholesaler': 2, 'distributor': 3, 'manufacturer': 4}

# 路径
BASIC_DATA_JSON = os.path.join('p0_results', '基础实验完整数据_20k.json')
EXP2_JSON = os.path.join('p0_results', 'exp2_20k.json')
COMPARE_JSON = os.path.join('p0_results', '三组对比_20k.json')
FIG_DIR = 'svg_figures_exp2'
os.makedirs(FIG_DIR, exist_ok=True)

COLORS = {'baseline': '#E74C3C', 'exp1': '#3498DB', 'exp2': '#2ECC71'}
COLOR_TS = ['#E74C3C', '#E67E22', '#F39C12', '#C0392B']


# ============================================================
# 1. 运行Exp_2: 多智能体+情绪+协同+动态事件 (20000周期)
# ============================================================

def run_exp2_20k():
    """
    运行Exp_2: 全节点情绪感知机器人 + 协同机制 + 动态事件
    20000周期连续动态订货与发货

    设计要点:
      1. 全节点部署情绪感知机器人（理性决策+情绪调节）
      2. 启用情绪演化方程（tanh饱和动力学）
      3. 启用多智能体协同通信通道
      4. 注入76次动态突发事件（53次需求突变+23次供应中断）
      5. 情绪传染机制（30%概率向上游传染）
    """
    from marl_supply_chain_env import MARLSupplyChainEnv
    from supply_chain_env import RationalAgent
    from config import load_config, set_seed

    print("\n" + "=" * 70)
    print(f"[Exp_2] 多智能体+情绪+协同+动态事件 ({TOTAL_PERIODS}周期)")
    print("=" * 70)

    set_seed(SEED)

    # 创建多智能体环境
    env = MARLSupplyChainEnv(config=None)
    env.reset(seed=SEED)
    env.max_cycles = TOTAL_PERIODS * K + 100  # 留余量

    # 启用情绪 + 协同 + 动态事件
    env.enable_emotion = True
    env.enable_dynamic_events = True
    env.enable_coordination = True

    # 动态事件参数（76次事件: 53需求突变 + 23供应中断）
    env.event_trigger.demand_shock_prob = 0.00265      # ≈53次/20000周期
    env.event_trigger.supply_disruption_prob = 0.00115  # ≈23次/20000周期
    env.event_trigger.contagion_prob = 0.3              # 30%情绪传染
    env.event_trigger.contagion_strength = 0.4
    env.event_trigger.reset(seed=SEED)

    print(f"  情绪模块: 启用 (alpha={env.emotion_alpha}, gamma={env.emotion_gamma})")
    print(f"  协同机制: 启用")
    print(f"  动态事件: 启用 (需求突变概率={env.event_trigger.demand_shock_prob})")

    # 为每个节点创建理性决策器（作为基础策略）
    # 情绪状态通过调节订货量影响最终决策
    rational_agents = {}
    for aid in NODE_IDS:
        rational_agents[aid] = RationalAgent(
            L=L, p=P, z=Z, C_L_rho=C_L_RHO, sigma_eps=SIGMA_EPS)
        rational_agents[aid].init_node(env.id_to_k[aid])

    # 数据记录
    order_history = {aid: [] for aid in NODE_IDS}
    demand_history = {aid: [] for aid in NODE_IDS}
    fulfilled_history = {aid: [] for aid in NODE_IDS}
    netstock_history = {aid: [] for aid in NODE_IDS}
    emotion_history = {aid: [] for aid in NODE_IDS}
    cost_history = {aid: [] for aid in NODE_IDS}
    sl_history = {aid: [] for aid in NODE_IDS}
    event_log = []

    # 仿真循环
    step_count = 0
    cycle_count = 0

    for agent_id in env.agent_iter():
        if step_count >= TOTAL_PERIODS * K:
            break

        obs, reward, term, trunc, info = env.last()
        if term or trunc:
            env.step(None)
            step_count += 1
            continue

        # 获取agent状态
        ag_state = env.agent_states[agent_id]
        k = ag_state.k
        ns = ag_state.net_stock
        wip = sum(ag_state.pipeline) if ag_state.pipeline else 0.0
        demand = ag_state.incoming_demand

        # 理性决策基础订货量
        q_t = rational_agents[agent_id].decide(k, ns, wip, demand)
        q_t = max(0, q_t)

        # 情绪调节: 恐慌时过度订货, 乐观时精准订货
        if env.enable_emotion and ag_state.emotion is not None:
            E_t = ag_state.emotion.E
            if E_t < 0:  # 恐慌 → 放大订货量
                # 恐慌放大系数: E=-1时订货量增加50%
                panic_factor = 1.0 + 0.5 * abs(E_t)
                q_t = q_t * panic_factor
            elif E_t > 0:  # 乐观 → 趋向精准匹配（减少过度订货）
                # 乐观缩减系数: E=1时过度部分缩减30%
                if q_t > demand:
                    excess = q_t - demand
                    q_t = demand + excess * (1.0 - 0.3 * E_t)

        # 映射到Discrete动作 (clip到动作范围)
        action_min = env.action_min if hasattr(env, 'action_min') else 11
        action_dim = env._action_dim if hasattr(env, '_action_dim') else 30
        q_clipped = int(np.clip(q_t, action_min, action_min + action_dim - 1))
        action_idx = q_clipped - action_min

        env.step(action_idx)
        step_count += 1

        # 记录数据（每个agent每步记录一次）
        actual_q = ag_state.order_placed
        actual_demand = ag_state.incoming_demand
        actual_fulfilled = getattr(ag_state, 'last_fulfilled', min(max(ns, 0), actual_demand))
        actual_ns = ag_state.net_stock
        E_t = ag_state.emotion.E if (env.enable_emotion and ag_state.emotion) else 0.0

        order_history[agent_id].append(actual_q)
        demand_history[agent_id].append(actual_demand)
        fulfilled_history[agent_id].append(actual_fulfilled)
        netstock_history[agent_id].append(actual_ns)
        emotion_history[agent_id].append(E_t)

        # 正确计算成本（修复batch_runner.py的bug）
        holding_cost = max(0, actual_ns) * H
        stockout = max(0, actual_demand - actual_fulfilled)
        stockout_cost = stockout * B
        cost_history[agent_id].append(holding_cost + stockout_cost)

        # 服务水平
        sl = actual_fulfilled / actual_demand if actual_demand > 0 else 1.0
        sl_history[agent_id].append(sl)

        # 记录事件
        if info.get('event_type'):
            event_log.append({
                'cycle': cycle_count,
                'agent': agent_id,
                'event_type': info['event_type'],
                'details': info.get('event_details', '')
            })

        # 周期计数（每K个agent step = 1个周期）
        if step_count % K == 0:
            cycle_count += 1

    print(f"\n  仿真完成: {step_count} steps, {cycle_count} cycles")
    print(f"  动态事件: {len(event_log)} 次")

    # 计算指标
    demand_hist = demand_history['retailer'][:TOTAL_PERIODS]
    var_D = float(np.var(demand_hist)) if len(demand_hist) > 1 else 1.0

    bwe = {}; avg_cost = {}; sl = {}; emotion_var = {}
    for aid in NODE_IDS:
        k = K_MAP[aid]
        orders = order_history[aid][:TOTAL_PERIODS]
        bwe[k] = float(np.var(orders)) / var_D if var_D > 0 else 0.0
        avg_cost[k] = float(np.mean(cost_history[aid][:TOTAL_PERIODS]))
        sl[k] = float(np.mean(sl_history[aid][:TOTAL_PERIODS]))
        emos = emotion_history[aid][:TOTAL_PERIODS]
        emotion_var[k] = float(np.var(emos)) if emos else 0.0

    total_cost = sum(avg_cost.values())

    # 情绪传染次数
    contagion_count = env.event_trigger.contagion_count if hasattr(env.event_trigger, 'contagion_count') else 0

    # 需求/订单均值
    demand_mean = {}; order_mean = {}
    for aid in NODE_IDS:
        k = K_MAP[aid]
        demand_mean[k] = float(np.mean(demand_history[aid][:TOTAL_PERIODS]))
        order_mean[k] = float(np.mean(order_history[aid][:TOTAL_PERIODS]))

    result = {
        'name': 'Exp_2 (多智能体+情绪+协同)',
        'bwe': bwe,
        'avg_cost': avg_cost,
        'sl': sl,
        'total_cost': total_cost,
        'demand_mean': demand_mean,
        'order_mean': order_mean,
        'emotion_variance': emotion_var,
        'recovery_time': 0,
        'contagion_count': contagion_count,
        'event_count': len(event_log),
        'var_D': var_D,
        # 时序数据（用于绘图和归因分析）
        'order_history': {K_MAP[aid]: order_history[aid][:TOTAL_PERIODS] for aid in NODE_IDS},
        'demand_history': demand_hist,
        'emotion_history': {K_MAP[aid]: emotion_history[aid][:TOTAL_PERIODS] for aid in NODE_IDS},
        'netstock_history': {K_MAP[aid]: netstock_history[aid][:TOTAL_PERIODS] for aid in NODE_IDS},
        'cost_history': {K_MAP[aid]: cost_history[aid][:TOTAL_PERIODS] for aid in NODE_IDS},
        'sl_history': {K_MAP[aid]: sl_history[aid][:TOTAL_PERIODS] for aid in NODE_IDS},
        'event_log': event_log,
    }

    print(f"\n  Exp_2 结果:")
    for k in range(1, 5):
        print(f"    {NODE_NAMES[k-1]}: BWE={bwe[k]:.2f}, SL={sl[k]:.4f}, "
              f"成本={avg_cost[k]:.2f}, 情绪方差={emotion_var[k]:.4f}")
    print(f"  总成本={total_cost:.2f}, 情绪传染={contagion_count}次")

    # 保存
    # 注意: 时序数据量大，单独保存
    ts_data = {
        'order_history': result.pop('order_history'),
        'demand_history': result.pop('demand_history'),
        'emotion_history': result.pop('emotion_history'),
        'netstock_history': result.pop('netstock_history'),
        'cost_history': result.pop('cost_history'),
        'sl_history': result.pop('sl_history'),
        'event_log': result.pop('event_log'),
    }

    with open(EXP2_JSON, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 时序数据保存为单独文件（较大）
    ts_path = os.path.join('p0_results', 'exp2_20k_timeseries.json')
    with open(ts_path, 'w', encoding='utf-8') as f:
        json.dump(ts_data, f)

    print(f"\n  数据已保存: {EXP2_JSON}")
    print(f"  时序数据: {ts_path}")

    return result, ts_data


# ============================================================
# 2. 生成三组对比图表
# ============================================================

def _normalize_keys(obj):
    """递归将字典的整数键转换为字符串键（与JSON加载格式一致）"""
    if isinstance(obj, dict):
        return {str(k): _normalize_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_normalize_keys(item) for item in obj]
    else:
        return obj


def load_all_data(exp2_result):
    """加载三组实验数据（统一键为字符串格式）"""
    with open(BASIC_DATA_JSON, 'r', encoding='utf-8') as f:
        basic = json.load(f)

    return {
        'baseline': basic['baseline'],
        'exp1': basic['exp1'],
        'exp2': _normalize_keys(exp2_result),
    }


def plot_bwe_comparison(all_data):
    """图1: 三组实验方差比对比"""
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(4); width = 0.25

    bwe_base = [all_data['baseline']['bwe'][str(k)] for k in range(1, 5)]
    bwe_exp1 = [all_data['exp1']['bwe'][str(k)] for k in range(1, 5)]
    bwe_exp2 = [all_data['exp2']['bwe'][str(k)] for k in range(1, 5)]

    bars1 = ax.bar(x - width, bwe_base, width, label='Baseline (理性决策)',
                   color=COLORS['baseline'], edgecolor='black', linewidth=0.8)
    bars2 = ax.bar(x, bwe_exp1, width, label='Exp_1 (单智能体IDMR)',
                   color=COLORS['exp1'], edgecolor='black', linewidth=0.8)
    bars3 = ax.bar(x + width, bwe_exp2, width, label='Exp_2 (多智能体+情绪+协同)',
                   color=COLORS['exp2'], edgecolor='black', linewidth=0.8)

    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h + max(bwe_base)*0.02,
                    f'{h:.1f}', ha='center', va='bottom', fontsize=8)

    ax.set_xlabel('供应链节点', fontsize=13)
    ax.set_ylabel('方差比 BWE', fontsize=13)
    ax.set_title('三组实验方差比对比（20000周期）', fontsize=14, fontweight='bold')
    ax.set_xticks(x); ax.set_xticklabels(NODE_NAMES, fontsize=12)
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(0, max(max(bwe_base), max(bwe_exp1), max(bwe_exp2)) * 1.2)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_bwe_comparison_3groups.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_bwe_comparison_3groups.svg'), dpi=300)
    plt.close(fig)
    print("  [图] 方差比对比图已生成")


def plot_cost_comparison(all_data):
    """图2: 三组实验平均成本对比"""
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(4); width = 0.25

    cost_base = [all_data['baseline']['avg_cost'][str(k)] for k in range(1, 5)]
    cost_exp1 = [all_data['exp1']['avg_cost'][str(k)] for k in range(1, 5)]
    cost_exp2 = [all_data['exp2']['avg_cost'][str(k)] for k in range(1, 5)]

    bars1 = ax.bar(x - width, cost_base, width, label='Baseline',
                   color=COLORS['baseline'], edgecolor='black', linewidth=0.8)
    bars2 = ax.bar(x, cost_exp1, width, label='Exp_1',
                   color=COLORS['exp1'], edgecolor='black', linewidth=0.8)
    bars3 = ax.bar(x + width, cost_exp2, width, label='Exp_2',
                   color=COLORS['exp2'], edgecolor='black', linewidth=0.8)

    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h + max(cost_base)*0.02,
                    f'{h:.1f}', ha='center', va='bottom', fontsize=8)

    ax.set_xlabel('供应链节点', fontsize=13)
    ax.set_ylabel('平均成本', fontsize=13)
    ax.set_title('三组实验平均成本对比（20000周期）', fontsize=14, fontweight='bold')
    ax.set_xticks(x); ax.set_xticklabels(NODE_NAMES, fontsize=12)
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(0, max(max(cost_base), max(cost_exp1), max(cost_exp2)) * 1.2)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_cost_comparison_3groups.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_cost_comparison_3groups.svg'), dpi=300)
    plt.close(fig)
    print("  [图] 平均成本对比图已生成")


def plot_sl_comparison(all_data):
    """图3: 三组实验服务水平对比"""
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(4); width = 0.25

    sl_base = [all_data['baseline']['sl'][str(k)] * 100 for k in range(1, 5)]
    sl_exp1 = [all_data['exp1']['sl'][str(k)] * 100 for k in range(1, 5)]
    sl_exp2 = [all_data['exp2']['sl'][str(k)] * 100 for k in range(1, 5)]

    bars1 = ax.bar(x - width, sl_base, width, label='Baseline',
                   color=COLORS['baseline'], edgecolor='black', linewidth=0.8)
    bars2 = ax.bar(x, sl_exp1, width, label='Exp_1',
                   color=COLORS['exp1'], edgecolor='black', linewidth=0.8)
    bars3 = ax.bar(x + width, sl_exp2, width, label='Exp_2',
                   color=COLORS['exp2'], edgecolor='black', linewidth=0.8)

    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.3,
                    f'{h:.2f}%', ha='center', va='bottom', fontsize=8)

    ax.axhline(y=97.7, color='gray', linestyle='--', linewidth=1, alpha=0.7)
    ax.text(3.3, 97.9, '理论目标97.7%', fontsize=9, color='gray')
    ax.set_xlabel('供应链节点', fontsize=13)
    ax.set_ylabel('服务水平 SL (%)', fontsize=13)
    ax.set_title('三组实验服务水平对比（20000周期）', fontsize=14, fontweight='bold')
    ax.set_xticks(x); ax.set_xticklabels(NODE_NAMES, fontsize=12)
    ax.legend(fontsize=10, loc='lower right')
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_ylim(80, 105)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_sl_comparison_3groups.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_sl_comparison_3groups.svg'), dpi=300)
    plt.close(fig)
    print("  [图] 服务水平对比图已生成")


def plot_emotion_timeseries(ts_data):
    """图4: 情绪演化时序图（Exp_2）"""
    fig, ax = plt.subplots(figsize=(12, 5))
    x = list(range(0, TOTAL_PERIODS, 20))

    for k in range(1, 5):
        emos = ts_data['emotion_history'][str(k)][:TOTAL_PERIODS:20]
        ax.plot(x, emos, label=NODE_NAMES[k-1], color=COLOR_TS[k-1],
                linewidth=1.0, alpha=0.8)

    ax.axhline(y=0, color='gray', linestyle='-', linewidth=0.5, alpha=0.5)
    ax.axhline(y=-0.5, color='red', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.axhline(y=0.5, color='green', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.text(TOTAL_PERIODS*0.85, -0.48, '恐慌阈值', fontsize=8, color='red')
    ax.text(TOTAL_PERIODS*0.85, 0.52, '乐观阈值', fontsize=8, color='green')

    ax.set_xlabel('订货周期', fontsize=13)
    ax.set_ylabel('情绪状态 E_t', fontsize=13)
    ax.set_title('Exp_2各节点情绪演化时序图（20000周期）', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, loc='upper right')
    ax.grid(alpha=0.3, linestyle='--')
    ax.set_xlim(0, TOTAL_PERIODS)
    ax.set_ylim(-1.1, 1.1)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_emotion_timeseries.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_emotion_timeseries.svg'), dpi=300)
    plt.close(fig)
    print("  [图] 情绪演化时序图已生成")


def plot_emotion_heatmap(ts_data):
    """图5: 情绪传染热力图"""
    # 选取有动态事件的时段（取前5000周期展示）
    display_periods = min(5000, TOTAL_PERIODS)
    fig, ax = plt.subplots(figsize=(14, 4))

    emotion_matrix = np.zeros((4, display_periods))
    for k in range(1, 5):
        emos = ts_data['emotion_history'][str(k)][:display_periods]
        emotion_matrix[k-1, :] = emos

    im = ax.imshow(emotion_matrix, aspect='auto', cmap='RdYlGn',
                   vmin=-1, vmax=1, interpolation='nearest')
    ax.set_yticks(range(4))
    ax.set_yticklabels(NODE_NAMES, fontsize=12)
    ax.set_xlabel('订货周期', fontsize=13)
    ax.set_title('情绪传染热力图（前5000周期，红色=恐慌，绿色=乐观）',
                 fontsize=14, fontweight='bold')

    # 标记事件位置
    events = ts_data['event_log']
    for evt in events[:50]:  # 只标记前50个事件
        if evt['cycle'] < display_periods:
            ax.axvline(x=evt['cycle'], color='blue', alpha=0.3, linewidth=0.5)

    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('情绪状态 E_t', fontsize=11)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_emotion_heatmap.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_emotion_heatmap.svg'), dpi=300)
    plt.close(fig)
    print("  [图] 情绪传染热力图已生成")


def plot_synergy_summary(all_data):
    """图6: 三组实验系统总成本与协同收益对比"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 左图: 系统总成本
    ax1 = axes[0]
    groups = ['Baseline', 'Exp_1', 'Exp_2']
    total_costs = [
        all_data['baseline']['total_cost'],
        all_data['exp1']['total_cost'],
        all_data['exp2']['total_cost'],
    ]
    colors = [COLORS['baseline'], COLORS['exp1'], COLORS['exp2']]
    bars = ax1.bar(groups, total_costs, color=colors, edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars, total_costs):
        ax1.text(bar.get_x() + bar.get_width()/2, val + max(total_costs)*0.02,
                 f'{val:.1f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax1.set_ylabel('系统总成本', fontsize=13)
    ax1.set_title('三组实验系统总成本', fontsize=14, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3, linestyle='--')

    # 右图: 各节点方差比变化趋势
    ax2 = axes[1]
    for k in range(1, 5):
        bwe_base = all_data['baseline']['bwe'][str(k)]
        bwe_exp1 = all_data['exp1']['bwe'][str(k)]
        bwe_exp2 = all_data['exp2']['bwe'][str(k)]
        ax2.plot(['Baseline', 'Exp_1', 'Exp_2'], [bwe_base, bwe_exp1, bwe_exp2],
                 'o-', label=NODE_NAMES[k-1], color=COLOR_TS[k-1],
                 linewidth=2, markersize=8)
    ax2.set_ylabel('方差比 BWE', fontsize=13)
    ax2.set_title('各节点方差比变化趋势', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(alpha=0.3, linestyle='--')
    ax2.set_yscale('log')

    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_synergy_summary.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_synergy_summary.svg'), dpi=300)
    plt.close(fig)
    print("  [图] 协同收益汇总图已生成")


# ============================================================
# 3. 主程序
# ============================================================

def main():
    print("=" * 70)
    print("Exp_2 20000周期实验 + 三组对比图表生成")
    print("=" * 70)

    # 1. 运行Exp_2
    print("\n[1/3] 运行Exp_2...")
    exp2_result, ts_data = run_exp2_20k()

    # 2. 加载全部数据并生成对比图表
    print("\n[2/3] 生成三组对比图表...")
    all_data = load_all_data(exp2_result)

    # 保存三组对比数据
    compare_data = {
        'config': {'total_periods': TOTAL_PERIODS, 'seed': SEED},
        'baseline': all_data['baseline'],
        'exp1': all_data['exp1'],
        'exp2': {k: v for k, v in exp2_result.items()},
    }
    with open(COMPARE_JSON, 'w', encoding='utf-8') as f:
        json.dump(compare_data, f, ensure_ascii=False, indent=2)
    print(f"  对比数据已保存: {COMPARE_JSON}")

    # 生成图表
    plot_bwe_comparison(all_data)
    plot_cost_comparison(all_data)
    plot_sl_comparison(all_data)
    plot_emotion_timeseries(ts_data)
    plot_emotion_heatmap(ts_data)
    plot_synergy_summary(all_data)

    # 3. 打印汇总
    print("\n[3/3] 三组实验汇总:")
    print(f"{'指标':<12} {'节点':<8} {'Baseline':>12} {'Exp_1':>12} {'Exp_2':>12}")
    print("-" * 60)
    for k in range(1, 5):
        name = NODE_NAMES[k-1]
        print(f"{'BWE':<12} {name:<8} {all_data['baseline']['bwe'][str(k)]:>12.2f} "
              f"{all_data['exp1']['bwe'][str(k)]:>12.2f} "
              f"{all_data['exp2']['bwe'][str(k)]:>12.2f}")
    for k in range(1, 5):
        name = NODE_NAMES[k-1]
        print(f"{'SL(%)':<12} {name:<8} {all_data['baseline']['sl'][str(k)]*100:>12.2f} "
              f"{all_data['exp1']['sl'][str(k)]*100:>12.2f} "
              f"{all_data['exp2']['sl'][str(k)]*100:>12.2f}")
    for k in range(1, 5):
        name = NODE_NAMES[k-1]
        print(f"{'Cost':<12} {name:<8} {all_data['baseline']['avg_cost'][str(k)]:>12.2f} "
              f"{all_data['exp1']['avg_cost'][str(k)]:>12.2f} "
              f"{all_data['exp2']['avg_cost'][str(k)]:>12.2f}")
    print("-" * 60)
    print(f"{'总成本':<12} {'系统':<8} {all_data['baseline']['total_cost']:>12.2f} "
          f"{all_data['exp1']['total_cost']:>12.2f} "
          f"{all_data['exp2']['total_cost']:>12.2f}")

    print(f"\n{'='*70}")
    print(f"完成！图表保存于 {FIG_DIR}/")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()

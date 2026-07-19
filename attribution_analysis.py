"""
深度归因分析: 情绪-决策相关性 / 传染路径 / 正向激励阻断效应
==============================================================

三项分析:
    1. 情绪-决策相关性: 皮尔逊相关系数 (E_t vs q_t / 超额库存)
       验证恐慌(E<0)时订货量是否显著上升
    2. 情绪传染路径可视化: Heatmap (时间×节点情绪) + NetworkX (传染网络)
       展示恐慌从零售商逐级向上游蔓延
    3. 正向激励阻断效应: 有/无正向激励对比
       分析恐慌时正向激励是否拉高订货阈值, 减少无效囤货

输出:
    - 归因分析_情绪决策相关性.png
    - 归因分析_情绪传染热力图.png
    - 归因分析_传染网络图.png
    - 归因分析_正向激励阻断效应.png
    - 归因分析_详细数据.csv
"""

import warnings
warnings.filterwarnings('ignore')
import os
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import numpy as np
import json
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

# 数据处理
try:
    import pandas as pd
    HAS_PANDAS = True
except Exception:
    HAS_PANDAS = False
    pd = None

# 统计
from scipy import stats

# 绘图
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False

try:
    import seaborn as sns
    HAS_SEABORN = True
except Exception:
    HAS_SEABORN = False
    sns = None

try:
    import networkx as nx
    HAS_NETWORKX = True
except Exception:
    HAS_NETWORKX = False
    nx = None

# ============================================================
# 配置
# ============================================================
SIM_PERIODS = 2000          # 仿真周期 (收集数据用)
SEED = 42
NODE_IDS = ['retailer', 'wholesaler', 'distributor', 'manufacturer']
NODE_NAMES_CN = {'retailer': '零售商', 'wholesaler': '批发商',
                 'distributor': '分销商', 'manufacturer': '制造商'}
K_TO_ID = {1: 'retailer', 2: 'wholesaler', 3: 'distributor', 4: 'manufacturer'}


# ============================================================
# 1. 数据收集: 运行 MARL 环境收集逐周期详细数据
# ============================================================

def collect_detailed_data(total_periods: int, seed: int,
                           enable_bonus: bool = True,
                           enable_emotion: bool = True,
                           enable_events: bool = True) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    运行 MARL 环境, 收集逐周期详细数据

    参数:
        total_periods: 仿真周期
        seed: 随机种子
        enable_bonus: 是否启用正向激励
        enable_emotion: 是否启用情绪模块
        enable_events: 是否启用动态事件

    返回:
        df: 逐周期数据 DataFrame
            列: [t, agent_id, node_name, k, emotion_E, order_q,
                 net_stock, demand, fulfilled, stockout, excess_inventory,
                 demand_shock, supply_disruption]
        contagion_log: 情绪传染事件日志
    """
    from marl_supply_chain_env import MARLSupplyChainEnv
    from supply_chain_env import RationalAgent

    env = MARLSupplyChainEnv(config=None)
    env.reset(seed=seed)
    env.max_cycles = total_periods + 10

    # 配置开关
    env.enable_emotion = enable_emotion
    env.enable_dynamic_events = enable_events
    env.enable_inventory_bonus = enable_bonus
    if enable_events:
        env.event_trigger.demand_shock_prob = 0.03
        env.event_trigger.supply_disruption_prob = 0.015
        env.event_trigger.contagion_prob = 0.4
        env.event_trigger.contagion_strength = 0.4
        env.event_trigger.reset(seed=seed)

    # 理性决策器 (基础策略)
    rational_agents = {}
    for aid in NODE_IDS:
        rational_agents[aid] = RationalAgent(L=2, p=5, z=2, C_L_rho=2.0, sigma_eps=5.0)
        rational_agents[aid].init_node(env.id_to_k[aid])

    records = []
    contagion_log = []
    step_count = 0
    max_steps = total_periods * 4

    for agent_id in env.agent_iter():
        if step_count >= max_steps:
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

        # 记录数据 (step后的状态)
        ag = env.agent_states[agent_id]
        E_val = float(ag.emotion.E) if ag.emotion is not None else 0.0
        # 超额库存: 超出需求的部分
        excess = max(0, ag.net_stock - ag.incoming_demand) if ag.incoming_demand > 0 else max(0, ag.net_stock)
        # 动态事件标记
        d_shock = env._current_cycle_events.get('demand_shock', False)
        s_disrupt = env._current_cycle_events.get('supply_disruption', False)

        records.append({
            't': info.get('t', env.t),
            'agent_id': agent_id,
            'node_name': NODE_NAMES_CN[agent_id],
            'k': k,
            'emotion_E': E_val,
            'order_q': float(ag.order_placed),
            'net_stock': float(ag.net_stock),
            'demand': float(ag.incoming_demand),
            'fulfilled': float(ag.fulfilled),
            'stockout': float(ag.stockout),
            'excess_inventory': float(excess),
            'demand_shock': d_shock,
            'supply_disruption': s_disrupt,
        })

        # 收集情绪传染事件
        conts = env._current_cycle_events.get('emotion_contagion', [])
        for c in conts:
            c_log = dict(c)
            c_log['t'] = info.get('t', env.t)
            contagion_log.append(c_log)

    df = pd.DataFrame(records)
    return df, contagion_log


# ============================================================
# 2. 分析1: 情绪-决策皮尔逊相关性分析
# ============================================================

def analyze_emotion_decision_correlation(df: pd.DataFrame, save_path: str):
    """
    计算各节点情绪状态值与订货量/超额库存的皮尔逊相关系数

    验证假设: 当情绪为负(恐慌)时, 订货量显著上升 (损失厌恶→过度订货)
    """
    print("\n" + "=" * 60)
    print("[分析1] 情绪-决策皮尔逊相关性分析")
    print("=" * 60)

    results = []
    for aid in NODE_IDS:
        sub = df[df['agent_id'] == aid].copy()
        if len(sub) < 3:
            continue
        name = NODE_NAMES_CN[aid]

        # 全样本相关系数
        r_order, p_order = stats.pearsonr(sub['emotion_E'], sub['order_q'])
        r_excess, p_excess = stats.pearsonr(sub['emotion_E'], sub['excess_inventory'])

        # 分组: 恐慌(E<0) vs 乐观(E>0)
        panic = sub[sub['emotion_E'] < -0.1]
        optimistic = sub[sub['emotion_E'] > 0.1]
        neutral = sub[(sub['emotion_E'] >= -0.1) & (sub['emotion_E'] <= 0.1)]

        panic_order_mean = panic['order_q'].mean() if len(panic) > 0 else 0
        opt_order_mean = optimistic['order_q'].mean() if len(optimistic) > 0 else 0
        neut_order_mean = neutral['order_q'].mean() if len(neutral) > 0 else 0

        results.append({
            'node': name,
            'agent_id': aid,
            'r_emotion_order': r_order,
            'p_emotion_order': p_order,
            'r_emotion_excess': r_excess,
            'p_emotion_excess': p_excess,
            'panic_order_mean': panic_order_mean,
            'optimistic_order_mean': opt_order_mean,
            'neutral_order_mean': neut_order_mean,
            'n_panic': len(panic),
            'n_optimistic': len(optimistic),
            'n_neutral': len(neutral),
        })

        sig = '***' if p_order < 0.01 else ('**' if p_order < 0.05 else ('*' if p_order < 0.1 else 'ns'))
        print(f"\n  [{name}]")
        print(f"    E vs 订货量: r={r_order:+.4f} (p={p_order:.4f}) {sig}")
        print(f"    E vs 超额库存: r={r_excess:+.4f} (p={p_excess:.4f})")
        print(f"    恐慌(E<-0.1)平均订货: {panic_order_mean:.2f} (n={len(panic)})")
        print(f"    乐观(E>+0.1)平均订货: {opt_order_mean:.2f} (n={len(optimistic)})")
        print(f"    中性平均订货: {neut_order_mean:.2f} (n={len(neutral)})")

    # 验证假设: 恐慌时订货量是否上升
    print("\n  [假设验证] 恐慌(E<0)时订货量是否显著上升:")
    for r in results:
        diff = r['panic_order_mean'] - r['optimistic_order_mean']
        pct = (diff / r['optimistic_order_mean'] * 100) if r['optimistic_order_mean'] > 0 else 0
        verdict = '支持' if diff > 0 else '不支持'
        print(f"    {r['node']}: 恐慌比乐观多订 {diff:+.2f} ({pct:+.1f}%) → {verdict}假设")

    # ---- 绘图: 相关性矩阵 + 分组对比 ----
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 左图: 各节点 r 系数条形图
    ax1 = axes[0]
    nodes = [r['node'] for r in results]
    r_vals = [r['r_emotion_order'] for r in results]
    colors = ['#E53935' if r < 0 else '#43A047' for r in r_vals]
    bars = ax1.barh(nodes, r_vals, color=colors, alpha=0.8, edgecolor='black')
    ax1.axvline(x=0, color='black', linewidth=0.8)
    ax1.set_xlabel('皮尔逊相关系数 r (E_t vs 订货量)', fontsize=12)
    ax1.set_title('情绪-订货量相关性\n(负值=恐慌↑→订货↑, 支持损失厌恶)', fontsize=12)
    ax1.set_xlim(-1, 1)
    for bar, r in zip(bars, results):
        sig = '***' if r['p_emotion_order'] < 0.01 else ('**' if r['p_emotion_order'] < 0.05 else '')
        ax1.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height()/2,
                 f'{r["r_emotion_order"]:+.3f}{sig}', va='center', fontsize=10)

    # 右图: 恐慌 vs 乐观 订货量对比
    ax2 = axes[1]
    x = np.arange(len(results))
    width = 0.35
    panic_vals = [r['panic_order_mean'] for r in results]
    opt_vals = [r['optimistic_order_mean'] for r in results]
    ax2.bar(x - width/2, panic_vals, width, label='恐慌(E<-0.1)', color='#E53935', alpha=0.8)
    ax2.bar(x + width/2, opt_vals, width, label='乐观(E>+0.1)', color='#43A047', alpha=0.8)
    ax2.set_xticks(x)
    ax2.set_xticklabels(nodes)
    ax2.set_ylabel('平均订货量', fontsize=12)
    ax2.set_title('恐慌 vs 乐观 订货量对比\n(验证恐慌时过度订货)', fontsize=12)
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  [绘图] 相关性分析图已保存: {save_path}")

    return pd.DataFrame(results)


# ============================================================
# 3. 分析2: 情绪传染路径可视化
# ============================================================

def plot_emotion_contagion(df: pd.DataFrame, contagion_log: List[Dict],
                            save_heatmap: str, save_network: str):
    """
    情绪传染路径可视化

    图1: Heatmap (时间×节点, 颜色=情绪值E_t)
         标注需求突变时刻, 展示恐慌蔓延
    图2: NetworkX 传染网络图 (节点=供应链层级, 边=传染次数)
    """
    print("\n" + "=" * 60)
    print("[分析2] 情绪传染路径可视化")
    print("=" * 60)

    # ---- 图1: 情绪时序热力图 ----
    pivot = df.pivot_table(index='agent_id', columns='t', values='emotion_E',
                            aggfunc='first')
    # 按供应链顺序排列
    pivot = pivot.reindex(NODE_IDS)

    fig, ax = plt.subplots(figsize=(14, 5))
    # 采样以避免图过宽
    n_cols = pivot.shape[1]
    if n_cols > 200:
        step = n_cols // 200
        pivot = pivot.iloc[:, ::step]

    im = ax.imshow(pivot.values, aspect='auto', cmap='RdBu_r',
                   vmin=-1, vmax=1, interpolation='nearest')
    ax.set_yticks(range(len(NODE_IDS)))
    ax.set_yticklabels([NODE_NAMES_CN[a] for a in NODE_IDS], fontsize=11)
    ax.set_xlabel('仿真周期', fontsize=12)
    ax.set_title('情绪传染时序热力图\n(红=恐慌 E<0, 蓝=乐观 E>0)', fontsize=13, fontweight='bold')

    # 标注需求突变时刻
    shock_ts = df[df['demand_shock']]['t'].unique()
    for st in shock_ts:
        if st <= pivot.columns[-1]:
            ax.axvline(x=st / (pivot.columns[1] - pivot.columns[0]) if len(pivot.columns) > 1 else st,
                       color='green', linewidth=1, linestyle='--', alpha=0.7)
    if len(shock_ts) > 0:
        ax.text(0.02, 0.95, f'绿线=需求突变 ({len(shock_ts)}次)',
                transform=ax.transAxes, fontsize=9, color='green',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.colorbar(im, ax=ax, label='情绪状态 E_t', shrink=0.8)
    plt.tight_layout()
    plt.savefig(save_heatmap, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [绘图] 情绪传染热力图已保存: {save_heatmap}")

    # ---- 图2: NetworkX 传染网络图 ----
    if contagion_log and HAS_NETWORKX:
        # 统计传染路径次数
        edge_counts = defaultdict(int)
        for c in contagion_log:
            edge_counts[(c['from'], c['to'])] += 1

        G = nx.DiGraph()
        # 添加所有节点
        for aid in NODE_IDS:
            G.add_node(aid, name=NODE_NAMES_CN[aid])

        # 添加传染边
        for (src, dst), count in edge_counts.items():
            G.add_edge(src, dst, weight=count)

        fig, ax = plt.subplots(figsize=(8, 5))
        # 层级布局 (左→右: 零售商→制造商)
        pos = {aid: (i, 0) for i, aid in enumerate(NODE_IDS)}

        # 节点大小: 按情绪波动
        node_sizes = []
        for aid in NODE_IDS:
            sub = df[df['agent_id'] == aid]
            vol = sub['emotion_E'].var() if len(sub) > 1 else 0
            node_sizes.append(500 + vol * 2000)

        # 节点颜色: 按平均情绪
        node_colors = []
        for aid in NODE_IDS:
            sub = df[df['agent_id'] == aid]
            mean_E = sub['emotion_E'].mean() if len(sub) > 0 else 0
            node_colors.append(mean_E)

        nodes = nx.draw_networkx_nodes(G, pos, node_size=node_sizes,
                                        node_color=node_colors, cmap='RdBu_r',
                                        vmin=-0.5, vmax=0.5, ax=ax)
        # 边
        edges = G.edges(data=True)
        edge_widths = [e[2]['weight'] * 0.5 + 0.5 for e in edges]
        nx.draw_networkx_edges(G, pos, edgelist=[(e[0], e[1]) for e in edges],
                              width=edge_widths, edge_color='#E53935',
                              arrows=True, arrowsize=20, ax=ax,
                              connectionstyle='arc3,rad=0.1')
        # 标签
        labels = {aid: NODE_NAMES_CN[aid] for aid in NODE_IDS}
        nx.draw_networkx_labels(G, pos, labels, font_size=11, ax=ax)
        # 边权重标注
        edge_labels = {(e[0], e[1]): f'{e[2]["weight"]}次' for e in edges}
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=9, ax=ax,
                                      label_pos=0.3)

        ax.set_title('情绪传染网络图\n(箭头=传染方向, 边宽=传染次数, '
                     '节点大小=情绪波动, 颜色=平均情绪)', fontsize=12, fontweight='bold')
        ax.axis('off')
        plt.colorbar(nodes, ax=ax, label='平均情绪 E', shrink=0.6)
        plt.tight_layout()
        plt.savefig(save_network, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  [绘图] 传染网络图已保存: {save_network}")
        print(f"  [统计] 传染路径: {dict(edge_counts)}")
    else:
        print("  [跳过] 无传染事件或NetworkX不可用")


# ============================================================
# 4. 分析3: 正向激励阻断效应
# ============================================================

def analyze_bonus_blocking_effect(save_path: str):
    """
    对比有/无正向激励两组实验, 分析阻断效应

    假设: 正向激励在恐慌时拉高订货阈值, 减少无效囤货
    """
    print("\n" + "=" * 60)
    print("[分析3] 正向激励阻断效应对比")
    print("=" * 60)

    # 运行两组实验
    print("  运行实验组A (有正向激励)...")
    df_bonus, _ = collect_detailed_data(
        SIM_PERIODS, SEED, enable_bonus=True, enable_emotion=True, enable_events=True)
    df_bonus['group'] = '有正向激励'

    print("  运行实验组B (无正向激励)...")
    df_no_bonus, _ = collect_detailed_data(
        SIM_PERIODS, SEED, enable_bonus=False, enable_emotion=True, enable_events=True)
    df_no_bonus['group'] = '无正向激励'

    combined = pd.concat([df_bonus, df_no_bonus], ignore_index=True)

    # 分析: 极度恐慌时(E<-0.5)的订货量对比
    print("\n  [极度恐慌时(E<-0.5)订货量对比]")
    panic_bonus = df_bonus[(df_bonus['emotion_E'] < -0.5)]
    panic_no = df_no_bonus[(df_no_bonus['emotion_E'] < -0.5)]

    results = []
    for aid in NODE_IDS:
        name = NODE_NAMES_CN[aid]
        pb = panic_bonus[panic_bonus['agent_id'] == aid]['order_q']
        pn = panic_no[panic_no['agent_id'] == aid]['order_q']
        pb_mean = pb.mean() if len(pb) > 0 else 0
        pn_mean = pn.mean() if len(pn) > 0 else 0
        diff = pn_mean - pb_mean
        pct = (diff / pn_mean * 100) if pn_mean > 0 else 0
        results.append({
            'node': name,
            'panic_order_bonus': pb_mean,
            'panic_order_no_bonus': pn_mean,
            'reduction': diff,
            'reduction_pct': pct,
            'n_bonus': len(pb),
            'n_no_bonus': len(pn),
        })
        print(f"    {name}: 有激励={pb_mean:.2f}(n={len(pb)}), "
              f"无激励={pn_mean:.2f}(n={len(pn)}), "
              f"减少{diff:+.2f} ({pct:+.1f}%)")

    # 整体超额库存对比
    print("\n  [超额库存对比 (全样本)]")
    for aid in NODE_IDS:
        name = NODE_NAMES_CN[aid]
        eb = df_bonus[df_bonus['agent_id'] == aid]['excess_inventory'].mean()
        en = df_no_bonus[df_no_bonus['agent_id'] == aid]['excess_inventory'].mean()
        print(f"    {name}: 有激励={eb:.2f}, 无激励={en:.2f}, "
              f"差异={en-eb:+.2f}")

    # ---- 绘图 ----
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 左图: 恐慌时订货量对比
    ax1 = axes[0]
    nodes = [r['node'] for r in results]
    x = np.arange(len(results))
    width = 0.35
    bonus_vals = [r['panic_order_bonus'] for r in results]
    no_bonus_vals = [r['panic_order_no_bonus'] for r in results]
    ax1.bar(x - width/2, bonus_vals, width, label='有正向激励', color='#43A047', alpha=0.8)
    ax1.bar(x + width/2, no_bonus_vals, width, label='无正向激励', color='#E53935', alpha=0.8)
    ax1.set_xticks(x)
    ax1.set_xticklabels(nodes)
    ax1.set_ylabel('恐慌时(E<-0.5)平均订货量', fontsize=12)
    ax1.set_title('正向激励阻断效应\n(恐慌时订货量: 有激励 vs 无激励)', fontsize=12)
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)
    # 标注减少百分比
    for i, r in enumerate(results):
        ax1.text(i, max(bonus_vals[i], no_bonus_vals[i]) + 1,
                 f'{r["reduction_pct"]:+.1f}%', ha='center', fontsize=9,
                 color='#1565C0', fontweight='bold')

    # 右图: 情绪-订货量散点图 (有激励 vs 无激励, 分销商)
    ax2 = axes[1]
    dist_bonus = df_bonus[df_bonus['agent_id'] == 'distributor']
    dist_no = df_no_bonus[df_no_bonus['agent_id'] == 'distributor']
    ax2.scatter(dist_bonus['emotion_E'], dist_bonus['order_q'],
                alpha=0.3, s=10, color='#43A047', label='有正向激励')
    ax2.scatter(dist_no['emotion_E'], dist_no['order_q'],
                alpha=0.3, s=10, color='#E53935', label='无正向激励')
    # 拟合线
    for sub, color, label in [(dist_bonus, '#2E7D32', '有激励拟合'),
                               (dist_no, '#B71C1C', '无激励拟合')]:
        if len(sub) > 2:
            z = np.polyfit(sub['emotion_E'], sub['order_q'], 1)
            xs = np.linspace(sub['emotion_E'].min(), sub['emotion_E'].max(), 50)
            ax2.plot(xs, np.polyval(z, xs), color=color, linewidth=2, label=label)
    ax2.axvline(x=-0.5, color='orange', linestyle='--', alpha=0.7, label='极度恐慌阈值')
    ax2.set_xlabel('情绪状态 E_t', fontsize=12)
    ax2.set_ylabel('订货量', fontsize=12)
    ax2.set_title('分销商: 情绪-订货量散点对比\n(正向激励阻断过度订货)', fontsize=12)
    ax2.legend(fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  [绘图] 阻断效应图已保存: {save_path}")

    return pd.DataFrame(results)


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 60)
    print("深度归因分析: 情绪-决策相关性 / 传染路径 / 阻断效应")
    print(f"配置: 仿真周期={SIM_PERIODS}, 种子={SEED}")
    print(f"环境: pandas={HAS_PANDAS}, seaborn={HAS_SEABORN}, networkx={HAS_NETWORKX}")
    print("=" * 60)

    # ---- 收集详细数据 ----
    print("\n[数据收集] 运行MARL环境收集逐周期数据...")
    df, contagion_log = collect_detailed_data(
        SIM_PERIODS, SEED, enable_bonus=True, enable_emotion=True, enable_events=True)
    print(f"  收集 {len(df)} 条记录, {len(contagion_log)} 次情绪传染事件")

    # 保存原始数据
    df.to_csv('归因分析_详细数据.csv', index=False, encoding='utf-8-sig')
    print(f"  详细数据已保存: 归因分析_详细数据.csv")

    # ---- 分析1: 情绪-决策相关性 ----
    corr_df = analyze_emotion_decision_correlation(
        df, '归因分析_情绪决策相关性.png')

    # ---- 分析2: 情绪传染路径可视化 ----
    plot_emotion_contagion(
        df, contagion_log,
        '归因分析_情绪传染热力图.png', '归因分析_传染网络图.png')

    # ---- 分析3: 正向激励阻断效应 ----
    bonus_df = analyze_bonus_blocking_effect(
        '归因分析_正向激励阻断效应.png')

    # ---- 汇总 ----
    print("\n" + "=" * 60)
    print("[完成] 深度归因分析全部完成!")
    print("=" * 60)
    print("\n生成文件:")
    print("  1. 归因分析_情绪决策相关性.png  (皮尔逊相关系数)")
    print("  2. 归因分析_情绪传染热力图.png  (时间×节点情绪热力图)")
    print("  3. 归因分析_传染网络图.png     (NetworkX传染路径)")
    print("  4. 归因分析_正向激励阻断效应.png (有/无激励对比)")
    print("  5. 归因分析_详细数据.csv       (逐周期原始数据)")


if __name__ == '__main__':
    main()

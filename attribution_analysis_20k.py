"""
归因分析（20000周期）
====================
基于Exp_2时序数据，进行三方面归因分析：

1. 情绪-决策相关性分析
   - 计算各节点情绪状态E_t与订货量q_t的Pearson相关系数
   - 验证H1: 恐慌时订货量是否显著上升
   - 分组对比: 恐慌/中性/乐观状态下的订货决策偏差

2. 情绪传染路径可视化
   - 情绪传染热力图（跨节点×时间）
   - NetworkX传染网络图（传染路径与强度）
   - 需求突变事件前后的情绪传染时序

3. 正向激励阻断效应分析
   - 对比Exp_1（无正向激励）vs Exp_2（有正向激励+情绪+协同）
   - 分析情绪极端状态下的订货偏差阻断效果
   - 验证H2: 正向激励是否阻断恐慌→过度订货的恶性循环

输出:
  - svg_figures_exp2/ 下的归因分析图表
  - p0_results/归因分析_20k.json 结构化分析结果
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

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    print("[警告] networkx未安装, 跳过网络图")

from scipy import stats

# ============================================================
# 配置
# ============================================================
TOTAL_PERIODS = 20000
NODE_NAMES = ['零售商', '批发商', '分销商', '制造商']
NODE_IDS = ['retailer', 'wholesaler', 'distributor', 'manufacturer']

EXP2_TS_JSON = os.path.join('p0_results', 'exp2_20k_timeseries.json')
EXP2_JSON = os.path.join('p0_results', 'exp2_20k.json')
BASIC_JSON = os.path.join('p0_results', '基础实验完整数据_20k.json')
COMPARE_JSON = os.path.join('p0_results', '三组对比_20k.json')
FIG_DIR = 'svg_figures_exp2'
RESULT_JSON = os.path.join('p0_results', '归因分析_20k.json')

COLOR_TS = ['#E74C3C', '#E67E22', '#F39C12', '#C0392B']
COLOR_NEG = '#E74C3C'   # 恐慌=红
COLOR_NEU = '#95A5A6'   # 中性=灰
COLOR_POS = '#2ECC71'   # 乐观=绿


# ============================================================
# 1. 情绪-决策相关性分析
# ============================================================

def analyze_emotion_decision_correlation(ts_data):
    """
    分析各节点情绪状态与订货决策的相关性

    H1验证: 恐慌时订货量是否显著上升
    """
    print("\n[1] 情绪-决策相关性分析")

    results = {}
    k_map = {1: '零售商', 2: '批发商', 3: '分销商', 4: '制造商'}

    for k in range(1, 5):
        emotions = np.array(ts_data['emotion_history'][str(k)][:TOTAL_PERIODS])
        orders = np.array(ts_data['order_history'][str(k)][:TOTAL_PERIODS])
        demands = np.array(ts_data['demand_history'][:TOTAL_PERIODS])

        # 计算超额订货量 = 订货量 - 需求
        excess_orders = orders - demands

        # Pearson相关系数
        corr_order, p_order = stats.pearsonr(emotions, orders)
        corr_excess, p_excess = stats.pearsonr(emotions, excess_orders)

        # 分组统计: 恐慌/中性/乐观
        panic_mask = emotions < -0.3
        neutral_mask = (emotions >= -0.1) & (emotions <= 0.1)
        optimistic_mask = emotions > 0.3

        panic_orders = orders[panic_mask] if panic_mask.sum() > 0 else np.array([0])
        neutral_orders = orders[neutral_mask] if neutral_mask.sum() > 0 else np.array([0])
        optimistic_orders = orders[optimistic_mask] if optimistic_mask.sum() > 0 else np.array([0])

        result = {
            'node': k_map[k],
            'pearson_emotion_order': float(corr_order),
            'p_value_order': float(p_order),
            'pearson_emotion_excess': float(corr_excess),
            'p_value_excess': float(p_excess),
            'panic_count': int(panic_mask.sum()),
            'neutral_count': int(neutral_mask.sum()),
            'optimistic_count': int(optimistic_mask.sum()),
            'panic_mean_order': float(np.mean(panic_orders)),
            'neutral_mean_order': float(np.mean(neutral_orders)),
            'optimistic_mean_order': float(np.mean(optimistic_orders)),
            'panic_std_order': float(np.std(panic_orders)),
            'neutral_std_order': float(np.std(neutral_orders)),
            'optimistic_std_order': float(np.std(optimistic_orders)),
        }
        results[k] = result

        print(f"  {k_map[k]}: corr(E,q)={corr_order:.3f}(p={p_order:.4f}), "
              f"corr(E,excess)={corr_excess:.3f}(p={p_excess:.4f})")
        print(f"    恐慌({panic_mask.sum()}): 均值={np.mean(panic_orders):.2f}, "
              f"中性({neutral_mask.sum()}): {np.mean(neutral_orders):.2f}, "
              f"乐观({optimistic_mask.sum()}): {np.mean(optimistic_orders):.2f}")

    return results


def plot_emotion_decision_correlation(ts_data, corr_results):
    """绘制情绪-决策相关性分析图"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    for idx, k in enumerate(range(1, 5)):
        ax = axes[idx // 2][idx % 2]
        emotions = np.array(ts_data['emotion_history'][str(k)][:TOTAL_PERIODS])
        orders = np.array(ts_data['order_history'][str(k)][:TOTAL_PERIODS])

        # 散点图
        ax.scatter(emotions, orders, alpha=0.1, s=5, color=COLOR_TS[k-1])

        # 回归线
        z = np.polyfit(emotions, orders, 1)
        x_line = np.linspace(-1, 1, 100)
        y_line = np.polyval(z, x_line)
        ax.plot(x_line, y_line, 'k--', linewidth=2, alpha=0.7)

        r = corr_results[k]['pearson_emotion_order']
        p = corr_results[k]['p_value_order']
        ax.set_title(f'{NODE_NAMES[k-1]} (r={r:.3f}, p={p:.4f})',
                     fontsize=12, fontweight='bold')
        ax.set_xlabel('情绪状态 E_t', fontsize=11)
        ax.set_ylabel('订货量 q_t', fontsize=11)
        ax.axvline(x=0, color='gray', linestyle='-', alpha=0.3)
        ax.grid(alpha=0.3, linestyle='--')

        # 标注恐慌/乐观区域
        ax.axvspan(-1, -0.3, alpha=0.1, color='red', label='恐慌区')
        ax.axvspan(0.3, 1, alpha=0.1, color='green', label='乐观区')

    plt.suptitle('情绪-决策相关性分析（Exp_2，20000周期）',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_emotion_decision_corr.pdf'),
                dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(FIG_DIR, 'fig_emotion_decision_corr.svg'),
                dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("  [图] 情绪-决策相关性图已生成")


def plot_grouped_order_comparison(corr_results):
    """绘制恐慌/中性/乐观状态下的订货量对比"""
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(4); width = 0.25

    panic_means = [corr_results[k]['panic_mean_order'] for k in range(1, 5)]
    neutral_means = [corr_results[k]['neutral_mean_order'] for k in range(1, 5)]
    optimistic_means = [corr_results[k]['optimistic_mean_order'] for k in range(1, 5)]

    panic_stds = [corr_results[k]['panic_std_order'] for k in range(1, 5)]
    neutral_stds = [corr_results[k]['neutral_std_order'] for k in range(1, 5)]
    optimistic_stds = [corr_results[k]['optimistic_std_order'] for k in range(1, 5)]

    bars1 = ax.bar(x - width, panic_means, width, yerr=panic_stds,
                   label='恐慌 (E<-0.3)', color=COLOR_NEG,
                   edgecolor='black', linewidth=0.8, capsize=3)
    bars2 = ax.bar(x, neutral_means, width, yerr=neutral_stds,
                   label='中性 (-0.1≤E≤0.1)', color=COLOR_NEU,
                   edgecolor='black', linewidth=0.8, capsize=3)
    bars3 = ax.bar(x + width, optimistic_means, width, yerr=optimistic_stds,
                   label='乐观 (E>0.3)', color=COLOR_POS,
                   edgecolor='black', linewidth=0.8, capsize=3)

    ax.set_xlabel('供应链节点', fontsize=13)
    ax.set_ylabel('平均订货量', fontsize=13)
    ax.set_title('不同情绪状态下的订货量对比（H1验证）', fontsize=14, fontweight='bold')
    ax.set_xticks(x); ax.set_xticklabels(NODE_NAMES, fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_grouped_order_comparison.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_grouped_order_comparison.svg'), dpi=300)
    plt.close(fig)
    print("  [图] 情绪分组订货量对比图已生成")


# ============================================================
# 2. 情绪传染路径可视化
# ============================================================

def analyze_contagion_paths(ts_data):
    """分析情绪传染路径"""
    print("\n[2] 情绪传染路径分析")

    # 检测情绪同步下降事件（传染信号）
    contagion_events = []
    window = 10  # 检测窗口

    emotions = {}
    for k in range(1, 5):
        emotions[k] = np.array(ts_data['emotion_history'][str(k)][:TOTAL_PERIODS])

    for t in range(window, TOTAL_PERIODS - window):
        # 检测下游节点情绪突然下降
        for k in range(1, 4):  # 零售商→批发商→分销商
            delta_down = emotions[k][t] - emotions[k][t-window]
            if delta_down < -0.2:  # 下游情绪下降>0.2
                # 检查上游是否在随后几个周期也下降
                for t_lag in range(1, 6):  # 1-5周期延迟
                    if t + t_lag < TOTAL_PERIODS:
                        delta_up = emotions[k+1][t+t_lag] - emotions[k+1][t]
                        if delta_up < -0.1:  # 上游也下降
                            contagion_events.append({
                                'cycle': t,
                                'source': NODE_NAMES[k-1],
                                'target': NODE_NAMES[k],
                                'lag': t_lag,
                                'source_delta': float(delta_down),
                                'target_delta': float(delta_up),
                            })
                            break

    # 统计传染路径频率
    path_counts = {}
    for evt in contagion_events:
        path = f"{evt['source']}→{evt['target']}"
        path_counts[path] = path_counts.get(path, 0) + 1

    print(f"  检测到 {len(contagion_events)} 次情绪传染事件")
    for path, count in path_counts.items():
        print(f"    {path}: {count}次")

    return contagion_events, path_counts


def plot_contagion_network(path_counts, contagion_events):
    """绘制情绪传染网络图"""
    if not HAS_NETWORKX:
        print("  [跳过] networkx未安装")
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    G = nx.DiGraph()

    # 添加节点
    for name in NODE_NAMES:
        G.add_node(name)

    # 添加边（权重=传染次数）
    max_count = max(path_counts.values()) if path_counts else 1
    for path, count in path_counts.items():
        parts = path.split('→')
        if len(parts) == 2:
            G.add_edge(parts[0], parts[1], weight=count)

    # 布局
    pos = {}
    for i, name in enumerate(NODE_NAMES):
        pos[name] = (i, 0)

    # 绘制节点
    nx.draw_networkx_nodes(G, pos, node_size=2000, node_color='lightblue',
                           edgecolors='black', linewidths=2, ax=ax)

    # 绘制边（宽度=传染次数）
    edges = G.edges(data=True)
    if edges:
        weights = [max(1, e[2]['weight'] / max_count * 5) for e in edges]
        nx.draw_networkx_edges(G, pos, width=weights, edge_color='red',
                               alpha=0.6, arrows=True, arrowsize=20,
                               connectionstyle='arc3,rad=0.1', ax=ax)

    # 标注传染次数
    edge_labels = {(e[0], e[1]): e[2]['weight'] for e in edges}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels,
                                 font_size=10, font_color='red', ax=ax)

    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold', ax=ax)

    ax.set_title(f'情绪传染网络图（共{len(contagion_events)}次传染事件）',
                 fontsize=14, fontweight='bold')
    ax.axis('off')
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_contagion_network.pdf'), dpi=300)
    fig.savefig(os.path.join(FIG_DIR, 'fig_contagion_network.svg'), dpi=300)
    plt.close(fig)
    print("  [图] 情绪传染网络图已生成")


def plot_contagion_timeseries(ts_data, contagion_events):
    """绘制需求突变事件前后的情绪传染时序图"""
    if not contagion_events:
        print("  [跳过] 无传染事件")
        return

    # 选取前5个传染事件，展示前后50周期的情绪变化
    n_events = min(5, len(contagion_events))
    fig, axes = plt.subplots(n_events, 1, figsize=(14, 3 * n_events), squeeze=False)

    for i in range(n_events):
        ax = axes[i][0]
        evt = contagion_events[i]
        center = evt['cycle']
        window = 50

        start = max(0, center - window)
        end = min(TOTAL_PERIODS, center + window)
        x = range(start, end)

        for k in range(1, 5):
            emos = ts_data['emotion_history'][str(k)][start:end]
            ax.plot(x, emos, label=NODE_NAMES[k-1], color=COLOR_TS[k-1],
                    linewidth=1.5, alpha=0.8)

        ax.axvline(x=center, color='blue', linestyle='--', linewidth=1, alpha=0.7)
        ax.text(center, 0.8, f"传染事件\n{evt['source']}→{evt['target']}",
                fontsize=8, ha='center', color='blue')
        ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
        ax.set_ylabel('情绪状态 E_t', fontsize=11)
        ax.set_title(f'传染事件 #{i+1} (周期{center})', fontsize=11)
        ax.legend(fontsize=9, loc='upper right')
        ax.grid(alpha=0.3, linestyle='--')
        ax.set_ylim(-1.1, 1.1)

    plt.suptitle('情绪传染时序图（需求突变→恐慌蔓延）',
                 fontsize=14, fontweight='bold', y=1.01)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_contagion_timeseries.pdf'),
                dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(FIG_DIR, 'fig_contagion_timeseries.svg'),
                dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("  [图] 情绪传染时序图已生成")


# ============================================================
# 3. 正向激励阻断效应分析
# ============================================================

def analyze_blocking_effect(all_data, ts_data, corr_results):
    """
    分析正向激励的阻断效应

    H2验证: 正向激励是否阻断恐慌→过度订货的恶性循环
    对比: Exp_1(无正向激励) vs Exp_2(有正向激励+情绪+协同)
    """
    print("\n[3] 正向激励阻断效应分析")

    results = {}

    # BWE对比
    for k in range(1, 5):
        bwe_base = all_data['baseline']['bwe'][str(k)]
        bwe_exp1 = all_data['exp1']['bwe'][str(k)]
        bwe_exp2 = all_data['exp2']['bwe'][str(k)]

        results[k] = {
            'node': NODE_NAMES[k-1],
            'bwe_baseline': bwe_base,
            'bwe_exp1': bwe_exp1,
            'bwe_exp2': bwe_exp2,
            'reduction_exp1_vs_base': (bwe_exp1 - bwe_base) / bwe_base * 100,
            'reduction_exp2_vs_base': (bwe_exp2 - bwe_base) / bwe_base * 100,
            'reduction_exp2_vs_exp1': (bwe_exp2 - bwe_exp1) / bwe_exp1 * 100 if bwe_exp1 > 0 else 0,
        }

        print(f"  {NODE_NAMES[k-1]}: Baseline={bwe_base:.2f} → "
              f"Exp_1={bwe_exp1:.2f} → Exp_2={bwe_exp2:.2f}")

    # 情绪极端状态下的订货偏差分析
    # 计算恐慌状态下的过度订货比例
    overorder_panic = {}
    overorder_neutral = {}
    for k in range(1, 5):
        emotions = np.array(ts_data['emotion_history'][str(k)][:TOTAL_PERIODS])
        orders = np.array(ts_data['order_history'][str(k)][:TOTAL_PERIODS])
        demands = np.array(ts_data['demand_history'][:TOTAL_PERIODS])

        panic_mask = emotions < -0.3
        neutral_mask = (emotions >= -0.1) & (emotions <= 0.1)

        if panic_mask.sum() > 0:
            overorder_panic[k] = float(np.mean(orders[panic_mask] > demands[panic_mask]))
        else:
            overorder_panic[k] = 0.0

        if neutral_mask.sum() > 0:
            overorder_neutral[k] = float(np.mean(orders[neutral_mask] > demands[neutral_mask]))
        else:
            overorder_neutral[k] = 0.0

        print(f"    恐慌时过度订货比例={overorder_panic[k]:.2%}, "
              f"中性时={overorder_neutral[k]:.2%}")

    results['overorder_panic'] = overorder_panic
    results['overorder_neutral'] = overorder_neutral
    results['blocking_effect'] = {
        k: overorder_neutral[k] - overorder_panic[k] for k in range(1, 5)
    }

    return results


def plot_blocking_effect(blocking_results):
    """绘制正向激励阻断效应图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 左图: BWE三组对比趋势
    ax1 = axes[0]
    for k in range(1, 5):
        bwe_vals = [
            blocking_results[k]['bwe_baseline'],
            blocking_results[k]['bwe_exp1'],
            blocking_results[k]['bwe_exp2'],
        ]
        ax1.plot(['Baseline', 'Exp_1', 'Exp_2'], bwe_vals,
                 'o-', label=NODE_NAMES[k-1], color=COLOR_TS[k-1],
                 linewidth=2, markersize=8)
    ax1.set_ylabel('方差比 BWE', fontsize=13)
    ax1.set_title('BWE变化趋势（三组对比）', fontsize=13, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.set_yscale('log')
    ax1.grid(alpha=0.3, linestyle='--')

    # 右图: 恐慌vs中性过度订货比例
    ax2 = axes[1]
    x = np.arange(4); width = 0.35
    panic_vals = [blocking_results['overorder_panic'][k] * 100 for k in range(1, 5)]
    neutral_vals = [blocking_results['overorder_neutral'][k] * 100 for k in range(1, 5)]

    bars1 = ax2.bar(x - width/2, panic_vals, width, label='恐慌状态',
                    color=COLOR_NEG, edgecolor='black', linewidth=0.8)
    bars2 = ax2.bar(x + width/2, neutral_vals, width, label='中性状态',
                    color=COLOR_NEU, edgecolor='black', linewidth=0.8)

    for bars in [bars1, bars2]:
        for bar in bars:
            h = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2, h + 1,
                     f'{h:.1f}%', ha='center', va='bottom', fontsize=9)

    ax2.set_xlabel('供应链节点', fontsize=13)
    ax2.set_ylabel('过度订货比例 (%)', fontsize=13)
    ax2.set_title('恐慌vs中性状态过度订货对比', fontsize=13, fontweight='bold')
    ax2.set_xticks(x); ax2.set_xticklabels(NODE_NAMES, fontsize=12)
    ax2.legend(fontsize=10)
    ax2.grid(axis='y', alpha=0.3, linestyle='--')

    plt.suptitle('正向激励阻断效应分析（H2验证）',
                 fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, 'fig_blocking_effect.pdf'),
                dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(FIG_DIR, 'fig_blocking_effect.svg'),
                dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("  [图] 正向激励阻断效应图已生成")


# ============================================================
# 主程序
# ============================================================

def main():
    print("=" * 70)
    print("归因分析（20000周期）")
    print("=" * 70)

    # 检查数据文件
    if not os.path.exists(EXP2_TS_JSON):
        print(f"[错误] Exp_2时序数据不存在: {EXP2_TS_JSON}")
        print("请先运行 run_exp2_20k.py")
        return

    # 加载数据
    print("\n[0] 加载数据...")
    with open(EXP2_TS_JSON, 'r', encoding='utf-8') as f:
        ts_data = json.load(f)
    with open(COMPARE_JSON, 'r', encoding='utf-8') as f:
        all_data = json.load(f)

    print(f"  Exp_2时序数据: {len(ts_data['emotion_history']['1'])} 周期")

    # 1. 情绪-决策相关性分析
    corr_results = analyze_emotion_decision_correlation(ts_data)
    plot_emotion_decision_correlation(ts_data, corr_results)
    plot_grouped_order_comparison(corr_results)

    # 2. 情绪传染路径可视化
    contagion_events, path_counts = analyze_contagion_paths(ts_data)
    plot_contagion_network(path_counts, contagion_events)
    plot_contagion_timeseries(ts_data, contagion_events)

    # 3. 正向激励阻断效应分析
    blocking_results = analyze_blocking_effect(all_data, ts_data, corr_results)
    plot_blocking_effect(blocking_results)

    # 保存结果
    analysis_result = {
        'emotion_decision_correlation': {str(k): v for k, v in corr_results.items()},
        'contagion_analysis': {
            'total_events': len(contagion_events),
            'path_counts': path_counts,
        },
        'blocking_effect': {str(k): v for k, v in blocking_results.items()
                           if isinstance(v, dict) and 'node' in v},
        'overorder_analysis': {
            'panic': blocking_results.get('overorder_panic', {}),
            'neutral': blocking_results.get('overorder_neutral', {}),
        },
    }

    with open(RESULT_JSON, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*70}")
    print(f"归因分析完成！")
    print(f"  结果保存: {RESULT_JSON}")
    print(f"  图表保存: {FIG_DIR}/")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()

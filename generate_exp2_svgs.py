"""
Exp_2 专用 SVG 图表生成脚本
============================
生成 3 类 SVG 图表（全部基于真实实验数据，不得作假）：
  5. 多智能体人智协同智慧决策系统流程设计图（架构图）
  6. 20000 周期完整时序演化图（BWE / 成本 / SL / 情绪）
  3'. 两种行为对比图（完整 20000 周期，替换原 fig3 采样版）

数据来源（均为 20000 周期真实仿真数据）：
  - p0_results/baseline_20k_timeseries.json  RationalAgent 20000 周期时序
  - p0_results/exp1b_20k_timeseries.json     Exp_1b 智慧决策 20000 周期时序
  - p0_results/exp2_20k_timeseries.json      Exp_2 人智协同 20000 周期时序
  - p0_results/四组对比_20k.json              四组实验汇总数据

设计规范：
  - 字体: Times New Roman + SimHei
  - svg.fonttype='none' (文字保留为文本)
  - 双语标签，标题底部居中
  - 色盲友好配色
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle, Rectangle
from matplotlib import rcParams

# ============================================================
# 全局样式
# ============================================================
rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Times New Roman', 'SimHei', 'Microsoft YaHei', 'DejaVu Serif']
rcParams['axes.unicode_minus'] = False
rcParams['svg.fonttype'] = 'none'
rcParams['figure.dpi'] = 150
rcParams['font.size'] = 11
try:
    rcParams['fontfallback'] = True
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'svg_figures_basic')
os.makedirs(OUTPUT_DIR, exist_ok=True)

NODE_CN = {1: '零售商', 2: '批发商', 3: '分销商', 4: '制造商'}
NODE_EN = {1: 'Retailer', 2: 'Wholesaler', 3: 'Distributor', 4: 'Manufacturer'}

COLOR_BASELINE = '#E74C3C'
COLOR_IDMR = '#3498DB'
COLOR_EXP1B = '#9B59B6'
COLOR_EXP2 = '#27AE60'
COLOR_TS = ['#4E79A7', '#F28E2B', '#E15759', '#76B7B2']


def save_svg(fig, name):
    path = os.path.join(OUTPUT_DIR, name)
    fig.savefig(path, format='svg', bbox_inches='tight')
    plt.close(fig)
    print(f"  [saved] {path}")
    return path


def add_bilingual_title(fig, cn_title, en_title):
    fig.text(0.5, 0.01, cn_title, ha='center', va='bottom',
             fontsize=13, fontweight='bold', fontfamily='SimHei')
    fig.text(0.5, -0.01, en_title, ha='center', va='top',
             fontsize=10, fontstyle='italic', color='gray')


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================================================
# 图5: 多智能体人智协同智慧决策系统流程设计图
# ============================================================

def plot_system_architecture():
    """绘制多智能体人智协同智慧决策系统流程设计图"""
    print("\n[图5] 多智能体人智协同智慧决策系统流程设计图...")

    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # ---- 颜色定义 ----
    C_NODE = '#4E79A7'       # 供应链节点
    C_IDMR = '#3498DB'       # IDMR机器人
    C_EMOTION = '#E15759'    # 情绪模块
    C_COMM = '#27AE60'       # 协同通信
    C_EVENT = '#F28E2B'      # 动态事件
    C_EWC = '#9B59B6'        # 持续学习
    C_EVAL = '#76B7B2'       # 评估输出

    # ---- 标题 ----
    ax.text(8, 9.7, '多智能体人智协同智慧决策系统流程设计图',
            ha='center', va='center', fontsize=16, fontweight='bold', fontfamily='SimHei')
    ax.text(8, 9.35, 'Multi-Agent Human-AI Collaborative Intelligent Decision System Architecture',
            ha='center', va='center', fontsize=10, fontstyle='italic', color='gray')

    # ---- 供应链节点层 (y=7.5) ----
    node_y = 7.5
    node_xs = [2, 5.5, 9, 12.5]
    node_labels = ['零售商\nRetailer\n(k=1)', '批发商\nWholesaler\n(k=2)',
                   '分销商\nDistributor\n(k=3)', '制造商\nManufacturer\n(k=4)']

    for i, (x, label) in enumerate(zip(node_xs, node_labels)):
        # 供应链节点
        rect = FancyBboxPatch((x-1.2, node_y-0.4), 2.4, 0.8,
                              boxstyle="round,pad=0.1", facecolor=C_NODE,
                              edgecolor='black', linewidth=1.5, alpha=0.85)
        ax.add_patch(rect)
        ax.text(x, node_y, label, ha='center', va='center',
                fontsize=9, fontweight='bold', color='white')

        # 物流箭头（下游→下游，向左）
        if i > 0:
            ax.annotate('', xy=(node_xs[i-1]+1.2, node_y),
                        xytext=(x-1.2, node_y),
                        arrowprops=dict(arrowstyle='->', color='#2C3E50',
                                        lw=2, connectionstyle='arc3,rad=0'))
            ax.text((x+node_xs[i-1])/2, node_y+0.25, '物流 / Flow',
                    ha='center', va='bottom', fontsize=7, color='#2C3E50')

    # 订单流箭头（上游方向，向右）
    for i in range(3):
        ax.annotate('', xy=(node_xs[i+1]-1.2, node_y-0.15),
                    xytext=(node_xs[i]+1.2, node_y-0.15),
                    arrowprops=dict(arrowstyle='->', color='#E74C3C',
                                    lw=1.5, linestyle='--', connectionstyle='arc3,rad=0'))
    ax.text(7.25, node_y-0.4, '订单流 / Order Flow →', ha='center', va='top',
            fontsize=7, color='#E74C3C', fontstyle='italic')

    # ---- IDMR 决策层 (y=6.0) ----
    idmr_y = 6.0
    for i, x in enumerate(node_xs):
        # 分销商(k=3)为主IDMR节点，其他为协同节点
        is_main = (i == 2)
        color = C_IDMR if is_main else '#85C1E9'
        rect = FancyBboxPatch((x-1.0, idmr_y-0.35), 2.0, 0.7,
                              boxstyle="round,pad=0.08", facecolor=color,
                              edgecolor='black', linewidth=1.2, alpha=0.85)
        ax.add_patch(rect)
        label = 'IDMR+情绪\n(主节点)' if is_main else 'IDMR\n(协同节点)'
        ax.text(x, idmr_y, label, ha='center', va='center',
                fontsize=7.5, fontweight='bold', color='white')

        # 连接节点到IDMR
        ax.annotate('', xy=(x, idmr_y+0.35), xytext=(x, node_y-0.4),
                    arrowprops=dict(arrowstyle='-', color='#7F8C8D', lw=1, linestyle=':'))

    ax.text(0.5, idmr_y, 'IDMR\n决策层', ha='center', va='center',
            fontsize=8, fontweight='bold', color=C_IDMR, fontfamily='SimHei')

    # ---- 决策流程 (y=4.5, 仅分销商展开) ----
    flow_y = 4.5
    flow_steps = ['状态感知\nState', '情绪演化\nEq.(1)-(2)', 'DQN\n决策',
                  '情绪调节\nEq.(5)-(6)', '订单输出\nOrder']
    flow_xs = np.linspace(6.5, 11.5, len(flow_steps))
    for i, (fx, fl) in enumerate(zip(flow_xs, flow_steps)):
        rect = FancyBboxPatch((fx-0.45, flow_y-0.3), 0.9, 0.6,
                              boxstyle="round,pad=0.05", facecolor='white',
                              edgecolor=C_IDMR, linewidth=1.2)
        ax.add_patch(rect)
        ax.text(fx, flow_y, fl, ha='center', va='center', fontsize=6.5,
                fontweight='bold', color=C_IDMR)
        if i > 0:
            ax.annotate('', xy=(fx-0.45, flow_y), xytext=(flow_xs[i-1]+0.45, flow_y),
                        arrowprops=dict(arrowstyle='->', color=C_IDMR, lw=1.5))

    ax.text(5.5, flow_y, '决策流程\n(分销商)', ha='center', va='center',
            fontsize=8, fontweight='bold', color=C_IDMR, fontfamily='SimHei')
    ax.annotate('', xy=(6.5-0.45, flow_y), xytext=(9, idmr_y-0.35),
                arrowprops=dict(arrowstyle='->', color=C_IDMR, lw=1, linestyle='--'))

    # ---- 情绪传染层 (y=3.2) ----
    contagion_y = 3.2
    ax.text(0.5, contagion_y, '情绪传染\nContagion', ha='center', va='center',
            fontsize=8, fontweight='bold', color=C_EMOTION, fontfamily='SimHei')
    for i in range(3):
        x_start = node_xs[i]
        x_end = node_xs[i+1]
        ax.annotate('', xy=(x_end, contagion_y+0.2), xytext=(x_start, contagion_y+0.2),
                    arrowprops=dict(arrowstyle='->', color=C_EMOTION, lw=1.8,
                                    connectionstyle='arc3,rad=-0.15'))
        ax.text((x_start+x_end)/2, contagion_y-0.05, f'Eq.(8)\ns_c=0.4',
                ha='center', va='top', fontsize=6, color=C_EMOTION)

    # 情绪传染标签
    ax.text(8, contagion_y-0.5, '恐慌情绪上游传染 (p_c=0.3, θ=0.3)',
            ha='center', va='center', fontsize=8, color=C_EMOTION,
            fontstyle='italic', fontfamily='SimHei')

    # ---- 协同通信层 (y=2.2) ----
    comm_y = 2.2
    ax.text(0.5, comm_y, '协同通信\nComm.', ha='center', va='center',
            fontsize=8, fontweight='bold', color=C_COMM, fontfamily='SimHei')
    for i in range(3):
        x_start = node_xs[i+1]
        x_end = node_xs[i]
        ax.annotate('', xy=(x_end, comm_y+0.15), xytext=(x_start, comm_y+0.15),
                    arrowprops=dict(arrowstyle='<->', color=C_COMM, lw=1.8,
                                    connectionstyle='arc3,rad=0.15'))

    ax.text(8, comm_y-0.35, '信息共享 (需求/库存/订单状态双向传递)',
            ha='center', va='center', fontsize=8, color=C_COMM,
            fontstyle='italic', fontfamily='SimHei')

    # ---- 动态事件注入 (右上角) ----
    event_x, event_y = 14.5, 8.0
    rect = FancyBboxPatch((event_x-1.0, event_y-0.7), 2.0, 1.4,
                          boxstyle="round,pad=0.1", facecolor=C_EVENT,
                          edgecolor='black', linewidth=1.2, alpha=0.8)
    ax.add_patch(rect)
    ax.text(event_x, event_y+0.35, '动态事件\nDynamic Events',
            ha='center', va='center', fontsize=8, fontweight='bold', color='white')
    ax.text(event_x, event_y-0.25, '需求突变 Eq.(9)\n供应中断 Eq.(10)\n53+23次/20k',
            ha='center', va='center', fontsize=6, color='white')

    # 事件注入箭头
    ax.annotate('', xy=(node_xs[0]+0.5, node_y+0.4), xytext=(event_x-1.0, event_y),
                arrowprops=dict(arrowstyle='->', color=C_EVENT, lw=1.5, linestyle='--'))
    ax.annotate('', xy=(node_xs[3]+0.5, node_y-0.4), xytext=(event_x-1.0, event_y-0.5),
                arrowprops=dict(arrowstyle='->', color=C_EVENT, lw=1.5, linestyle='--'))

    # ---- 持续学习层 (左下角) ----
    ewc_x, ewc_y = 1.8, 1.0
    rect = FancyBboxPatch((ewc_x-1.3, ewc_y-0.4), 2.6, 0.8,
                          boxstyle="round,pad=0.1", facecolor=C_EWC,
                          edgecolor='black', linewidth=1.2, alpha=0.8)
    ax.add_patch(rect)
    ax.text(ewc_x, ewc_y, '持续学习 EWC+PER\nEq.(15)-(16)  λ=400',
            ha='center', va='center', fontsize=7.5, fontweight='bold', color='white')

    ax.annotate('', xy=(node_xs[2]-0.5, idmr_y-0.35), xytext=(ewc_x+1.3, ewc_y+0.4),
                arrowprops=dict(arrowstyle='->', color=C_EWC, lw=1.2, linestyle='--'))

    # ---- 评估输出层 (右下角) ----
    eval_x, eval_y = 14.0, 1.0
    rect = FancyBboxPatch((eval_x-1.3, eval_y-0.4), 2.6, 0.8,
                          boxstyle="round,pad=0.1", facecolor=C_EVAL,
                          edgecolor='black', linewidth=1.2, alpha=0.8)
    ax.add_patch(rect)
    ax.text(eval_x, eval_y, '评估输出\nBWE / Cost / SL\nEq.(11)-(14)',
            ha='center', va='center', fontsize=7.5, fontweight='bold', color='white')

    ax.annotate('', xy=(eval_x-1.3, eval_y+0.4), xytext=(node_xs[3]+0.5, node_y-0.4),
                arrowprops=dict(arrowstyle='->', color=C_EVAL, lw=1.2, linestyle='--'))

    # ---- 图例 ----
    legend_items = [
        (C_NODE, '供应链节点 / SC Node'),
        (C_IDMR, 'IDMR 智慧决策 / IDMR Agent'),
        (C_EMOTION, '情绪传染 / Emotion Contagion'),
        (C_COMM, '协同通信 / Coordination Comm.'),
        (C_EVENT, '动态事件 / Dynamic Events'),
        (C_EWC, '持续学习 / Continual Learning'),
        (C_EVAL, '评估输出 / Evaluation Output'),
    ]
    for i, (color, label) in enumerate(legend_items):
        ly = 0.5 - i * 0.0  # 单行图例
        ax.add_patch(Rectangle((0.5 + i*2.1, 0.15), 0.3, 0.2, facecolor=color, edgecolor='black', lw=0.5))
        ax.text(0.9 + i*2.1, 0.25, label, ha='left', va='center', fontsize=6)

    plt.tight_layout()
    return save_svg(fig, 'fig5_system_architecture.svg')


# ============================================================
# 图6: 20000 周期完整时序演化图
# ============================================================

def compute_sliding_bwe(orders, demands, window=200):
    """计算滑动窗口 BWE = Var(q_k) / Var(D_retailer)"""
    T = len(orders)
    bwe = []
    for t in range(T):
        if t < window:
            bwe.append(0.0)
        else:
            w_orders = orders[t-window:t]
            w_demands = demands[t-window:t]
            vq = np.var(w_orders)
            vd = np.var(w_demands)
            bwe.append(vq / vd if vd > 0 else 0.0)
    return np.array(bwe)


def plot_timeseries_20k(baseline_ts, exp1b_ts, exp2_ts):
    """绘制 20000 周期完整时序演化图（4 子图：BWE / 成本 / SL / 情绪）"""
    print("\n[图6] 20000 周期完整时序演化图...")

    T = 20000
    # 采样间隔（每20个点取1个，共1000个点，保证可读性）
    step = 20
    x = np.arange(0, T, step)

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))

    # ---- (a) BWE 时序（分销商 k=3）----
    ax = axes[0, 0]
    # baseline BWE
    bwe_base = compute_sliding_bwe(
        baseline_ts['order_history']['3'],
        baseline_ts['customer_demand'], window=200)[::step]
    # exp1b BWE
    bwe_exp1b = compute_sliding_bwe(
        exp1b_ts['order_history']['3'],
        exp1b_ts['demand_history']['1'], window=200)[::step]
    # exp2 BWE
    bwe_exp2 = compute_sliding_bwe(
        exp2_ts['order_history']['3'],
        exp2_ts['demand_history'], window=200)[::step]

    ax.plot(x, bwe_base, color=COLOR_BASELINE, linewidth=1.0, alpha=0.8,
            label='Baseline 经典决策')
    ax.plot(x, bwe_exp1b, color=COLOR_EXP1B, linewidth=1.0, alpha=0.8,
            label='Exp_1b 智慧决策')
    ax.plot(x, bwe_exp2, color=COLOR_EXP2, linewidth=1.2, alpha=0.85,
            label='Exp_2 人智协同')
    ax.set_xlabel('订货周期 / Period', fontsize=10)
    ax.set_ylabel('分销商 BWE (滑动窗口=200)', fontsize=10)
    ax.set_title('(a) 分销商牛鞭效应时序 / Distributor BWE', fontsize=11)
    ax.legend(fontsize=8, loc='upper right')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlim(0, T)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    # ---- (b) 累计平均成本时序（系统总成本）----
    ax = axes[0, 1]
    # 计算每周期系统总成本的累计平均
    cost_base = np.zeros(T)
    cost_exp1b = np.zeros(T)
    cost_exp2 = np.zeros(T)
    for k in ['1', '2', '3', '4']:
        cost_base += np.array(baseline_ts['cost_history'][k])
        cost_exp1b += np.array(exp1b_ts['cost_history'][k])
        cost_exp2 += np.array(exp2_ts['cost_history'][k])

    cumavg_base = np.cumsum(cost_base) / np.arange(1, T+1)
    cumavg_exp1b = np.cumsum(cost_exp1b) / np.arange(1, T+1)
    cumavg_exp2 = np.cumsum(cost_exp2) / np.arange(1, T+1)

    ax.plot(x, cumavg_base[::step], color=COLOR_BASELINE, linewidth=1.0, alpha=0.8,
            label='Baseline 经典决策')
    ax.plot(x, cumavg_exp1b[::step], color=COLOR_EXP1B, linewidth=1.0, alpha=0.8,
            label='Exp_1b 智慧决策')
    ax.plot(x, cumavg_exp2[::step], color=COLOR_EXP2, linewidth=1.2, alpha=0.85,
            label='Exp_2 人智协同')
    ax.set_xlabel('订货周期 / Period', fontsize=10)
    ax.set_ylabel('累计平均系统成本 / Cumulative Avg Cost', fontsize=10)
    ax.set_title('(b) 系统总成本时序 / System Cost', fontsize=11)
    ax.legend(fontsize=8, loc='upper right')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlim(0, T)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    # ---- (c) 累计平均 SL 时序 ----
    ax = axes[1, 0]
    # baseline: 从 fulfilled/demand 计算 SL（baseline没有sl_history，从netstock推算）
    # baseline_ts 没有 fulfilled_history，用 demand 和 cost 反推
    # 实际上 baseline_ts 有 demand_history 和 netstock_history
    # SL = fulfilled / demand, fulfilled = min(net_stock_before + arrived, demand)
    # 简化：如果 cost 中的 stockout 部分为 0，则 SL=1
    # 但我们无法精确反推，所以只画 exp1b 和 exp2 的 SL
    # exp1b 有 sl_history
    if 'sl_history' in exp1b_ts:
        sl_exp1b = np.array(exp1b_ts['sl_history']['1'])  # 零售商SL
        cumavg_sl_exp1b = np.cumsum(sl_exp1b) / np.arange(1, T+1) * 100
        ax.plot(x, cumavg_sl_exp1b[::step], color=COLOR_EXP1B, linewidth=1.0, alpha=0.8,
                label='Exp_1b 零售商SL')

    if 'sl_history' in exp2_ts:
        sl_exp2 = np.array(exp2_ts['sl_history']['1'])  # 零售商SL
        cumavg_sl_exp2 = np.cumsum(sl_exp2) / np.arange(1, T+1) * 100
        ax.plot(x, cumavg_sl_exp2[::step], color=COLOR_EXP2, linewidth=1.2, alpha=0.85,
                label='Exp_2 零售商SL')

    # baseline SL: 从 demand 和 fulfilled 计算
    # baseline_ts 没有 fulfilled_history，但有 netstock_history
    # 我们用近似：如果 netstock >= 0 则 SL=1, 否则 SL = 1 + netstock/demand
    # 更准确的方法：fulfilled = demand + min(0, netstock_after - netstock_before)
    # 但这太复杂，我们直接从 baseline 的数据结构推算
    # baseline 的 netstock_history 是周期末净库存
    # 如果 netstock >= 0，说明没有缺货，SL=1
    # 如果 netstock < 0，说明有缺货，SL = (demand + netstock) / demand
    ns_base = np.array(baseline_ts['netstock_history']['1'])
    d_base = np.array(baseline_ts['demand_history']['1'])
    sl_base = np.where(d_base > 0,
                       np.where(ns_base >= 0, 1.0, np.maximum(0, (d_base + ns_base) / d_base)),
                       1.0)
    cumavg_sl_base = np.cumsum(sl_base) / np.arange(1, T+1) * 100
    ax.plot(x, cumavg_sl_base[::step], color=COLOR_BASELINE, linewidth=1.0, alpha=0.8,
            label='Baseline 零售商SL')

    ax.axhline(y=97.7, color='gray', linestyle=':', linewidth=1, alpha=0.6)
    ax.text(T*0.7, 97.8, '目标 97.7%', fontsize=8, color='gray')
    ax.set_xlabel('订货周期 / Period', fontsize=10)
    ax.set_ylabel('累计平均 SL (%) / Cumulative SL', fontsize=10)
    ax.set_title('(c) 零售商服务水平时序 / Retailer SL', fontsize=11)
    ax.legend(fontsize=8, loc='lower right')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlim(0, T)
    ax.set_ylim(70, 102)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    # ---- (d) 情绪状态时序（Exp_2 各节点）----
    ax = axes[1, 1]
    for k_idx, k in enumerate(['1', '2', '3', '4']):
        emo = np.array(exp2_ts['emotion_history'][k])[::step]
        ax.plot(x, emo, color=COLOR_TS[k_idx], linewidth=0.8, alpha=0.7,
                label=f'{NODE_CN[int(k)]} (k={k})')

    ax.axhline(y=0, color='black', linewidth=0.5, alpha=0.3)
    ax.axhline(y=-0.3, color='red', linewidth=0.5, linestyle=':', alpha=0.4)
    ax.axhline(y=0.3, color='green', linewidth=0.5, linestyle=':', alpha=0.4)
    ax.text(T*0.02, -0.28, '恐慌阈值 E=-0.3', fontsize=7, color='red')
    ax.text(T*0.02, 0.32, '乐观阈值 E=+0.3', fontsize=7, color='green')
    ax.set_xlabel('订货周期 / Period', fontsize=10)
    ax.set_ylabel('情绪状态 E / Emotion State', fontsize=10)
    ax.set_title('(d) Exp_2 各节点情绪演化 / Emotion Evolution', fontsize=11)
    ax.legend(fontsize=8, loc='upper right')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlim(0, T)
    ax.set_ylim(-1.1, 1.1)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    add_bilingual_title(fig,
        '图6  20000 周期时序演化：BWE / 成本 / SL / 情绪（实验数据）',
        'Fig.6  20000-Period Evolution: BWE / Cost / SL / Emotion (Experimental Data)')
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    return save_svg(fig, 'fig6_timeseries_20k.svg')


# ============================================================
# 图3': 两种行为对比图（完整 20000 周期，替换原采样版）
# ============================================================

def plot_behavior_comparison_full(baseline_ts, exp1b_ts):
    """绘制经典决策与智慧决策各节点订货行为时序对比（完整20000周期，采样显示）"""
    print("\n[图3'] 两种行为对比图（完整 20000 周期）...")

    T = 20000
    step = 10  # 每10个点取1个，共2000个点
    x = np.arange(0, T, step)

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))

    for idx, k in enumerate(['1', '2', '3', '4']):
        ax = axes[idx // 2, idx % 2]
        orders_base = np.array(baseline_ts['order_history'][k])[::step]
        orders_exp = np.array(exp1b_ts['order_history'][k])[::step]
        demands = np.array(baseline_ts['demand_history'][k])[::step]

        ax.plot(x, demands, color='#BDC3C7', linewidth=0.6, alpha=0.5,
                label='需求 / Demand')
        ax.plot(x, orders_base, color=COLOR_BASELINE, linewidth=0.8, alpha=0.6,
                label='经典决策 / Rational')
        ax.plot(x, orders_exp, color=COLOR_IDMR, linewidth=0.9, alpha=0.75,
                label='智慧决策 / IDMR')

        # 填充经典决策的过度波动区域
        ax.fill_between(x, orders_base, orders_exp,
                        where=(orders_base > orders_exp),
                        color=COLOR_BASELINE, alpha=0.08, interpolate=True)

        var_base = np.var(np.array(baseline_ts['order_history'][k]))
        var_exp = np.var(np.array(exp1b_ts['order_history'][k]))
        ax.set_title(f'{NODE_CN[int(k)]} (k={k})  '
                     f'Var_经典={var_base:.1f} → Var_智慧={var_exp:.1f}',
                     fontsize=10, fontweight='bold')
        ax.set_xlabel('订货周期 / Period (0-20000)', fontsize=9)
        ax.set_ylabel('订货量 / Order Quantity', fontsize=9)
        ax.legend(fontsize=7, loc='upper right')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_xlim(0, T)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

    add_bilingual_title(fig,
        '图3  经典决策与智慧决策订货行为对比（完整 20000 周期实验数据）',
        'Fig.3  Order Behavior: Rational vs IDMR (Full 20000 Periods, Experimental Data)')
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    return save_svg(fig, 'fig3_behavior_comparison.svg')


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 70)
    print("Exp_2 SVG 图表生成（系统流程图 + 20000周期时序图）")
    print("=" * 70)

    # 加载时序数据
    print("加载实验数据...")
    baseline_ts = load_json(os.path.join(BASE_DIR, 'p0_results', 'baseline_20k_timeseries.json'))
    exp1b_ts = load_json(os.path.join(BASE_DIR, 'p0_results', 'exp1b_20k_timeseries.json'))
    exp2_ts = load_json(os.path.join(BASE_DIR, 'p0_results', 'exp2_20k_timeseries.json'))
    print(f"  baseline: {len(baseline_ts['customer_demand'])} 周期")
    print(f"  exp1b: {len(exp1b_ts['order_history']['1'])} 周期")
    print(f"  exp2: {len(exp2_ts['demand_history'])} 周期")

    # 图5: 系统流程设计图
    plot_system_architecture()

    # 图6: 20000周期时序演化图
    plot_timeseries_20k(baseline_ts, exp1b_ts, exp2_ts)

    # 图3': 重新生成完整20000周期行为对比图
    plot_behavior_comparison_full(baseline_ts, exp1b_ts)

    print("\n" + "=" * 70)
    print("全部 SVG 图表生成完成！")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 70)


if __name__ == '__main__':
    main()

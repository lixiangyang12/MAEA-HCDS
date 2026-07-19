"""
论文配图生成器（719版）
======================
符合SCI顶刊标准的论文配图：
  - A4竖版 (8.27 x 11.69 inches)
  - SCI顶刊配色 (Nature/Science柔和低饱和)
  - 双语坐标轴 (中文主 + English副)
  - 图标题底部居中
  - 矢量输出 (PDF + SVG + PNG)
  - Microsoft YaHei + Arial字体

生成3张论文配图：
  Fig.1 MAEA-HCDS系统机制图 (四层架构+递进因果链)
  Fig.2 多智能体人智协同供应链决策设计流程图 (四级供应链+四组实验)
  Fig.8 情绪传染网络图 (2830次事件+逐级衰减)
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle, Circle, Wedge, ConnectionPatch
from matplotlib.lines import Line2D
import matplotlib.gridspec as gridspec

# ============================================================
# 全局样式: SCI顶刊标准
# ============================================================
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['font.size'] = 9
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['axes.titlesize'] = 10
plt.rcParams['xtick.labelsize'] = 8.5
plt.rcParams['ytick.labelsize'] = 8.5
plt.rcParams['legend.fontsize'] = 8
plt.rcParams['legend.frameon'] = False
plt.rcParams['svg.fonttype'] = 'none'
plt.rcParams['pdf.fonttype'] = 42

# A4竖版尺寸 (inches)
A4_W = 8.27
A4_H = 11.69

# SCI顶刊配色 (4层信号色 + 辅助色)
LAYER_COLORS = {
    'perception':   '#4C72B0',  # 柔和蓝 - 行为感知
    'decision':     '#DD8452',  # 柔和橙 - 智能决策
    'coordination': '#55A868',  # 柔和绿 - 多体协同
    'adaptation':   '#8172B3',  # 柔和紫 - 持续适应
}

NODE_COLORS = {
    'retailer':    '#C44E52',  # 零售商 - 红
    'wholesaler':  '#DD8452',  # 批发商 - 橙
    'distributor': '#55A868',  # 分销商 - 绿
    'manufacturer':'#4C72B0',  # 制造商 - 蓝
}

EXP_COLORS = {
    'baseline': '#5B5B5B',  # 灰
    'exp1':     '#4C72B0',  # 蓝
    'exp1b':    '#DD8452',  # 橙
    'exp2':     '#55A868',  # 绿
}

# 输出目录
FIG_DIR = 'svg_figures_paper_719'
os.makedirs(FIG_DIR, exist_ok=True)


def save_figure(fig, name, caption_zh, caption_en):
    """添加底部居中标题并保存为PDF+SVG+PNG"""
    fig.text(0.5, 0.02, f'{caption_zh}\n{caption_en}',
             ha='center', va='bottom', fontsize=9.5,
             fontweight='normal', wrap=True)
    pdf_path = os.path.join(FIG_DIR, f'{name}.pdf')
    svg_path = os.path.join(FIG_DIR, f'{name}.svg')
    png_path = os.path.join(FIG_DIR, f'{name}.png')
    fig.savefig(pdf_path, dpi=300, bbox_inches='tight')
    fig.savefig(svg_path, dpi=300, bbox_inches='tight')
    fig.savefig(png_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'  [Saved] {name}.pdf / .svg / .png')


# ============================================================
# Fig.1 MAEA-HCDS系统机制图 (四层架构+递进因果链)
# ============================================================
def plot_fig1_system_mechanism():
    """MAEA-HCDS系统机制图：四层架构+递进因果链"""
    fig = plt.figure(figsize=(A4_W, A4_H))
    ax = fig.add_axes([0.02, 0.04, 0.96, 0.92])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 标题
    ax.text(50, 97, '多智能体情绪感知人智协同决策系统 (MAEA-HCDS)',
            ha='center', va='top', fontsize=13, fontweight='bold')
    ax.text(50, 93.5, 'Multi-Agent Emotion-Aware Human-AI Collaborative Decision System',
            ha='center', va='top', fontsize=9.5, style='italic', color='#444444')

    # 四层定义
    layers = [
        {
            'key': 'perception', 'color': LAYER_COLORS['perception'],
            'layer_num': 'Layer 1', 'title_zh': '行为感知层', 'title_en': 'Behavior Perception Layer',
            'role': '诊断 · 何时需干预',
            'theories': ['Schweitzer & Cachon [18] 行为运营管理', 'Gino & Pisano [19] 行为运营',
                         'Picard [20] 情感计算', 'Poria等 [21] 多模态情感融合',
                         'Kahneman & Tversky [22] 前景理论', 'Ortony等 [26] OCC情绪评价'],
            'mechanisms': ['tanh饱和动力学情绪演化方程 E_t = tanh(α·E_{t-1}+γ·Φ_t)',
                           'α=0.7, γ=2.0；Φ_t = w_s·缺货率 + w_m·精准匹配度 + w_e·过度积压率',
                           '损失厌恶系数 (1.5, 2.5) 使有效缺货惩罚放大约70%'],
            'output': '输出：情绪状态 E_t ∈ [-1, 1]（-1恐慌饱和 / +1乐观饱和）',
            'y_top': 88, 'y_bot': 70,
        },
        {
            'key': 'decision', 'color': LAYER_COLORS['decision'],
            'layer_num': 'Layer 2', 'title_zh': '智能决策层', 'title_en': 'Intelligent Decision Layer',
            'role': '治疗 · 如何个体干预',
            'theories': ['Mnih等 [12] 深度Q网络 (DQN)', 'Schaul等 [27] 优先经验回放 (PER)',
                         '李勇等 [10] IDMR智慧决策机器人'],
            'mechanisms': ['DQN基础学习器 + ε-greedy动作选择',
                           '库存精准匹配正向激励函数：将"最小化缺货"重塑为"最大化精准匹配"',
                           '奖励 r = w_s·r_shortage + w_m·r_match + w_e·r_overstock + w_e·r_emotion',
                           'PER按TD误差优先采样，提升样本效率'],
            'output': '输出：订货决策 a_t，目标重塑阻断"缺货→恐慌→过度订货"恶性循环',
            'y_top': 67, 'y_bot': 49,
        },
        {
            'key': 'coordination', 'color': LAYER_COLORS['coordination'],
            'layer_num': 'Layer 3', 'title_zh': '多体协同层', 'title_en': 'Multi-Agent Coordination Layer',
            'role': '免疫 · 如何系统强化',
            'theories': ['Foerster等 [13] CTDE范式 (集中训练分散执行)',
                         'Rashid等 [14] QMIX值分解', 'Lee等 [1-2] 牛鞭效应理论'],
            'mechanisms': ['信息共享通道：下游节点→上游节点传递订单流+情绪状态',
                           'CTDE：集中训练时共享全局信息，分散执行时各节点独立决策',
                           'QMIX单调性约束：保证联合动作值函数的可分解性',
                           '从"反应式"到"预应式"决策转变'],
            'output': '输出：协同订货策略，上游节点提前感知下游需求突变',
            'y_top': 46, 'y_bot': 28,
        },
        {
            'key': 'adaptation', 'color': LAYER_COLORS['adaptation'],
            'layer_num': 'Layer 4', 'title_zh': '持续适应层', 'title_en': 'Continual Adaptation Layer',
            'role': '鲁棒 · 如何长期稳健',
            'theories': ['Kirkpatrick等 [17] 弹性权重巩固 (EWC)',
                         'Schaul等 [27] 优先经验回放 (PER)'],
            'mechanisms': ['EWC正则损失 L_EWC = λ·Σ F_i·(θ_i - θ*_i)²，λ=2000',
                           'Fisher信息矩阵对角元 F_i 量化参数重要性',
                           '任务切换前调用 consolidate_knowledge() 保护旧任务知识',
                           '抑制需求模式漂移/人员更替下的灾难性遗忘'],
            'output': '输出：长期稳健决策，SL提升1.42pp，BWE遗忘率-53.77%',
            'y_top': 25, 'y_bot': 7,
        },
    ]

    # 绘制四层
    for layer in layers:
        y_top = layer['y_top']
        y_bot = layer['y_bot']
        color = layer['color']

        # 层背景框
        rect = FancyBboxPatch((3, y_bot), 94, y_top - y_bot,
                              boxstyle="round,pad=0.5,rounding_size=1.5",
                              facecolor=color, alpha=0.08, edgecolor=color, linewidth=1.8)
        ax.add_patch(rect)

        # 层编号标签（左侧）
        rect_label = FancyBboxPatch((4, y_top - 3), 10, 2.5,
                                    boxstyle="round,pad=0.1,rounding_size=0.5",
                                    facecolor=color, edgecolor=color, linewidth=1.2)
        ax.add_patch(rect_label)
        ax.text(9, y_top - 1.75, layer['layer_num'],
                ha='center', va='center', fontsize=8, color='white', fontweight='bold')

        # 层标题（中文+英文）
        ax.text(16, y_top - 1.2, layer['title_zh'],
                ha='left', va='center', fontsize=11, fontweight='bold', color=color)
        ax.text(16, y_top - 2.8, f'{layer["title_en"]}  |  {layer["role"]}',
                ha='left', va='center', fontsize=8, color='#555555', style='italic')

        # 理论支柱（左侧）
        ax.text(5, y_top - 5, '■ 理论支柱 / Theoretical Pillars:',
                ha='left', va='top', fontsize=8, fontweight='bold', color=color)
        for i, theory in enumerate(layer['theories']):
            ax.text(6, y_top - 6.5 - i * 1.3, f'· {theory}',
                    ha='left', va='top', fontsize=7.2, color='#333333')

        # 机制（中间）
        mech_x = 42
        ax.text(mech_x, y_top - 5, '■ 核心机制 / Core Mechanisms:',
                ha='left', va='top', fontsize=8, fontweight='bold', color=color)
        for i, mech in enumerate(layer['mechanisms']):
            ax.text(mech_x + 1, y_top - 6.5 - i * 1.3, f'· {mech}',
                    ha='left', va='top', fontsize=7.2, color='#333333')

        # 输出（右侧）
        out_x = 75
        rect_out = FancyBboxPatch((out_x, y_top - 6.5), 21, 4,
                                  boxstyle="round,pad=0.2,rounding_size=0.5",
                                  facecolor='white', edgecolor=color, linewidth=1.2, alpha=0.9)
        ax.add_patch(rect_out)
        ax.text(out_x + 0.5, y_top - 3, '输出 / Output:',
                ha='left', va='center', fontsize=7, fontweight='bold', color=color)
        ax.text(out_x + 0.5, y_top - 4.8, layer['output'],
                ha='left', va='center', fontsize=6.8, color='#222222', wrap=True)

    # 递进因果链侧栏（最右侧）
    causal_chain = [
        ('情绪扰动', 'Emotional\nPerturbation', '诊断', LAYER_COLORS['perception'], 80),
        ('激励阻断', 'Incentive\nInterruption', '治疗', LAYER_COLORS['decision'], 57),
        ('协同鲁棒', 'Collaborative\nRobustness', '免疫', LAYER_COLORS['coordination'], 34),
        ('持续稳健', 'Continual\nStability', '鲁棒', LAYER_COLORS['adaptation'], 16),
    ]

    # 递进因果链标题
    ax.text(98, 91, '递进因果链\nProgressive Causal Chain',
            ha='center', va='center', fontsize=8.5, fontweight='bold', color='#222222')

    # 递进箭头
    for i in range(len(causal_chain) - 1):
        zh, en, role, color, y = causal_chain[i]
        next_y = causal_chain[i + 1][4]
        ax.annotate('', xy=(98, next_y + 2), xytext=(98, y - 2),
                    arrowprops=dict(arrowstyle='->', color='#666666', lw=1.5,
                                    connectionstyle='arc3,rad=0'))

    # 四级供应链示意（底部）
    ax.text(50, 5, '四级供应链：零售商 → 批发商 → 分销商 → 制造商  |  Four-echelon supply chain',
            ha='center', va='center', fontsize=9, fontweight='bold', color='#222222')

    save_figure(fig, 'Fig1_System_Mechanism',
                '图1 多智能体情绪感知人智协同决策系统机制图',
                'Fig.1 Mechanism of Multi-Agent Emotion-Aware Human-AI Collaborative Decision System')


# ============================================================
# Fig.2 多智能体人智协同供应链决策设计流程图
# ============================================================
def plot_fig2_decision_flow():
    """多智能体人智协同供应链决策设计流程图"""
    fig = plt.figure(figsize=(A4_W, A4_H))
    ax = fig.add_axes([0.02, 0.04, 0.96, 0.92])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # 标题
    ax.text(50, 97, '多智能体人智协同供应链决策设计流程',
            ha='center', va='top', fontsize=13, fontweight='bold')
    ax.text(50, 93.5, 'Multi-Agent Human-AI Collaborative Supply Chain Decision Design Flow',
            ha='center', va='top', fontsize=9.5, style='italic', color='#444444')

    # ===== 顶部：四级供应链结构 =====
    ax.text(50, 89, '■ 四级供应链结构 / Four-Echelon Supply Chain Structure',
            ha='center', va='top', fontsize=10, fontweight='bold', color='#222222')

    node_y = 82
    node_positions = [
        ('零售商\nRetailer', 15, NODE_COLORS['retailer'], '终端需求\nTerminal Demand'),
        ('批发商\nWholesaler', 38, NODE_COLORS['wholesaler'], '中游集散\nMid-distribution'),
        ('分销商\nDistributor', 61, NODE_COLORS['distributor'], '+IDMR+情绪\n+IDMR+Emotion'),
        ('制造商\nManufacturer', 84, NODE_COLORS['manufacturer'], '上游生产\nUpstream Production'),
    ]

    # 绘制节点
    for label, x, color, role in node_positions:
        circle = Circle((x, node_y), 4.5, facecolor=color, edgecolor='black', linewidth=1.2, alpha=0.85)
        ax.add_patch(circle)
        ax.text(x, node_y, label, ha='center', va='center', fontsize=7.5,
                color='white', fontweight='bold')
        ax.text(x, node_y - 6.5, role, ha='center', va='top', fontsize=6.8, color=color)

    # 订单流箭头（下游→上游）
    for i in range(len(node_positions) - 1):
        x1 = node_positions[i][1] + 4.5
        x2 = node_positions[i + 1][1] - 4.5
        ax.annotate('', xy=(x2, node_y), xytext=(x1, node_y),
                    arrowprops=dict(arrowstyle='->', color='#888888', lw=1.5))
        ax.text((x1 + x2) / 2, node_y + 1.5, '订单流+情绪状态',
                ha='center', va='bottom', fontsize=6.5, color='#666666', style='italic')

    # 需求箭头（外部→零售商）
    ax.annotate('', xy=(node_positions[0][1] - 4.5, node_y),
                xytext=(node_positions[0][1] - 10, node_y),
                arrowprops=dict(arrowstyle='->', color='#C44E52', lw=1.8))
    ax.text(node_positions[0][1] - 10, node_y + 2, 'AR(1)需求\nAR(1) Demand',
            ha='center', va='bottom', fontsize=7, color='#C44E52', fontweight='bold')

    # ===== 中部：四组对比实验设计 =====
    ax.text(50, 72, '■ 四组对比实验设计（控制变量法 + 剥离实验）/ Four-Group Controlled Experiments',
            ha='center', va='top', fontsize=10, fontweight='bold', color='#222222')

    experiments = [
        {
            'name': 'Baseline', 'name_en': '理性决策',
            'color': EXP_COLORS['baseline'],
            'config': 'SMA + OUT\n理性决策',
            'emotion': '×', 'coord': '×', 'dynamic': '×',
            'bwe': '301.75', 'sl': '99.61%', 'cost': '1664.80',
            'y': 64,
        },
        {
            'name': 'Exp_1', 'name_en': '单智能体IDMR',
            'color': EXP_COLORS['exp1'],
            'config': 'DQN部署于分销商\n李勇[10]复现',
            'emotion': '×', 'coord': '×', 'dynamic': '×',
            'bwe': '22.70', 'sl': '99.62%', 'cost': '39.54*',
            'y': 55,
        },
        {
            'name': 'Exp_1b', 'name_en': 'IDMR+情绪',
            'color': EXP_COLORS['exp1b'],
            'config': 'Exp_1 + 情绪演化方程\n+ 正向激励函数',
            'emotion': '√', 'coord': '×', 'dynamic': '×',
            'bwe': '22.78', 'sl': '99.61%', 'cost': '634.96',
            'y': 46,
        },
        {
            'name': 'Exp_2', 'name_en': '完整MAEA-HCDS',
            'color': EXP_COLORS['exp2'],
            'config': 'Exp_1b + 多智能体协同通信\n+ 76次动态事件',
            'emotion': '√', 'coord': '√', 'dynamic': '√',
            'bwe': '10.07', 'sl': '94.73%', 'cost': '458.34',
            'y': 37,
        },
    ]

    # 表头
    header_y = 68
    headers = [('实验组', 8), ('配置', 22), ('情绪', 45), ('协同', 52), ('动态事件', 59),
               ('制造商BWE', 68), ('系统SL', 77), ('系统成本', 86)]
    for header, x in headers:
        ax.text(x, header_y, header, ha='center', va='center',
                fontsize=7.5, fontweight='bold', color='#222222')

    # 表头分割线
    ax.plot([3, 97], [header_y - 1.5, header_y - 1.5], color='#888888', linewidth=0.8)

    # 绘制实验组
    for exp in experiments:
        y = exp['y']
        color = exp['color']

        # 实验组名（带色块）
        rect = FancyBboxPatch((4, y - 1.8), 8, 3.5,
                              boxstyle="round,pad=0.1,rounding_size=0.4",
                              facecolor=color, edgecolor=color, linewidth=1, alpha=0.85)
        ax.add_patch(rect)
        ax.text(8, y + 0.5, exp['name'], ha='center', va='center',
                fontsize=8, color='white', fontweight='bold')
        ax.text(8, y - 1.2, exp['name_en'], ha='center', va='center',
                fontsize=6.5, color='white')

        # 配置
        ax.text(22, y, exp['config'], ha='center', va='center',
                fontsize=6.8, color='#333333')

        # 情绪/协同/动态事件
        for marker, x in [(exp['emotion'], 45), (exp['coord'], 52), (exp['dynamic'], 59)]:
            mk_color = '#55A868' if marker == '√' else '#C44E52'
            ax.text(x, y, marker, ha='center', va='center',
                    fontsize=10, color=mk_color, fontweight='bold')

        # 性能指标
        ax.text(68, y, exp['bwe'], ha='center', va='center',
                fontsize=7.5, color=color, fontweight='bold')
        ax.text(77, y, exp['sl'], ha='center', va='center',
                fontsize=7, color='#333333')
        ax.text(86, y, exp['cost'], ha='center', va='center',
                fontsize=7, color='#333333')

    # 剥离逻辑箭头
    arrow_xs = [12, 12, 12]
    arrow_ys = [(64, 55), (55, 46), (46, 37)]
    arrow_labels = [
        '+IDMR智慧决策\n→ 制造商BWE -92.5%',
        '+情绪机制\n→ 情绪独立效应 <2%',
        '+协同通信+动态事件\n→ 制造商BWE -55.79%'
    ]
    for (y1, y2), label in zip(arrow_ys, arrow_labels):
        ax.annotate('', xy=(12, y2 + 2), xytext=(12, y1 - 2),
                    arrowprops=dict(arrowstyle='->', color='#444444', lw=1.5))
        ax.text(13.5, (y1 + y2) / 2, label, ha='left', va='center',
                fontsize=6.5, color='#444444', style='italic')

    # ===== 底部：剥离实验效应分解 =====
    ax.text(50, 30, '■ 剥离实验效应分解 / Ablation Effect Decomposition',
            ha='center', va='top', fontsize=10, fontweight='bold', color='#222222')

    # 三大效应
    effects = [
        ('情绪机制独立效应', 'Emotion Effect', 'Exp_1b - Exp_1',
         '分销商BWE: -1.3%\n机制存在性成立\nH1部分验证', LAYER_COLORS['perception'], 18),
        ('协同通信效应', 'Coordination Effect', 'Exp_2 - Exp_1b',
         '制造商BWE: -55.79%\n核心创新机制\nH3部分验证', LAYER_COLORS['coordination'], 50),
        ('联合效应', 'Joint Effect', 'Exp_2 - Exp_1',
         '制造商BWE: -96.66%\n系统总成本: -72.5%\nH2验证成立', LAYER_COLORS['decision'], 82),
    ]

    for title_zh, title_en, formula, result, color, x in effects:
        # 效应框
        rect = FancyBboxPatch((x - 12, 16), 24, 11,
                              boxstyle="round,pad=0.3,rounding_size=0.8",
                              facecolor=color, alpha=0.1, edgecolor=color, linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x, 25, title_zh, ha='center', va='center',
                fontsize=8.5, fontweight='bold', color=color)
        ax.text(x, 23, title_en, ha='center', va='center',
                fontsize=7, color=color, style='italic')
        ax.text(x, 20.5, formula, ha='center', va='center',
                fontsize=7, color='#555555')
        ax.text(x, 18, result, ha='center', va='center',
                fontsize=7, color='#222222', fontweight='bold')

    # 底部说明
    ax.text(50, 11, '注：Exp_1成本采用简化公式（与李勇等[10]一致），不与其他三组直接比较',
            ha='center', va='center', fontsize=7, color='#666666', style='italic')
    ax.text(50, 8.5, '随机种子 seed=42 | 仿真周期 T=20000 | 动态事件 76次（53次需求突变+23次供应中断）',
            ha='center', va='center', fontsize=7.5, color='#222222')
    ax.text(50, 6, '所有实验共享相同需求模型 AR(1): ρ=0.5, σ=5, d=10, L=2 | 成本参数 h=1.0, b=2.0',
            ha='center', va='center', fontsize=7.5, color='#222222')

    save_figure(fig, 'Fig2_Decision_Flow',
                '图2 多智能体人智协同供应链决策设计流程图',
                'Fig.2 Multi-Agent Human-AI Collaborative Supply Chain Decision Design Flow')


# ============================================================
# Fig.8 情绪传染网络图
# ============================================================
def plot_fig8_emotion_contagion():
    """情绪传染网络图：2830次事件+逐级衰减"""
    fig = plt.figure(figsize=(A4_W, A4_H))
    gs = gridspec.GridSpec(3, 2, hspace=0.45, wspace=0.30,
                           left=0.10, right=0.95, top=0.90, bottom=0.10)

    # 标题
    fig.text(0.5, 0.95, '情绪传染网络分析（Exp_2, 20000周期）',
             ha='center', va='center', fontsize=12, fontweight='bold')
    fig.text(0.5, 0.92, 'Emotional Contagion Network Analysis',
             ha='center', va='center', fontsize=9.5, style='italic', color='#444444')

    # ===== 子图a：供应链节点情绪传染网络图 =====
    ax1 = fig.add_subplot(gs[0, :])
    ax1.set_xlim(-5, 105)
    ax1.set_ylim(-5, 50)
    ax1.axis('off')
    ax1.set_title('(a) 情绪传染网络图 | Emotional Contagion Network', fontsize=10, loc='left')

    # 节点位置（横向排列）
    nodes = [
        ('零售商\nRetailer', 10, 25, NODE_COLORS['retailer'], 1839),
        ('批发商\nWholesaler', 35, 25, NODE_COLORS['wholesaler'], 594),
        ('分销商\nDistributor', 60, 25, NODE_COLORS['distributor'], 397),
        ('制造商\nManufacturer', 85, 25, NODE_COLORS['manufacturer'], 0),
    ]

    # 绘制节点（大小按传染事件数）
    for label, x, y, color, count in nodes:
        # 节点圆（大小根据事件数）
        size = 3 + count / 300 if count > 0 else 3
        circle = Circle((x, y), size, facecolor=color, edgecolor='black',
                        linewidth=1.2, alpha=0.85)
        ax1.add_patch(circle)
        ax1.text(x, y, label, ha='center', va='center', fontsize=7.5,
                 color='white', fontweight='bold')
        # 事件数标签
        if count > 0:
            ax1.text(x, y - size - 2, f'传染事件: {count}',
                     ha='center', va='top', fontsize=7, color=color, fontweight='bold')

    # 传染箭头（零售商→批发商→分销商→制造商）
    contagion_data = [
        (10, 25, 35, 25, 1839, 65.0, NODE_COLORS['retailer']),     # R→W
        (35, 25, 60, 25, 594, 21.0, NODE_COLORS['wholesaler']),    # W→D
        (60, 25, 85, 25, 397, 14.0, NODE_COLORS['distributor']),   # D→M
    ]

    for x1, y1, x2, y2, count, pct, color in contagion_data:
        # 上方曲线箭头
        arrow = FancyArrowPatch((x1 + 3.5, y1 + 2), (x2 - 3.5, y2 + 2),
                                arrowstyle='->', mutation_scale=15,
                                color=color, linewidth=2 + count / 600,
                                alpha=0.7, connectionstyle='arc3,rad=-0.25')
        ax1.add_patch(arrow)
        # 百分比标签
        mid_x = (x1 + x2) / 2
        ax1.text(mid_x, y1 + 9, f'{pct}%',
                 ha='center', va='center', fontsize=9, color=color, fontweight='bold')
        ax1.text(mid_x, y1 + 6.5, f'({count}次)',
                 ha='center', va='center', fontsize=7, color='#555555')

    # 情绪状态示意（下方）
    emotion_y = 12
    emotion_states = [
        ('恐慌饱和\nPanic', -0.778, NODE_COLORS['retailer'], 10),
        ('恐慌饱和\nPanic', -0.685, NODE_COLORS['wholesaler'], 35),
        ('恐慌饱和\nPanic', -0.712, NODE_COLORS['distributor'], 60),
        ('轻度恐慌\nMild Panic', -0.456, NODE_COLORS['manufacturer'], 85),
    ]

    for label, emo_val, color, x in emotion_states:
        rect = FancyBboxPatch((x - 5, emotion_y - 2), 10, 4,
                              boxstyle="round,pad=0.1,rounding_size=0.3",
                              facecolor=color, alpha=0.2, edgecolor=color, linewidth=1)
        ax1.add_patch(rect)
        ax1.text(x, emotion_y, label,
                 ha='center', va='center', fontsize=6.5, color=color, fontweight='bold')
        ax1.text(x, emotion_y - 3.2, f'E = {emo_val}',
                 ha='center', va='center', fontsize=6.5, color='#333333')

    # 图例
    ax1.text(50, 2, '总传染事件: 2830次 | 逐级衰减: 1839 → 594 → 397 | 零售商→批发商占比最高 (65.0%)',
             ha='center', va='center', fontsize=7.5, color='#222222', fontweight='bold')

    # ===== 子图b：传染事件逐级衰减柱状图 =====
    ax2 = fig.add_subplot(gs[1, 0])
    contagion_counts = [1839, 594, 397]
    contagion_labels = ['R→W', 'W→D', 'D→M']
    contagion_colors = [NODE_COLORS['retailer'], NODE_COLORS['wholesaler'], NODE_COLORS['distributor']]

    bars = ax2.bar(contagion_labels, contagion_counts, color=contagion_colors,
                   edgecolor='black', linewidth=0.8, alpha=0.85)
    for bar, count in zip(bars, contagion_counts):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 30,
                 f'{count}', ha='center', va='bottom', fontsize=8, fontweight='bold')

    ax2.set_ylabel('传染事件数\nContagion Count')
    ax2.set_title('(b) 传染事件逐级衰减 | Stepwise Attenuation', fontsize=9, loc='left')
    ax2.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax2.set_ylim(0, 2100)

    # 衰减率标注
    ax2.annotate(f'-67.7%', xy=(1, 594), xytext=(1.3, 1200),
                 fontsize=8, color='#C44E52', fontweight='bold',
                 arrowprops=dict(arrowstyle='->', color='#C44E52', lw=1))
    ax2.annotate(f'-33.2%', xy=(2, 397), xytext=(2.3, 800),
                 fontsize=8, color='#C44E52', fontweight='bold',
                 arrowprops=dict(arrowstyle='->', color='#C44E52', lw=1))

    # ===== 子图c：各节点恐慌占比 =====
    ax3 = fig.add_subplot(gs[1, 1])
    panic_pcts = [98.7, 87.52, 94.98, 93.11]  # 零售商、批发商、分销商、制造商
    node_labels = ['零售商\nR', '批发商\nW', '分销商\nD', '制造商\nM']
    node_colors_list = [NODE_COLORS['retailer'], NODE_COLORS['wholesaler'],
                        NODE_COLORS['distributor'], NODE_COLORS['manufacturer']]

    bars = ax3.bar(node_labels, panic_pcts, color=node_colors_list,
                   edgecolor='black', linewidth=0.8, alpha=0.85)
    for bar, pct in zip(bars, panic_pcts):
        ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f'{pct}%', ha='center', va='bottom', fontsize=7.5, fontweight='bold')

    ax3.set_ylabel('恐慌占比 (%)\nPanic Ratio')
    ax3.set_title('(c) 各节点恐慌占比 | Panic Ratio by Node', fontsize=9, loc='left')
    ax3.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax3.set_ylim(0, 110)
    ax3.axhline(y=90, color='red', linestyle=':', linewidth=0.7, alpha=0.6)

    # ===== 子图d：情绪波动指数对比（Exp_1b vs Exp_2）=====
    ax4 = fig.add_subplot(gs[2, 0])
    nodes_x = np.arange(4)
    exp1b_emo = [0.005, 0.008, 0.0305, 0.012]  # Exp_1b情绪方差
    exp2_emo = [0.0634, 0.0428, 0.0356, 0.0235]  # Exp_2情绪方差

    width = 0.35
    bars1 = ax4.bar(nodes_x - width/2, exp1b_emo, width, label='Exp_1b (无动态事件)',
                    color=EXP_COLORS['exp1b'], edgecolor='black', linewidth=0.6, alpha=0.85)
    bars2 = ax4.bar(nodes_x + width/2, exp2_emo, width, label='Exp_2 (76次动态事件)',
                    color=EXP_COLORS['exp2'], edgecolor='black', linewidth=0.6, alpha=0.85)

    for bar, val in zip(bars1, exp1b_emo):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
                 f'{val:.4f}', ha='center', va='bottom', fontsize=6.5)
    for bar, val in zip(bars2, exp2_emo):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
                 f'{val:.4f}', ha='center', va='bottom', fontsize=6.5)

    ax4.set_xticks(nodes_x)
    ax4.set_xticklabels(['零售商\nR', '批发商\nW', '分销商\nD', '制造商\nM'], fontsize=7.5)
    ax4.set_ylabel('情绪方差 σ²_E\nEmotion Variance')
    ax4.set_title('(d) 情绪波动指数对比 | Emotion Variance', fontsize=9, loc='left')
    ax4.legend(loc='upper right', fontsize=7)
    ax4.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    # ===== 子图e：情绪-决策Pearson相关系数 =====
    ax5 = fig.add_subplot(gs[2, 1])
    pearson_r = [0.234, 0.187, 0.156, -0.198]  # 零售商、批发商、分销商（正相关）、制造商（负相关）
    p_values = [r'$p<10^{-60}$'] * 4

    colors_pearson = ['#55A868' if r > 0 else '#C44E52' for r in pearson_r]
    bars = ax5.barh(node_labels, pearson_r, color=colors_pearson,
                    edgecolor='black', linewidth=0.8, alpha=0.85)
    for bar, r, p in zip(bars, pearson_r, p_values):
        x_pos = bar.get_width() + (0.01 if r > 0 else -0.01)
        ha = 'left' if r > 0 else 'right'
        ax5.text(x_pos, bar.get_y() + bar.get_height()/2,
                 f'r={r:+.3f} ({p})', ha=ha, va='center', fontsize=7)

    ax5.axvline(x=0, color='black', linewidth=0.8)
    ax5.set_xlabel('Pearson相关系数 | Pearson Correlation')
    ax5.set_title('(e) 情绪-决策相关性 | Emotion-Decision Correlation', fontsize=9, loc='left')
    ax5.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
    ax5.set_xlim(-0.35, 0.35)

    # 图例说明
    ax5.text(0.02, 0.02, '绿: 正相关（乐观→多订货）\n红: 负相关（恐慌→多订货）',
             transform=ax5.transAxes, fontsize=6.5, color='#555555',
             verticalalignment='bottom')

    save_figure(fig, 'Fig8_Emotion_Contagion',
                '图8 情绪传染网络图（Exp_2, 20000周期, 2830次传染事件）',
                'Fig.8 Emotional Contagion Network (Exp_2, 20,000 cycles, 2,830 contagion events)')


# ============================================================
# 主函数
# ============================================================
if __name__ == '__main__':
    print('=' * 60)
    print('论文配图生成器（719版）')
    print('=' * 60)
    print(f'输出目录: {FIG_DIR}/')
    print()

    print('[1/3] 绘制图1: MAEA-HCDS系统机制图...')
    plot_fig1_system_mechanism()

    print('[2/3] 绘制图2: 多智能体人智协同供应链决策设计流程图...')
    plot_fig2_decision_flow()

    print('[3/3] 绘制图8: 情绪传染网络图...')
    plot_fig8_emotion_contagion()

    print()
    print('=' * 60)
    print('全部3张论文配图生成完毕！')
    print(f'输出目录: {FIG_DIR}/')
    print('=' * 60)

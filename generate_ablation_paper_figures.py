"""
消融实验论文级配图生成器
======================
符合SCI顶刊标准的消融实验配图:
  - A4竖版 (8.27 x 11.69 inches)
  - SCI顶刊配色 (Nature/Science柔和低饱和)
  - 双语坐标轴 (中文主 + English副)
  - 图标题底部居中
  - 矢量输出 (PDF + SVG)
  - Arial字体 + Songti_SC汉字

消融实验设计:
  主消融(4组): Baseline / Exp_1 / Exp_1b / Exp_2
  子消融(4组): Exp_2a(仅情绪) / Exp_2b(仅协同) / Exp_2c(情绪+协同) / Exp_2(完整)
  持续学习(3组): A(无EWC无噪声) / B(有EWC无噪声) / C(有EWC+噪声)

生成6张论文配图:
  Fig.1 四组主消融BWE对比 (A4竖版, 4子图)
  Fig.2 剥离效应分解堆叠图 (情绪/协同/联合效应)
  Fig.3 情绪-决策归因分析 (4节点散点+Pearson)
  Fig.4 情绪传染网络桑基图
  Fig.5 正向激励阻断效应 (恐慌vs中性过度订货)
  Fig.6 持续学习鲁棒性 (EWC三组对比)
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D
import matplotlib.gridspec as gridspec

# ============================================================
# 全局样式: SCI顶刊标准
# ============================================================
plt.rcParams['font.family'] = 'sans-serif'
# 中文字体优先 (YaHei支持中英文，确保中文不缺字; Arial作为西文备选)
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['mathtext.fontset'] = 'stix'  # 数学公式用STIX字体
plt.rcParams['font.size'] = 9
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['axes.titlesize'] = 10
plt.rcParams['xtick.labelsize'] = 8.5
plt.rcParams['ytick.labelsize'] = 8.5
plt.rcParams['legend.fontsize'] = 8
plt.rcParams['legend.frameon'] = False
plt.rcParams['svg.fonttype'] = 'none'  # text stays as <text>, not paths
plt.rcParams['pdf.fonttype'] = 42      # TrueType, editable in Illustrator

# A4竖版尺寸 (inches)
A4_PORTRAIT_W = 8.27
A4_PORTRAIT_H = 11.69

# SCI顶刊配色 (Nature/Science柔和低饱和)
COLORS_NATURE = {
    'baseline': '#5B5B5B',   # 中性灰
    'exp1':     '#4C72B0',   # 柔和蓝
    'exp1b':    '#DD8452',   # 柔和橙
    'exp2':     '#55A868',   # 柔和绿
    'exp2a':    '#C44E52',   # 柔和红
    'exp2b':    '#8172B3',   # 柔和紫
    'exp2c':    '#937860',   # 柔和棕
    'panic':    '#C44E52',   # 恐慌红
    'neutral':  '#4C72B0',   # 中性蓝
    'optimistic':'#55A868',  # 乐观绿
    'ewc_A':    '#DD8452',   # 无EWC橙
    'ewc_B':    '#55A868',   # 有EWC绿
    'ewc_C':    '#C44E52',   # EWC+噪声红
}

NODE_NAMES_ZH = ['零售商', '批发商', '分销商', '制造商']
NODE_NAMES_EN = ['Retailer', 'Wholesaler', 'Distributor', 'Manufacturer']
NODE_LABELS = [f'{z}\n{e}' for z, e in zip(NODE_NAMES_ZH, NODE_NAMES_EN)]

# 路径
P0_DIR = 'p0_results'
FIG_DIR = 'svg_figures_ablation'
os.makedirs(FIG_DIR, exist_ok=True)


# ============================================================
# 数据加载
# ============================================================
def load_all_data():
    """加载消融实验全部数据"""
    with open(os.path.join(P0_DIR, '四组对比_20k.json'), 'r', encoding='utf-8') as f:
        four_group = json.load(f)
    with open(os.path.join(P0_DIR, '消融实验结果.json'), 'r', encoding='utf-8') as f:
        sub_ablation = json.load(f)
    with open(os.path.join(P0_DIR, '归因分析_20k.json'), 'r', encoding='utf-8') as f:
        attr_exp2 = json.load(f)
    with open(os.path.join(P0_DIR, '归因分析_exp1b.json'), 'r', encoding='utf-8') as f:
        attr_exp1b = json.load(f)
    # 持续学习文件在主目录而非 p0_results/
    cl_path = os.path.join('灾难性遗忘_结果摘要.json')
    if not os.path.exists(cl_path):
        cl_path = os.path.join(P0_DIR, '灾难性遗忘_结果摘要.json')
    with open(cl_path, 'r', encoding='utf-8') as f:
        continual = json.load(f)
    return four_group, sub_ablation, attr_exp2, attr_exp1b, continual


# ============================================================
# 通用: 保存图 + 添加底部标题
# ============================================================
def save_figure(fig, name, caption_zh, caption_en):
    """添加底部居中标题并保存为PDF+SVG+PNG（PNG用于docx嵌入）"""
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
# Fig.1 四组主消融BWE对比 (A4竖版, 4子图: BWE/SL/Cost/Emotion)
# ============================================================
def plot_fig1_main_ablation_4panel(four_group):
    """四组主消融实验4面板对比: BWE / SL / Cost / Emotion Variance"""
    fig = plt.figure(figsize=(A4_PORTRAIT_W, 10.5))
    gs = gridspec.GridSpec(2, 2, hspace=0.45, wspace=0.32,
                           left=0.10, right=0.96, top=0.94, bottom=0.10)

    groups = [
        ('baseline', 'Baseline\n理性决策\nRational', COLORS_NATURE['baseline']),
        ('exp1',     'Exp_1\n单智能体IDMR\nSingle IDMR', COLORS_NATURE['exp1']),
        ('exp1b',    'Exp_1b\nIDMR+情绪\nIDMR+Emotion', COLORS_NATURE['exp1b']),
        ('exp2',     'Exp_2\n完整版\nFull System', COLORS_NATURE['exp2']),
    ]
    x = np.arange(4)
    width = 0.20

    # (a) BWE
    ax1 = fig.add_subplot(gs[0, 0])
    for i, (key, label, color) in enumerate(groups):
        bwe_vals = [four_group[key]['bwe'][str(k)] for k in range(1, 5)]
        # 对制造商BWE做对数压缩便于可视化
        bwe_vals_log = [v if v < 50 else 50 + np.log10(v / 50) * 30 for v in bwe_vals]
        bars = ax1.bar(x + (i - 1.5) * width, bwe_vals_log, width,
                       label=label.split('\n')[0], color=color,
                       edgecolor='black', linewidth=0.5)
        for bar, v in zip(bars, bwe_vals):
            h = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2, h + 2,
                     f'{v:.1f}', ha='center', va='bottom', fontsize=6.5, rotation=0)
    ax1.set_xticks(x)
    ax1.set_xticklabels(NODE_LABELS, fontsize=8)
    ax1.set_ylabel('方差比 BWE\nVariance Ratio (log-scaled above 50)')
    ax1.set_title('(a) 牛鞭效应方差比', fontsize=9.5, loc='left')
    ax1.legend(loc='upper left', fontsize=6.5, ncol=2)
    ax1.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax1.axhline(y=50, color='gray', linestyle=':', linewidth=0.5, alpha=0.5)
    ax1.set_ylim(0, 200)

    # (b) Service Level
    ax2 = fig.add_subplot(gs[0, 1])
    for i, (key, label, color) in enumerate(groups):
        sl_vals = [four_group[key]['sl'][str(k)] * 100 for k in range(1, 5)]
        bars = ax2.bar(x + (i - 1.5) * width, sl_vals, width,
                       label=label.split('\n')[0], color=color,
                       edgecolor='black', linewidth=0.5)
        for bar, v in zip(bars, sl_vals):
            h = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                     f'{v:.2f}', ha='center', va='bottom', fontsize=6.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels(NODE_LABELS, fontsize=8)
    ax2.set_ylabel('服务水平 SL (%)\nService Level')
    ax2.set_title('(b) 服务水平', fontsize=9.5, loc='left')
    ax2.legend(loc='lower left', fontsize=6.5, ncol=2)
    ax2.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax2.set_ylim(75, 102)
    ax2.axhline(y=99, color='red', linestyle=':', linewidth=0.7, alpha=0.6)

    # (c) Average Cost (log scale)
    ax3 = fig.add_subplot(gs[1, 0])
    for i, (key, label, color) in enumerate(groups):
        cost_vals = [four_group[key]['avg_cost'][str(k)] for k in range(1, 5)]
        bars = ax3.bar(x + (i - 1.5) * width, cost_vals, width,
                       label=label.split('\n')[0], color=color,
                       edgecolor='black', linewidth=0.5)
        for bar, v in zip(bars, cost_vals):
            h = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width() / 2, h * 1.02,
                     f'{v:.1f}', ha='center', va='bottom', fontsize=6.5)
    ax3.set_xticks(x)
    ax3.set_xticklabels(NODE_LABELS, fontsize=8)
    ax3.set_ylabel('平均成本\nAverage Cost (per cycle)')
    ax3.set_title('(c) 节点平均成本', fontsize=9.5, loc='left')
    ax3.set_yscale('log')
    ax3.legend(loc='upper left', fontsize=6.5, ncol=2)
    ax3.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5, which='both')

    # (d) Emotion Variance (only exp1b & exp2)
    ax4 = fig.add_subplot(gs[1, 1])
    emo_groups = [('exp1b', 'Exp_1b', COLORS_NATURE['exp1b']),
                  ('exp2',  'Exp_2',  COLORS_NATURE['exp2'])]
    for i, (key, label, color) in enumerate(emo_groups):
        ev = four_group[key].get('emotion_variance', {})
        emo_vals = [ev.get(str(k), 0.0) for k in range(1, 5)]
        bars = ax4.bar(x + (i - 0.5) * width * 1.2, emo_vals, width * 1.2,
                       label=label, color=color, edgecolor='black', linewidth=0.5)
        for bar, v in zip(bars, emo_vals):
            h = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width() / 2, h + 0.005,
                     f'{v:.3f}', ha='center', va='bottom', fontsize=7)
    ax4.set_xticks(x)
    ax4.set_xticklabels(NODE_LABELS, fontsize=8)
    ax4.set_ylabel('情绪方差 $\\sigma_E^2$\nEmotion Variance')
    ax4.set_title('(d) 情绪波动指数', fontsize=9.5, loc='left')
    ax4.legend(loc='upper right', fontsize=7)
    ax4.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    save_figure(fig, 'fig1_main_ablation_4panel',
                '图1 四组主消融实验多指标对比 (20000周期)',
                'Fig.1 Multi-metric comparison across four main ablation groups (20,000 cycles)')


# ============================================================
# Fig.2 剥离效应分解堆叠图 (情绪/协同/联合效应)
# ============================================================
def plot_fig2_ablation_decomposition(four_group, sub_ablation):
    """剥离效应分解: 情绪效应 / 协同效应 / 联合效应"""
    fig = plt.figure(figsize=(A4_PORTRAIT_W, 9.5))
    gs = gridspec.GridSpec(2, 1, hspace=0.40, left=0.12, right=0.95, top=0.93, bottom=0.12)

    # 上图: 主消融4组的剥离效应 (Exp_1 -> Exp_1b -> Exp_2)
    ax1 = fig.add_subplot(gs[0])
    x = np.arange(4)
    width = 0.28

    # 计算剥离效应
    bwe_base = np.array([four_group['baseline']['bwe'][str(k)] for k in range(1, 5)])
    bwe_exp1 = np.array([four_group['exp1']['bwe'][str(k)] for k in range(1, 5)])
    bwe_exp1b = np.array([four_group['exp1b']['bwe'][str(k)] for k in range(1, 5)])
    bwe_exp2 = np.array([four_group['exp2']['bwe'][str(k)] for k in range(1, 5)])

    # IDMR效应 (base -> exp1)
    effect_idmr = bwe_base - bwe_exp1
    # 情绪效应 (exp1 -> exp1b)
    effect_emotion = bwe_exp1 - bwe_exp1b
    # 协同效应 (exp1b -> exp2)
    effect_coord = bwe_exp1b - bwe_exp2

    # 堆叠柱状图
    p1 = ax1.bar(x, effect_idmr, width, label='IDMR效应 IDMR Effect (Base→Exp_1)',
                 color=COLORS_NATURE['exp1'], edgecolor='black', linewidth=0.5)
    p2 = ax1.bar(x, effect_emotion, width, bottom=effect_idmr,
                 label='情绪效应 Emotion Effect (Exp_1→Exp_1b)',
                 color=COLORS_NATURE['exp1b'], edgecolor='black', linewidth=0.5)
    p3 = ax1.bar(x, effect_coord, width, bottom=effect_idmr + effect_emotion,
                 label='协同效应 Coordination Effect (Exp_1b→Exp_2)',
                 color=COLORS_NATURE['exp2'], edgecolor='black', linewidth=0.5)

    # 标注每个分段数值
    for i in range(4):
        # IDMR
        if effect_idmr[i] > 5:
            ax1.text(i, effect_idmr[i] / 2, f'{effect_idmr[i]:.1f}',
                     ha='center', va='center', fontsize=7, color='white', fontweight='bold')
        # Emotion
        if abs(effect_emotion[i]) > 0.5:
            y_pos = effect_idmr[i] + effect_emotion[i] / 2
            ax1.text(i, y_pos, f'{effect_emotion[i]:+.2f}',
                     ha='center', va='center', fontsize=7, color='white', fontweight='bold')
        # Coord
        if effect_coord[i] > 5:
            y_pos = effect_idmr[i] + effect_emotion[i] + effect_coord[i] / 2
            ax1.text(i, y_pos, f'{effect_coord[i]:.1f}',
                     ha='center', va='center', fontsize=7, color='white', fontweight='bold')
        # Total
        total = effect_idmr[i] + effect_emotion[i] + effect_coord[i]
        ax1.text(i, total + 5, f'Σ={total:.1f}',
                 ha='center', va='bottom', fontsize=8, fontweight='bold')

    ax1.set_xticks(x)
    ax1.set_xticklabels(NODE_LABELS, fontsize=9)
    ax1.set_ylabel('BWE降幅 (绝对值)\nBWE Reduction (absolute)')
    ax1.set_title('(a) 主消融实验剥离效应分解', fontsize=10, loc='left')
    ax1.legend(loc='upper right', fontsize=7.5)
    ax1.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax1.axhline(y=0, color='black', linewidth=0.7)

    # 下图: 子消融4组 BWE (Exp_2a / 2b / 2c / 2)
    ax2 = fig.add_subplot(gs[1])
    sub_groups = [
        ('exp2a', 'Exp_2a\n仅情绪\nEmotion only', COLORS_NATURE['exp2a']),
        ('exp2b', 'Exp_2b\n仅协同\nCoord. only', COLORS_NATURE['exp2b']),
        ('exp2c', 'Exp_2c\n情绪+协同\nEmo.+Coord.', COLORS_NATURE['exp2c']),
        ('exp2',  'Exp_2\n完整版\nFull (w/ events)', COLORS_NATURE['exp2']),
    ]
    width2 = 0.20
    for i, (key, label, color) in enumerate(sub_groups):
        bwe_vals = [sub_ablation[key]['bwe'][str(k)] for k in range(1, 5)]
        bars = ax2.bar(x + (i - 1.5) * width2, bwe_vals, width2,
                       label=label.split('\n')[0], color=color,
                       edgecolor='black', linewidth=0.5)
        for bar, v in zip(bars, bwe_vals):
            h = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width() / 2, h + 0.3,
                     f'{v:.2f}', ha='center', va='bottom', fontsize=7)
    ax2.set_xticks(x)
    ax2.set_xticklabels(NODE_LABELS, fontsize=9)
    ax2.set_ylabel('方差比 BWE\nVariance Ratio')
    ax2.set_title('(b) 子消融实验BWE对比 (无动态事件 vs 完整版)', fontsize=10, loc='left')
    ax2.legend(loc='upper left', fontsize=7.5, ncol=2)
    ax2.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    save_figure(fig, 'fig2_ablation_decomposition',
                '图2 消融实验剥离效应分解',
                'Fig.2 Ablation effect decomposition (main + sub-ablation)')


# ============================================================
# Fig.3 情绪-决策归因分析 (4节点散点+Pearson)
# ============================================================
def plot_fig3_emotion_decision_attribution(attr_exp2, attr_exp1b):
    """4节点情绪vs订货量散点 + Pearson系数 + Exp_1b对照"""
    fig = plt.figure(figsize=(A4_PORTRAIT_W, 10.5))
    gs = gridspec.GridSpec(2, 2, hspace=0.40, wspace=0.30,
                           left=0.10, right=0.96, top=0.93, bottom=0.10)

    # 上2图: Exp_2 各节点情绪-订货量散点
    for idx in range(4):
        k = str(idx + 1)
        node_data = attr_exp2['emotion_decision_correlation'][k]
        ax = fig.add_subplot(gs[idx // 2, idx % 2])

        # 用统计量绘制分组柱状 (恐慌/中性/乐观的平均订货量+/-std)
        categories = ['恐慌\nPanic\n(E<-0.3)', '中性\nNeutral\n(|E|<=0.1)', '乐观\nOptimistic\n(E>0.3)']
        means = [node_data['panic_mean_order'], node_data['neutral_mean_order'], node_data['optimistic_mean_order']]
        stds = [node_data['panic_std_order'], node_data['neutral_std_order'], node_data['optimistic_std_order']]
        counts = [node_data['panic_count'], node_data['neutral_count'], node_data['optimistic_count']]
        colors_emo = [COLORS_NATURE['panic'], COLORS_NATURE['neutral'], COLORS_NATURE['optimistic']]

        x_pos = np.arange(3)
        bars = ax.bar(x_pos, means, yerr=stds, width=0.55,
                      color=colors_emo, edgecolor='black', linewidth=0.6,
                      capsize=4, error_kw={'linewidth': 0.8, 'ecolor': 'black'})
        for bar, m, n in zip(bars, means, counts):
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + max(means) * 0.04,
                    f'{m:.2f}\n(n={n})', ha='center', va='bottom', fontsize=7)

        # Pearson系数
        r = node_data['pearson_emotion_order']
        p = node_data['p_value_order']
        p_str = f'p<10^{-int(np.ceil(-np.log10(max(p, 1e-300))))}' if p < 1e-10 else f'p={p:.2e}'
        ax.set_title(f'({chr(97+idx)}) {NODE_NAMES_ZH[idx]} {NODE_NAMES_EN[idx]}\n'
                     f'r(E,q)={r:+.3f}, {p_str}', fontsize=9, loc='left')
        ax.set_xticks(x_pos)
        ax.set_xticklabels(categories, fontsize=7.5)
        ax.set_ylabel('平均订货量\nMean Order Quantity')
        ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
        ax.set_ylim(0, max(means) * 1.35)

    save_figure(fig, 'fig3_emotion_decision_attribution',
                '图3 情绪-决策归因分析 (Exp_2, 4节点)',
                'Fig.3 Emotion-decision attribution analysis (Exp_2, 4 nodes)')


# ============================================================
# Fig.4 情绪传染网络桑基图
# ============================================================
def plot_fig4_contagion_network(attr_exp2):
    """情绪传染路径流量图 (Sankey-like)"""
    fig = plt.figure(figsize=(A4_PORTRAIT_W, 8.5))
    gs = gridspec.GridSpec(1, 1, left=0.10, right=0.95, top=0.90, bottom=0.12)
    ax = fig.add_subplot(gs[0])

    contagion = attr_exp2['contagion_analysis']
    total = contagion['total_events']
    paths = contagion['path_counts']

    # 4节点位置 (横向)
    node_x = [0.15, 0.40, 0.65, 0.90]
    node_y = [0.5] * 4
    node_width = 0.05
    node_height_base = 0.35

    # 各节点流量 (出度+入度)
    flows = {
        '1->2': paths.get('零售商→批发商', 0),
        '2->3': paths.get('批发商→分销商', 0),
        '3->4': paths.get('分销商→制造商', 0),
    }

    # 绘制节点 (矩形)
    node_colors = [COLORS_NATURE['panic'] for _ in range(4)]
    for i, name in enumerate(NODE_NAMES_ZH):
        # 节点高度按入度比例
        inflow = sum([flows[f'{j}->{i+1}'] for j in range(1, i+1) if f'{j}->{i+1}' in flows])
        outflow = sum([flows[f'{i+1}->{j}'] for j in range(i+2, 5) if f'{i+1}->{j}' in flows])
        h = node_height_base * (0.5 + 0.5 * (inflow + outflow) / total * 4)
        rect = FancyArrowPatch((node_x[i], node_y[i] - h/2),
                                (node_x[i] + node_width, node_y[i] - h/2),
                                arrowstyle='-', color=node_colors[i], linewidth=0)
        ax.add_patch(plt.Rectangle((node_x[i] - node_width/2, node_y[i] - h/2),
                                    node_width, h, facecolor=node_colors[i],
                                    edgecolor='black', linewidth=1, alpha=0.75))
        ax.text(node_x[i], node_y[i] + h/2 + 0.05,
                f'{name}\n{NODE_NAMES_EN[i]}', ha='center', va='bottom', fontsize=9.5)
        # 入度/出度标注
        if i == 0:
            ax.text(node_x[i], node_y[i] - h/2 - 0.04,
                    f'源头 Source\n出度 Out={outflow}', ha='center', va='top', fontsize=7.5,
                    color=COLORS_NATURE['panic'])
        elif i == 3:
            ax.text(node_x[i], node_y[i] - h/2 - 0.04,
                    f'终端 Terminal\n入度 In={inflow}', ha='center', va='top', fontsize=7.5,
                    color=COLORS_NATURE['panic'])
        else:
            ax.text(node_x[i], node_y[i] - h/2 - 0.04,
                    f'入度 In={inflow}\n出度 Out={outflow}', ha='center', va='top', fontsize=7.5)

    # 绘制流量曲线 (贝塞尔)
    for path_key, count in flows.items():
        # path_key 格式如 '1->2'
        src, dst = path_key.split('->')
        s_idx = int(src) - 1
        d_idx = int(dst) - 1
        x_start = node_x[s_idx] + node_width/2
        x_end = node_x[d_idx] - node_width/2
        y_start = node_y[s_idx]
        y_end = node_y[d_idx]

        # 流量宽度
        width = 0.005 + 0.020 * count / max(flows.values())

        # 贝塞尔曲线
        from matplotlib.path import Path
        verts = [(x_start, y_start + 0.05),
                 ((x_start + x_end)/2, y_start + 0.10),
                 ((x_start + x_end)/2, y_end + 0.10),
                 (x_end, y_end + 0.05)]
        codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4]
        path = Path(verts, codes)
        patch = mpatches.PathPatch(path, facecolor='none',
                                    edgecolor=COLORS_NATURE['panic'],
                                    linewidth=width * 100, alpha=0.55)
        ax.add_patch(patch)

        # 中点标注
        mid_x = (x_start + x_end) / 2
        mid_y = (y_start + y_end) / 2 + 0.08
        pct = count / total * 100
        ax.text(mid_x, mid_y, f'{count}次\n({pct:.1f}%)',
                ha='center', va='center', fontsize=8.5,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                          edgecolor=COLORS_NATURE['panic'], linewidth=0.8))

    # 总数标注
    ax.text(0.5, 0.92, f'总传染事件 Total Contagion Events: {total}',
            ha='center', va='top', fontsize=10.5, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#FFF3E0',
                      edgecolor=COLORS_NATURE['panic'], linewidth=1.2))

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('auto')
    ax.axis('off')
    ax.set_title('情绪传染路径流量图 (下游 → 上游, 恐慌蔓延)',
                 fontsize=11, loc='center', pad=10)

    save_figure(fig, 'fig4_contagion_network',
                '图4 情绪传染网络流量图 (Exp_2, 2830次传染事件)',
                'Fig.4 Emotion contagion network flow (Exp_2, 2830 events)')


# ============================================================
# Fig.5 正向激励阻断效应 (恐慌vs中性过度订货比例)
# ============================================================
def plot_fig5_blocking_effect(attr_exp2, attr_exp1b):
    """正向激励阻断效应: 恐慌vs中性过度订货比例对比"""
    fig = plt.figure(figsize=(A4_PORTRAIT_W, 9.0))
    gs = gridspec.GridSpec(1, 1, left=0.12, right=0.95, top=0.90, bottom=0.14)
    ax = fig.add_subplot(gs[0])

    # Exp_2: 4节点 恐慌vs中性
    nodes = list(attr_exp2['overorder_analysis']['panic'].keys())
    panic_vals = [attr_exp2['overorder_analysis']['panic'][k] * 100 for k in nodes]
    neutral_vals = [attr_exp2['overorder_analysis']['neutral'][k] * 100 for k in nodes]

    # 计算阻断效应 (中性 - 恐慌): 正值表示阻断成功
    blocking = [n - p for n, p in zip(neutral_vals, panic_vals)]

    x = np.arange(4)
    width = 0.32

    # 分组柱状
    bars1 = ax.bar(x - width/2, panic_vals, width,
                   label='恐慌时过度订货比例 Over-ordering (Panic)',
                   color=COLORS_NATURE['panic'], edgecolor='black', linewidth=0.6)
    bars2 = ax.bar(x + width/2, neutral_vals, width,
                   label='中性时过度订货比例 Over-ordering (Neutral)',
                   color=COLORS_NATURE['neutral'], edgecolor='black', linewidth=0.6)

    # 标注数值
    for bars, vals in [(bars1, panic_vals), (bars2, neutral_vals)]:
        for bar, v in zip(bars, vals):
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 1.5,
                    f'{v:.2f}%', ha='center', va='bottom', fontsize=8.5)

    # 阻断效应箭头
    for i, blk in enumerate(blocking):
        if blk > 0:
            color = COLORS_NATURE['exp2']
            text = f'阻断 +{blk:.2f}pp'
        else:
            color = COLORS_NATURE['exp2a']
            text = f'反向 {blk:.2f}pp'
        # 箭头从恐慌柱顶指向中性柱顶
        ax.annotate('', xy=(x[i] + width/2, neutral_vals[i] - 3),
                    xytext=(x[i] - width/2, panic_vals[i] - 3),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.5))
        ax.text(x[i], max(panic_vals[i], neutral_vals[i]) + 10,
                text, ha='center', va='bottom', fontsize=8.5,
                color=color, fontweight='bold')

    # Exp_1b分销商对照 (水平参考线)
    exp1b_overorder = attr_exp1b['group_stats']['恐慌']['overorder_ratio'] * 100
    ax.axhline(y=exp1b_overorder, color=COLORS_NATURE['exp1b'],
               linestyle='--', linewidth=1.2, alpha=0.7,
               label=f'Exp_1b分销商恐慌过度订货={exp1b_overorder:.2f}% (无协同)')

    ax.set_xticks(x)
    ax.set_xticklabels(NODE_LABELS, fontsize=9.5)
    ax.set_ylabel('过度订货比例 (%)\nOver-ordering Ratio')
    ax.set_title('正向激励阻断效应: 恐慌 vs 中性状态', fontsize=11, loc='center')
    ax.legend(loc='upper right', fontsize=8.5)
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_ylim(0, max(max(panic_vals), max(neutral_vals)) * 1.30)

    save_figure(fig, 'fig5_blocking_effect',
                '图5 正向激励阻断效应 (恐慌vs中性过度订货比例对比)',
                'Fig.5 Positive incentive blocking effect (panic vs neutral over-ordering)')


# ============================================================
# Fig.6 持续学习鲁棒性 (EWC三组对比)
# ============================================================
def plot_fig6_continual_learning(continual):
    """持续学习实验: A/B/C三组 Task1→Task2 性能变化"""
    fig = plt.figure(figsize=(A4_PORTRAIT_W, 10.5))
    gs = gridspec.GridSpec(2, 2, hspace=0.40, wspace=0.32,
                           left=0.11, right=0.96, top=0.93, bottom=0.10)

    summary = continual['summary']
    forgetting = continual['forgetting']
    groups = ['A_无EWC无噪声', 'B_有EWC无噪声', 'C_有EWC有噪声']
    group_labels = ['A: 无EWC无噪声\nNo EWC, No Noise',
                    'B: 有EWC无噪声\nEWC, No Noise',
                    'C: 有EWC+噪声\nEWC + Noise']
    group_colors = [COLORS_NATURE['ewc_A'], COLORS_NATURE['ewc_B'], COLORS_NATURE['ewc_C']]

    x = np.arange(3)
    width = 0.30

    # (a) BWE 变化 (Task1训练后 vs Task2训练后)
    ax1 = fig.add_subplot(gs[0, 0])
    bwe_before = [summary['bwe_distributor'][g]['before'] for g in groups]
    bwe_after = [summary['bwe_distributor'][g]['after'] for g in groups]
    bars1 = ax1.bar(x - width/2, bwe_before, width, label='Task1训练后\nAfter Task1',
                    color=[c for c in group_colors], edgecolor='black', linewidth=0.5, alpha=0.6)
    bars2 = ax1.bar(x + width/2, bwe_after, width, label='Task2训练后\nAfter Task2',
                    color=group_colors, edgecolor='black', linewidth=0.5)
    for bars, vals in [(bars1, bwe_before), (bars2, bwe_after)]:
        for bar, v in zip(bars, vals):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15,
                     f'{v:.2f}', ha='center', va='bottom', fontsize=7.5)
    ax1.set_xticks(x)
    ax1.set_xticklabels([l.split('\n')[0] for l in group_labels], fontsize=8)
    ax1.set_ylabel('分销商BWE\nDistributor BWE')
    ax1.set_title('(a) BWE变化 (Task1 → Task2)', fontsize=9.5, loc='left')
    ax1.legend(loc='upper right', fontsize=7)
    ax1.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    # (b) Service Level
    ax2 = fig.add_subplot(gs[0, 1])
    sl_before = [summary['service_level'][g]['before'] * 100 for g in groups]
    sl_after = [summary['service_level'][g]['after'] * 100 for g in groups]
    bars1 = ax2.bar(x - width/2, sl_before, width, label='After Task1',
                    color=group_colors, edgecolor='black', linewidth=0.5, alpha=0.6)
    bars2 = ax2.bar(x + width/2, sl_after, width, label='After Task2',
                    color=group_colors, edgecolor='black', linewidth=0.5)
    for bars, vals in [(bars1, sl_before), (bars2, sl_after)]:
        for bar, v in zip(bars, vals):
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                     f'{v:.2f}%', ha='center', va='bottom', fontsize=7.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels([l.split('\n')[0] for l in group_labels], fontsize=8)
    ax2.set_ylabel('服务水平 SL (%)\nService Level')
    ax2.set_title('(b) SL变化 (Task1 → Task2)', fontsize=9.5, loc='left')
    ax2.legend(loc='lower left', fontsize=7)
    ax2.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax2.set_ylim(85, 95)

    # (c) Average Reward
    ax3 = fig.add_subplot(gs[1, 0])
    rw_before = [summary['avg_reward'][g]['before'] for g in groups]
    rw_after = [summary['avg_reward'][g]['after'] for g in groups]
    bars1 = ax3.bar(x - width/2, rw_before, width, label='After Task1',
                    color=group_colors, edgecolor='black', linewidth=0.5, alpha=0.6)
    bars2 = ax3.bar(x + width/2, rw_after, width, label='After Task2',
                    color=group_colors, edgecolor='black', linewidth=0.5)
    for bars, vals in [(bars1, rw_before), (bars2, rw_after)]:
        for bar, v in zip(bars, vals):
            ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                     f'{v:.3f}', ha='center', va='bottom', fontsize=7.5)
    ax3.set_xticks(x)
    ax3.set_xticklabels([l.split('\n')[0] for l in group_labels], fontsize=8)
    ax3.set_ylabel('平均奖励\nAverage Reward')
    ax3.set_title('(c) 平均奖励变化', fontsize=9.5, loc='left')
    ax3.legend(loc='upper left', fontsize=7)
    ax3.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    # (d) Fisher信息矩阵范数 (B vs C)
    ax4 = fig.add_subplot(gs[1, 1])
    ewc_stats = continual['ewc_stats']
    layers = ['W1', 'b1', 'W2', 'b2', 'W3', 'b3']
    fisher_B = [ewc_stats['B_有EWC无噪声']['fisher_norms'][L] for L in layers]
    fisher_C = [ewc_stats['C_有EWC有噪声']['fisher_norms'][L] for L in layers]
    x_l = np.arange(len(layers))
    bars1 = ax4.bar(x_l - width/2, fisher_B, width, label='B组 (无噪声)',
                    color=COLORS_NATURE['ewc_B'], edgecolor='black', linewidth=0.5)
    bars2 = ax4.bar(x_l + width/2, fisher_C, width, label='C组 (有噪声)',
                    color=COLORS_NATURE['ewc_C'], edgecolor='black', linewidth=0.5)
    for bars, vals in [(bars1, fisher_B), (bars2, fisher_C)]:
        for bar, v in zip(bars, vals):
            ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.02,
                     f'{v:.1f}', ha='center', va='bottom', fontsize=7, rotation=0)
    ax4.set_xticks(x_l)
    ax4.set_xticklabels(layers, fontsize=8.5)
    ax4.set_ylabel('Fisher范数 $\\|F_i\\|_2$\nFisher Norm')
    ax4.set_title('(d) Fisher信息矩阵参数重要性', fontsize=9.5, loc='left')
    ax4.legend(loc='upper right', fontsize=7.5)
    ax4.set_yscale('log')
    ax4.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5, which='both')

    save_figure(fig, 'fig6_continual_learning',
                '图6 持续学习鲁棒性 (EWC+PER 三组对比)',
                'Fig.6 Continual learning robustness (EWC + PER, 3 groups)')


# ============================================================
# 主函数
# ============================================================
def main():
    print('=' * 70)
    print('消融实验论文级配图生成')
    print('=' * 70)

    four_group, sub_ablation, attr_exp2, attr_exp1b, continual = load_all_data()
    print(f'  [数据加载] 4组主消融 + 4组子消融 + 归因 + 持续学习数据已加载')

    print('\n[1/6] 生成 Fig.1 四组主消融BWE对比 (4面板)...')
    plot_fig1_main_ablation_4panel(four_group)

    print('[2/6] 生成 Fig.2 剥离效应分解堆叠图...')
    plot_fig2_ablation_decomposition(four_group, sub_ablation)

    print('[3/6] 生成 Fig.3 情绪-决策归因分析 (4节点)...')
    plot_fig3_emotion_decision_attribution(attr_exp2, attr_exp1b)

    print('[4/6] 生成 Fig.4 情绪传染网络流量图...')
    plot_fig4_contagion_network(attr_exp2)

    print('[5/6] 生成 Fig.5 正向激励阻断效应...')
    plot_fig5_blocking_effect(attr_exp2, attr_exp1b)

    print('[6/6] 生成 Fig.6 持续学习鲁棒性...')
    plot_fig6_continual_learning(continual)

    print('\n' + '=' * 70)
    print(f'全部6张消融实验配图已生成至: {FIG_DIR}/')
    print('格式: PDF (矢量) + SVG (矢量), A4竖版, SCI顶刊配色')
    print('=' * 70)


if __name__ == '__main__':
    main()

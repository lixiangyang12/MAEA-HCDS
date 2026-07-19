"""
多智能体情绪感知供应链人智协同决策系统设计流程图 (v4 优化布局版)
====================================================================
改进：
  - 层标签移到层背景左侧外 (竖向旋转 90°, 不侵占中间图示)
  - 公式使用通用 Unicode 子集 (避免上标 ᵘᵖ 显示为方框)
  - 紧凑美观布局 (高度小于 A4, 比例协调)
  - 字号 16pt 保持
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib import rcParams

# ============================================================
# 字体与全局样式
# ============================================================
rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Times New Roman', 'SimHei', 'Microsoft YaHei', 'DejaVu Serif']
rcParams['axes.unicode_minus'] = False
rcParams['svg.fonttype'] = 'none'
rcParams['figure.dpi'] = 150
try:
    rcParams['fontfallback'] = True
except Exception:
    pass

# ============================================================
# SCI 顶刊配色方案 (深色系, 白色背景)
# ============================================================
COLOR_BG       = '#FFFFFF'
COLOR_LAYER1   = '#2C3E50'   # 深蓝灰
COLOR_LAYER2   = '#1A5276'   # 深蓝
COLOR_LAYER3   = '#7D3C98'   # 深紫
COLOR_LAYER4   = '#B7950B'   # 深金
COLOR_LAYER5   = '#1E8449'   # 深绿
COLOR_LAYER6   = '#922B21'   # 深红

NODE_COLORS = ['#2874A6', '#2E86C1', '#3498DB', '#5DADE2']
COLOR_ARROW  = '#566573'
COLOR_BORDER = '#212F3D'

# 字号
FONT_MAIN     = 16
FONT_NODE     = 14
FONT_LABEL    = 12
FONT_FORMULA  = 11
FONT_TITLE_CN = 16
FONT_TITLE_EN = 13


def draw_box(ax, x, y, w, h, facecolor, text, text_color='white',
             fontsize=FONT_NODE, fontweight='bold', alpha=0.9, edgecolor=None, lw=1.0):
    if edgecolor is None:
        edgecolor = facecolor
    box = FancyBboxPatch((x, y), w, h,
                         boxstyle="round,pad=0.02",
                         facecolor=facecolor, edgecolor=edgecolor,
                         linewidth=lw, alpha=alpha, transform=ax.transData)
    ax.add_patch(box)
    ax.text(x + w / 2, y + h / 2, text,
            ha='center', va='center',
            fontsize=fontsize, fontweight=fontweight,
            color=text_color, transform=ax.transData, zorder=5)


def draw_arrow(ax, x1, y1, x2, y2, color=COLOR_ARROW, style='->', lw=1.5):
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                            arrowstyle=style, color=color, linewidth=lw,
                            mutation_scale=14, transform=ax.transData)
    ax.add_patch(arrow)


def draw_double_arrow(ax, x1, y1, x2, y2, color=COLOR_LAYER4, lw=1.5):
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                            arrowstyle='<->', color=color, linewidth=lw,
                            mutation_scale=14, transform=ax.transData)
    ax.add_patch(arrow)


def draw_layer_band(ax, x, y, w, h, color, label_cn, label_en, alpha=0.06):
    """绘制层背景, 左侧外嵌入竖向标签 (中英文分开, 不在一行)"""
    bg = FancyBboxPatch((x, y), w, h,
                        boxstyle="round,pad=0.03",
                        facecolor=color, edgecolor=color,
                        linewidth=1.2, alpha=alpha, transform=ax.transData)
    ax.add_patch(bg)
    # 左侧外竖向标签 (旋转 90°, 中英文分两行显示)
    label_x = x - 0.25
    # 中文标签 (层中心偏上, 旋转 90° 后在竖直方向上部)
    ax.text(label_x, y + h * 0.65, label_cn,
            ha='center', va='center',
            fontsize=FONT_LABEL, fontweight='bold',
            color=color, alpha=0.9,
            transform=ax.transData, rotation=90, zorder=6)
    # 英文标签 (层中心偏下, 旋转 90° 后在竖直方向下部)
    ax.text(label_x, y + h * 0.35, label_en,
            ha='center', va='center',
            fontsize=9, fontstyle='italic',
            color=color, alpha=0.7,
            transform=ax.transData, rotation=90, zorder=6)


# ============================================================
# 主绘图函数
# ============================================================
def plot_system_architecture_a4():
    # 紧凑布局: 10 × 11.5 英寸
    fig, ax = plt.subplots(1, 1, figsize=(10, 11.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 11.5)
    ax.set_aspect('auto')
    ax.axis('off')
    fig.patch.set_facecolor(COLOR_BG)

    # ============================================================
    # 布局参数 (层背景左移留出标签空间)
    # ============================================================
    LAYER_X = 1.4          # 层背景起始x (左侧留 1.4 给竖向标签)
    LAYER_W = 8.3          # 层背景宽度 (到 9.7)
    NODE_X = [1.7, 3.5, 5.3, 7.1]  # 节点x坐标 (在层背景内)
    NODE_W = 1.5           # 节点宽度
    CONTENT_LEFT = 1.7     # 内容区起始 x
    CONTENT_RIGHT = 9.4    # 内容区结束 x

    # ============================================================
    # 层1: 环境输入层 (y: 10.3 - 11.2)
    # ============================================================
    layer1_y, layer1_h = 10.3, 0.9
    draw_layer_band(ax, LAYER_X, layer1_y, LAYER_W, layer1_h, COLOR_LAYER1,
                    '① 环境输入', 'Environment', alpha=0.07)

    # 三个内容框均匀分布在层背景内
    box_w = 2.4
    box_gap = (LAYER_W - 3 * box_w) / 4  # 间距
    box_y = layer1_y + 0.12
    box_h = 0.66
    box_positions = [LAYER_X + box_gap + i * (box_w + box_gap) for i in range(3)]

    draw_box(ax, box_positions[0], box_y, box_w, box_h, COLOR_LAYER1,
             'AR(1) 需求模型\nDₜ = d + ρ·Dₜ₋₁ + εₜ',
             fontsize=FONT_FORMULA, fontweight='bold')

    draw_box(ax, box_positions[1], box_y, box_w, box_h, COLOR_LAYER1,
             '需求突变事件\n(2× / 0.5×)',
             fontsize=FONT_FORMULA)

    draw_box(ax, box_positions[2], box_y, box_w, box_h, COLOR_LAYER1,
             '供应中断事件\n(3-5 周期)',
             fontsize=FONT_FORMULA)

    # 层1 → 层2 箭头
    for x_pos in [LAYER_X + LAYER_W / 2]:
        draw_arrow(ax, x_pos, layer1_y, x_pos, layer1_y - 0.05, COLOR_ARROW, lw=1.5)

    # ============================================================
    # 层2: 供应链节点层 (y: 8.8 - 10.2)
    # ============================================================
    layer2_y, layer2_h = 8.8, 1.4
    draw_layer_band(ax, LAYER_X, layer2_y, LAYER_W, layer2_h, COLOR_LAYER2,
                    '② 供应链节点', 'Supply Chain', alpha=0.07)

    node_info = [
        ('零售商\nRetailer\n(k=1)', NODE_COLORS[0]),
        ('批发商\nWholesaler\n(k=2)', NODE_COLORS[1]),
        ('分销商\nDistributor\n(k=3, IDMR)', NODE_COLORS[2]),
        ('制造商\nManufacturer\n(k=4)', NODE_COLORS[3]),
    ]
    node_y = layer2_y + 0.2
    node_h = 1.0

    for i, (label, color) in enumerate(node_info):
        edge = COLOR_BORDER if i == 2 else color
        lw_box = 2.5 if i == 2 else 1.0
        box = FancyBboxPatch((NODE_X[i], node_y), NODE_W, node_h,
                             boxstyle="round,pad=0.03",
                             facecolor=color, edgecolor=edge,
                             linewidth=lw_box, alpha=0.88)
        ax.add_patch(box)
        ax.text(NODE_X[i] + NODE_W / 2, node_y + node_h / 2,
                label, ha='center', va='center',
                fontsize=FONT_LABEL, fontweight='bold',
                color='white', zorder=5)

    # 节点间水平箭头
    for i in range(3):
        draw_arrow(ax, NODE_X[i] + NODE_W, node_y + node_h / 2,
                   NODE_X[i + 1], node_y + node_h / 2,
                   COLOR_ARROW, lw=1.2)

    # 顾客 → 零售商 (顾客在层背景外左侧)
    customer_x = LAYER_X - 0.6
    draw_arrow(ax, customer_x, node_y + node_h / 2,
               NODE_X[0], node_y + node_h / 2,
               COLOR_LAYER1, lw=1.5)
    ax.text(customer_x, node_y + node_h / 2 + 0.18, '顾客',
            ha='center', fontsize=FONT_LABEL, color=COLOR_LAYER1, fontweight='bold')
    ax.text(customer_x, node_y + node_h / 2 - 0.02, 'Customer',
            ha='center', fontsize=9, color=COLOR_LAYER1, fontstyle='italic')

    # 层2 → 层3
    for i in range(4):
        cx = NODE_X[i] + NODE_W / 2
        draw_arrow(ax, cx, node_y, cx, layer2_y - 0.05, COLOR_ARROW, lw=1.0)

    # ============================================================
    # 层3: 智能体决策层 (y: 6.3 - 8.7)
    # ============================================================
    layer3_y, layer3_h = 6.3, 2.4
    draw_layer_band(ax, LAYER_X, layer3_y, LAYER_W, layer3_h, COLOR_LAYER3,
                    '③ 智能体决策', 'Agent Layer', alpha=0.07)

    for i in range(4):
        color = NODE_COLORS[i]
        cx = NODE_X[i] + NODE_W / 2

        # DQN 智能体
        draw_box(ax, NODE_X[i], layer3_y + 1.75, NODE_W, 0.5, color,
                'DQN 智能体', fontsize=FONT_LABEL, alpha=0.88)

        # 情绪演化模块
        draw_box(ax, NODE_X[i], layer3_y + 1.10, NODE_W, 0.5, COLOR_LAYER3,
                '情绪演化 Eₜ ∈ [-1,1]',
                fontsize=FONT_FORMULA, alpha=0.78)

        # 正向激励函数
        draw_box(ax, NODE_X[i], layer3_y + 0.45, NODE_W, 0.5, COLOR_LAYER4,
                '正向激励\n(钟形奖励)',
                fontsize=FONT_LABEL, alpha=0.78)

        draw_arrow(ax, cx, layer3_y + 1.75, cx, layer3_y + 1.60, COLOR_ARROW, lw=0.8)
        draw_arrow(ax, cx, layer3_y + 1.10, cx, layer3_y + 0.95, COLOR_ARROW, lw=0.8)

    # 层3 → 层4
    for i in range(4):
        cx = NODE_X[i] + NODE_W / 2
        draw_arrow(ax, cx, layer3_y + 0.45, cx, layer3_y - 0.05, COLOR_ARROW, lw=1.0)

    # ============================================================
    # 层4: 协同通信层 (y: 5.1 - 6.2, 增加高度容纳公式在框内)
    # ============================================================
    layer4_y, layer4_h = 5.1, 1.1
    draw_layer_band(ax, LAYER_X, layer4_y, LAYER_W, layer4_h, COLOR_LAYER4,
                    '④ 协同通信', 'Coordination', alpha=0.07)

    # 通道框 (增大高度, 容纳标题和公式)
    collab_y = layer4_y + 0.15
    collab_h = 0.85
    channel = FancyBboxPatch((LAYER_X + 0.3, collab_y), LAYER_W - 0.6, collab_h,
                            boxstyle="round,pad=0.02",
                            facecolor=COLOR_LAYER4, edgecolor=COLOR_LAYER4,
                            linewidth=1.5, alpha=0.22)
    ax.add_patch(channel)

    # 通道标题 (框内上部)
    ax.text(LAYER_X + LAYER_W / 2, collab_y + collab_h * 0.72,
            '多智能体信息共享通道  Multi-Agent Information Sharing',
            ha='center', va='center',
            fontsize=FONT_LABEL, fontweight='bold',
            color=COLOR_LAYER4, zorder=5)

    # 情绪传染公式 (框内下部, 在通道标题下方)
    ax.text(LAYER_X + LAYER_W / 2, collab_y + collab_h * 0.28,
            '情绪传染: E_up,k ← E_up,k + η·(E_(k-1) − E_up,k),   η ~ Bernoulli(0.3)',
            ha='center', va='center',
            fontsize=10, fontstyle='italic', color=COLOR_LAYER4, zorder=5)

    for i in range(4):
        cx = NODE_X[i] + NODE_W / 2
        draw_double_arrow(ax, cx, layer3_y, cx, collab_y + collab_h, COLOR_LAYER4, lw=1.0)

    draw_arrow(ax, LAYER_X + LAYER_W / 2, collab_y, LAYER_X + LAYER_W / 2, layer4_y - 0.05,
               COLOR_ARROW, lw=1.5)

    # ============================================================
    # 层5: 持续学习层 (y: 3.5 - 4.9, 调整以适配层4新高度)
    # ============================================================
    layer5_y, layer5_h = 3.5, 1.4
    draw_layer_band(ax, LAYER_X, layer5_y, LAYER_W, layer5_h, COLOR_LAYER5,
                    '⑤ 持续学习', 'Continual Learning', alpha=0.07)

    cl_box_w = 2.4
    cl_box_gap = (LAYER_W - 3 * cl_box_w) / 4
    cl_box_y = layer5_y + 0.25
    cl_box_h = 1.0
    cl_positions = [LAYER_X + cl_box_gap + i * (cl_box_w + cl_box_gap) for i in range(3)]

    draw_box(ax, cl_positions[0], cl_box_y, cl_box_w, cl_box_h, COLOR_LAYER5,
             'EWC 弹性权重巩固\nElastic Weight\nConsolidation',
             fontsize=FONT_LABEL, alpha=0.88)

    draw_box(ax, cl_positions[1], cl_box_y, cl_box_w, cl_box_h, COLOR_LAYER5,
             'PER 优先经验回放\nPrioritized\nExperience Replay',
             fontsize=FONT_LABEL, alpha=0.88)

    draw_box(ax, cl_positions[2], cl_box_y, cl_box_w, cl_box_h, '#196F3D',
             '任务切换测试\nTask 1 → Task 2',
             fontsize=FONT_LABEL, alpha=0.85)

    draw_double_arrow(ax, cl_positions[0] + cl_box_w, cl_box_y + cl_box_h / 2,
                      cl_positions[1], cl_box_y + cl_box_h / 2, COLOR_LAYER5, lw=1.0)
    draw_arrow(ax, LAYER_X + LAYER_W / 2, cl_box_y, LAYER_X + LAYER_W / 2, layer5_y - 0.05,
               COLOR_ARROW, lw=1.5)

    # ============================================================
    # 层6: 评估输出层 (y: 1.9 - 3.3, 调整以适配层5新位置)
    # ============================================================
    layer6_y, layer6_h = 1.9, 1.4
    draw_layer_band(ax, LAYER_X, layer6_y, LAYER_W, layer6_h, COLOR_LAYER6,
                    '⑥ 评估输出', 'Evaluation', alpha=0.07)

    output_info = [
        ('BWE 方差比\nvar(qₖ)/var(D)', COLOR_LAYER6),
        ('SL 服务水平\nfulfilled/D', COLOR_LAYER6),
        ('平均成本\nh·NS + b·shortage', COLOR_LAYER6),
        ('情绪波动 σ_E\nstd(Eₜ)', COLOR_LAYER6),
    ]
    out_w = 1.8
    out_gap = (LAYER_W - 4 * out_w) / 5
    out_h = 0.85
    out_y = layer6_y + 0.25
    out_positions = [LAYER_X + out_gap + i * (out_w + out_gap) for i in range(4)]

    for i, (label, color) in enumerate(output_info):
        draw_box(ax, out_positions[i], out_y, out_w, out_h, color,
                label, fontsize=FONT_FORMULA, alpha=0.85)

    # ============================================================
    # 底部图例区 (y: 0.3 - 1.7, 调整以适配层6新位置)
    # ============================================================
    legend_y = 1.2
    # 三组对比实验
    ax.text(5.0, legend_y + 0.25,
            '三组对比实验:  Baseline (纯理性)   |   Exp_1 (单智能体 IDMR, k=3)   |   Exp_2 (多智能体 + 情绪 + 协同)',
            ha='center', va='center',
            fontsize=FONT_LABEL, color=COLOR_BORDER, fontweight='bold')

    # 人机协同三大机制 (横向排列)
    mech_y = legend_y - 0.15
    mechanisms = [
        ('① 传授经验', '理性决策作为参考', COLOR_LAYER2),
        ('② 限制决策', 'ε-greedy, 动作 ∈ [11, 40]', COLOR_LAYER3),
        ('③ 惩罚机制', '库存 > 5× 阈值则不订货', COLOR_LAYER4),
    ]
    mech_xs = [1.5, 5.0, 8.5]
    for (title, desc, color), mx in zip(mechanisms, mech_xs):
        ax.text(mx, mech_y, title,
                ha='center', va='center',
                fontsize=FONT_LABEL, fontweight='bold', color=color)
        ax.text(mx, mech_y - 0.28, desc,
                ha='center', va='center',
                fontsize=9, color='gray', fontstyle='italic')

    # 数据流图例
    ax.text(5.0, mech_y - 0.65,
            '数据流 →    |    协同通信 ↔    |    箭头方向表示信息传递路径',
            ha='center', va='center',
            fontsize=9, color='gray', fontstyle='italic')

    # ============================================================
    # 标题 (底部居中, 双语)
    # ============================================================
    fig.text(0.5, 0.015,
            '多智能体情绪感知供应链人智协同决策系统设计流程图',
            ha='center', va='bottom',
            fontsize=FONT_TITLE_CN, fontweight='bold',
            fontfamily='SimHei')
    fig.text(0.5, -0.005,
            'System Architecture of Multi-Agent Emotion-Aware Human-AI Collaborative Supply Chain',
            ha='center', va='top',
            fontsize=FONT_TITLE_EN, fontstyle='italic', color='gray',
            fontfamily='Times New Roman')

    plt.subplots_adjust(left=0.02, right=0.98, top=0.99, bottom=0.05)

    # 保存
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'svg_figures')
    os.makedirs(output_dir, exist_ok=True)
    svg_path = os.path.join(output_dir, 'system_architecture_flowchart.svg')
    plt.savefig(svg_path, format='svg', bbox_inches='tight',
               facecolor=COLOR_BG, edgecolor='none')
    plt.close()
    print(f"[OK] 优化布局版流程图已生成: {svg_path}")
    print(f"     大小: {os.path.getsize(svg_path) / 1024:.1f} KB")


if __name__ == '__main__':
    plot_system_architecture_a4()

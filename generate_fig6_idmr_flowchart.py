"""
图6 智慧决策机器人设计流程图 SVG 生成
======================================
基于李勇等(2022)论文《缓解牛鞭效应的新途径：人机协同的智慧决策机器人》
第3.2节人机协同机制，忠实复现图6的三个机制流程：
  1) 传授经验 - 决策"老师"将理论最优决策教授给智慧决策机器人
  2) 限制决策 - ε-greedy策略，以1-ε概率选择Q值最大行动
  3) 惩罚机制 - 库存积压超阈值时禁止订货

设计要求：
  - 真实：严格依据论文文字描述和核心算法表2
  - 美观：Nature/Science风格，色盲友好配色
  - 图名和标题在图下方
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle, Polygon
from matplotlib.patches import ConnectionPatch
import matplotlib.patheffects as pe
import numpy as np

# ============================================================
# 全局样式
# ============================================================
rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Times New Roman', 'SimHei', 'Microsoft YaHei', 'DejaVu Serif']
rcParams['axes.unicode_minus'] = False
rcParams['svg.fonttype'] = 'none'
rcParams['figure.dpi'] = 150
rcParams['font.size'] = 10
try:
    rcParams['fontfallback'] = True
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'svg_figures_basic')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Nature/Science 色盲友好配色
COLOR_INPUT = '#4E79A7'       # 蓝色 - 环境输入
COLOR_TEACHER = '#F28E2B'     # 橙色 - 决策"老师"（理性决策）
COLOR_STUDENT = '#E15759'     # 红色 - 智慧决策机器人
COLOR_MECH1 = '#76B7B2'       # 青色 - 机制1传授经验
COLOR_MECH2 = '#59A14F'       # 绿色 - 机制2限制决策
COLOR_MECH3 = '#EDC948'       # 黄色 - 机制3惩罚机制
COLOR_OUTPUT = '#B07AA1'      # 紫色 - 决策输出
COLOR_LEARN = '#FF9DA7'       # 粉色 - 学习更新
COLOR_ARROW = '#59595E'       # 深灰 - 箭头
COLOR_BG = '#FAFAFA'          # 浅灰背景


def draw_box(ax, x, y, w, h, text, facecolor, edgecolor=None, textcolor='white',
             fontsize=9, fontweight='bold', style='round', alpha=0.95):
    """绘制圆角矩形框"""
    if edgecolor is None:
        edgecolor = facecolor
    if style == 'round':
        box = FancyBboxPatch((x - w/2, y - h/2), w, h,
                              boxstyle="round,pad=0.02,rounding_size=0.08",
                              facecolor=facecolor, edgecolor=edgecolor,
                              linewidth=1.2, alpha=alpha, zorder=2)
    else:
        box = Rectangle((x - w/2, y - h/2), w, h,
                        facecolor=facecolor, edgecolor=edgecolor,
                        linewidth=1.2, alpha=alpha, zorder=2)
    ax.add_patch(box)
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize,
            color=textcolor, fontweight=fontweight, zorder=3,
            wrap=True)


def draw_arrow(ax, x1, y1, x2, y2, color=COLOR_ARROW, style='->', linewidth=1.2,
               connectionstyle='arc3,rad=0', alpha=0.8):
    """绘制箭头"""
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                            arrowstyle=style,
                            color=color, linewidth=linewidth,
                            connectionstyle=connectionstyle,
                            mutation_scale=15, alpha=alpha, zorder=1)
    ax.add_patch(arrow)


def draw_diamond(ax, x, y, w, h, text, facecolor, textcolor='white', fontsize=8):
    """绘制菱形（判断框）"""
    diamond = Polygon([(x, y+h/2), (x+w/2, y), (x, y-h/2), (x-w/2, y)],
                      facecolor=facecolor, edgecolor=facecolor,
                      linewidth=1.2, alpha=0.95, zorder=2)
    ax.add_patch(diamond)
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize,
            color=textcolor, fontweight='bold', zorder=3)


def draw_circle(ax, x, y, r, text, facecolor, textcolor='white', fontsize=8):
    """绘制圆形"""
    circle = Circle((x, y), r, facecolor=facecolor, edgecolor=facecolor,
                    linewidth=1.2, alpha=0.95, zorder=2)
    ax.add_patch(circle)
    ax.text(x, y, text, ha='center', va='center', fontsize=fontsize,
            color=textcolor, fontweight='bold', zorder=3)


# ============================================================
# 主图绘制
# ============================================================

def plot_fig6_idmr_flowchart():
    """图6 智慧决策机器人设计流程图"""
    print("\n[图6] 智慧决策机器人设计流程图...")

    fig, ax = plt.subplots(figsize=(14, 16))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 18)
    ax.set_aspect('equal')
    ax.axis('off')

    # ============================================================
    # 第0层：环境输入（顶部）
    # ============================================================
    y_env = 16.8
    draw_box(ax, 7, y_env, 8, 0.9,
             '环境输入  Environment Input\n周期 t，接收批发商订单 $q_{2t}$，观察状态 $s_t=(S^3_t, WIP^3_t, Trans^3_{t-1}, q^3_{t-1})$',
             COLOR_INPUT, fontsize=9)

    # ============================================================
    # 第1层：双决策并行（理性决策"老师" + 智慧决策机器人）
    # ============================================================
    y_dual = 15.2

    # 左：理性决策"老师"
    draw_box(ax, 3.5, y_dual, 5, 1.0,
             '决策"老师"（理性决策者）\nDecision "Teacher" (Rational Agent)\n理论最优决策 $q_t^{*}$（式4：SMA预测+OUT策略）',
             COLOR_TEACHER, fontsize=8.5)

    # 右：智慧决策机器人
    draw_box(ax, 10.5, y_dual, 5, 1.0,
             '智慧决策机器人 IDMR\nIntelligent Decision-Making Robot\n基于DQN，值函数 $Q(s,a;\\theta_i)$',
             COLOR_STUDENT, fontsize=8.5)

    # 环境输入到双决策的箭头
    draw_arrow(ax, 5, y_env - 0.45, 3.5, y_dual + 0.5, linewidth=1.3)
    draw_arrow(ax, 9, y_env - 0.45, 10.5, y_dual + 0.5, linewidth=1.3)

    # ============================================================
    # 第2层：三个机制（核心）
    # ============================================================
    y_mech_title = 13.8
    ax.text(7, y_mech_title, '人机协同机制  Human-AI Collaborative Mechanism',
            ha='center', va='center', fontsize=11, fontweight='bold',
            color='#333333',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#E8E8E8',
                      edgecolor='#999999', linewidth=0.8))

    # 三个机制的背景区域
    mech_bg = FancyBboxPatch((0.5, 9.5), 13, 4.0,
                              boxstyle="round,pad=0.05,rounding_size=0.1",
                              facecolor=COLOR_BG, edgecolor='#CCCCCC',
                              linewidth=0.8, alpha=0.5, linestyle='--', zorder=0)
    ax.add_patch(mech_bg)

    # ---- 机制1：传授经验（左） ----
    y_m1 = 12.5
    draw_box(ax, 2.5, y_m1, 3.6, 0.7,
             '机制1  传授经验\nMechanism 1: Experience Transfer',
             COLOR_MECH1, fontsize=8.5)

    # 传授经验内容
    draw_box(ax, 2.5, 11.3, 3.6, 1.4,
             '决策"老师"将理论最优决策 $q_t^{*}$\n教授给智慧决策机器人\n→ 融入学习环境\n→ 做出回报最大的决策',
             'white', edgecolor=COLOR_MECH1, textcolor='#333333',
             fontsize=7.5, fontweight='normal', alpha=0.95)

    # 老师→机制1→学生的箭头
    draw_arrow(ax, 3.5, y_dual - 0.5, 2.5, y_m1 + 0.35,
               color=COLOR_MECH1, linewidth=1.3)
    draw_arrow(ax, 2.5, 11.3 - 0.7, 8.7, y_dual - 0.5,
               color=COLOR_MECH1, linewidth=1.3,
               connectionstyle='arc3,rad=-0.2')

    # ---- 机制2：限制决策（中） ----
    draw_box(ax, 7, y_m1, 3.6, 0.7,
             '机制2  限制决策\nMechanism 2: Decision Constraint',
             COLOR_MECH2, fontsize=8.5)

    # 限制决策：ε-greedy 判断
    draw_diamond(ax, 7, 11.3, 2.0, 1.0,
                 '探索概率\nε-greedy',
                 COLOR_MECH2, fontsize=8)

    # 左分支：1-ε 概率
    draw_box(ax, 5.3, 10.2, 2.2, 0.7,
             '概率 $1-\\epsilon$\n$a_t=\\arg\\max_a Q(s,a;\\theta)$',
             'white', edgecolor=COLOR_MECH2, textcolor='#333333',
             fontsize=7.5, fontweight='normal')

    # 右分支：ε 概率
    draw_box(ax, 8.7, 10.2, 2.2, 0.7,
             '概率 $\\epsilon$\n随机探索 $a_t\\in[11,40]$',
             'white', edgecolor=COLOR_MECH2, textcolor='#333333',
             fontsize=7.5, fontweight='normal')

    # 菱形到两个分支的箭头
    draw_arrow(ax, 6.5, 10.9, 5.3, 10.55, color=COLOR_MECH2, linewidth=1.1)
    draw_arrow(ax, 7.5, 10.9, 8.7, 10.55, color=COLOR_MECH2, linewidth=1.1)

    # 标注 1-ε 和 ε
    ax.text(5.7, 11.0, '$1-\\epsilon$', fontsize=7, color=COLOR_MECH2,
            fontweight='bold', ha='center')
    ax.text(8.3, 11.0, '$\\epsilon$', fontsize=7, color=COLOR_MECH2,
            fontweight='bold', ha='center')

    # 学生→机制2的箭头
    draw_arrow(ax, 10.5, y_dual - 0.5, 7, y_m1 + 0.35,
               color=COLOR_MECH2, linewidth=1.3)

    # ---- 机制3：惩罚机制（右） ----
    draw_box(ax, 11.5, y_m1, 3.6, 0.7,
             '机制3  惩罚机制\nMechanism 3: Penalty Mechanism',
             COLOR_MECH3, fontsize=8.5, textcolor='#333333')

    # 惩罚机制：判断框
    draw_diamond(ax, 11.5, 11.3, 2.2, 1.0,
                 '库存积压\n$NS^3_t > \\overline{NS}^{classic}$?',
                 COLOR_MECH3, textcolor='#333333', fontsize=7.5)

    # 是：禁止订货
    draw_box(ax, 11.5, 10.2, 2.8, 0.7,
             '是 → 禁止订货 $a_t=0$\n决策"老师"施加严厉惩罚',
             '#FF6B6B', edgecolor='#CC4444', fontsize=7.5)

    # 否：允许订货
    draw_box(ax, 11.5, 9.3, 2.8, 0.55,
             '否 → 允许订货',
             'white', edgecolor=COLOR_MECH3, textcolor='#333333',
             fontsize=7.5, fontweight='normal')

    # 菱形到是/否的箭头
    draw_arrow(ax, 11.5, 10.8, 11.5, 10.55, color='#CC4444', linewidth=1.1)
    draw_arrow(ax, 11.5, 10.8, 11.5, 9.58, color=COLOR_MECH3, linewidth=1.1)

    ax.text(12.0, 10.7, '是', fontsize=7, color='#CC4444', fontweight='bold')
    ax.text(12.0, 10.15, '否', fontsize=7, color=COLOR_MECH3, fontweight='bold')

    # 学生→机制3的箭头
    draw_arrow(ax, 10.5, y_dual - 0.5, 11.5, y_m1 + 0.35,
               color=COLOR_MECH3, linewidth=1.3)

    # ============================================================
    # 第3层：决策输出
    # ============================================================
    y_out = 8.5
    draw_box(ax, 7, y_out, 7, 0.9,
             '智慧决策输出  Intelligent Decision Output\n$a_t$ → 向制造商订货，同时满足批发商当期需求',
             COLOR_OUTPUT, fontsize=9)

    # 三个机制汇聚到决策输出
    draw_arrow(ax, 2.5, 9.8, 5.5, y_out + 0.45, linewidth=1.2, alpha=0.6)
    draw_arrow(ax, 7, 9.8, 7, y_out + 0.45, linewidth=1.2, alpha=0.6)
    draw_arrow(ax, 11.5, 9.0, 8.5, y_out + 0.45, linewidth=1.2, alpha=0.6)

    # ============================================================
    # 第4层：环境反馈
    # ============================================================
    y_fb = 7.0
    draw_box(ax, 7, y_fb, 7, 0.8,
             '环境反馈  Environment Feedback\n获得当期收益 $r_t = \\frac{\\text{完全满足顾客需求次数}}{\\text{订货次数}}$（式11）',
             COLOR_INPUT, fontsize=8.5, alpha=0.9)

    draw_arrow(ax, 7, y_out - 0.45, 7, y_fb + 0.4, linewidth=1.3)

    # ============================================================
    # 第5层：经验池存储
    # ============================================================
    y_rep = 5.6
    draw_box(ax, 7, y_rep, 7, 0.8,
             '经验池存储  Experience Replay Buffer\n存储转移 $(s_t, a_t, r_t, s_{t+1})$ → 经验池 $E$',
             '#59595E', fontsize=8.5)

    draw_arrow(ax, 7, y_fb - 0.4, 7, y_rep + 0.4, linewidth=1.3)

    # ============================================================
    # 第6层：DQN训练
    # ============================================================
    y_dqn = 4.2
    draw_box(ax, 7, y_dqn, 8, 1.0,
             'DQN 值网络训练  Value Network Training\n小批量采样 $(s_j,a_j,r_j,s_{j+1})$，计算目标 $y_i=r_j+\\gamma\\max_{a\' }\\hat{Q}(s_{j+1},a\';\\theta_i^-)$\n损失函数 $f_i(\\theta_i)=\\mathbb{E}[(y_i-Q(s_j,a_j;\\theta_i))^2]$，随机梯度下降更新 $\\theta_i$',
             COLOR_LEARN, textcolor='#333333', fontsize=8)

    draw_arrow(ax, 7, y_rep - 0.4, 7, y_dqn + 0.5, linewidth=1.3)

    # ============================================================
    # 第7层：目标网络更新
    # ============================================================
    y_target = 2.8
    draw_box(ax, 7, y_target, 6, 0.7,
             '目标网络更新  Target Network Update\n每隔 N 步：$\\theta_i^- \\leftarrow \\theta_i$',
             '#59595E', fontsize=8.5)

    draw_arrow(ax, 7, y_dqn - 0.5, 7, y_target + 0.35, linewidth=1.3)

    # ============================================================
    # 第8层：循环回到顶部
    # ============================================================
    y_loop = 1.5
    draw_box(ax, 7, y_loop, 5, 0.6,
             '进入下一周期  $t \\leftarrow t+1$\nFor $t=1:T$ do',
             '#999999', fontsize=8.5)

    draw_arrow(ax, 7, y_target - 0.35, 7, y_loop + 0.3, linewidth=1.3)

    # 循环回到顶部的弧形箭头
    draw_arrow(ax, 9.5, y_loop, 13.5, y_loop, linewidth=1.2,
               connectionstyle='arc3,rad=0', alpha=0.6)
    draw_arrow(ax, 13.5, y_loop, 13.5, y_env, linewidth=1.2,
               connectionstyle='arc3,rad=0', alpha=0.6)
    draw_arrow(ax, 13.5, y_env, 11, y_env, linewidth=1.2,
               connectionstyle='arc3,rad=0', alpha=0.6)

    # 循环标注
    ax.text(13.7, 9, '循\n环\n反\n馈', ha='center', va='center',
            fontsize=8, color='#999999', fontweight='bold', rotation=0)

    # ============================================================
    # 左侧：核心要素说明
    # ============================================================
    ax.text(0.5, 15.5, 'DQN\n四要素', ha='center', va='center',
            fontsize=8, fontweight='bold', color='#333333',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#FFF3CD',
                      edgecolor='#FFCC00', linewidth=0.8))

    elements = ['① 策略 Policy', '② 奖惩反馈 Reward', '③ 值函数 Value Func', '④ 环境 Environment']
    for i, e in enumerate(elements):
        ax.text(0.5, 14.8 - i*0.4, e, ha='center', va='center',
                fontsize=7, color='#333333',
                bbox=dict(boxstyle='round,pad=0.15', facecolor='#FFFBF0',
                          edgecolor='#FFCC00', linewidth=0.5))

    # ============================================================
    # 右侧：角色说明
    # ============================================================
    ax.text(13.5, 15.5, '角色\n分工', ha='center', va='center',
            fontsize=8, fontweight='bold', color='#333333',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='#E8F4FD',
                      edgecolor='#4E79A7', linewidth=0.8))

    roles = ['教师 Teacher\n理性决策', '学生 Student\n智慧决策机器人']
    for i, r in enumerate(roles):
        color_bg = '#FFF0E6' if i == 0 else '#FFE6E6'
        color_edge = COLOR_TEACHER if i == 0 else COLOR_STUDENT
        ax.text(13.5, 14.8 - i*0.5, r, ha='center', va='center',
                fontsize=7, color='#333333',
                bbox=dict(boxstyle='round,pad=0.15', facecolor=color_bg,
                          edgecolor=color_edge, linewidth=0.5))

    # ============================================================
    # 图名和标题在图下方
    # ============================================================
    fig.text(0.5, 0.02,
             '图6  智慧决策机器人设计流程图',
             ha='center', va='bottom', fontsize=14, fontweight='bold',
             fontfamily='SimHei')
    fig.text(0.5, 0.005,
             'Fig.6  Design Flowchart of Intelligent Decision-Making Robot',
             ha='center', va='bottom', fontsize=11, fontstyle='italic',
             color='gray')

    # 数据来源说明
    fig.text(0.5, -0.01,
             '依据：李勇等(2022)《缓解牛鞭效应的新途径：人机协同的智慧决策机器人》第3.2节  '
             '机制：传授经验(式4) + 限制决策(式10, ε-greedy) + 惩罚机制(库存阈值)',
             ha='center', va='top', fontsize=7.5, color='#7F8C8D')

    fig.tight_layout(rect=[0, 0.04, 1, 1])
    path = os.path.join(OUTPUT_DIR, 'fig6_idmr_design_flowchart.svg')
    fig.savefig(path, format='svg', bbox_inches='tight')
    plt.close(fig)
    print(f"  [saved] {path}")
    return path


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 70)
    print("图6 智慧决策机器人设计流程图 SVG 生成")
    print("依据：李勇等(2022)论文第3.2节人机协同机制")
    print("=" * 70)

    plot_fig6_idmr_flowchart()

    print("\n" + "=" * 70)
    print("图6 SVG 生成完成！")
    print("输出目录: %s" % OUTPUT_DIR)
    print("=" * 70)


if __name__ == '__main__':
    main()

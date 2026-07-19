# -*- coding: utf-8 -*-
"""
MAEA-HCDS 系统机制图生成器
==========================
多智能体情绪感知人智协同决策系统机制图

四层架构 (递进因果链: 情绪扰动 → 激励阻断 → 协同鲁棒):
  Layer 1: 行为感知层 (Behavior Perception)
    - Schweitzer & Cachon [17], Gino & Pisano [18] (行为运营管理)
    - Picard [19], Poria [20] (情感计算)
    - Kahneman & Tversky [21] (前景理论/损失厌恶)
    - Ortony [22] (OCC情绪评价框架)

  Layer 2: 智能决策层 (Intelligent Decision)
    - DQN [11] (基础学习器)
    - Schaul [23] (优先经验回放 PER)

  Layer 3: 多体协同层 (Multi-Agent Coordination)
    - CTDE [12] (集中训练分散执行)
    - QMIX [13] (单调性保证)

  Layer 4: 持续适应层 (Continual Adaptation)
    - EWC [16] (弹性权重巩固)

输出格式: A4纵向, PDF + SVG + PNG, SCI顶刊配色, 中英双语
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D

# ============================================================
# 全局样式: SCI顶刊标准
# ============================================================
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['svg.fonttype'] = 'none'      # text stays as <text>
plt.rcParams['pdf.fonttype'] = 42          # TrueType, editable
plt.rcParams['axes.linewidth'] = 0.8

# A4纵向尺寸 (inches)
A4_W = 8.27
A4_H = 11.69

# SCI顶刊配色 (Nature/Science柔和低饱和 + 4层信号色)
LAYER_COLORS = {
    'perception':  '#4C72B0',  # 柔和蓝 - 行为感知
    'decision':    '#DD8452',  # 柔和橙 - 智能决策
    'coordination':'#55A868',  # 柔和绿 - 多体协同
    'adaptation':  '#8172B3',  # 柔和紫 - 持续适应
}
LAYER_BG = {
    'perception':  '#E8EFF7',  # 浅蓝背景
    'decision':    '#FBEFE5',  # 浅橙背景
    'coordination':'#E8F3EC',  # 浅绿背景
    'adaptation':  '#EFEAF5',  # 浅紫背景
}

# ============================================================
# 机制图绘制
# ============================================================

def draw_mechanism_figure(output_dir='svg_figures_mechanism'):
    """绘制MAEA-HCDS系统机制图"""

    os.makedirs(output_dir, exist_ok=True)

    fig = plt.figure(figsize=(A4_W, A4_H), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4_W)
    ax.set_ylim(0, A4_H)
    ax.axis('off')

    # --------------------------------------------------------
    # 顶部标题
    # --------------------------------------------------------
    title_y = A4_H - 0.55
    ax.text(A4_W / 2, title_y,
            '图1  多智能体情绪感知人智协同决策系统机制图',
            ha='center', va='center',
            fontsize=14, fontweight='bold', color='#222222')
    ax.text(A4_W / 2, title_y - 0.30,
            'Fig.1  Mechanism of Multi-Agent Emotion-Aware Human-AI Collaborative Decision System',
            ha='center', va='center',
            fontsize=9.5, color='#555555', style='italic')

    # --------------------------------------------------------
    # 4层主区块参数
    # --------------------------------------------------------
    # 布局: 顶部留0.95标题, 底部留1.5图注, 中间4层
    top_margin = 1.05
    bottom_margin = 1.55
    layer_gap = 0.18  # 层间箭头空间
    available_h = A4_H - top_margin - bottom_margin
    layer_h = (available_h - 3 * layer_gap) / 4  # 每层高度

    left_pad = 0.30
    right_pad = 0.30
    block_w = A4_W - left_pad - right_pad

    # 每层3列布局: 层名 | 机制描述 | 文献引用
    col_layer  = 1.35   # 左列宽 (层名)
    col_ref    = 1.45   # 右列宽 (文献)
    col_mid    = block_w - col_layer - col_ref - 0.4  # 中列宽 (机制)

    # 4层定义 (从上到下: 感知→决策→协同→适应)
    layers = [
        {
            'key': 'perception',
            'layer_num': 'Layer 1',
            'title_zh': '行为感知层',
            'title_en': 'Behavior Perception',
            'role': '理论整合与情绪量化',
            'mechanisms': [
                ('行为运营管理理论', 'Schweitzer & Cachon [17]; Gino & Pisano [18]'),
                ('情感计算方法',     'Picard [19]; Poria et al. [20]'),
                ('前景理论(损失厌恶)', 'Kahneman & Tversky [21]'),
                ('OCC情绪评价框架',  'Ortony et al. [22]'),
            ],
            'output': '可计算决策参数: 情绪状态 $E_t \\in [-1, 1]$',
            'refs': '[17][18]\n[19][20]\n[21][22]',
        },
        {
            'key': 'decision',
            'layer_num': 'Layer 2',
            'title_zh': '智能决策层',
            'title_en': 'Intelligent Decision',
            'role': '基础学习器与样本效率',
            'mechanisms': [
                ('深度Q网络 (DQN)',   '基础学习器, 状态-动作值函数逼近'),
                ('优先经验回放 (PER)', 'Schaul et al. [23], 提升样本效率'),
                ('ε-greedy探索',      'ε: 1.0 → 0.01 线性衰减'),
                ('目标网络软更新',    '每10步同步, 稳定训练'),
            ],
            'output': '策略: 兼顾效率与行为兼容性的"按需订货"',
            'refs': '[11]\n[23]',
        },
        {
            'key': 'coordination',
            'layer_num': 'Layer 3',
            'title_zh': '多体协同层',
            'title_en': 'Multi-Agent Coordination',
            'role': '信息共享与策略单调性',
            'mechanisms': [
                ('CTDE范式',          '集中训练分散执行 [12]'),
                ('信息共享通道',       '订单流与情绪状态实时耦合传递'),
                ('QMIX值分解',        '保证协同策略单调性 [13]'),
                ('情绪传染机制',       '恐慌以30%概率向上游蔓延'),
            ],
            'output': '协同策略: 上游提前感知下游需求突变',
            'refs': '[12]\n[13]',
        },
        {
            'key': 'adaptation',
            'layer_num': 'Layer 4',
            'title_zh': '持续适应层',
            'title_en': 'Continual Adaptation',
            'role': '灾难性遗忘抑制',
            'mechanisms': [
                ('弹性权重巩固 (EWC)', 'Kirkpatrick et al. [16]'),
                ('Fisher信息正则',     '$L_{ewc} = \\frac{1}{2}\\lambda \\sum_i F_i (\\theta_i - \\theta_i^*)^2$'),
                ('任务切换适应',       '需求模式漂移 / 人员更替'),
                ('长期决策稳健性',     '维持旧任务知识 + 学习新任务'),
            ],
            'output': '稳健性: 模式漂移下避免知识遗忘',
            'refs': '[16]',
        },
    ]

    # --------------------------------------------------------
    # 绘制4层主区块
    # --------------------------------------------------------
    layer_y_positions = []  # 记录每层中心y, 用于箭头连接

    for i, layer in enumerate(layers):
        # 从上往下: 第0层在最上方
        y_top = A4_H - top_margin - i * (layer_h + layer_gap)
        y_bot = y_top - layer_h
        layer_y_positions.append((y_top, y_bot))

        color_main = LAYER_COLORS[layer['key']]
        color_bg = LAYER_BG[layer['key']]

        # 主区块背景 (圆角矩形)
        bg_box = FancyBboxPatch(
            (left_pad, y_bot), block_w, layer_h,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            linewidth=1.4, edgecolor=color_main, facecolor=color_bg,
            zorder=2
        )
        ax.add_patch(bg_box)

        # 左侧色条 (强调层主色)
        bar_w = 0.10
        bar = Rectangle((left_pad, y_bot), bar_w, layer_h,
                        linewidth=0, facecolor=color_main, zorder=3)
        ax.add_patch(bar)

        # ---- 左列: 层名 ----
        lx = left_pad + bar_w + 0.15
        col_layer_x = lx + col_layer / 2

        ax.text(col_layer_x, y_top - 0.22,
                layer['layer_num'],
                ha='center', va='center',
                fontsize=8.5, color='#666666', style='italic')

        ax.text(col_layer_x, y_top - 0.48,
                layer['title_zh'],
                ha='center', va='center',
                fontsize=13, fontweight='bold', color=color_main)

        ax.text(col_layer_x, y_top - 0.72,
                layer['title_en'],
                ha='center', va='center',
                fontsize=8.5, color='#555555', style='italic')

        ax.text(col_layer_x, y_top - 0.95,
                layer['role'],
                ha='center', va='center',
                fontsize=8, color='#444444',
                bbox=dict(boxstyle='round,pad=0.25',
                          facecolor='white', edgecolor=color_main,
                          linewidth=0.6))

        # 左列与中列之间的分隔线
        sep_x1 = left_pad + bar_w + 0.15 + col_layer + 0.10
        ax.plot([sep_x1, sep_x1], [y_bot + 0.15, y_top - 0.15],
                color=color_main, linewidth=0.5, alpha=0.5, zorder=4)

        # ---- 中列: 机制描述 ----
        mid_x = sep_x1 + 0.15
        mid_w = col_mid - 0.30

        # 4个机制条目
        n_mech = len(layer['mechanisms'])
        mech_top = y_top - 0.18
        mech_h = (layer_h - 0.55) / n_mech

        for j, (mech_name, mech_desc) in enumerate(layer['mechanisms']):
            my_top = mech_top - j * mech_h
            my_center = my_top - mech_h / 2

            # 机制条目背景
            mech_box = FancyBboxPatch(
                (mid_x, my_center - mech_h / 2 + 0.04), mid_w, mech_h - 0.08,
                boxstyle="round,pad=0.01,rounding_size=0.04",
                linewidth=0.5, edgecolor=color_main, facecolor='white',
                alpha=0.85, zorder=4
            )
            ax.add_patch(mech_box)

            # 机制名称 (左侧加粗)
            ax.text(mid_x + 0.12, my_center + 0.05,
                    mech_name,
                    ha='left', va='center',
                    fontsize=9.5, fontweight='bold', color='#222222')

            # 机制描述 (右侧小字)
            ax.text(mid_x + 0.12, my_center - 0.13,
                    mech_desc,
                    ha='left', va='center',
                    fontsize=8.2, color='#555555')

        # ---- 右列: 输出 + 文献引用 ----
        sep_x2 = mid_x + mid_w + 0.10
        col_ref_x = sep_x2 + col_ref / 2

        # 右列与中列分隔线
        ax.plot([sep_x2, sep_x2], [y_bot + 0.15, y_top - 0.15],
                color=color_main, linewidth=0.5, alpha=0.5, zorder=4)

        # 输出标签 (顶部)
        output_y = y_top - 0.32
        ax.text(col_ref_x, output_y,
                '层输出',
                ha='center', va='center',
                fontsize=8, color='#666666', style='italic')

        ax.text(col_ref_x, output_y - 0.32,
                layer['output'],
                ha='center', va='center',
                fontsize=8.2, color=color_main, fontweight='bold',
                wrap=True)

        # 文献引用框 (底部)
        ref_y = y_bot + 0.30
        ref_box = FancyBboxPatch(
            (sep_x2 + 0.10, ref_y - 0.18), col_ref - 0.20, 0.50,
            boxstyle="round,pad=0.01,rounding_size=0.04",
            linewidth=0.6, edgecolor=color_main, facecolor='white',
            zorder=4
        )
        ax.add_patch(ref_box)

        ax.text(col_ref_x, ref_y + 0.07,
                '理论依据',
                ha='center', va='center',
                fontsize=7.5, color='#666666', style='italic')

        ax.text(col_ref_x, ref_y - 0.10,
                layer['refs'],
                ha='center', va='center',
                fontsize=9, fontweight='bold', color=color_main)

    # --------------------------------------------------------
    # 层间连接箭头 (向下流动)
    # --------------------------------------------------------
    arrow_x = A4_W / 2
    for i in range(3):
        y_arrow_top = layer_y_positions[i][1]    # 上层底部
        y_arrow_bot = layer_y_positions[i + 1][0]  # 下层顶部

        # 主箭头 (粗)
        arrow = FancyArrowPatch(
            (arrow_x, y_arrow_top - 0.01),
            (arrow_x, y_arrow_bot + 0.01),
            arrowstyle='->,head_width=0.25,head_length=0.18',
            color='#333333', linewidth=1.8, zorder=5
        )
        ax.add_patch(arrow)

        # 箭头标签 (信号流说明)
        flow_labels = [
            '情绪状态 $E_t$',
            '策略 $\\pi(a|s)$',
            '协同动作 $\\mathbf{a}$',
        ]
        ax.text(arrow_x + 0.20, (y_arrow_top + y_arrow_bot) / 2,
                flow_labels[i],
                ha='left', va='center',
                fontsize=8, color='#333333', style='italic',
                bbox=dict(boxstyle='round,pad=0.20',
                          facecolor='white', edgecolor='#999999',
                          linewidth=0.5))

    # --------------------------------------------------------
    # 右侧递进因果链标识
    # --------------------------------------------------------
    causal_x = A4_W - 0.18
    causal_labels = [
        ('情绪扰动',  'Emotional\nDisturbance',  '#C44E52'),
        ('激励阻断',  'Incentive\nBlockage',     '#DD8452'),
        ('协同鲁棒',  'Collaborative\nRobustness','#55A868'),
        ('持续稳健',  'Continual\nRobustness',   '#4C72B0'),
    ]

    # 因果链整体框 (从Layer 2右侧延伸到Layer 4)
    # 这里改为: 在最右侧加一个垂直的因果链侧栏
    side_x = A4_W - 0.13
    side_top = layer_y_positions[1][0]  # Layer 2顶部
    side_bot = layer_y_positions[3][1]  # Layer 4底部

    # 实际上, 因果链与层对应关系:
    # 行为感知层 → 情绪扰动 (问题诊断)
    # 智能决策层 → 激励阻断 (机制设计)
    # 多体协同层 → 协同鲁棒 (核心贡献)
    # 持续适应层 → 持续稳健 (鲁棒性延伸)

    # 在每层右侧添加因果链标签
    for i, (label_zh, label_en, color) in enumerate(causal_labels):
        y_layer_top = layer_y_positions[i][0]
        y_layer_bot = layer_y_positions[i][1]
        y_center = (y_layer_top + y_layer_bot) / 2

        # 因果链标签 (放在右图边外)
        ax.text(A4_W - 0.10, y_center,
                label_zh,
                ha='right', va='center',
                fontsize=9, fontweight='bold', color=color,
                rotation=90,
                bbox=dict(boxstyle='round,pad=0.18',
                          facecolor='white', edgecolor=color,
                          linewidth=0.8))

    # 因果链向下箭头 (3个, 连接4个因果链标签)
    chain_x = A4_W - 0.10
    for i in range(3):
        y_top_chain = layer_y_positions[i][1] - 0.08
        y_bot_chain = layer_y_positions[i + 1][0] + 0.08
        chain_color = causal_labels[i][2]
        chain_arrow = FancyArrowPatch(
            (chain_x, y_top_chain),
            (chain_x, y_bot_chain),
            arrowstyle='->,head_width=0.15,head_length=0.10',
            color=chain_color, linewidth=1.2, zorder=6,
            alpha=0.85
        )
        ax.add_patch(chain_arrow)

    # --------------------------------------------------------
    # 底部图注
    # --------------------------------------------------------
    note_y = 0.85
    ax.text(left_pad + 0.10, note_y,
            '注: MAEA-HCDS遵循"情绪扰动→激励阻断→协同鲁棒→持续稳健"递进因果链。'
            '行为感知层将前景理论与OCC框架转化为可计算情绪状态$E_t$；',
            ha='left', va='center',
            fontsize=8.5, color='#333333')

    ax.text(left_pad + 0.10, note_y - 0.22,
            '智能决策层通过DQN+PER习得"按需订货"策略; 多体协同层基于CTDE+QMIX实现上下游信息共享;',
            ha='left', va='center',
            fontsize=8.5, color='#333333')

    ax.text(left_pad + 0.10, note_y - 0.44,
            '持续适应层引入EWC抑制灾难性遗忘。各层文献引用对应正文参考文献编号。',
            ha='left', va='center',
            fontsize=8.5, color='#333333')

    # 英文图注
    ax.text(left_pad + 0.10, note_y - 0.70,
            'Note: MAEA-HCDS follows the progressive causal chain of "Emotional Disturbance → '
            'Incentive Blockage → Collaborative Robustness → Continual Robustness".',
            ha='left', va='center',
            fontsize=7.8, color='#555555', style='italic')

    ax.text(left_pad + 0.10, note_y - 0.88,
            'Behavior Perception converts prospect theory and OCC framework into computable '
            'emotion state $E_t$; Intelligent Decision learns "on-demand ordering" via DQN+PER;',
            ha='left', va='center',
            fontsize=7.8, color='#555555', style='italic')

    ax.text(left_pad + 0.10, note_y - 1.06,
            'Multi-Agent Coordination enables upstream-downstream information sharing via '
            'CTDE+QMIX; Continual Adaptation suppresses catastrophic forgetting via EWC.',
            ha='left', va='center',
            fontsize=7.8, color='#555555', style='italic')

    # --------------------------------------------------------
    # 顶部右上角标注 (系统名称)
    # --------------------------------------------------------
    ax.text(A4_W - 0.10, A4_H - 0.20,
            'MAEA-HCDS',
            ha='right', va='center',
            fontsize=10, fontweight='bold', color='#222222',
            bbox=dict(boxstyle='round,pad=0.30',
                      facecolor='white', edgecolor='#222222',
                      linewidth=1.0))

    # --------------------------------------------------------
    # 保存: PDF + SVG + PNG
    # --------------------------------------------------------
    base = os.path.join(output_dir, 'Fig1_MAEA_HCDS_Mechanism')
    fig.savefig(f'{base}.pdf', bbox_inches='tight', dpi=300)
    fig.savefig(f'{base}.svg', bbox_inches='tight', dpi=300)
    fig.savefig(f'{base}.png', bbox_inches='tight', dpi=300)

    plt.close(fig)
    print(f'[OK] Saved: {base}.pdf / .svg / .png')
    return base


if __name__ == '__main__':
    out_dir = r'c:\个人资料\申博材料\企业运营与科研管理数据库\svg_figures_mechanism'
    base = draw_mechanism_figure(output_dir=out_dir)
    print('\n=== Mechanism figure generation complete ===')
    print(f'Output directory: {out_dir}')

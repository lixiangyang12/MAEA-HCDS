"""
图15-17 SVG 图表生成脚本
=========================
基于 Exp_2 人智协同实验 20000 周期真实时序数据生成：
  图15: 方差比(BWE)随周期变化图（2组：20000周期+最后500周期）
  图16: 各节点平均成本随20000周期变化图
  图17: 供应链各级服务水平图（2组：20000周期+最后500周期）

要求：
  - 图名和标题都在图下方
  - 横轴间隔：20000周期用2500，500周期用100
  - 给出各节点平均值数值
  - 全部基于实验数据，不得作假

数据来源: p0_results/exp2_20k_timeseries.json
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

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

NODE_CN = ['零售商', '批发商', '分销商', '制造商']
NODE_EN = ['Retailer', 'Wholesaler', 'Distributor', 'Manufacturer']
COLOR_TS = ['#4E79A7', '#F28E2B', '#E15759', '#76B7B2']

# 验证数据来源
DATA_PATH = os.path.join(BASE_DIR, 'p0_results', 'exp2_20k_timeseries.json')


def load_data():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_svg(fig, name):
    path = os.path.join(OUTPUT_DIR, name)
    fig.savefig(path, format='svg', bbox_inches='tight')
    plt.close(fig)
    print(f"  [saved] {path}")
    return path


def compute_sliding_bwe(orders, demands, window=200):
    """滑动窗口 BWE = Var(q_k) / Var(D_retailer)"""
    T = len(orders)
    bwe = np.zeros(T)
    for t in range(window, T):
        w_o = orders[t-window:t]
        w_d = demands[t-window:t]
        vq = np.var(w_o)
        vd = np.var(w_d)
        bwe[t] = vq / vd if vd > 0 else 0.0
    return bwe


# ============================================================
# 图15: 方差比(BWE)随周期变化图
# ============================================================

def plot_fig15_bwe(data):
    """图15 多智能体人智协同实验下的方差比随周期变化图"""
    print("\n[图15] 方差比随周期变化图...")

    T = 20000
    demands = np.array(data['demand_history'])
    window = 200

    # 计算各节点滑动窗口BWE和全周期BWE
    bwe_data = {}
    bwe_full = {}
    for k_idx, k in enumerate(['1', '2', '3', '4']):
        orders = np.array(data['order_history'][k])
        bwe_data[k] = compute_sliding_bwe(orders, demands, window)
        bwe_full[k] = np.var(orders) / np.var(demands) if np.var(demands) > 0 else 0

    # 2行×4列：上行20000周期，下行最后500周期
    fig, axes = plt.subplots(2, 4, figsize=(18, 8))

    # ---- 上行：20000周期，横轴间隔2500 ----
    step = 20  # 采样显示
    x_full = np.arange(0, T, step)
    xticks_full = np.arange(0, 22500, 2500)

    for k_idx, k in enumerate(['1', '2', '3', '4']):
        ax = axes[0, k_idx]
        bwe_ts = bwe_data[k][::step]
        ax.plot(x_full, bwe_ts, color=COLOR_TS[k_idx], linewidth=0.8, alpha=0.75)
        # 平滑线（移动平均）
        if len(bwe_ts) > 50:
            smooth = np.convolve(bwe_ts, np.ones(50)/50, mode='valid')
            ax.plot(x_full[49:49+len(smooth)], smooth, color=COLOR_TS[k_idx],
                    linewidth=1.5, alpha=0.9)

        # 标注全周期BWE均值
        avg_bwe = bwe_full[k]
        ax.axhline(y=avg_bwe, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax.text(T*0.02, avg_bwe + 0.5, '均值=%.2f' % avg_bwe,
                fontsize=8, color='gray', fontweight='bold')

        ax.set_xticks(xticks_full)
        ax.set_xlim(0, T)
        ax.set_xlabel('订货周期 / Period', fontsize=9)
        ax.set_ylabel('BWE (滑动窗口=200)', fontsize=9)
        # 子图标识在下方
        ax.text(0.5, -0.22, '(%s) %s  BWE=%.2f' % (chr(97+k_idx), NODE_CN[k_idx], avg_bwe),
                transform=ax.transAxes, ha='center', va='top', fontsize=9,
                fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    # ---- 下行：最后500周期，横轴间隔100 ----
    last_n = 500
    x_last = np.arange(T - last_n, T)
    xticks_last = np.arange(T - last_n, T + 50, 100)

    for k_idx, k in enumerate(['1', '2', '3', '4']):
        ax = axes[1, k_idx]
        bwe_ts = bwe_data[k][T-last_n:T]
        ax.plot(x_last, bwe_ts, color=COLOR_TS[k_idx], linewidth=1.0, alpha=0.8)

        # 标注最后500周期BWE均值
        avg_bwe_last = np.mean(bwe_ts)
        ax.axhline(y=avg_bwe_last, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax.text(T - last_n + 10, avg_bwe_last + 0.5, '500周期均值=%.2f' % avg_bwe_last,
                fontsize=8, color='gray', fontweight='bold')

        ax.set_xticks(xticks_last)
        ax.set_xlim(T - last_n, T)
        ax.set_xlabel('订货周期 / Period', fontsize=9)
        ax.set_ylabel('BWE', fontsize=9)
        # 子图标识在下方
        ax.text(0.5, -0.22, '(%s) %s  500周期均值=%.2f' % (chr(101+k_idx), NODE_CN[k_idx], avg_bwe_last),
                transform=ax.transAxes, ha='center', va='top', fontsize=9,
                fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    # 图名和标题在图下方
    fig.text(0.5, 0.01,
             '图15  多智能体人智协同实验下的方差比随周期变化图',
             ha='center', va='bottom', fontsize=13, fontweight='bold', fontfamily='SimHei')
    fig.text(0.5, -0.02,
             'Fig.15  Bullwhip Effect Ratio over Periods under Multi-Agent Human-AI Collaborative Experiment',
             ha='center', va='top', fontsize=10, fontstyle='italic', color='gray')
    fig.text(0.5, -0.04,
             '上排：20000周期（横轴间隔2500）  下排：最后500周期（横轴间隔100）  数据来源：exp2_20k_timeseries.json',
             ha='center', va='top', fontsize=8, color='#7F8C8D')

    fig.tight_layout(rect=[0, 0.06, 1, 1])
    return save_svg(fig, 'fig15_bwe_over_periods.svg')


# ============================================================
# 图16: 各节点平均成本随20000周期变化
# ============================================================

def plot_fig16_cost(data):
    """图16 多智能体人智协同实验下的各节点随20000个周期变化的平均成本"""
    print("\n[图16] 各节点平均成本随周期变化图...")

    T = 20000
    step = 20
    x = np.arange(0, T, step)
    xticks = np.arange(0, 22500, 2500)

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))

    for k_idx, k in enumerate(['1', '2', '3', '4']):
        ax = axes[k_idx // 2, k_idx % 2]
        costs = np.array(data['cost_history'][k])

        # 累计平均成本
        cumavg = np.cumsum(costs) / np.arange(1, T + 1)

        ax.plot(x, cumavg[::step], color=COLOR_TS[k_idx], linewidth=1.2, alpha=0.85)

        # 标注全周期成本均值
        avg_cost = np.mean(costs)
        ax.axhline(y=avg_cost, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax.text(T * 0.02, avg_cost + max(cumavg) * 0.03,
                '均值=%.2f' % avg_cost,
                fontsize=9, color='gray', fontweight='bold')

        # 标注最终收敛值
        final_cost = cumavg[-1]
        ax.text(T * 0.7, final_cost + max(cumavg) * 0.03,
                '收敛值=%.2f' % final_cost,
                fontsize=8, color=COLOR_TS[k_idx], fontweight='bold')

        ax.set_xticks(xticks)
        ax.set_xlim(0, T)
        ax.set_xlabel('订货周期 / Period', fontsize=9)
        ax.set_ylabel('累计平均成本 / Cumulative Avg Cost', fontsize=9)
        # 子图标识在下方
        ax.text(0.5, -0.18,
                '(%s) %s (k=%s)  均值=%.2f  收敛=%.2f' % (chr(97+k_idx), NODE_CN[k_idx], k, avg_cost, final_cost),
                transform=ax.transAxes, ha='center', va='top', fontsize=9,
                fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    # 图名和标题在图下方
    fig.text(0.5, 0.01,
             '图16  多智能体人智协同实验下的各节点随20000周期变化的平均成本',
             ha='center', va='bottom', fontsize=13, fontweight='bold', fontfamily='SimHei')
    fig.text(0.5, -0.01,
             'Fig.16  Cumulative Average Cost per Node over 20000 Periods under Multi-Agent Human-AI Collaborative Experiment',
             ha='center', va='top', fontsize=10, fontstyle='italic', color='gray')
    fig.text(0.5, -0.03,
             '横轴间隔2500  数据来源：exp2_20k_timeseries.json  成本公式：C = h*max(0,NS) + b*max(0,D-F)，h=1.0, b=2.0',
             ha='center', va='top', fontsize=8, color='#7F8C8D')

    fig.tight_layout(rect=[0, 0.05, 1, 1])
    return save_svg(fig, 'fig16_cost_over_periods.svg')


# ============================================================
# 图17: 供应链各级服务水平图
# ============================================================

def plot_fig17_sl(data):
    """图17 供应链各级服务水平图"""
    print("\n[图17] 供应链各级服务水平图...")

    T = 20000
    step = 20

    # 2行×4列：上行20000周期，下行最后500周期
    fig, axes = plt.subplots(2, 4, figsize=(18, 8))

    # ---- 上行：20000周期，横轴间隔2500 ----
    x_full = np.arange(0, T, step)
    xticks_full = np.arange(0, 22500, 2500)

    for k_idx, k in enumerate(['1', '2', '3', '4']):
        ax = axes[0, k_idx]
        sls = np.array(data['sl_history'][k])

        # 累计平均SL
        cumavg_sl = np.cumsum(sls) / np.arange(1, T + 1) * 100

        ax.plot(x_full, cumavg_sl[::step], color=COLOR_TS[k_idx], linewidth=1.2, alpha=0.85)

        # 标注全周期SL均值
        avg_sl = np.mean(sls) * 100
        ax.axhline(y=avg_sl, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax.text(T * 0.02, avg_sl + 0.5, '均值=%.2f%%' % avg_sl,
                fontsize=8, color='gray', fontweight='bold')

        # 标注97.7%目标线
        ax.axhline(y=97.7, color='green', linestyle=':', linewidth=0.8, alpha=0.4)

        ax.set_xticks(xticks_full)
        ax.set_xlim(0, T)
        ax.set_ylim(60, 105)
        ax.set_xlabel('订货周期 / Period', fontsize=9)
        ax.set_ylabel('累计平均 SL (%)', fontsize=9)
        # 子图标识在下方
        ax.text(0.5, -0.22, '(%s) %s  SL=%.2f%%' % (chr(97+k_idx), NODE_CN[k_idx], avg_sl),
                transform=ax.transAxes, ha='center', va='top', fontsize=9,
                fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    # ---- 下行：最后500周期，横轴间隔100 ----
    last_n = 500
    x_last = np.arange(T - last_n, T)
    xticks_last = np.arange(T - last_n, T + 50, 100)

    for k_idx, k in enumerate(['1', '2', '3', '4']):
        ax = axes[1, k_idx]
        sls = np.array(data['sl_history'][k])

        # 最后500周期的逐周期SL
        sl_last = sls[T - last_n:T] * 100

        ax.plot(x_last, sl_last, color=COLOR_TS[k_idx], linewidth=1.0, alpha=0.8)

        # 标注最后500周期SL均值
        avg_sl_last = np.mean(sl_last)
        ax.axhline(y=avg_sl_last, color='gray', linestyle='--', linewidth=1, alpha=0.5)
        ax.text(T - last_n + 10, avg_sl_last + 1, '500周期均值=%.2f%%' % avg_sl_last,
                fontsize=8, color='gray', fontweight='bold')

        # 标注97.7%目标线
        ax.axhline(y=97.7, color='green', linestyle=':', linewidth=0.8, alpha=0.4)

        ax.set_xticks(xticks_last)
        ax.set_xlim(T - last_n, T)
        ax.set_ylim(max(0, avg_sl_last - 30), 105)
        ax.set_xlabel('订货周期 / Period', fontsize=9)
        ax.set_ylabel('SL (%)', fontsize=9)
        # 子图标识在下方
        ax.text(0.5, -0.22, '(%s) %s  500周期均值=%.2f%%' % (chr(101+k_idx), NODE_CN[k_idx], avg_sl_last),
                transform=ax.transAxes, ha='center', va='top', fontsize=9,
                fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    # 图名和标题在图下方
    fig.text(0.5, 0.01,
             '图17  供应链各级服务水平图',
             ha='center', va='bottom', fontsize=13, fontweight='bold', fontfamily='SimHei')
    fig.text(0.5, -0.02,
             'Fig.17  Service Level at Each Supply Chain Echelon',
             ha='center', va='top', fontsize=10, fontstyle='italic', color='gray')
    fig.text(0.5, -0.04,
             '上排：20000周期（横轴间隔2500）  下排：最后500周期（横轴间隔100）  数据来源：exp2_20k_timeseries.json',
             ha='center', va='top', fontsize=8, color='#7F8C8D')

    fig.tight_layout(rect=[0, 0.06, 1, 1])
    return save_svg(fig, 'fig17_sl_over_periods.svg')


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 70)
    print("图15-17 SVG 图表生成（Exp_2 20000周期实验数据）")
    print("=" * 70)

    data = load_data()
    print("数据加载完成: exp2_20k_timeseries.json")
    print("  demand_history: %d 周期" % len(data['demand_history']))
    for k in ['1', '2', '3', '4']:
        print("  k=%s: order=%d, cost=%d, sl=%d" % (k, len(data['order_history'][k]),
              len(data['cost_history'][k]), len(data['sl_history'][k])))

    # 各节点平均值
    demands = np.array(data['demand_history'])
    print("\n各节点平均值（全周期20000）:")
    for k_idx, k in enumerate(['1', '2', '3', '4']):
        orders = np.array(data['order_history'][k])
        costs = np.array(data['cost_history'][k])
        sls = np.array(data['sl_history'][k])
        bwe = np.var(orders) / np.var(demands) if np.var(demands) > 0 else 0
        print("  %s (k=%s): BWE=%.2f, Cost=%.2f, SL=%.2f%%" % (NODE_CN[k_idx], k, bwe, np.mean(costs), np.mean(sls)*100))

    # 生成3张图
    plot_fig15_bwe(data)
    plot_fig16_cost(data)
    plot_fig17_sl(data)

    print("\n" + "=" * 70)
    print("图15-17 SVG 图表生成完成！")
    print("输出目录: %s" % OUTPUT_DIR)
    print("=" * 70)


if __name__ == '__main__':
    main()

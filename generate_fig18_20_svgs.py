"""
图18-20 SVG 图表生成（基础实验：理性决策 vs 智慧决策）
=========================================================
基于20000周期完整时序数据，对比Baseline（理性决策）与Exp_1（智慧决策）：

图18：方差比随周期变化图
  - 2行×4列：每列一个节点，上行20000周期(间隔2500)，下行最后500周期(间隔100)
  - 理性决策 vs 智慧决策两条线对比
  - 标注各节点BWE平均值

图19：各节点随20000周期变化的平均成本
  - 2×2子图：每个子图一个节点
  - 累计平均成本，横轴间隔2500
  - 标注均值和收敛值

图20：供应链各级服务水平图
  - 2行×4列：每列一个节点，上行20000周期(间隔2500)，下行最后500周期(间隔100)
  - 理性决策 vs 智慧决策两条线对比
  - 标注各节点SL平均值

数据来源：
  - p0_results/baseline_20k_timeseries.json (理性决策)
  - p0_results/exp1_20k_timeseries.json (智慧决策)
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

# Nature/Science 色盲友好配色
COLOR_RATIONAL = '#E74C3C'    # 红色 - 理性决策
COLOR_IDMR = '#3498DB'        # 蓝色 - 智慧决策
COLOR_TARGET = '#7F8C8D'      # 灰色 - 目标线

NODE_NAMES_CN = ['零售商', '批发商', '分销商', '制造商']
NODE_NAMES_EN = ['Retailer', 'Wholesaler', 'Distributor', 'Manufacturer']


# ============================================================
# 数据加载
# ============================================================

def load_data():
    """加载Baseline和Exp_1时序数据"""
    print("加载数据...")
    with open(os.path.join(BASE_DIR, 'p0_results', 'baseline_20k_timeseries.json'), 'r', encoding='utf-8') as f:
        baseline = json.load(f)
    with open(os.path.join(BASE_DIR, 'p0_results', 'exp1_20k_timeseries.json'), 'r', encoding='utf-8') as f:
        exp1 = json.load(f)

    data = {'baseline': baseline, 'exp1': exp1}

    # 验证数据
    T = len(baseline['customer_demand'])
    print(f"  理性决策: {T} 周期")
    for k in ['1', '2', '3', '4']:
        print(f"    k={k}: order={len(baseline['order_history'][k])}, "
              f"cost={len(baseline['cost_history'][k])}, sl={len(baseline['sl_history'][k])}")

    T2 = len(exp1['customer_demand'])
    print(f"  智慧决策: {T2} 周期")
    for k in ['1', '2', '3', '4']:
        print(f"    k={k}: order={len(exp1['order_history'][k])}, "
              f"cost={len(exp1['cost_history'][k])}, sl={len(exp1['sl_history'][k])}")

    # 计算各节点平均值
    print("\n各节点平均值（全周期20000）:")
    print(f"  {'节点':<8} {'─理性决策─':^30} {'─智慧决策─':^30}")
    print(f"  {'':8} {'BWE':>8}{'Cost':>8}{'SL':>8} {'BWE':>8}{'Cost':>8}{'SL':>8}")
    for k in ['1', '2', '3', '4']:
        idx = int(k) - 1
        # Baseline
        var_D_b = np.var(baseline['customer_demand'])
        bwe_b = np.var(baseline['order_history'][k]) / var_D_b if var_D_b > 0 else 0
        cost_b = np.mean(baseline['cost_history'][k])
        sl_b = np.mean(baseline['sl_history'][k])
        # Exp1
        var_D_e = np.var(exp1['customer_demand'])
        bwe_e = np.var(exp1['order_history'][k]) / var_D_e if var_D_e > 0 else 0
        cost_e = np.mean(exp1['cost_history'][k])
        sl_e = np.mean(exp1['sl_history'][k])
        print(f"  {NODE_NAMES_CN[idx]:<8} {bwe_b:>8.2f}{cost_b:>8.2f}{sl_b*100:>7.2f}% "
              f"{bwe_e:>8.2f}{cost_e:>8.2f}{sl_e*100:>7.2f}%")

    return data


# ============================================================
# BWE 滑动窗口计算
# ============================================================

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
    # 填充前window个周期
    bwe[:window] = bwe[window] if window < T else 0
    return bwe


# ============================================================
# 图18：方差比随周期变化图
# ============================================================

def plot_fig18_bwe(data):
    """图18 方差比随周期变化图 - 2行×4列"""
    print("\n[图18] 方差比随周期变化图...")
    baseline = data['baseline']
    exp1 = data['exp1']

    fig, axes = plt.subplots(2, 4, figsize=(20, 10))

    # 上行：20000周期，横轴间隔2500
    # 下行：最后500周期，横轴间隔100

    for col, k in enumerate(['1', '2', '3', '4']):
        idx = int(k) - 1

        # 计算BWE时序
        bwe_b = compute_sliding_bwe(
            np.array(baseline['order_history'][k]),
            np.array(baseline['customer_demand']))
        bwe_e = compute_sliding_bwe(
            np.array(exp1['order_history'][k]),
            np.array(exp1['customer_demand']))

        # 全周期平均值
        avg_bwe_b = np.var(baseline['order_history'][k]) / np.var(baseline['customer_demand'])
        avg_bwe_e = np.var(exp1['order_history'][k]) / np.var(exp1['customer_demand'])

        # ---- 上行：20000周期 ----
        ax_top = axes[0, col]
        T = 20000
        x_full = np.arange(T)
        ax_top.plot(x_full, bwe_b, color=COLOR_RATIONAL, linewidth=1.0,
                    alpha=0.8, label='理性决策 Rational')
        ax_top.plot(x_full, bwe_e, color=COLOR_IDMR, linewidth=1.0,
                    alpha=0.8, label='智慧决策 IDMR')

        # 横轴间隔2500
        ax_top.set_xticks(np.arange(0, T+1, 2500))
        ax_top.set_xlim(0, T)
        ax_top.set_xlabel('周期 Period', fontsize=9)
        ax_top.set_ylabel('方差比 BWE', fontsize=9)
        ax_top.set_title(f'({chr(97+col)}) {NODE_NAMES_CN[idx]} {NODE_NAMES_EN[idx]}\n'
                         f'理性BWE={avg_bwe_b:.2f}, 智慧BWE={avg_bwe_e:.2f}',
                         fontsize=9, fontweight='bold')
        ax_top.grid(True, alpha=0.3, linestyle='--')
        ax_top.legend(fontsize=7, loc='upper right')
        if avg_bwe_b > 50:
            ax_top.set_yscale('log')

        # ---- 下行：最后500周期 ----
        ax_bot = axes[1, col]
        last_500_b = bwe_b[-500:]
        last_500_e = bwe_e[-500:]
        x_500 = np.arange(19500, 20000)

        ax_bot.plot(x_500, last_500_b, color=COLOR_RATIONAL, linewidth=1.2,
                    alpha=0.85, label='理性决策 Rational')
        ax_bot.plot(x_500, last_500_e, color=COLOR_IDMR, linewidth=1.2,
                    alpha=0.85, label='智慧决策 IDMR')

        # 最后500周期平均值
        avg_bwe_b_500 = np.mean(last_500_b)
        avg_bwe_e_500 = np.mean(last_500_e)

        # 横轴间隔100
        ax_bot.set_xticks(np.arange(19500, 20001, 100))
        ax_bot.set_xlim(19500, 20000)
        ax_bot.set_xlabel('周期 Period', fontsize=9)
        ax_bot.set_ylabel('方差比 BWE', fontsize=9)
        ax_bot.set_title(f'({chr(101+col)}) {NODE_NAMES_CN[idx]} 最后500周期\n'
                         f'理性BWE={avg_bwe_b_500:.2f}, 智慧BWE={avg_bwe_e_500:.2f}',
                         fontsize=9, fontweight='bold')
        ax_bot.grid(True, alpha=0.3, linestyle='--')
        ax_bot.legend(fontsize=7, loc='upper right')
        if avg_bwe_b_500 > 50 or max(last_500_b) > 100:
            ax_bot.set_yscale('log')

    # 图名和标题在图下方
    fig.text(0.5, 0.01,
             '图18  理性决策与智慧决策下的方差比随周期变化图',
             ha='center', va='bottom', fontsize=14, fontweight='bold',
             fontfamily='SimHei')
    fig.text(0.5, -0.005,
             'Fig.18  Bullwhip Effect Ratio over Periods under Rational vs. Intelligent Decision-Making',
             ha='center', va='bottom', fontsize=11, fontstyle='italic', color='gray')
    fig.text(0.5, -0.02,
             '数据来源：基础实验20000周期  |  上行: 全周期(间隔2500)  下行: 最后500周期(间隔100)  |  BWE=Var(q_k)/Var(D)',
             ha='center', va='top', fontsize=8, color='#7F8C8D')

    fig.tight_layout(rect=[0, 0.04, 1, 1])
    path = os.path.join(OUTPUT_DIR, 'fig18_bwe_comparison_periods.svg')
    fig.savefig(path, format='svg', bbox_inches='tight')
    plt.close(fig)
    print(f"  [saved] {path}")


# ============================================================
# 图19：各节点随20000周期变化的平均成本
# ============================================================

def plot_fig19_cost(data):
    """图19 各节点平均成本随20000周期变化 - 2×2子图"""
    print("\n[图19] 各节点平均成本随20000周期变化图...")
    baseline = data['baseline']
    exp1 = data['exp1']

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    T = 20000
    x_full = np.arange(1, T+1)

    for idx, k in enumerate(['1', '2', '3', '4']):
        row = idx // 2
        col = idx % 2
        ax = axes[row, col]

        # 累计平均成本
        costs_b = np.array(baseline['cost_history'][k])
        costs_e = np.array(exp1['cost_history'][k])

        cum_avg_b = np.cumsum(costs_b) / x_full
        cum_avg_e = np.cumsum(costs_e) / x_full

        avg_cost_b = np.mean(costs_b)
        avg_cost_e = np.mean(costs_e)

        # 收敛值（最后1000周期平均）
        conv_b = np.mean(costs_b[-1000:])
        conv_e = np.mean(costs_e[-1000:])

        ax.plot(x_full, cum_avg_b, color=COLOR_RATIONAL, linewidth=1.5,
                alpha=0.85, label=f'理性决策 Rational (均值={avg_cost_b:.2f})')
        ax.plot(x_full, cum_avg_e, color=COLOR_IDMR, linewidth=1.5,
                alpha=0.85, label=f'智慧决策 IDMR (均值={avg_cost_e:.2f})')

        # 标注均值水平线
        ax.axhline(y=avg_cost_b, color=COLOR_RATIONAL, linestyle='--',
                   linewidth=0.8, alpha=0.5)
        ax.axhline(y=avg_cost_e, color=COLOR_IDMR, linestyle='--',
                   linewidth=0.8, alpha=0.5)

        # 横轴间隔2500
        ax.set_xticks(np.arange(0, T+1, 2500))
        ax.set_xlim(0, T)
        ax.set_xlabel('周期 Period', fontsize=10)
        ax.set_ylabel('累计平均成本 Cumulative Avg. Cost', fontsize=10)
        ax.set_title(f'({chr(97+idx)}) {NODE_NAMES_CN[idx]} {NODE_NAMES_EN[idx]}\n'
                     f'理性: 均值={avg_cost_b:.2f}, 收敛={conv_b:.2f}  |  '
                     f'智慧: 均值={avg_cost_e:.2f}, 收敛={conv_e:.2f}',
                     fontsize=10, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(fontsize=8, loc='upper right')

    # 图名和标题在图下方
    fig.text(0.5, 0.01,
             '图19  理性决策与智慧决策下的各节点随20000周期变化的平均成本',
             ha='center', va='bottom', fontsize=14, fontweight='bold',
             fontfamily='SimHei')
    fig.text(0.5, -0.005,
             'Fig.19  Cumulative Average Cost per Node over 20000 Periods under Rational vs. Intelligent Decision-Making',
             ha='center', va='bottom', fontsize=11, fontstyle='italic', color='gray')
    fig.text(0.5, -0.02,
             '注：理性决策成本=库存持有(h=1.0)+缺货惩罚(b=2.0)；智慧决策成本=0.5×|q|（李勇论文简化公式）  |  横轴间隔2500',
             ha='center', va='top', fontsize=8, color='#7F8C8D')

    fig.tight_layout(rect=[0, 0.04, 1, 1])
    path = os.path.join(OUTPUT_DIR, 'fig19_cost_comparison_periods.svg')
    fig.savefig(path, format='svg', bbox_inches='tight')
    plt.close(fig)
    print(f"  [saved] {path}")


# ============================================================
# 图20：供应链各级服务水平图
# ============================================================

def plot_fig20_sl(data):
    """图20 供应链各级服务水平图 - 2行×4列"""
    print("\n[图20] 供应链各级服务水平图...")
    baseline = data['baseline']
    exp1 = data['exp1']

    fig, axes = plt.subplots(2, 4, figsize=(20, 10))

    for col, k in enumerate(['1', '2', '3', '4']):
        idx = int(k) - 1

        # SL时序
        sl_b = np.array(baseline['sl_history'][k])
        sl_e = np.array(exp1['sl_history'][k])

        # 累计平均SL
        T = len(sl_b)
        x_full = np.arange(1, T+1)
        cum_sl_b = np.cumsum(sl_b) / x_full
        cum_sl_e = np.cumsum(sl_e) / x_full

        avg_sl_b = np.mean(sl_b)
        avg_sl_e = np.mean(sl_e)

        # ---- 上行：20000周期累计平均SL ----
        ax_top = axes[0, col]
        ax_top.plot(x_full, cum_sl_b * 100, color=COLOR_RATIONAL, linewidth=1.0,
                    alpha=0.85, label='理性决策 Rational')
        ax_top.plot(x_full, cum_sl_e * 100, color=COLOR_IDMR, linewidth=1.0,
                    alpha=0.85, label='智慧决策 IDMR')

        # 97.7%目标线
        ax_top.axhline(y=97.7, color=COLOR_TARGET, linestyle='--',
                       linewidth=0.8, alpha=0.6)
        ax_top.text(T*0.7, 97.8, '目标97.7%', fontsize=7, color=COLOR_TARGET)

        ax_top.set_xticks(np.arange(0, T+1, 2500))
        ax_top.set_xlim(0, T)
        ax_top.set_xlabel('周期 Period', fontsize=9)
        ax_top.set_ylabel('服务水平 SL (%)', fontsize=9)
        ax_top.set_title(f'({chr(97+col)}) {NODE_NAMES_CN[idx]} {NODE_NAMES_EN[idx]}\n'
                         f'理性SL={avg_sl_b*100:.2f}%, 智慧SL={avg_sl_e*100:.2f}%',
                         fontsize=9, fontweight='bold')
        ax_top.grid(True, alpha=0.3, linestyle='--')
        ax_top.legend(fontsize=7, loc='lower right')
        ax_top.set_ylim(80, 102)

        # ---- 下行：最后500周期逐周期SL ----
        ax_bot = axes[1, col]
        last_500_b = sl_b[-500:]
        last_500_e = sl_e[-500:]
        x_500 = np.arange(19500, 20000)

        ax_bot.plot(x_500, last_500_b * 100, color=COLOR_RATIONAL, linewidth=1.2,
                    alpha=0.85, label='理性决策 Rational')
        ax_bot.plot(x_500, last_500_e * 100, color=COLOR_IDMR, linewidth=1.2,
                    alpha=0.85, label='智慧决策 IDMR')

        # 最后500周期平均
        avg_sl_b_500 = np.mean(last_500_b)
        avg_sl_e_500 = np.mean(last_500_e)

        # 97.7%目标线
        ax_bot.axhline(y=97.7, color=COLOR_TARGET, linestyle='--',
                       linewidth=0.8, alpha=0.6)
        ax_bot.text(19550, 97.8, '目标97.7%', fontsize=7, color=COLOR_TARGET)

        ax_bot.set_xticks(np.arange(19500, 20001, 100))
        ax_bot.set_xlim(19500, 20000)
        ax_bot.set_xlabel('周期 Period', fontsize=9)
        ax_bot.set_ylabel('服务水平 SL (%)', fontsize=9)
        ax_bot.set_title(f'({chr(101+col)}) {NODE_NAMES_CN[idx]} 最后500周期\n'
                         f'理性SL={avg_sl_b_500*100:.2f}%, 智慧SL={avg_sl_e_500*100:.2f}%',
                         fontsize=9, fontweight='bold')
        ax_bot.grid(True, alpha=0.3, linestyle='--')
        ax_bot.legend(fontsize=7, loc='lower right')
        ax_bot.set_ylim(60, 105)

    # 图名和标题在图下方
    fig.text(0.5, 0.01,
             '图20  理性决策与智慧决策下的供应链各级服务水平图',
             ha='center', va='bottom', fontsize=14, fontweight='bold',
             fontfamily='SimHei')
    fig.text(0.5, -0.005,
             'Fig.20  Service Level at Each Node under Rational vs. Intelligent Decision-Making',
             ha='center', va='bottom', fontsize=11, fontstyle='italic', color='gray')
    fig.text(0.5, -0.02,
             '数据来源：基础实验20000周期  |  上行: 全周期累计平均(间隔2500)  下行: 最后500周期逐周期(间隔100)  |  SL=fulfilled/demand',
             ha='center', va='top', fontsize=8, color='#7F8C8D')

    fig.tight_layout(rect=[0, 0.04, 1, 1])
    path = os.path.join(OUTPUT_DIR, 'fig20_sl_comparison_periods.svg')
    fig.savefig(path, format='svg', bbox_inches='tight')
    plt.close(fig)
    print(f"  [saved] {path}")


# ============================================================
# 主函数
# ============================================================

def main():
    print("=" * 70)
    print("图18-20 SVG 图表生成（基础实验：理性决策 vs 智慧决策）")
    print("=" * 70)

    data = load_data()

    plot_fig18_bwe(data)
    plot_fig19_cost(data)
    plot_fig20_sl(data)

    print("\n" + "=" * 70)
    print("图18-20 SVG 生成完成！")
    print("输出目录: %s" % OUTPUT_DIR)
    print("=" * 70)


if __name__ == '__main__':
    main()

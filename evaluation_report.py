"""
多维度综合评估报告生成器
========================

基于现有实验数据, 计算 4 个维度的评估指标, 输出 LaTeX 表格:

    1. 传统供应链指标: BWE方差比 / 平均总成本 / 服务水平 (三组实验)
    2. 行为经济学指标: 损失厌恶程度 (实际订货量 vs 理论最优订货量偏差)
    3. 系统鲁棒性指标: 需求突变/供应中断事件下的恢复时间 (Recovery Time)
    4. 情绪健康度指标: 极端恐慌/过度乐观状态时长占比

数据来源:
    - 实验结果摘要.json (三组实验汇总)
    - 归因分析_详细数据.csv (Exp_2 逐周期数据, 含情绪/事件标记)

输出:
    - 综合评估报告.tex (LaTeX 表格源码)
    - 综合评估报告.json (结构化数据)
"""

import warnings
warnings.filterwarnings('ignore')
import os
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import json
import numpy as np
from typing import Dict, List, Any, Tuple

# 数据处理 (容忍 pandas 不可用)
try:
    import pandas as pd
    HAS_PANDAS = True
except Exception:
    HAS_PANDAS = False
    pd = None


# ============================================================
# 配置
# ============================================================
SUMMARY_FILE = '实验结果摘要.json'
DETAIL_FILE = '归因分析_详细数据.csv'
TEX_OUTPUT = '综合评估报告.tex'
JSON_OUTPUT = '综合评估报告.json'

NODE_IDS = ['retailer', 'wholesaler', 'distributor', 'manufacturer']
NODE_NAMES_CN = {'retailer': '零售商', 'wholesaler': '批发商',
                 'distributor': '分销商', 'manufacturer': '制造商'}
K_TO_ID = {1: 'retailer', 2: 'wholesaler', 3: 'distributor', 4: 'manufacturer'}

# 情绪阈值 (用于情绪健康度计算)
PANIC_THRESHOLD = -0.5      # 极端恐慌: E < -0.5
OPTIMISM_THRESHOLD = 0.5    # 过度乐观: E > 0.5
NEUTRAL_LOW = -0.1          # 轻度焦虑边界
NEUTRAL_HIGH = 0.1          # 轻度自信边界

# 恢复时间判定
RECOVERY_TOLERANCE = 0.20  # BWE 回到事件前 ±20% 范围内视为恢复
RECOVERY_MAX_WINDOW = 30   # 最大观察窗口 (避免无限等待)


# ============================================================
# 数据加载
# ============================================================

def load_data() -> Tuple[Dict, Any]:
    """加载实验结果摘要和详细数据"""
    with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
        summary = json.load(f)

    if HAS_PANDAS:
        df = pd.read_csv(DETAIL_FILE)
    else:
        # 退化: 手动解析 CSV
        df = _parse_csv_manual(DETAIL_FILE)

    return summary, df


def _parse_csv_manual(path: str):
    """无 pandas 时的退化 CSV 解析"""
    import csv
    from collections import defaultdict
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            row = {}
            for k, v in r.items():
                try:
                    if k in ['t', 'k']:
                        row[k] = int(v)
                    elif k in ['demand_shock', 'supply_disruption']:
                        row[k] = v == 'True'
                    else:
                        row[k] = float(v)
                except (ValueError, TypeError):
                    row[k] = v
            rows.append(row)

    class _DFFallback:
        def __init__(self, rows):
            self.rows = rows
            self.columns = list(rows[0].keys()) if rows else []

        def __len__(self):
            return len(self.rows)

        def __getitem__(self, key):
            return [r.get(key) for r in self.rows]

        def filter(self, **kwargs):
            return _DFFallback([r for r in self.rows
                                if all(r.get(k) == v for k, v in kwargs.items())])

    return _DFFallback(rows)


# ============================================================
# 维度 1: 传统供应链指标
# ============================================================

def compute_traditional_metrics(summary: Dict) -> Dict[str, Dict[str, Any]]:
    """
    传统供应链指标: BWE方差比 / 平均总成本 / 服务水平

    数据直接来自 实验结果摘要.json (三组实验)
    """
    results = {}
    for exp_key, exp_data in summary['experiments'].items():
        bwe = exp_data['bwe']
        avg_cost = exp_data['avg_cost']
        sl = exp_data['sl']

        # 计算平均值 (跨 4 个节点)
        avg_bwe = float(np.mean(list(bwe.values())))
        total_cost = exp_data['total_cost']
        avg_sl = float(np.mean(list(sl.values())))

        results[exp_key] = {
            'name': exp_data['name'],
            'bwe_per_node': {NODE_NAMES_CN[K_TO_ID[int(k)]]: float(v)
                              for k, v in bwe.items()},
            'avg_bwe': avg_bwe,
            'avg_cost_per_node': {NODE_NAMES_CN[K_TO_ID[int(k)]]: float(v)
                                    for k, v in avg_cost.items()},
            'total_cost': float(total_cost),
            'sl_per_node': {NODE_NAMES_CN[K_TO_ID[int(k)]]: float(v)
                             for k, v in sl.items()},
            'avg_sl': avg_sl,
        }
    return results


# ============================================================
# 维度 2: 行为经济学指标 (损失厌恶程度)
# ============================================================

def compute_loss_aversion(summary: Dict, df) -> Dict[str, Any]:
    """
    损失厌恶程度量化

    定义:
        loss_aversion = mean(|q_actual - q_optimal|) / mean(q_optimal)

    其中:
        q_optimal  = 理论最优订货量 (用该节点面临的下游需求均值作为基准,
                     在 AR(1) 需求下, 理性订至点策略的订货量应趋近需求)
        q_actual   = Exp_2 实际订货量 (含情绪扰动的多智能体决策)

    损失厌恶表现为: 决策者因害怕缺货而过度订货 (q_actual > q_demand)
    恐慌性囤货表现为: q_actual 显著大于 q_demand
    """
    # Exp_2 实际订货量与该节点面临的下游需求对比 (从详细数据)
    results = {}
    if HAS_PANDAS:
        for k in range(1, 5):
            aid = K_TO_ID[k]
            sub = df[df['agent_id'] == aid]
            q_actual = sub['order_q'].values
            q_demand = sub['demand'].values  # 该节点收到的下游订单 (= 应满足的需求)

            # 理论最优: 理性决策下订货量应趋近需求 (供需平衡)
            q_optimal = float(np.mean(q_demand))

            # 损失厌恶程度: 实际订货量偏离需求的程度
            mae = float(np.mean(np.abs(q_actual - q_demand)))  # 平均绝对偏差
            ratio = mae / max(q_optimal, 1e-6)  # 相对偏差率

            # 过度订货比例 (q_actual > q_demand 的样本占比)
            over_order_ratio = float(np.mean(q_actual > q_demand))

            # 平均订货量
            avg_q_actual = float(np.mean(q_actual))

            results[NODE_NAMES_CN[aid]] = {
                'avg_q_actual': avg_q_actual,
                'avg_q_optimal': q_optimal,
                'mae': mae,
                'loss_aversion_ratio': ratio,  # 损失厌恶程度
                'over_order_ratio': over_order_ratio,  # 过度订货比例
            }
    else:
        # 退化计算
        orders_by_node = {aid: [] for aid in NODE_IDS}
        demands_by_node = {aid: [] for aid in NODE_IDS}
        for r in df.rows:
            orders_by_node[r['agent_id']].append(r['order_q'])
            demands_by_node[r['agent_id']].append(r['demand'])
        for k in range(1, 5):
            aid = K_TO_ID[k]
            q_actual = np.array(orders_by_node[aid])
            q_demand = np.array(demands_by_node[aid])
            q_optimal = float(np.mean(q_demand))
            mae = float(np.mean(np.abs(q_actual - q_demand)))
            ratio = mae / max(q_optimal, 1e-6)
            over_order_ratio = float(np.mean(q_actual > q_demand))
            results[NODE_NAMES_CN[aid]] = {
                'avg_q_actual': float(np.mean(q_actual)),
                'avg_q_optimal': q_optimal,
                'mae': mae,
                'loss_aversion_ratio': ratio,
                'over_order_ratio': over_order_ratio,
            }

    # 系统级汇总
    avg_loss_aversion = float(np.mean([results[n]['loss_aversion_ratio']
                                        for n in results]))
    avg_over_order = float(np.mean([results[n]['over_order_ratio']
                                     for n in results]))

    return {
        'per_node': results,
        'system_avg_loss_aversion': avg_loss_aversion,
        'system_avg_over_order_ratio': avg_over_order,
    }


# ============================================================
# 维度 3: 系统鲁棒性指标 (恢复时间)
# ============================================================

def compute_recovery_time(df) -> Dict[str, Any]:
    """
    恢复时间 (Recovery Time) 计算

    定义:
        在发生"需求突变"或"供应中断"事件后,
        系统恢复到稳态所需的平均周期数.

    稳态判定:
        事件发生前 50 周期的平均订货量作为基线 q_baseline
        恢复条件: 连续 5 周期 |q_t - q_baseline| <= RECOVERY_TOLERANCE * q_baseline

    数据来源:
        归因分析_详细数据.csv 的 demand_shock 和 supply_disruption 标记
    """
    # 提取事件时间点
    if HAS_PANDAS:
        # 取分销商 (k=3) 作为系统稳态代表节点
        sub = df[df['agent_id'] == 'distributor'].copy()
        sub = sub.sort_values('t').reset_index(drop=True)
        orders = sub['order_q'].values
        t_arr = sub['t'].values
        shock_flags = sub['demand_shock'].values
        disrupt_flags = sub['supply_disruption'].values
    else:
        orders_by_t = {}
        shock_by_t = {}
        disrupt_by_t = {}
        for r in df.rows:
            if r['agent_id'] == 'distributor':
                orders_by_t[r['t']] = r['order_q']
                shock_by_t[r['t']] = r['demand_shock']
                disrupt_by_t[r['t']] = r['supply_disruption']
        t_arr = np.array(sorted(orders_by_t.keys()))
        orders = np.array([orders_by_t[t] for t in t_arr])
        shock_flags = np.array([shock_by_t[t] for t in t_arr])
        disrupt_flags = np.array([disrupt_by_t[t] for t in t_arr])

    # 找到事件发生点 (标记从 False→True 的转换)
    event_indices = []
    for i in range(1, len(shock_flags)):
        is_event = bool(shock_flags[i]) or bool(disrupt_flags[i])
        was_event = bool(shock_flags[i-1]) or bool(disrupt_flags[i-1])
        if is_event and not was_event:
            event_type = 'demand_shock' if shock_flags[i] else 'supply_disruption'
            event_indices.append({'t': int(t_arr[i]), 'idx': i, 'type': event_type})

    # 计算每个事件的恢复时间
    recovery_times = {'demand_shock': [], 'supply_disruption': []}
    for event in event_indices:
        i = event['idx']
        etype = event['type']

        # 事件前基线 (前 50 周期, 或可用范围)
        baseline_start = max(0, i - 50)
        baseline_end = i
        if baseline_end - baseline_start < 5:
            continue  # 数据不足
        q_baseline = float(np.mean(orders[baseline_start:baseline_end]))
        if q_baseline < 1e-6:
            continue

        # 寻找恢复点: 连续 5 周期 |q - baseline| <= tolerance * baseline
        tolerance = RECOVERY_TOLERANCE * abs(q_baseline)
        recovery_window = min(RECOVERY_MAX_WINDOW, len(orders) - i)
        consecutive_stable = 0
        recovery_t = None

        for j in range(i, i + recovery_window):
            if abs(orders[j] - q_baseline) <= tolerance:
                consecutive_stable += 1
                if consecutive_stable >= 5:
                    recovery_t = j - i  # 恢复周期数
                    break
            else:
                consecutive_stable = 0

        if recovery_t is not None:
            recovery_times[etype].append(recovery_t)
        else:
            # 未恢复, 记录为最大窗口
            recovery_times[etype].append(RECOVERY_MAX_WINDOW)

    # 汇总
    all_demand_recovery = recovery_times['demand_shock']
    all_supply_recovery = recovery_times['supply_disruption']
    all_recovery = all_demand_recovery + all_supply_recovery

    return {
        'n_demand_shock_events': len(all_demand_recovery),
        'n_supply_disruption_events': len(all_supply_recovery),
        'n_total_events': len(all_recovery),
        'recovery_time_demand_shock': {
            'mean': float(np.mean(all_demand_recovery)) if all_demand_recovery else 0.0,
            'std': float(np.std(all_demand_recovery)) if all_demand_recovery else 0.0,
            'max': float(np.max(all_demand_recovery)) if all_demand_recovery else 0.0,
            'min': float(np.min(all_demand_recovery)) if all_demand_recovery else 0.0,
        },
        'recovery_time_supply_disruption': {
            'mean': float(np.mean(all_supply_recovery)) if all_supply_recovery else 0.0,
            'std': float(np.std(all_supply_recovery)) if all_supply_recovery else 0.0,
            'max': float(np.max(all_supply_recovery)) if all_supply_recovery else 0.0,
            'min': float(np.min(all_supply_recovery)) if all_supply_recovery else 0.0,
        },
        'overall_recovery_time': {
            'mean': float(np.mean(all_recovery)) if all_recovery else 0.0,
            'std': float(np.std(all_recovery)) if all_recovery else 0.0,
        },
    }


# ============================================================
# 维度 4: 情绪健康度指标
# ============================================================

def compute_emotion_health(df) -> Dict[str, Any]:
    """
    情绪健康度指标

    计算整个实验周期内, 系统处于以下状态的时长占比:
        - 极端恐慌 (E < -0.5): 损失厌恶极值, 可能导致恐慌性囤货
        - 焦虑 (-0.5 <= E < -0.1): 轻度恐慌, 决策趋于保守
        - 中性 (-0.1 <= E <= 0.1): 理性决策区
        - 自信 (0.1 < E <= 0.5): 轻度乐观
        - 过度乐观 (E > 0.5): 过度自信, 可能低估风险

    系统情绪健康度 = 1 - (极端恐慌占比 + 过度乐观占比)
    """
    if HAS_PANDAS:
        emotions = df['emotion_E'].values
    else:
        emotions = np.array([r['emotion_E'] for r in df.rows])

    total = len(emotions)
    if total == 0:
        return {}

    # 各状态统计
    extreme_panic = np.sum(emotions < PANIC_THRESHOLD)
    anxiety = np.sum((emotions >= PANIC_THRESHOLD) & (emotions < NEUTRAL_LOW))
    neutral = np.sum((emotions >= NEUTRAL_LOW) & (emotions <= NEUTRAL_HIGH))
    confidence = np.sum((emotions > NEUTRAL_HIGH) & (emotions <= OPTIMISM_THRESHOLD))
    extreme_optimism = np.sum(emotions > OPTIMISM_THRESHOLD)

    # 占比
    extreme_panic_ratio = float(extreme_panic / total)
    anxiety_ratio = float(anxiety / total)
    neutral_ratio = float(neutral / total)
    confidence_ratio = float(confidence / total)
    extreme_optimism_ratio = float(extreme_optimism / total)

    # 极端状态总占比 (越低越健康)
    extreme_total_ratio = extreme_panic_ratio + extreme_optimism_ratio

    # 情绪健康度 (0-100, 越高越健康)
    emotion_health_score = (1.0 - extreme_total_ratio) * 100

    # 情绪波动度 (标准差)
    emotion_volatility = float(np.std(emotions))

    # 按节点细分
    per_node = {}
    if HAS_PANDAS:
        for aid in NODE_IDS:
            sub = df[df['agent_id'] == aid]
            e = sub['emotion_E'].values
            if len(e) > 0:
                per_node[NODE_NAMES_CN[aid]] = {
                    'extreme_panic_ratio': float(np.sum(e < PANIC_THRESHOLD) / len(e)),
                    'extreme_optimism_ratio': float(np.sum(e > OPTIMISM_THRESHOLD) / len(e)),
                    'mean_emotion': float(np.mean(e)),
                    'std_emotion': float(np.std(e)),
                }
    else:
        emo_by_node = {aid: [] for aid in NODE_IDS}
        for r in df.rows:
            emo_by_node[r['agent_id']].append(r['emotion_E'])
        for aid in NODE_IDS:
            e = np.array(emo_by_node[aid])
            if len(e) > 0:
                per_node[NODE_NAMES_CN[aid]] = {
                    'extreme_panic_ratio': float(np.sum(e < PANIC_THRESHOLD) / len(e)),
                    'extreme_optimism_ratio': float(np.sum(e > OPTIMISM_THRESHOLD) / len(e)),
                    'mean_emotion': float(np.mean(e)),
                    'std_emotion': float(np.std(e)),
                }

    return {
        'total_samples': int(total),
        'state_distribution': {
            '极端恐慌 (E<-0.5)': extreme_panic_ratio,
            '焦虑 (-0.5≤E<-0.1)': anxiety_ratio,
            '中性 (-0.1≤E≤0.1)': neutral_ratio,
            '自信 (0.1<E≤0.5)': confidence_ratio,
            '过度乐观 (E>0.5)': extreme_optimism_ratio,
        },
        'extreme_state_ratio': extreme_total_ratio,
        'emotion_health_score': emotion_health_score,
        'emotion_volatility': emotion_volatility,
        'per_node': per_node,
    }


# ============================================================
# LaTeX 表格生成
# ============================================================

def generate_latex_report(traditional: Dict, loss_aversion: Dict,
                            recovery: Dict, emotion_health: Dict) -> str:
    """生成 LaTeX 表格源码"""

    latex = r"""\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage{ctex}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{array}
\usepackage{amsmath}
\usepackage{geometry}
\geometry{a4paper, margin=2cm}

\title{多智能体供应链协同系统综合评估报告}
\author{}
\date{}

\begin{document}
\maketitle

\section*{维度一: 传统供应链指标}

\subsection*{表1. 三组实验牛鞭效应方差比对比}

\begin{table}[h]
\centering
\caption{三组实验各节点牛鞭效应方差比 (BWE = var($q$)/var($D$))}
\label{tab:bwe}
\begin{tabular}{lcccccc}
\toprule
实验组 & 零售商 & 批发商 & 分销商 & 制造商 & 平均 & 总成本 \\
\midrule
"""

    # 表1: BWE 对比
    for exp_key in ['baseline', 'exp1', 'exp2']:
        data = traditional[exp_key]
        bwe = data['bwe_per_node']
        row = f"{data['name']}"
        for node in ['零售商', '批发商', '分销商', '制造商']:
            row += f" & {bwe[node]:.2f}"
        row += f" & {data['avg_bwe']:.2f} & {data['total_cost']:.2f}"
        row += r" \\"
        latex += row + "\n"

    latex += r"""\bottomrule
\end{tabular}
\end{table}

\subsection*{表2. 三组实验服务水平 (SL) 对比}

\begin{table}[h]
\centering
\caption{三组实验各节点服务水平 (SL = fulfilled/demand)}
\label{tab:sl}
\begin{tabular}{lccccc}
\toprule
实验组 & 零售商 & 批发商 & 分销商 & 制造商 & 平均 \\
\midrule
"""

    # 表2: SL 对比
    for exp_key in ['baseline', 'exp1', 'exp2']:
        data = traditional[exp_key]
        sl = data['sl_per_node']
        row = f"{data['name']}"
        for node in ['零售商', '批发商', '分销商', '制造商']:
            row += f" & {sl[node]:.4f}"
        row += f" & {data['avg_sl']:.4f}"
        row += r" \\"
        latex += row + "\n"

    latex += r"""\bottomrule
\end{tabular}
\end{table}

\section*{维度二: 行为经济学指标}

\subsection*{表3. 损失厌恶程度量化 (Exp\_2 vs 理论最优)}

\begin{table}[h]
\centering
\caption{损失厌恶程度: 实际订货量与理论最优订货量的偏差 (基于 Exp\_2 多智能体实验)}
\label{tab:loss_aversion}
\begin{tabular}{lccccc}
\toprule
节点 & 实际订货量 & 理论最优 & 平均绝对偏差 & 损失厌恶率 & 过度订货比例 \\
& $\bar{q}_{actual}$ & $\bar{q}_{optimal}$ & MAE & MAE/$\bar{q}_{optimal}$ & $P(q>q^*)$ \\
\midrule
"""

    # 表3: 损失厌恶
    for node in ['零售商', '批发商', '分销商', '制造商']:
        d = loss_aversion['per_node'][node]
        row = (f"{node} & {d['avg_q_actual']:.2f} & {d['avg_q_optimal']:.2f} & "
               f"{d['mae']:.2f} & {d['loss_aversion_ratio']:.4f} & "
               f"{d['over_order_ratio']:.4f}")
        row += r" \\"
        latex += row + "\n"

    latex += (f"\\midrule\n"
              f"系统平均 & - & - & - & "
              f"{loss_aversion['system_avg_loss_aversion']:.4f} & "
              f"{loss_aversion['system_avg_over_order_ratio']:.4f}"
              r" \\")
    latex += "\n"

    latex += r"""\bottomrule
\end{tabular}
\end{table}

\textbf{说明:}
\begin{itemize}
    \item 损失厌恶率 = MAE / $\bar{q}_{optimal}$, 衡量实际决策偏离理性最优的程度
    \item 过度订货比例 $P(q > q^*)$ 反映"因害怕缺货而过度订货"的倾向 (损失厌恶核心表现)
    \item 理论最优 $\bar{q}_{optimal}$ 取该节点面临的下游需求均值 (AR(1) 需求下理性订至点策略订货量应趋近需求)
\end{itemize}

\section*{维度三: 系统鲁棒性指标}

\subsection*{表4. 动态事件下的恢复时间 (Recovery Time)}

\begin{table}[h]
\centering
\caption{系统在需求突变与供应中断事件下的恢复时间 (基于 Exp\_2)}
\label{tab:recovery}
\begin{tabular}{lcccc}
\toprule
事件类型 & 事件次数 & 平均恢复周期 & 标准差 & 最长恢复 \\
\midrule
"""

    # 表4: 恢复时间
    latex += (f"需求突变 (Demand Shock) & {recovery['n_demand_shock_events']} & "
              f"{recovery['recovery_time_demand_shock']['mean']:.1f} & "
              f"{recovery['recovery_time_demand_shock']['std']:.1f} & "
              f"{recovery['recovery_time_demand_shock']['max']:.0f}"
              r" \\" + "\n")

    latex += (f"供应中断 (Supply Disruption) & {recovery['n_supply_disruption_events']} & "
              f"{recovery['recovery_time_supply_disruption']['mean']:.1f} & "
              f"{recovery['recovery_time_supply_disruption']['std']:.1f} & "
              f"{recovery['recovery_time_supply_disruption']['max']:.0f}"
              r" \\" + "\n")

    latex += (f"\\midrule\n"
              f"总体 & {recovery['n_total_events']} & "
              f"{recovery['overall_recovery_time']['mean']:.1f} & "
              f"{recovery['overall_recovery_time']['std']:.1f} & -"
              r" \\" + "\n")

    latex += r"""\bottomrule
\end{tabular}
\end{table}

\textbf{恢复判定标准:} 事件发生后, 系统连续 5 周期满足
$|q_t - q_{baseline}| \leq 20\% \cdot |q_{baseline}|$ 视为恢复稳态,
其中 $q_{baseline}$ 为事件前 50 周期的平均订货量.

\section*{维度四: 情绪健康度指标}

\subsection*{表5. 系统情绪状态分布 (基于 Exp\_2)}

\begin{table}[h]
\centering
\caption{系统情绪状态时长占比 (基于 Exp\_2 多智能体实验)}
\label{tab:emotion_health}
\begin{tabular}{lc}
\toprule
情绪状态 & 占比 \\
\midrule
"""

    # 表5: 情绪健康度
    for state, ratio in emotion_health['state_distribution'].items():
        latex += f"{state} & {ratio*100:.2f}\\% \\\\\n"

    latex += (f"\\midrule\n"
              f"极端状态总占比 (恐慌+乐观) & "
              f"{emotion_health['extreme_state_ratio']*100:.2f}\\% \\\\\n")
    latex += (f"情绪健康度 (100 - 极端占比) & "
              f"{emotion_health['emotion_health_score']:.2f} \\\\\n")
    latex += (f"情绪波动度 (标准差) & "
              f"{emotion_health['emotion_volatility']:.4f} \\\\\n")

    latex += r"""\bottomrule
\end{tabular}
\end{table}

\subsection*{表6. 各节点情绪健康度细分}

\begin{table}[h]
\centering
\caption{各节点情绪状态分布与波动度}
\label{tab:emotion_per_node}
\begin{tabular}{lcccc}
\toprule
节点 & 极端恐慌占比 & 过度乐观占比 & 平均情绪 & 情绪波动度 \\
\midrule
"""

    # 表6: 节点级情绪
    for node in ['零售商', '批发商', '分销商', '制造商']:
        if node in emotion_health['per_node']:
            d = emotion_health['per_node'][node]
            latex += (f"{node} & {d['extreme_panic_ratio']*100:.2f}\\% & "
                      f"{d['extreme_optimism_ratio']*100:.2f}\\% & "
                      f"{d['mean_emotion']:.4f} & {d['std_emotion']:.4f}"
                      r" \\" + "\n")

    latex += r"""\bottomrule
\end{tabular}
\end{table}

\section*{综合结论}

\begin{enumerate}
    \item \textbf{传统指标}: Exp\_2 (多智能体+情绪+协同) 在分销商 BWE 上较 Baseline 降低
          """ + f"{(1 - traditional['exp2']['bwe_per_node']['分销商']/traditional['baseline']['bwe_per_node']['分销商'])*100:.1f}" + r"""\%,
          制造商 BWE 降低
          """ + f"{(1 - traditional['exp2']['bwe_per_node']['制造商']/traditional['baseline']['bwe_per_node']['制造商'])*100:.1f}" + r"""\%.
    \item \textbf{行为经济学}: 系统平均损失厌恶率为
          """ + f"{loss_aversion['system_avg_loss_aversion']:.4f}" + r""",
          过度订货比例 """ + f"{loss_aversion['system_avg_over_order_ratio']*100:.1f}" + r"""\%,
          表明情绪扰动确实导致决策偏离理性最优.
    \item \textbf{鲁棒性}: 系统在 """ + f"{recovery['n_total_events']}" + r""" 次动态事件下平均恢复时间为
          """ + f"{recovery['overall_recovery_time']['mean']:.1f}" + r""" 周期,
          多数事件达到观察窗口上限, 表明频繁的突发事件使系统难以完全回到稳态,
          需进一步引入持续学习与情绪调节机制缩短恢复时间.
    \item \textbf{情绪健康}: 系统情绪健康度为
          """ + f"{emotion_health['emotion_health_score']:.2f}" + r""",
          极端状态占比 """ + f"{emotion_health['extreme_state_ratio']*100:.2f}" + r"""\%,
          表明情绪模块整体处于可控范围但仍有优化空间.
\end{enumerate}

\end{document}
"""

    return latex


# ============================================================
# 主程序
# ============================================================

def main():
    print("=" * 70)
    print("多维度综合评估报告生成器")
    print("=" * 70)

    # 数据加载
    print("\n[1/5] 加载实验数据...")
    summary, df = load_data()
    print(f"  实验摘要: {SUMMARY_FILE}")
    print(f"  详细数据: {DETAIL_FILE} ({len(df)} 条记录)")

    # 维度 1: 传统供应链指标
    print("\n[2/5] 计算传统供应链指标...")
    traditional = compute_traditional_metrics(summary)
    for exp_key in ['baseline', 'exp1', 'exp2']:
        d = traditional[exp_key]
        print(f"  {d['name']}: 平均BWE={d['avg_bwe']:.2f}, "
              f"总成本={d['total_cost']:.2f}, 平均SL={d['avg_sl']:.4f}")

    # 维度 2: 行为经济学指标
    print("\n[3/5] 计算行为经济学指标 (损失厌恶程度)...")
    loss_aversion = compute_loss_aversion(summary, df)
    print(f"  系统平均损失厌恶率: {loss_aversion['system_avg_loss_aversion']:.4f}")
    print(f"  系统平均过度订货比例: {loss_aversion['system_avg_over_order_ratio']*100:.2f}%")
    for node, d in loss_aversion['per_node'].items():
        print(f"    {node}: 实际={d['avg_q_actual']:.2f}, "
              f"最优={d['avg_q_optimal']:.2f}, "
              f"损失厌恶率={d['loss_aversion_ratio']:.4f}")

    # 维度 3: 系统鲁棒性指标
    print("\n[4/5] 计算系统鲁棒性指标 (恢复时间)...")
    recovery = compute_recovery_time(df)
    print(f"  需求突变事件: {recovery['n_demand_shock_events']} 次, "
          f"平均恢复 {recovery['recovery_time_demand_shock']['mean']:.1f} 周期")
    print(f"  供应中断事件: {recovery['n_supply_disruption_events']} 次, "
          f"平均恢复 {recovery['recovery_time_supply_disruption']['mean']:.1f} 周期")
    print(f"  总体平均恢复时间: {recovery['overall_recovery_time']['mean']:.1f} 周期")

    # 维度 4: 情绪健康度指标
    print("\n[5/5] 计算情绪健康度指标...")
    emotion_health = compute_emotion_health(df)
    print(f"  总样本数: {emotion_health['total_samples']}")
    print(f"  状态分布:")
    for state, ratio in emotion_health['state_distribution'].items():
        print(f"    {state}: {ratio*100:.2f}%")
    print(f"  极端状态总占比: {emotion_health['extreme_state_ratio']*100:.2f}%")
    print(f"  情绪健康度: {emotion_health['emotion_health_score']:.2f}")
    print(f"  情绪波动度: {emotion_health['emotion_volatility']:.4f}")

    # 生成 LaTeX 报告
    print("\n[生成] LaTeX 报告...")
    latex = generate_latex_report(traditional, loss_aversion, recovery, emotion_health)
    with open(TEX_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(latex)
    print(f"  已保存: {TEX_OUTPUT}")

    # 保存 JSON 结构化数据
    full_report = {
        'traditional_metrics': traditional,
        'loss_aversion': loss_aversion,
        'recovery_time': recovery,
        'emotion_health': emotion_health,
    }
    with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(full_report, f, indent=2, ensure_ascii=False, default=str)
    print(f"  已保存: {JSON_OUTPUT}")

    print("\n" + "=" * 70)
    print("[完成] 综合评估报告生成完成!")
    print("=" * 70)
    print(f"\nLaTeX 文件可直接编译: {TEX_OUTPUT}")
    print(f"结构化数据: {JSON_OUTPUT}")


if __name__ == '__main__':
    main()

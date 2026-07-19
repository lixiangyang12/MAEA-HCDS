"""
实验数据集加载器 (Dataset Loader)
=================================

功能:
    统一加载本项目的所有实验结果数据 (CSV + JSON),
    方便其他研究者直接调用实验结果进行二次分析。

数据集说明:
    1. 归因分析_详细数据.csv   - Exp_2 多智能体实验逐周期数据 (8000条)
       字段: t, node_id, node_name, order_q, demand, net_stock, fulfilled,
              emotion_E, stockout_flag, demand_shock_flag, supply_disruption_flag

    2. 实验结果摘要.json        - 三组实验汇总指标 (BWE/SL/成本/情绪方差)
    3. 灾难性遗忘_结果摘要.json  - EWC + 情绪感知噪声实验结果
    4. 综合评估报告.json        - 多维度评估指标 (传统/行为经济学/鲁棒性/情绪健康)

使用示例:
    from load_dataset import load_all, load_attribution_data

    # 加载全部数据集
    data = load_all()

    # 仅加载归因分析数据 (DataFrame)
    df = load_attribution_data()
    print(df.describe())

    # 获取三组实验BWE对比
    summary = load_experiment_summary()
    print(summary['experiments']['baseline']['bwe'])

作者: 杨理想
许可证: MIT
"""

import json
import os
from typing import Dict, Any, Optional

import pandas as pd


# ============================================================
# 路径配置
# ============================================================

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_DATA_FILES = {
    'attribution_csv': '归因分析_详细数据.csv',
    'experiment_summary': '实验结果摘要.json',
    'forgetting_summary': '灾难性遗忘_结果摘要.json',
    'evaluation_report': '综合评估报告.json',
}


def _resolve_path(key: str) -> str:
    """解析数据文件路径"""
    filename = _DATA_FILES.get(key)
    if filename is None:
        raise KeyError(f"未知数据集: {key}, 可选: {list(_DATA_FILES.keys())}")
    path = os.path.join(_BASE_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"数据文件不存在: {path}")
    return path


# ============================================================
# 数据加载函数
# ============================================================

def load_attribution_data(encoding: str = 'utf-8-sig') -> pd.DataFrame:
    """
    加载归因分析详细数据 (Exp_2 多智能体实验逐周期记录)

    返回:
        DataFrame, 包含以下字段:
            - t:                    周期编号
            - node_id:              节点标识 (retailer/wholesaler/distributor/manufacturer)
            - node_name:            节点中文名
            - order_q:              订货量
            - demand:               需求量
            - net_stock:            期末净库存
            - fulfilled:            实际履约量
            - emotion_E:            情绪状态值 E_t ∈ [-1, 1]
            - stockout_flag:        缺货标记 (1=缺货)
            - demand_shock_flag:    需求突变标记
            - supply_disruption_flag: 供应中断标记
    """
    path = _resolve_path('attribution_csv')
    df = pd.read_csv(path, encoding=encoding)
    return df


def load_experiment_summary() -> Dict[str, Any]:
    """
    加载三组对比实验汇总结果

    返回:
        dict, 结构:
            config: {total_periods, train_steps, seed}
            experiments:
                baseline: {bwe, avg_cost, sl, total_cost, emotion_variance, ...}
                exp1:    {bwe, avg_cost, sl, total_cost, emotion_variance, ...}
                exp2:    {bwe, avg_cost, sl, total_cost, emotion_variance, ...}
            synergy_gain_pct: 协同收益百分比
    """
    path = _resolve_path('experiment_summary')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_forgetting_results() -> Dict[str, Any]:
    """
    加载灾难性遗忘测试结果 (EWC + 情绪感知噪声)

    返回:
        dict, 包含:
            config: 实验配置 (Task1/Task2参数, EWC lambda, 噪声σ)
            summary: 三组实验的BWE/SL/奖励变化
            forgetting: 遗忘率
            perception_stats: 情绪感知误差统计
            ewc_stats: Fisher矩阵统计
    """
    path = _resolve_path('forgetting_summary')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_evaluation_report() -> Dict[str, Any]:
    """
    加载多维度综合评估报告

    返回:
        dict, 包含4个维度:
            traditional:    传统供应链指标 (BWE/SL/成本)
            loss_aversion:   行为经济学指标 (损失厌恶率)
            recovery:        系统鲁棒性指标 (恢复时间)
            emotion_health:  情绪健康度指标
    """
    path = _resolve_path('evaluation_report')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_all() -> Dict[str, Any]:
    """
    加载全部实验数据集 (一站式加载)

    返回:
        dict, 包含所有数据集的字典:
            'attribution':   DataFrame (逐周期数据)
            'experiment':     dict (三组实验汇总)
            'forgetting':     dict (EWC遗忘测试)
            'evaluation':     dict (综合评估报告)
    """
    return {
        'attribution': load_attribution_data(),
        'experiment': load_experiment_summary(),
        'forgetting': load_forgetting_results(),
        'evaluation': load_evaluation_report(),
    }


def list_available_datasets() -> Dict[str, str]:
    """列出所有可用数据集及其路径"""
    result = {}
    for key, filename in _DATA_FILES.items():
        path = os.path.join(_BASE_DIR, filename)
        result[key] = {
            'filename': filename,
            'path': path,
            'exists': os.path.exists(path),
        }
    return result


# ============================================================
# 自检
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("数据集加载器自检")
    print("=" * 60)

    # 列出可用数据集
    print("\n[可用数据集]")
    datasets = list_available_datasets()
    for key, info in datasets.items():
        status = "[OK]" if info['exists'] else "[缺失]"
        print(f"  {status} {key}: {info['filename']}")

    # 加载归因分析数据
    print("\n[归因分析数据]")
    try:
        df = load_attribution_data()
        print(f"  形状: {df.shape}")
        print(f"  字段: {list(df.columns)}")
        print(f"  节点: {df['node_name'].unique() if 'node_name' in df.columns else 'N/A'}")
    except Exception as e:
        print(f"  [错误] {e}")

    # 加载实验摘要
    print("\n[实验结果摘要]")
    try:
        summary = load_experiment_summary()
        print(f"  实验组: {list(summary['experiments'].keys())}")
        for exp_name, exp_data in summary['experiments'].items():
            bwe = exp_data.get('bwe', {})
            print(f"    {exp_name}: 分销商BWE={bwe.get('3', 'N/A'):.2f}")
    except Exception as e:
        print(f"  [错误] {e}")

    # 加载遗忘测试结果
    print("\n[灾难性遗忘结果]")
    try:
        forgetting = load_forgetting_results()
        print(f"  配置: {forgetting.get('config', {})}")
    except Exception as e:
        print(f"  [错误] {e}")

    print("\n" + "=" * 60)
    print("[OK] 数据集加载器自检完成!")
    print("=" * 60)

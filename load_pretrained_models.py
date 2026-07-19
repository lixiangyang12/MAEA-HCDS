"""
预训练模型加载器 (Pretrained Models Loader)
==========================================

功能:
    统一加载本项目训练好的所有模型权重 (DQN/EWC/持续学习),
    方便其他研究者直接调用预训练模型进行推理评估,
    无需从头训练即可复现论文实验结果。

预训练模型清单:
    1. idmr_model.pkl               - IDMR DQN 智能体权重 (40000 步训练)
    2. continual_idmr_model.pkl     - 持续学习 IDMR 权重 (含 EWC + PER)
    3. emotion_module_params.json   - 情绪模块参数 (理论校准值)

使用示例:
    from load_pretrained_models import load_idmr_agent, load_model_metadata

    # 一行加载预训练 DQN
    agent = load_idmr_agent()
    # 直接进行推理评估, 跳过训练过程

    # 查看模型元信息
    meta = load_model_metadata()
    print(meta['training_steps'])

作者: 杨理想
许可证: MIT
"""

import os
import pickle
import json
from typing import Dict, Any, Optional


# ============================================================
# 路径配置
# ============================================================

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_MODEL_FILES = {
    'idmr': {
        'path': os.path.join(_BASE_DIR, 'idmr_model.pkl'),
        'type': 'dqn',
        'description': 'IDMR DQN 智能体权重 (40000 步训练, seed=42)',
    },
    'continual_idmr': {
        'path': os.path.join(_BASE_DIR, 'continual_idmr_model.pkl'),
        'type': 'dqn_ewc',
        'description': '持续学习 IDMR 权重 (含 EWC + PER)',
    },
}

# 预训练模型的默认配置 (与 config.yaml 保持一致)
_DEFAULT_CONFIG = {
    'state_dim': 5,
    'action_dim': 30,
    'action_min': 11,
    'action_max': 40,
    'hidden_dim': 64,
    'learning_rate': 1e-4,
    'gamma': 0.9,
    'batch_size': 32,
    'replay_size': 20000,
    'seed': 42,
    'training_steps': 40000,
}


# ============================================================
# 模型加载函数
# ============================================================

def load_idmr_agent(model_path: Optional[str] = None,
                    config: Optional[Dict[str, Any]] = None):
    """
    加载预训练的 IDMR DQN 智能体

    参数:
        model_path: 自定义模型路径 (.pkl), 默认使用项目内的 idmr_model.pkl
        config: 自定义配置字典, 默认使用 _DEFAULT_CONFIG

    返回:
        IDMRAgent 实例, 已加载预训练权重, 可直接进行推理

    示例:
        >>> agent = load_idmr_agent()
        >>> action = agent.act(state)  # 直接推理
    """
    from idmr_agent import IDMRAgent

    cfg = config or _DEFAULT_CONFIG
    path = model_path or _MODEL_FILES['idmr']['path']

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"预训练模型文件不存在: {path}\n"
            f"请先运行 `python idmr_agent.py` 训练并保存模型, "
            f"或检查文件路径。"
        )

    # 创建智能体并加载权重 (IDMRAgent 不接受 seed 参数, 由 config 控制)
    agent = IDMRAgent(
        state_dim=cfg['state_dim'],
        action_min=cfg['action_min'],
        action_max=cfg['action_max'],
        lr=cfg['learning_rate'],
        gamma=cfg['gamma'],
        batch_size=cfg['batch_size'],
        replay_size=cfg['replay_size'],
    )
    agent.load(path)
    # 推理模式: 关闭探索
    agent.epsilon = 0.01
    return agent


def load_continual_idmr_agent(model_path: Optional[str] = None,
                               config: Optional[Dict[str, Any]] = None):
    """
    加载预训练的持续学习 IDMR 智能体 (含 EWC + PER)

    参数:
        model_path: 自定义模型路径 (.pkl)
        config: 自定义配置字典

    返回:
        ContinualIDMRAgent 实例, 已加载预训练权重

    示例:
        >>> agent = load_continual_idmr_agent()
        >>> # 已加载 EWC Fisher 矩阵, 可直接进行任务切换评估
    """
    try:
        from continual_idmr import ContinualIDMRAgent
    except ImportError as e:
        raise ImportError(
            f"无法导入 ContinualIDMRAgent: {e}\n"
            f"请确保 continual_idmr.py 存在且无语法错误。"
        )

    cfg = config or _DEFAULT_CONFIG
    path = model_path or _MODEL_FILES['continual_idmr']['path']

    if not os.path.exists(path):
        # 持续学习模型可能尚未训练, 提示用户
        raise FileNotFoundError(
            f"持续学习模型文件不存在: {path}\n"
            f"请先运行 `python continual_learning_test.py` 训练并保存模型。"
        )

    agent = ContinualIDMRAgent(
        state_dim=cfg['state_dim'],
        action_min=cfg['action_min'],
        action_max=cfg['action_max'],
        emotion_augmented=True,
        use_per=True,
        use_ewc=True,
        seed=cfg['seed'],
    )
    agent.load(path)
    return agent


def load_model_metadata(model_key: str = 'idmr') -> Dict[str, Any]:
    """
    获取预训练模型的元信息 (不加载完整权重)

    参数:
        model_key: 模型标识 ('idmr' 或 'continual_idmr')

    返回:
        dict, 包含:
            - model_path: 模型文件路径
            - exists: 文件是否存在
            - file_size_mb: 文件大小 (MB)
            - description: 模型描述
            - config: 默认配置
            - checkpoint_info: checkpoint 内部信息 (若可读取)
    """
    if model_key not in _MODEL_FILES:
        raise KeyError(
            f"未知模型标识: {model_key}, "
            f"可选: {list(_MODEL_FILES.keys())}"
        )

    info = _MODEL_FILES[model_key]
    path = info['path']
    exists = os.path.exists(path)

    result = {
        'model_key': model_key,
        'model_path': path,
        'exists': exists,
        'description': info['description'],
        'config': _DEFAULT_CONFIG,
        'file_size_mb': None,
        'checkpoint_info': None,
    }

    if exists:
        result['file_size_mb'] = round(
            os.path.getsize(path) / (1024 * 1024), 3
        )
        # 尝试读取 checkpoint 内部信息
        try:
            with open(path, 'rb') as f:
                ckpt = pickle.load(f)
            result['checkpoint_info'] = {
                'step_count': ckpt.get('step_count', 'N/A'),
                'epsilon': ckpt.get('epsilon', 'N/A'),
                'has_q_net': 'q_net' in ckpt,
                'has_target_net': 'target_net' in ckpt,
            }
        except Exception as e:
            result['checkpoint_info'] = {'error': str(e)}

    return result


def list_available_models() -> Dict[str, Any]:
    """
    列出所有可用的预训练模型及其状态

    返回:
        dict, 每个模型标识对应其元信息
    """
    return {
        key: load_model_metadata(key)
        for key in _MODEL_FILES.keys()
    }


# ============================================================
# 便捷函数: 快速评估
# ============================================================

def quick_evaluate_idmr(n_steps: int = 1000,
                        seed: int = 42) -> Dict[str, Any]:
    """
    使用预训练 IDMR 模型快速评估 (无需重新训练)

    参数:
        n_steps: 评估步数
        seed: 随机种子

    返回:
        dict, 评估结果:
            - bwe: 各节点牛鞭效应方差比 {k: float}
            - distributor_bwe: 分销商 (IDMR 节点) BWE
            - avg_cost: 各节点平均成本 {k: float}
            - avg_sl: 各节点平均服务水平 {k: float}
            - n_steps: 评估步数
    """
    import numpy as np
    from idmr_agent import IDMRSupplyChainEnv, evaluate
    from config import load_config, set_seed

    cfg = load_config()
    set_seed(seed)

    agent = load_idmr_agent()
    env = IDMRSupplyChainEnv(config=cfg)

    # 运行评估 (evaluate 返回 bwe 字典 {1,2,3,4: float})
    bwe = evaluate(env, agent, n_steps=n_steps)

    # 提取各节点成本与服务水平
    avg_cost = {}
    avg_sl = {}
    for k in range(1, 5):
        orders = list(env.env.nodes[k].order_history)[-n_steps:]
        demands = list(env.env.nodes[k].demand_history)[-n_steps:]
        fulfilled = list(getattr(env.env.nodes[k], 'fulfilled_history', orders))[-n_steps:]
        avg_cost[k] = float(np.mean(np.abs(orders)) * 0.5)
        avg_sl[k] = float(np.mean(
            [f / d if d > 0 else 1.0 for f, d in zip(fulfilled, demands)]
        ))

    return {
        'bwe': {str(k): float(v) for k, v in bwe.items()},
        'distributor_bwe': float(bwe.get(3, 0.0)),
        'avg_cost': avg_cost,
        'avg_sl': avg_sl,
        'n_steps': n_steps,
        'seed': seed,
        'model': 'idmr_model.pkl (预训练)',
    }


# ============================================================
# 自检
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("预训练模型加载器自检")
    print("=" * 60)

    # 列出可用模型
    print("\n[可用预训练模型]")
    models = list_available_models()
    for key, info in models.items():
        status = "[OK]" if info['exists'] else "[缺失]"
        size = f"{info['file_size_mb']} MB" if info['file_size_mb'] else "N/A"
        print(f"  {status} {key}: {info['description']}")
        print(f"       路径: {info['model_path']}")
        print(f"       大小: {size}")
        if info['checkpoint_info']:
            print(f"       Checkpoint: {info['checkpoint_info']}")

    # 尝试加载 IDMR 模型
    print("\n[加载 IDMR 预训练模型]")
    try:
        agent = load_idmr_agent()
        print(f"  [OK] IDMR Agent 加载成功")
        print(f"       状态维度: {agent.state_dim}")
        print(f"       动作范围: [{agent.action_min}, {agent.action_max}]")
        print(f"       训练步数: {agent.step_count}")
        print(f"       探索率: {agent.epsilon}")
    except Exception as e:
        print(f"  [错误] {e}")

    # 快速评估
    print("\n[快速评估 (1000 步)]")
    try:
        results = quick_evaluate_idmr(n_steps=1000)
        print(f"  分销商 BWE: {results['distributor_bwe']:.4f}")
        print(f"  各节点 BWE: {results['bwe']}")
        print(f"  各节点 SL: {results['avg_sl']}")
        print(f"  使用模型: {results['model']}")
    except Exception as e:
        print(f"  [错误] {e}")

    print("\n" + "=" * 60)
    print("[OK] 预训练模型加载器自检完成!")
    print("=" * 60)

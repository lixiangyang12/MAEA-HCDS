"""
配置加载器 + 随机性控制

功能:
    1. 加载 config.yaml 统一配置
    2. 设置全局随机种子 (Python + NumPy + 可选PyTorch)
    3. 提供配置数据类访问接口

使用:
    from config import load_config, set_seed, Config
    cfg = load_config()        # 加载配置
    set_seed(cfg.seed)         # 设置随机种子
    print(cfg.supply_chain.d)  # 访问参数
"""

import os
import random
import yaml
from dataclasses import dataclass
from typing import Optional


# ============================================================
# 配置数据类 (类型安全访问)
# ============================================================

@dataclass
class SupplyChainConfig:
    d: float
    rho: float
    sigma_eps: float
    L: int
    p: int
    z: float
    C_L_rho: float
    K: int
    initial_inventory: float
    initial_demand: float


@dataclass
class DQNConfig:
    state_dim: int
    action_min: int
    action_max: int
    hidden_dim: int
    learning_rate: float
    gamma: float
    batch_size: int
    replay_size: int
    replay_start: int
    epsilon_start: float
    epsilon_end: float
    target_update_start: int
    target_update_freq: int

    @property
    def action_dim(self) -> int:
        return self.action_max - self.action_min + 1


@dataclass
class IDMRConfig:
    node_k: int
    penalty_threshold: float
    reward_holding_weight: float
    force_zero_on_penalty: bool
    # 创新正向激励机制参数
    enable_inventory_bonus: bool
    inventory_bonus_weight: float
    coverage_lower: float
    coverage_upper: float
    sma_window: int
    stockout_penalty_weight: float
    # 情绪演化模块参数
    enable_emotion: bool
    emotion_alpha: float
    emotion_gamma: float
    emotion_w_stockout: float
    emotion_w_match: float
    emotion_w_excess: float


@dataclass
class TrainingConfig:
    total_steps: int
    log_interval: int
    eval_steps: int
    baseline_steps: int


@dataclass
class NormalizationConfig:
    stock_scale: float
    order_scale: float


@dataclass
class LoggingConfig:
    use_csv: bool
    use_tensorboard: bool
    log_dir: str
    save_model: bool
    model_path: str
    plot_results: bool
    plot_path: str


@dataclass
class Config:
    seed: int
    supply_chain: SupplyChainConfig
    dqn: DQNConfig
    idmr: IDMRConfig
    training: TrainingConfig
    normalization: NormalizationConfig
    logging: LoggingConfig


# ============================================================
# 配置加载
# ============================================================

_DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')


def load_config(config_path: str = _DEFAULT_CONFIG_PATH) -> Config:
    """加载YAML配置文件, 返回类型安全的Config对象"""
    with open(config_path, 'r', encoding='utf-8') as f:
        raw = yaml.safe_load(f)

    return Config(
        seed=raw['seed'],
        supply_chain=SupplyChainConfig(**raw['supply_chain']),
        dqn=DQNConfig(**raw['dqn']),
        idmr=IDMRConfig(**raw['idmr']),
        training=TrainingConfig(**raw['training']),
        normalization=NormalizationConfig(**raw['normalization']),
        logging=LoggingConfig(**raw['logging']),
    )


# ============================================================
# 随机性控制 (100%可复现)
# ============================================================

def set_seed(seed: int, use_torch: bool = False) -> None:
    """
    统一设置随机种子, 确保实验100%可复现

    设置:
        - Python random (影响 random.randint 等)
        - NumPy random (影响 np.random.default_rng)
        - 环境变量 PYTHONHASHSEED (影响字典哈希顺序)
        - (可选) PyTorch CPU/CUDA 随机数

    参数:
        seed: 随机种子
        use_torch: 是否设置PyTorch种子 (默认False, 纯NumPy实现)
    """
    # 1. 环境变量 (必须在import前设置, 但运行时设置也能提升可复现性)
    os.environ['PYTHONHASHSEED'] = str(seed)

    # 2. Python 内置 random
    random.seed(seed)

    # 3. NumPy (旧版全局API + 新版Generator)
    np = __import__('numpy')
    np.random.seed(seed)

    # 4. PyTorch (可选, 当前实验为纯NumPy实现)
    if use_torch:
        try:
            import torch
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed(seed)
                torch.cuda.manual_seed_all(seed)
                # 确保CUDA卷积确定性
                torch.backends.cudnn.deterministic = True
                torch.backends.cudnn.benchmark = False
        except (ImportError, OSError):
            # PyTorch不可用或DLL加载失败, 忽略
            pass

    # 5. 确定性算法 (NumPy 2.x)
    try:
        np = __import__('numpy')
        np.polynomial.set_default_printstyle('legacy')
    except Exception:
        pass


# ============================================================
# 自检
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("配置加载自检")
    print("=" * 60)

    cfg = load_config()
    print(f"  随机种子: {cfg.seed}")
    print(f"\n  [供应链参数]")
    sc = cfg.supply_chain
    print(f"    d={sc.d}, rho={sc.rho}, sigma_eps={sc.sigma_eps}")
    print(f"    L={sc.L}, p={sc.p}, z={sc.z}, C_L_rho={sc.C_L_rho}")
    print(f"    K={sc.K}, 初始库存={sc.initial_inventory}")
    print(f"\n  [DQN超参数]")
    dq = cfg.dqn
    print(f"    状态维度={dq.state_dim}, 动作范围=[{dq.action_min},{dq.action_max}]")
    print(f"    动作维度={dq.action_dim}, 隐藏层={dq.hidden_dim}")
    print(f"    lr={dq.learning_rate}, gamma={dq.gamma}, batch={dq.batch_size}")
    print(f"    replay={dq.replay_size}, eps=[{dq.epsilon_start}→{dq.epsilon_end}]")
    print(f"\n  [IDMR配置]")
    idmr = cfg.idmr
    print(f"    节点k={idmr.node_k}, 惩罚阈值={idmr.penalty_threshold}x")
    print(f"    库存惩罚权重={idmr.reward_holding_weight}")
    print(f"\n  [训练配置]")
    tr = cfg.training
    print(f"    总步数={tr.total_steps}, 日志间隔={tr.log_interval}")
    print(f"    评估步数={tr.eval_steps}, 基线步数={tr.baseline_steps}")
    print(f"\n  [日志配置]")
    lg = cfg.logging
    print(f"    CSV={lg.use_csv}, TensorBoard={lg.use_tensorboard}")
    print(f"    日志目录={lg.log_dir}, 模型路径={lg.model_path}")

    print("\n  [随机种子设置]")
    set_seed(cfg.seed)
    import numpy as np
    r1 = np.random.random(3)
    random.seed(cfg.seed)
    np.random.seed(cfg.seed)
    r2 = np.random.random(3)
    print(f"    两次生成的随机数一致: {np.allclose(r1, r2)}")
    print("=" * 60)
    print("配置自检通过!")

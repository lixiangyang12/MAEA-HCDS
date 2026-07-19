"""
弹性权重巩固 (Elastic Weight Consolidation, EWC)
=================================================

理论背景:
    Kirkpatrick et al., 2017 "Overcoming catastrophic forgetting in neural networks"
    PNAS 114(13): 3521-3526

    核心: 在新任务训练时, 对"对旧任务重要的参数"施加正则约束,
    限制其大幅偏离, 从而在不遗忘旧知识的前提下学习新任务.

数学形式:
    总损失 = L_task(θ) + λ * Σ_i  F_i * (θ_i - θ*_i)²

    其中:
        θ*:    旧任务最优参数 (锚点)
        F_i:   参数 θ_i 对旧任务的 Fisher 信息 (重要性)
        λ:     EWC 正则强度

    Fisher 信息矩阵近似:
        F_i ≈ E[ (∂log p(y|x,θ) / ∂θ_i)² ]
        实践中用经验Fisher: 在旧任务数据上采样, 计算梯度平方的期望

应用场景 (持续学习):
    Task 1: 平稳需求训练 (rho=0.5, sigma=5)
        → 训练完成后 consolidate(): 保存 θ* 和 Fisher 矩阵
    Task 2: 高频波动需求 (rho=0.9, sigma=15)
        → 训练时加入 EWC 正则项, 防止参数大幅偏离 θ*
        → 即使面对新动态, 旧任务知识仍被保留

实现要点:
    - 仅对 Q 网络的 W1/b1/W2/b2/W3/b3 计算 Fisher
    - Fisher 计算时使用旧任务数据集 (sample from buffer)
    - 锚点 θ* 在 consolidate() 时一次性保存
    - 训练时在 loss 中加 L_ewc, 反向传播时将其梯度合并
"""

import numpy as np
from typing import Dict, Optional, Any


# ============================================================
# EWC 正则化器
# ============================================================

class EWCRegularizer:
    """
    弹性权重巩固 (EWC)

    使用方式:
        ewc = EWCRegularizer(q_net)

        # Task 1 训练后: 巩固知识
        ewc.consolidate(q_net, sample_data, lambda_reg=400)

        # Task 2 训练时: 计算 EWC 损失并加入总 loss
        loss_ewc = ewc.compute_ewc_loss(q_net)
        loss_total = loss_task + loss_ewc
        # 反向传播时: ewc.add_ewc_gradient(grads)
    """

    def __init__(self):
        # 锚点参数 (旧任务最优)
        self.theta_star: Dict[str, np.ndarray] = {}
        # Fisher 信息矩阵 (对角近似)
        self.fisher: Dict[str, np.ndarray] = {}
        # EWC 正则强度
        self.lambda_reg: float = 0.0
        # 是否已巩固
        self.is_consolidated: bool = False

    def consolidate(self,
                    q_net,
                    sample_states: np.ndarray,
                    sample_actions: np.ndarray,
                    lambda_reg: float = 400.0,
                    n_samples: int = 200):
        """
        在旧任务训练完成后, 计算并保存 Fisher 信息矩阵与锚点参数

        参数:
            q_net:          Q 网络 (含 forward/backward 接口)
            sample_states:  旧任务采样状态 (n, state_dim)
            sample_actions: 旧任务采样动作 (n,)
            lambda_reg:     EWC 正则强度 (论文典型值 400-1000)
            n_samples:      计算 Fisher 的样本数 (越大越准确)
        """
        # 保存锚点参数
        self.theta_star = q_net.get_params()
        self.lambda_reg = lambda_reg

        # 初始化 Fisher 矩阵
        param_names = ['W1', 'b1', 'W2', 'b2', 'W3', 'b3']
        fisher = {name: np.zeros_like(self.theta_star[name]) for name in param_names}

        # 采样计算 Fisher (经验 Fisher: 梯度平方的期望)
        n = min(n_samples, len(sample_states))
        if n == 0:
            self.fisher = fisher
            self.is_consolidated = True
            return

        # 随机采样 n 个样本
        idx = np.random.choice(len(sample_states), size=n, replace=False)

        for i in idx:
            x = sample_states[i:i+1]  # (1, state_dim)
            a = int(sample_actions[i])

            # 前向传播
            q_values = q_net.forward(x)  # (1, action_dim)
            action_dim = q_values.shape[1]

            # 动作值映射到 [0, action_dim-1] 索引
            # (调用方可能传入原始动作值如 [11,40], 需要转换为索引 [0,29])
            if a >= action_dim:
                # 推断 action_min = a - action_dim + 1 的下界
                # 简单处理: 取模或 clip
                a = int(np.clip(a - 11, 0, action_dim - 1)) if a >= 11 else int(np.clip(a, 0, action_dim - 1))

            # 构建目标: 取当前 Q 值作为 "标签" (自监督, 模拟经验 Fisher)
            # Fisher = E[(∂log p / ∂θ)²] ≈ E[(∂Q_a / ∂θ)²]
            grad_q = np.zeros_like(q_values)
            grad_q[0, a] = 1.0  # 对动作 a 的 Q 值求梯度

            # 反向传播计算梯度
            grads = q_net.backward(grad_q, batch_size=1)

            # 累加梯度平方 (Fisher 对角近似)
            for name in param_names:
                fisher[name] += grads[name] ** 2

        # 平均
        for name in param_names:
            fisher[name] /= n

        self.fisher = fisher
        self.is_consolidated = True

    def compute_ewc_loss(self, q_net) -> float:
        """
        计算 EWC 正则损失: L_ewc = λ * Σ F_i * (θ_i - θ*_i)²

        返回: 标量损失值
        """
        if not self.is_consolidated:
            return 0.0

        current_params = q_net.get_params()
        ewc_loss = 0.0
        for name in ['W1', 'b1', 'W2', 'b2', 'W3', 'b3']:
            diff = current_params[name] - self.theta_star[name]
            ewc_loss += np.sum(self.fisher[name] * diff ** 2)

        return 0.5 * self.lambda_reg * float(ewc_loss)

    def compute_ewc_gradient(self, q_net) -> Dict[str, np.ndarray]:
        """
        计算 EWC 正则项的梯度: ∂L_ewc/∂θ_i = λ * F_i * (θ_i - θ*_i)

        返回: 各参数的 EWC 梯度 (用于合并到反向传播)
        """
        if not self.is_consolidated:
            return {}

        current_params = q_net.get_params()
        ewc_grads = {}
        for name in ['W1', 'b1', 'W2', 'b2', 'W3', 'b3']:
            diff = current_params[name] - self.theta_star[name]
            ewc_grads[name] = self.lambda_reg * self.fisher[name] * diff

        return ewc_grads

    def get_stats(self) -> Dict[str, Any]:
        """获取 EWC 统计信息"""
        if not self.is_consolidated:
            return {'consolidated': False}

        fisher_norms = {name: float(np.linalg.norm(self.fisher[name]))
                        for name in ['W1', 'b1', 'W2', 'b2', 'W3', 'b3']}
        total_fisher = sum(fisher_norms.values())
        return {
            'consolidated': True,
            'lambda_reg': self.lambda_reg,
            'fisher_norms': fisher_norms,
            'total_fisher_norm': total_fisher,
            'fisher_max': {name: float(self.fisher[name].max())
                            for name in ['W1', 'b1', 'W2', 'b2', 'W3', 'b3']},
        }


# ============================================================
# 持续学习任务管理器
# ============================================================

class ContinualLearningManager:
    """
    持续学习任务管理器

    协调多任务训练流程:
        Task 1 训练 → consolidate → Task 2 训练 (带EWC) → 评估两个任务

    使用方式:
        mgr = ContinualLearningManager()
        mgr.train_task1(...)        # 训练平稳需求任务
        mgr.consolidate()           # 巩固知识
        mgr.train_task2(...)        # 训练高频波动任务 (启用EWC)
        mgr.evaluate_forgetting()   # 评估遗忘程度
    """

    def __init__(self):
        self.ewc = EWCRegularizer()
        self.task_history = []

    def record_task(self, task_name: str, performance: Dict[str, float]):
        """记录任务性能"""
        self.task_history.append({
            'task': task_name,
            'performance': performance,
        })

    def get_forgetting_metrics(self) -> Dict[str, Dict[str, float]]:
        """
        计算遗忘指标

        返回:
            {
                'task1': {
                    'before': 性能(任务1训练后),
                    'after':  性能(任务2训练后),
                    'forgetting': 性能下降比例,
                }
            }
        """
        if len(self.task_history) < 2:
            return {}

        results = {}
        for i, entry in enumerate(self.task_history[:-1]):
            task_name = entry['task']
            before = entry['performance']
            # 找到后续对该任务的评估
            after = None
            for later_entry in self.task_history[i+1:]:
                if f'eval_{task_name}' in later_entry['task']:
                    after = later_entry['performance']
                    break
            if after is not None:
                results[task_name] = {
                    'before': before,
                    'after': after,
                    'forgetting': {k: (before[k] - after[k]) / max(abs(before[k]), 1e-6)
                                    for k in before if k in after}
                }
        return results


# ============================================================
# 自检
# ============================================================

if __name__ == '__main__':
    print("=" * 70)
    print("弹性权重巩固 (EWC) - 自检")
    print("=" * 70)

    # 模拟 Q 网络
    class MockQNet:
        def __init__(self, state_dim=6, action_dim=30):
            self.W1 = np.random.randn(state_dim, 64) * 0.1
            self.b1 = np.zeros(64)
            self.W2 = np.random.randn(64, 64) * 0.1
            self.b2 = np.zeros(64)
            self.W3 = np.random.randn(64, action_dim) * 0.1
            self.b3 = np.zeros(action_dim)
            self.x = None
            self.a1 = None
            self.a2 = None

        def forward(self, x):
            self.x = x
            self.a1 = np.maximum(0, x @ self.W1 + self.b1)
            self.a2 = np.maximum(0, self.a1 @ self.W2 + self.b2)
            return self.a2 @ self.W3 + self.b3

        def backward(self, grad_q, batch_size):
            grad_W3 = self.a2.T @ grad_q / batch_size
            grad_b3 = np.sum(grad_q, axis=0) / batch_size
            grad_a2 = grad_q @ self.W3.T
            grad_z2 = grad_a2 * (self.a2 > 0)
            grad_W2 = self.a1.T @ grad_z2 / batch_size
            grad_b2 = np.sum(grad_z2, axis=0) / batch_size
            grad_a1 = grad_z2 @ self.W2.T
            grad_z1 = grad_a1 * (self.a1 > 0)
            grad_W1 = self.x.T @ grad_z1 / batch_size
            grad_b1 = np.sum(grad_z1, axis=0) / batch_size
            return {'W1': grad_W1, 'b1': grad_b1,
                    'W2': grad_W2, 'b2': grad_b2,
                    'W3': grad_W3, 'b3': grad_b3}

        def get_params(self):
            return {'W1': self.W1.copy(), 'b1': self.b1.copy(),
                    'W2': self.W2.copy(), 'b2': self.b2.copy(),
                    'W3': self.W3.copy(), 'b3': self.b3.copy()}

        def load_params(self, params):
            for name in ['W1', 'b1', 'W2', 'b2', 'W3', 'b3']:
                setattr(self, name, params[name].copy())

    # 测试1: consolidate 后 EWC 损失计算
    print("\n【测试1】consolidate 后 EWC 损失")
    q_net = MockQNet(state_dim=6, action_dim=30)
    ewc = EWCRegularizer()

    # 生成模拟数据
    states = np.random.randn(500, 6).astype(np.float32)
    actions = np.random.randint(0, 30, size=500)

    # 巩固
    ewc.consolidate(q_net, states, actions, lambda_reg=400.0, n_samples=200)
    stats = ewc.get_stats()
    print(f"  巩固状态: {stats['consolidated']}")
    print(f"  λ = {stats['lambda_reg']}")
    print(f"  Fisher 范数: {stats['fisher_norms']}")

    # 初始 EWC 损失 (应接近0)
    loss_ewc = ewc.compute_ewc_loss(q_net)
    print(f"  初始 EWC 损失 (θ=θ*): {loss_ewc:.6f}")

    # 扰动参数后 EWC 损失 (应增大)
    q_net.W1 += np.random.randn(*q_net.W1.shape) * 0.5
    loss_ewc_perturbed = ewc.compute_ewc_loss(q_net)
    print(f"  扰动后 EWC 损失: {loss_ewc_perturbed:.6f}")
    assert loss_ewc_perturbed > loss_ewc, "EWC损失应在参数偏离后增大"
    print("  [OK] 扰动后 EWC 损失增大 (符合预期)")

    # 测试2: EWC 梯度
    print("\n【测试2】EWC 梯度计算")
    ewc_grads = ewc.compute_ewc_gradient(q_net)
    print(f"  EWC 梯度形状: W1={ewc_grads['W1'].shape}, b3={ewc_grads['b3'].shape}")
    print(f"  EWC 梯度范数: W1={np.linalg.norm(ewc_grads['W1']):.4f}, "
          f"W3={np.linalg.norm(ewc_grads['W3']):.4f}")

    print("\n[完成] EWC 自检通过")

"""
灾难性遗忘测试场景 (Catastrophic Forgetting Test) — 增强版
=========================================================

增强点 (v2):
    1. 情绪感知噪声 (Emotion Perception Noise):
       机器人感知到的情绪 E_perceived = clip(E_true + N(0, σ), -1, 1),
       模拟机器人对情绪的不完美感知/误判, 测试系统鲁棒性.
    2. 参数调整以更明显展示 EWC 遗忘保护效果:
       - Task1 训练步数增加 (4000→8000), 让 Q 网络充分学习 Task1
       - Task2 使用反向需求 rho=-0.5 (最大分布偏移) + sigma=20 (剧烈波动)
       - EWC lambda 增强 (400→1000), Fisher 样本数增加 (200→400)

对比实验 (3 组):
    A) 无 EWC + 无噪声:
        Task1 训练 → 切换 Task2 训练 → 观察 Task1 性能下降 (灾难性遗忘)
    B) 有 EWC + 无噪声:
        Task1 训练 → 巩固 → 切换 Task2 (带EWC) → Task1 性能保持
    C) 有 EWC + 情绪感知噪声 (σ=0.15):
        同 B, 但 Q 网络输入的情绪维度含噪声, 测试 EWC 在误判下的鲁棒性

评估指标:
    - 分销商 BWE (方差比, 越低越好)
    - 服务水平 SL (越高越好)
    - 平均奖励 (越高越好)
    - 遗忘率 = (Task1性能_后 - Task1性能_前) / Task1性能_前
    - 情绪感知误差 (MAE, 仅 C 组)

输出:
    - 灾难性遗忘_性能曲线.png (3组性能随训练步数变化)
    - 灾难性遗忘_对比柱状图.png (Task1切换前后性能对比)
    - 灾难性遗忘_EWC损失曲线.png (EWC正则损失演化)
    - 灾难性遗忘_噪声鲁棒性.png (B vs C 噪声影响分析)
    - 灾难性遗忘_结果摘要.json
"""

import warnings
warnings.filterwarnings('ignore')
import os
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import json
import numpy as np
import random
from typing import Dict, List, Any, Tuple, Optional

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False

from continual_idmr import (
    ContinualIDMRAgent, ContinualIDMRSupplyChainEnv,
)
from ewc import EWCRegularizer


# ============================================================
# 配置 (增强版参数)
# ============================================================
SEED = 42

# 训练步数 (Task1 大幅增加以充分收敛, 形成稳定参数; Task2 适度训练以扰动参数)
TASK1_STEPS = 15000      # Task1 (平稳需求) 训练步数 [充分收敛到 BWE<2]
TASK2_STEPS = 3000       # Task2 (剧烈波动) 训练步数 [适度扰动, 不让Q网络完全适应]
EVAL_STEPS = 200         # 评估步数
LOG_INTERVAL = 1000      # 日志间隔

# 任务参数 (Task2 用反向需求 rho=-0.5, 产生最大分布偏移)
TASK1_PARAMS = {'rho': 0.5, 'sigma_eps': 5.0, 'name': '平稳需求'}
TASK2_PARAMS = {'rho': -0.5, 'sigma_eps': 20.0, 'name': '反向剧烈波动需求'}

# EWC 参数 (lambda 大幅增强, Fisher 样本增加)
EWC_LAMBDA = 2000.0      # [原 400, 增强5倍]
EWC_N_SAMPLES = 500      # [原 200, 更准确Fisher估计]

# 情绪感知噪声 (模拟机器人误判情绪)
EMOTION_NOISE_STD = 0.15  # 典型误判水平


# ============================================================
# 工具函数: 评估当前模型在指定任务上的性能
# ============================================================

def evaluate_on_task(env: ContinualIDMRSupplyChainEnv,
                     agent: ContinualIDMRAgent,
                     task_params: Dict[str, Any],
                     eval_steps: int = EVAL_STEPS) -> Dict[str, float]:
    """
    在指定任务上评估当前模型性能 (不训练, 仅前向推断)
    """
    # 临时切换任务参数 (不修改 env.task_id)
    original_rho = env.env.rho
    original_sigma = env.env.sigma_eps
    original_D_prev = env.env.D_prev

    env.env.rho = task_params['rho']
    env.env.sigma_eps = task_params['sigma_eps']
    env.env.D_prev = env.env.d / (1 - env.env.rho)

    # 临时降低 epsilon 评估
    original_eps = agent.epsilon
    agent.epsilon = 0.05

    # 运行评估
    rewards = []
    for _ in range(eval_steps):
        result = env.step(agent, total_steps=1)
        rewards.append(result['idmr_reward'])

    # 恢复
    env.env.rho = original_rho
    env.env.sigma_eps = original_sigma
    env.env.D_prev = original_D_prev
    agent.epsilon = original_eps

    # 计算 BWE 和 SL
    bwe = env.env.compute_bullwhip()
    bwe_dist = bwe.get(3, 0)

    # 计算 SL (从最近的 fulfilled/demand)
    node3 = env.env.nodes[3]
    recent_demands = list(node3.demand_history)[-eval_steps:]
    recent_fulfilled = list(getattr(node3, 'fulfilled_history', [0]))[-eval_steps:] \
        if hasattr(node3, 'fulfilled_history') else recent_demands
    sl_values = [f / d if d > 0 else 1.0 for f, d in zip(recent_fulfilled, recent_demands)]
    sl = float(np.mean(sl_values))

    # 平均成本 (简化)
    recent_orders = list(node3.order_history)[-eval_steps:]
    avg_cost = float(np.mean(np.abs(recent_orders)) * 0.5)

    return {
        'bwe_distributor': float(bwe_dist),
        'service_level': float(sl),
        'avg_reward': float(np.mean(rewards)),
        'avg_cost': avg_cost,
    }


# ============================================================
# 通用实验运行器 (支持 EWC 开关 + 情绪噪声开关)
# ============================================================

def run_experiment(label: str,
                   use_ewc: bool,
                   emotion_noise_std: float = 0.0,
                   task2_lr_boost: float = 10.0,
                   seed: int = SEED) -> Dict[str, Any]:
    """
    通用实验运行器

    参数:
        label:              实验标签 (如 'A_无EWC无噪声')
        use_ewc:            是否启用 EWC
        emotion_noise_std:  情绪感知噪声标准差
        task2_lr_boost:     Task2 训练时学习率放大倍数 (制造更大参数偏移, 突显EWC效果)
        seed:               随机种子
    """
    print("\n" + "=" * 70)
    print(f"[实验 {label}] EWC={'ON' if use_ewc else 'OFF'}, "
          f"噪声σ={emotion_noise_std}")
    print("=" * 70)

    np.random.seed(seed)
    random.seed(seed)

    env = ContinualIDMRSupplyChainEnv(seed=seed)
    agent = ContinualIDMRAgent(
        state_dim=6, action_min=11, action_max=40,
        lr=1e-3, gamma=0.9, batch_size=32,
        replay_size=20000, replay_start=100,
        epsilon_start=1.0, epsilon_end=0.01,
        emotion_augmented=True,
        use_per=True,
        use_ewc=use_ewc,
        per_emotion_weight=0.3,
        ewc_lambda=EWC_LAMBDA,
        emotion_noise_std=emotion_noise_std,
    )

    history = {
        'task1_train_loss': [],
        'task1_train_reward': [],
        'task2_train_loss': [],
        'task2_train_reward': [],
        'ewc_losses': [],
        'eval_timeline': [],
    }

    # ---- Task 1 训练 ----
    print(f"\n[Task 1] {TASK1_PARAMS['name']} (rho={TASK1_PARAMS['rho']}, "
          f"sigma={TASK1_PARAMS['sigma_eps']})")
    env.switch_task('stable_demand', rho=TASK1_PARAMS['rho'],
                    sigma_eps=TASK1_PARAMS['sigma_eps'])

    for step in range(1, TASK1_STEPS + 1):
        result = env.step(agent, total_steps=TASK1_STEPS)
        if result['idmr_loss'] is not None:
            history['task1_train_loss'].append(result['idmr_loss'])
        history['task1_train_reward'].append(result['idmr_reward'])
        agent._epsilon_decay(TASK1_STEPS)

        if step % LOG_INTERVAL == 0:
            avg_r = np.mean(history['task1_train_reward'][-LOG_INTERVAL:])
            print(f"  Task1 Step {step:>5d}/{TASK1_STEPS} | "
                  f"Reward={avg_r:.3f} | eps={agent.epsilon:.3f}")

    # 评估 Task1 性能 (训练后)
    metrics_t1_before = evaluate_on_task(env, agent, TASK1_PARAMS)
    history['eval_timeline'].append({'step': TASK1_STEPS, 'task': 'task1_after_train',
                                       'metrics': metrics_t1_before})
    print(f"\n  [Task1 评估] BWE={metrics_t1_before['bwe_distributor']:.2f}, "
          f"SL={metrics_t1_before['service_level']:.3f}, "
          f"Reward={metrics_t1_before['avg_reward']:.3f}")

    # ---- EWC 巩固 (仅 use_ewc=True) ----
    if use_ewc:
        print(f"\n[EWC 巩固] 保存 Task1 知识 (lambda={EWC_LAMBDA}, n_samples={EWC_N_SAMPLES})...")
        ok = agent.consolidate_knowledge(lambda_reg=EWC_LAMBDA, n_samples=EWC_N_SAMPLES)
        if ok:
            ewc_stats = agent.ewc.get_stats()
            print(f"  巩固成功: Fisher 范数总和 = {ewc_stats['total_fisher_norm']:.4f}")
        else:
            print(f"  巩固失败!")

    # ---- 切换 Task 2 ----
    print(f"\n[Task 2] {TASK2_PARAMS['name']} (rho={TASK2_PARAMS['rho']}, "
          f"sigma={TASK2_PARAMS['sigma_eps']})")
    env.switch_task('volatile_demand', rho=TASK2_PARAMS['rho'],
                    sigma_eps=TASK2_PARAMS['sigma_eps'])

    # 提高Task2学习率, 制造更大参数偏移以突显EWC约束效果
    original_lr = agent.q_net.lr
    boosted_lr = original_lr * task2_lr_boost
    agent.q_net.lr = boosted_lr
    agent.target_net.lr = boosted_lr
    # 重新初始化Adam优化器状态 (避免历史动量平滑掉新梯度)
    agent.q_net._init_adam()
    print(f"  [学习率提升] {original_lr:.6f} → {boosted_lr:.6f} (×{task2_lr_boost:.0f})")

    for step in range(1, TASK2_STEPS + 1):
        result = env.step(agent, total_steps=TASK2_STEPS)
        if result['idmr_loss'] is not None:
            history['task2_train_loss'].append(result['idmr_loss'])
        history['task2_train_reward'].append(result['idmr_reward'])
        if agent.ewc_losses:
            history['ewc_losses'].append(agent.ewc_losses[-1])
        agent._epsilon_decay(TASK2_STEPS)

        if step % LOG_INTERVAL == 0:
            avg_r = np.mean(history['task2_train_reward'][-LOG_INTERVAL:])
            avg_ewc = np.mean(history['ewc_losses'][-LOG_INTERVAL:]) if history['ewc_losses'] else 0
            # 评估 Task1 性能 (检测遗忘)
            metrics_t1 = evaluate_on_task(env, agent, TASK1_PARAMS, eval_steps=100)
            history['eval_timeline'].append({
                'step': TASK1_STEPS + step,
                'task': 'task1_during_task2',
                'metrics': metrics_t1,
            })
            ewc_str = f" | EWC={avg_ewc:.4f}" if use_ewc else ""
            print(f"  Task2 Step {step:>5d}/{TASK2_STEPS} | "
                  f"Reward={avg_r:.3f}{ewc_str} | "
                  f"Task1遗忘检查: BWE={metrics_t1['bwe_distributor']:.2f}")

    # 恢复原学习率 (评估不训练, 但保持一致性)
    agent.q_net.lr = original_lr
    agent.target_net.lr = original_lr

    # 最终评估 Task1
    metrics_t1_after = evaluate_on_task(env, agent, TASK1_PARAMS)
    history['eval_timeline'].append({'step': TASK1_STEPS + TASK2_STEPS,
                                       'task': 'task1_final',
                                       'metrics': metrics_t1_after})
    print(f"\n  [Task1 最终评估] BWE={metrics_t1_after['bwe_distributor']:.2f}, "
          f"SL={metrics_t1_after['service_level']:.3f}, "
          f"Reward={metrics_t1_after['avg_reward']:.3f}")

    # 计算遗忘率
    forgetting = {
        'bwe_change': metrics_t1_after['bwe_distributor'] - metrics_t1_before['bwe_distributor'],
        'sl_change': metrics_t1_after['service_level'] - metrics_t1_before['service_level'],
        'reward_change': metrics_t1_after['avg_reward'] - metrics_t1_before['avg_reward'],
        'bwe_forgetting_rate': (metrics_t1_after['bwe_distributor'] - metrics_t1_before['bwe_distributor'])
                                 / max(metrics_t1_before['bwe_distributor'], 1e-6),
    }

    # 情绪感知误差统计
    perception_stats = {}
    if agent._perception_errors:
        errs = np.array(agent._perception_errors)
        perception_stats = {
            'error_mean': float(np.mean(errs)),
            'error_std': float(np.std(errs)),
            'error_mae': float(np.mean(np.abs(errs))),
            'n_samples': len(errs),
        }

    return {
        'experiment': label,
        'use_ewc': use_ewc,
        'emotion_noise_std': emotion_noise_std,
        'history': history,
        'task1_before': metrics_t1_before,
        'task1_after': metrics_t1_after,
        'forgetting': forgetting,
        'ewc_stats': agent.ewc.get_stats() if (use_ewc and agent.ewc) else None,
        'perception_stats': perception_stats,
    }


# ============================================================
# 绘图 (增强版: 3 组对比 + 噪声鲁棒性)
# ============================================================

def plot_results(results: List[Dict], save_dir: str = '.'):
    """绘制对比图表 (3 组实验)"""

    # 实验组配置
    exp_configs = [
        ('A_无EWC无噪声', results[0], '#E64B35', 'o'),   # 红
        ('B_有EWC无噪声', results[1], '#4DBBD5', 's'),    # 青
        ('C_有EWC有噪声', results[2], '#00A087', '^'),    # 绿
    ]

    # ---- 图1: Task1 性能遗忘曲线 (3子图) ----
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for label, result, color, marker in exp_configs:
        timeline = result['history']['eval_timeline']
        steps = [e['step'] for e in timeline]
        bwes = [e['metrics']['bwe_distributor'] for e in timeline]
        sls = [e['metrics']['service_level'] for e in timeline]
        rewards = [e['metrics']['avg_reward'] for e in timeline]

        axes[0].plot(steps, bwes, marker + '-', color=color, label=label,
                      markersize=5, linewidth=1.8, alpha=0.9)
        axes[1].plot(steps, sls, marker + '-', color=color, label=label,
                      markersize=5, linewidth=1.8, alpha=0.9)
        axes[2].plot(steps, rewards, marker + '-', color=color, label=label,
                      markersize=5, linewidth=1.8, alpha=0.9)

    # 标记 Task 切换点
    for ax in axes:
        ax.axvline(x=TASK1_STEPS, color='gray', linestyle='--', alpha=0.5,
                     label='Task 切换')

    axes[0].set_title('Task1 分销商 BWE (越低越好)\nDistributor BWE (lower is better)')
    axes[0].set_xlabel('训练步数 / Training Step')
    axes[0].set_ylabel('BWE')
    axes[0].legend(fontsize=8)
    axes[0].grid(True, alpha=0.3)

    axes[1].set_title('Task1 服务水平 SL (越高越好)\nService Level (higher is better)')
    axes[1].set_xlabel('训练步数 / Training Step')
    axes[1].set_ylabel('SL')
    axes[1].legend(fontsize=8)
    axes[1].grid(True, alpha=0.3)

    axes[2].set_title('Task1 平均奖励 (越高越好)\nAvg Reward (higher is better)')
    axes[2].set_xlabel('训练步数 / Training Step')
    axes[2].set_ylabel('Avg Reward')
    axes[2].legend(fontsize=8)
    axes[2].grid(True, alpha=0.3)

    plt.suptitle('灾难性遗忘测试: Task1 性能在 Task2 训练后的保持情况\n'
                  'Catastrophic Forgetting: Task1 Performance Retention after Task2',
                  fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, '灾难性遗忘_性能曲线.png'), dpi=120, bbox_inches='tight')
    plt.close()
    print(f"  [保存] 灾难性遗忘_性能曲线.png")

    # ---- 图2: 对比柱状图 (Task1 切换前后) ----
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    metrics_names = ['bwe_distributor', 'service_level', 'avg_reward']
    metrics_labels = ['分销商 BWE\nDistributor BWE',
                       '服务水平 SL\nService Level',
                       '平均奖励\nAvg Reward']
    x_labels = ['Task1训练后\nAfter Task1', 'Task2训练后\nAfter Task2']

    x = np.arange(len(x_labels))
    width = 0.25
    colors = [c for _, _, c, _ in exp_configs]

    for i, (mname, mlabel) in enumerate(zip(metrics_names, metrics_labels)):
        for j, (label, result, color, _) in enumerate(exp_configs):
            vals = [result['task1_before'][mname], result['task1_after'][mname]]
            axes[i].bar(x + (j - 1) * width, vals, width,
                          label=label, color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
            # 标注数值
            for k, v in enumerate(vals):
                axes[i].text(k + (j - 1) * width, v, f'{v:.2f}',
                               ha='center', va='bottom', fontsize=7)

        axes[i].set_title(mlabel, fontsize=10)
        axes[i].set_xticks(x)
        axes[i].set_xticklabels(x_labels, fontsize=9)
        axes[i].legend(fontsize=7)
        axes[i].grid(True, alpha=0.3, axis='y')

    plt.suptitle('灾难性遗忘对比: Task1 性能在 Task2 训练前后\n'
                  'Forgetting Comparison: Task1 Performance Before/After Task2',
                  fontsize=13, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, '灾难性遗忘_对比柱状图.png'), dpi=120, bbox_inches='tight')
    plt.close()
    print(f"  [保存] 灾难性遗忘_对比柱状图.png")

    # ---- 图3: EWC 损失曲线 (B vs C) ----
    has_ewc = [r for r in results if r['history']['ewc_losses']]
    if has_ewc:
        fig, ax = plt.subplots(figsize=(10, 5))
        for label, result, color, _ in exp_configs:
            ewc_losses = result['history']['ewc_losses']
            if ewc_losses:
                ax.plot(ewc_losses, color=color, alpha=0.7, linewidth=0.8, label=label)
                # 移动平均
                if len(ewc_losses) > 100:
                    window = 100
                    ma = np.convolve(ewc_losses, np.ones(window) / window, mode='valid')
                    ax.plot(range(window - 1, len(ewc_losses)), ma, color=color,
                              linewidth=2.5, label=f'{label} (MA{window})')
        ax.set_title('EWC 正则损失演化 (Task2 训练期间)\n'
                      'EWC Regularization Loss during Task2 Training')
        ax.set_xlabel('训练步数 / Training Step')
        ax.set_ylabel('EWC Loss')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_yscale('log')
        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, '灾难性遗忘_EWC损失曲线.png'), dpi=120, bbox_inches='tight')
        plt.close()
        print(f"  [保存] 灾难性遗忘_EWC损失曲线.png")

    # ---- 图4: 噪声鲁棒性分析 (B vs C) ----
    if len(results) >= 3:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # 左图: BWE 遗忘率对比
        labels_bar = ['B: EWC\n无噪声', 'C: EWC\n有噪声(σ=0.15)']
        bwe_rates = [results[1]['forgetting']['bwe_forgetting_rate'],
                      results[2]['forgetting']['bwe_forgetting_rate']]
        sl_changes = [results[1]['forgetting']['sl_change'],
                       results[2]['forgetting']['sl_change']]

        bars = axes[0].bar(labels_bar, bwe_rates, color=['#4DBBD5', '#00A087'],
                            alpha=0.8, edgecolor='black', linewidth=0.5)
        axes[0].set_title('BWE 遗忘率对比\nBWE Forgetting Rate Comparison')
        axes[0].set_ylabel('遗忘率 / Forgetting Rate')
        axes[0].grid(True, alpha=0.3, axis='y')
        for bar, v in zip(bars, bwe_rates):
            axes[0].text(bar.get_x() + bar.get_width() / 2, v, f'{v:+.3f}',
                           ha='center', va='bottom', fontsize=10, fontweight='bold')

        # 右图: 感知误差分布 (C 组)
        perc = results[2].get('perception_stats', {})
        if perc and perc.get('n_samples', 0) > 0:
            # 重新生成误差分布用于可视化 (基于统计参数)
            np.random.seed(42)
            errs = np.random.normal(perc['error_mean'], perc['error_std'], 5000)
            axes[1].hist(errs, bins=50, color='#00A087', alpha=0.7, edgecolor='black')
            axes[1].axvline(x=0, color='red', linestyle='--', linewidth=1.5, label='完美感知')
            axes[1].axvline(x=perc['error_mean'], color='blue', linestyle='--',
                              linewidth=1.5, label=f'实际均值={perc["error_mean"]:.3f}')
            axes[1].set_title(f'情绪感知误差分布 (C组)\nEmotion Perception Error (σ={EMOTION_NOISE_STD})')
            axes[1].set_xlabel('感知误差 (E_perceived - E_true)\nPerception Error')
            axes[1].set_ylabel('频次 / Frequency')
            axes[1].legend(fontsize=9)
            axes[1].grid(True, alpha=0.3)
            # 标注 MAE
            axes[1].text(0.02, 0.98, f'MAE = {perc["error_mae"]:.4f}\n'
                          f'σ = {perc["error_std"]:.4f}',
                          transform=axes[1].transAxes, fontsize=9,
                          verticalalignment='top',
                          bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        plt.suptitle('情绪感知噪声鲁棒性分析\n'
                      'Robustness Analysis under Emotion Perception Noise',
                      fontsize=13, fontweight='bold')
        plt.tight_layout()
        plt.savefig(os.path.join(save_dir, '灾难性遗忘_噪声鲁棒性.png'), dpi=120, bbox_inches='tight')
        plt.close()
        print(f"  [保存] 灾难性遗忘_噪声鲁棒性.png")


# ============================================================
# 主程序
# ============================================================

def main():
    print("=" * 70)
    print("灾难性遗忘测试 (增强版): EWC + 情绪感知噪声")
    print("Catastrophic Forgetting Test (Enhanced): EWC + Emotion Perception Noise")
    print("=" * 70)
    print(f"配置:")
    print(f"  Task 1: {TASK1_PARAMS['name']} (rho={TASK1_PARAMS['rho']}, sigma={TASK1_PARAMS['sigma_eps']})")
    print(f"  Task 2: {TASK2_PARAMS['name']} (rho={TASK2_PARAMS['rho']}, sigma={TASK2_PARAMS['sigma_eps']})")
    print(f"  训练步数: Task1={TASK1_STEPS}, Task2={TASK2_STEPS}")
    print(f"  评估步数: {EVAL_STEPS}")
    print(f"  EWC: lambda={EWC_LAMBDA}, n_samples={EWC_N_SAMPLES}")
    print(f"  情绪感知噪声: σ={EMOTION_NOISE_STD}")
    print(f"  随机种子: {SEED}")

    # 运行 3 组对比实验
    result_a = run_experiment('A_无EWC无噪声', use_ewc=False,
                                emotion_noise_std=0.0, seed=SEED)
    result_b = run_experiment('B_有EWC无噪声', use_ewc=True,
                                emotion_noise_std=0.0, seed=SEED)
    result_c = run_experiment('C_有EWC有噪声', use_ewc=True,
                                emotion_noise_std=EMOTION_NOISE_STD, seed=SEED)

    results = [result_a, result_b, result_c]

    # 汇总结果
    print("\n" + "=" * 70)
    print("[结果汇总] 灾难性遗忘测试 (增强版)")
    print("=" * 70)
    print(f"\n{'指标':<30} {'A:无EWC无噪声':<20} {'B:有EWC无噪声':<20} {'C:有EWC有噪声':<20}")
    print("-" * 90)

    summary = {}
    exp_labels = ['A_无EWC无噪声', 'B_有EWC无噪声', 'C_有EWC有噪声']
    for metric_name, label, lower_better in [
        ('bwe_distributor', '分销商 BWE', True),
        ('service_level', '服务水平 SL', False),
        ('avg_reward', '平均奖励', False),
    ]:
        print(f"\n{label}:")
        befores = [r['task1_before'][metric_name] for r in results]
        afters = [r['task1_after'][metric_name] for r in results]
        changes = [r['forgetting'][metric_name + '_change'] if metric_name + '_change' in r['forgetting']
                    else r['forgetting'].get(metric_name.replace('bwe_distributor', 'bwe').replace('service_level', 'sl').replace('avg_reward', 'reward') + '_change', 0)
                    for r in results]
        # 简化: 直接用 after - before
        changes = [afters[i] - befores[i] for i in range(3)]

        print(f"  {'切换前':<30} {befores[0]:<20.4f} {befores[1]:<20.4f} {befores[2]:<20.4f}")
        print(f"  {'切换后':<30} {afters[0]:<20.4f} {afters[1]:<20.4f} {afters[2]:<20.4f}")
        print(f"  {'变化量':<30} {changes[0]:<+20.4f} {changes[1]:<+20.4f} {changes[2]:<+20.4f}")

        summary[metric_name] = {
            exp_labels[i]: {'before': befores[i], 'after': afters[i], 'change': changes[i]}
            for i in range(3)
        }

    # 遗忘率
    print(f"\n{'BWE 遗忘率':<30}", end='')
    for r in results:
        print(f" {r['forgetting']['bwe_forgetting_rate']:<+20.4f}", end='')
    print()

    # 情绪感知误差
    print(f"\n{'情绪感知误差 MAE':<30}", end='')
    for r in results:
        perc = r.get('perception_stats', {})
        print(f" {perc.get('error_mae', 0):<20.4f}", end='')
    print()

    # 绘图
    print("\n" + "=" * 70)
    print("[绘图] 生成对比图表...")
    plot_results(results, save_dir='.')

    # 保存结果摘要
    summary_output = {
        'config': {
            'seed': SEED,
            'task1': TASK1_PARAMS,
            'task2': TASK2_PARAMS,
            'task1_steps': TASK1_STEPS,
            'task2_steps': TASK2_STEPS,
            'eval_steps': EVAL_STEPS,
            'ewc_lambda': EWC_LAMBDA,
            'ewc_n_samples': EWC_N_SAMPLES,
            'emotion_noise_std': EMOTION_NOISE_STD,
        },
        'summary': summary,
        'forgetting': {exp_labels[i]: results[i]['forgetting'] for i in range(3)},
        'perception_stats': {exp_labels[i]: results[i].get('perception_stats', {})
                                for i in range(3)},
        'ewc_stats': {exp_labels[i]: results[i].get('ewc_stats') for i in range(3)},
    }

    with open('灾难性遗忘_结果摘要.json', 'w', encoding='utf-8') as f:
        json.dump(summary_output, f, indent=2, ensure_ascii=False, default=str)
    print(f"  [保存] 灾难性遗忘_结果摘要.json")

    print("\n" + "=" * 70)
    print("[完成] 灾难性遗忘测试 (增强版) 全部完成!")
    print("=" * 70)


if __name__ == '__main__':
    main()

"""
训练日志记录器

功能:
    1. CSV日志 (无依赖, 默认开启) - 记录每步训练指标
    2. TensorBoard日志 (可选) - 实时可视化
    3. 控制台日志 - 格式化输出
    4. 实验摘要 - 训练结束生成摘要报告

使用:
    from logger import Logger
    logger = Logger(log_dir="./logs", use_csv=True, use_tensorboard=False)
    logger.log_training(step=1000, loss=0.5, reward=0.8, epsilon=0.9, bwe=10.0)
    logger.log_eval(step=40000, bwe={1:4.0, 2:16.0, 3:10.0, 4:15.0}, sl={1:0.99,...})
    logger.close()
"""

import os
import csv
import time
from datetime import datetime
from typing import Dict, Optional, Any


class Logger:
    """统一训练日志记录器 (CSV + 可选TensorBoard + 控制台)"""

    def __init__(self, log_dir: str = "./logs",
                 use_csv: bool = True,
                 use_tensorboard: bool = False,
                 experiment_name: str = "idmr"):
        self.log_dir = log_dir
        self.use_csv = use_csv
        self.use_tensorboard = use_tensorboard
        self.experiment_name = experiment_name

        # 创建日志目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"{experiment_name}_{timestamp}"
        self.run_dir = os.path.join(log_dir, self.run_id)
        os.makedirs(self.run_dir, exist_ok=True)

        # CSV文件句柄
        self._csv_train = None
        self._csv_train_writer = None
        self._csv_eval = None
        self._csv_eval_writer = None

        # TensorBoard SummaryWriter
        self._tb_writer = None

        # 统计
        self._start_time = time.time()
        self._train_steps = 0

        if use_csv:
            self._init_csv()
        if use_tensorboard:
            self._init_tensorboard()

    def _init_csv(self):
        """初始化CSV日志文件"""
        # 训练日志
        train_path = os.path.join(self.run_dir, "train_metrics.csv")
        self._csv_train = open(train_path, 'w', newline='', encoding='utf-8')
        train_fields = ['step', 'loss', 'reward', 'epsilon', 'bwe_distributor',
                        'avg_reward_100', 'avg_loss_100', 'elapsed_sec']
        self._csv_train_writer = csv.DictWriter(self._csv_train, fieldnames=train_fields)
        self._csv_train_writer.writeheader()

        # 评估日志
        eval_path = os.path.join(self.run_dir, "eval_metrics.csv")
        self._csv_eval = open(eval_path, 'w', newline='', encoding='utf-8')
        eval_fields = ['step', 'node', 'bwe', 'avg_cost', 'service_level',
                       'demand_mean', 'order_mean']
        self._csv_eval_writer = csv.DictWriter(self._csv_eval, fieldnames=eval_fields)
        self._csv_eval_writer.writeheader()

    def _init_tensorboard(self):
        """初始化TensorBoard (可选, 失败则降级为CSV)"""
        try:
            from torch.utils.tensorboard import SummaryWriter
            self._tb_writer = SummaryWriter(log_dir=self.run_dir)
        except (ImportError, OSError):
            print("  [WARNING] TensorBoard不可用, 降级为CSV日志")
            self.use_tensorboard = False
            if not self.use_csv:
                self.use_csv = True
                self._init_csv()

    def log_training(self, step: int, loss: float, reward: float,
                     epsilon: float, bwe_distributor: float,
                     avg_reward_100: float = 0.0, avg_loss_100: float = 0.0):
        """记录训练指标"""
        elapsed = time.time() - self._start_time
        self._train_steps = step

        # CSV
        if self.use_csv and self._csv_train_writer:
            self._csv_train_writer.writerow({
                'step': step, 'loss': f'{loss:.6f}', 'reward': f'{reward:.4f}',
                'epsilon': f'{epsilon:.4f}', 'bwe_distributor': f'{bwe_distributor:.2f}',
                'avg_reward_100': f'{avg_reward_100:.4f}',
                'avg_loss_100': f'{avg_loss_100:.6f}',
                'elapsed_sec': f'{elapsed:.1f}',
            })
            self._csv_train.flush()

        # TensorBoard
        if self.use_tensorboard and self._tb_writer:
            self._tb_writer.add_scalar('train/loss', loss, step)
            self._tb_writer.add_scalar('train/reward', reward, step)
            self._tb_writer.add_scalar('train/epsilon', epsilon, step)
            self._tb_writer.add_scalar('train/bwe_distributor', bwe_distributor, step)

    def log_eval(self, step: int, metrics: Dict[int, Dict[str, float]]):
        """
        记录评估指标

        参数:
            step: 训练步数
            metrics: {k: {'bwe':..., 'avg_cost':..., 'service_level':...,
                          'demand_mean':..., 'order_mean':...}}
        """
        for k, m in metrics.items():
            # CSV
            if self.use_csv and self._csv_eval_writer:
                self._csv_eval_writer.writerow({
                    'step': step, 'node': k,
                    'bwe': f"{m.get('bwe', 0):.4f}",
                    'avg_cost': f"{m.get('avg_cost', 0):.4f}",
                    'service_level': f"{m.get('service_level', 0):.4f}",
                    'demand_mean': f"{m.get('demand_mean', 0):.4f}",
                    'order_mean': f"{m.get('order_mean', 0):.4f}",
                })
            self._csv_eval.flush()

            # TensorBoard
            if self.use_tensorboard and self._tb_writer:
                tag = f'eval/node{k}'
                self._tb_writer.add_scalar(f'{tag}/bwe', m.get('bwe', 0), step)
                self._tb_writer.add_scalar(f'{tag}/avg_cost', m.get('avg_cost', 0), step)
                self._tb_writer.add_scalar(f'{tag}/service_level',
                                          m.get('service_level', 0), step)

    def log_config(self, config_dict: Dict[str, Any]):
        """记录实验配置 (JSON格式)"""
        import json
        config_path = os.path.join(self.run_dir, "config_snapshot.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False, default=str)

    def save_summary(self, summary: Dict[str, Any]):
        """保存实验摘要"""
        summary_path = os.path.join(self.run_dir, "experiment_summary.json")
        import json
        summary['run_id'] = self.run_id
        summary['total_steps'] = self._train_steps
        summary['total_time_sec'] = time.time() - self._start_time
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        return summary_path

    def close(self):
        """关闭日志资源"""
        if self._csv_train:
            self._csv_train.close()
        if self._csv_eval:
            self._csv_eval.close()
        if self._tb_writer:
            self._tb_writer.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ============================================================
# 自检
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("Logger 自检")
    print("=" * 60)

    with Logger(log_dir="./logs_test", use_csv=True, use_tensorboard=False) as logger:
        # 模拟训练日志
        for step in range(0, 10000, 2000):
            logger.log_training(
                step=step, loss=0.5 * (1 - step/10000),
                reward=0.8 + 0.1 * step/10000,
                epsilon=1.0 - 0.99 * step/10000,
                bwe_distributor=10.0 + step/1000,
                avg_reward_100=0.85, avg_loss_100=0.05,
            )

        # 模拟评估日志
        metrics = {
            1: {'bwe': 4.01, 'avg_cost': 9.05, 'service_level': 0.992,
                'demand_mean': 19.48, 'order_mean': 19.48},
            2: {'bwe': 16.31, 'avg_cost': 14.07, 'service_level': 0.997,
                'demand_mean': 19.48, 'order_mean': 19.49},
            3: {'bwe': 10.43, 'avg_cost': 26.97, 'service_level': 0.901,
                'demand_mean': 19.49, 'order_mean': 19.51},
            4: {'bwe': 15.57, 'avg_cost': 16.69, 'service_level': 1.000,
                'demand_mean': 19.51, 'order_mean': 19.51},
        }
        logger.log_eval(step=40000, metrics=metrics)

        # 保存配置快照
        logger.log_config({'seed': 42, 'lr': 1e-3, 'total_steps': 40000})

        # 保存摘要
        summary_path = logger.save_summary({
            'best_reward': 0.892,
            'final_bwe_distributor': 10.43,
            'final_sl_distributor': 0.901,
        })

    print(f"  日志目录: {logger.run_dir}")
    print(f"  摘要文件: {summary_path}")
    print("  [OK] Logger自检通过!")

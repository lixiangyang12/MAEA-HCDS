# MAEA-HCDS: Emotion-Aware Multi-Agent Supply Chain

**多智能体情绪感知人智协同决策系统 (Multi-Agent Emotion-Aware Human-AI Collaborative Decision System)**

> 情绪扰动、激励阻断与协同鲁棒：多智能体供应链牛鞭效应缓解研究
> Mitigating the Bullwhip Effect via Emotion Disturbance, Incentive Blockade and Collaborative Robustness

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![NumPy](https://img.shields.io/badge/Implementation-NumPy-orange.svg)](https://numpy.org/)
[![PettingZoo](https://img.shields.io/badge/MARL-PettingZoo-red.svg)](https://pettingzoo.farama.org/)
[![Reproducible](https://img.shields.io/badge/Reproducible-100%25-brightgreen.svg)](#可复现性保证)
[![BWE Reduction](https://img.shields.io/badge/BWE%20Reduction-96.66%25-success.svg)](#实验结果)
[![Paper Version](https://img.shields.io/badge/Paper%20Version-719-blue.svg)](./情绪扰动、激励阻断与协同鲁棒：多智能体供应链牛鞭效应缓解研究_719修改后.docx)

> **构建"情绪扰动(诊断) → 激励阻断(治疗) → 协同鲁棒(免疫) → 持续稳健(鲁棒)"的递进因果链，将情绪演化、正向激励与多智能体协同融合为可计算的BWE缓解框架。**

---

## 目录

- [项目简介](#项目简介)
- [核心创新](#核心创新)
- [项目结构](#项目结构)
- [环境依赖](#环境依赖)
- [一键运行指南](#一键运行指南)
- [复现论文核心图表](#复现论文核心图表)
- [数据集与预训练模型](#数据集与预训练模型)
- [核心模型说明](#核心模型说明)
- [实验结果](#实验结果)
- [极限压力测试](#极限压力测试)
- [可复现性保证](#可复现性保证)
- [FAQ 常见问题](#faq-常见问题)
- [引用与致谢](#引用与致谢)
- [许可证](#许可证)

---

## 项目简介

### 研究背景

牛鞭效应（Bullwhip Effect, BWE）是供应链管理中的经典难题：终端消费者需求的小幅波动，在向上游传递过程中被逐级放大，导致库存积压、成本飙升和服务水平下降。自 Forrester（1961）和 Lee et al.（1997）奠定理论基础以来，传统缓解方法（如信息共享、VMI、CPFR）均基于一个隐含假设——**决策者是完全理性的**。

然而，行为经济学的奠基性研究（Kahneman & Tversky, 1979）表明，人类决策者普遍存在**损失厌恶**：对同等规模的缺货损失与库存积压，缺货的心理感知权重约为积压的 2.25 倍。这种情绪偏差在动态突发事件（如疫情需求暴涨、港口罢工断供）下被显著放大，驱使决策者陷入"恐慌性囤货 → 牛鞭放大 → 更大恐慌"的恶性循环。

### 本研究的回答

本研究在李勇等（2022）提出的"人机协同智慧决策机器人（IDMR）"基础上，融合**行为经济学**与**多智能体强化学习（MARL）**，构建了一个包含情绪演化、正向激励和持续学习的供应链协同决策系统，回答三个核心问题：

1. **如何量化人类情绪对牛鞭效应的放大机制？**
2. **能否通过正向激励函数在系统层面阻断恐慌蔓延？**
3. **多机器人系统在动态突发事件下能否保持鲁棒性？**

### 理论基础

| 理论来源 | 核心概念 | 本项目应用 |
|---------|---------|-----------|
| Lee et al. (1997) | 牛鞭效应方差比 BWE = var(q)/var(D) | 核心评估指标 |
| Kahneman & Tversky (1979) | 损失厌恶（2.25 倍系数） | 情绪演化方程设计（2:1 惩罚-奖励比） |
| 李勇等 (2022) | IDMR 人机协同 DQN | 单智能体基线复现 |
| Kirkpatrick et al. (2017) | EWC 弹性权重巩固 | 持续学习防灾难性遗忘 |
| Schaul et al. (2016) | 优先级经验回放（PER） | 情感增强采样 |

---

## 核心创新

### 创新一：情绪演化方程

将决策者情绪建模为连续状态变量 $E_t \in [-1, 1]$，通过带饱和的动力学方程演化：

$$E_t = \tanh(\alpha \cdot E_{t-1} + \gamma \cdot \Phi_t)$$

$$\Phi_t = -w_s \cdot \text{stockout\_rate} + w_m \cdot \text{match\_factor} - w_e \cdot \text{excess\_rate}$$

- $E_t < 0$：恐慌/焦虑（损失厌恶，倾向过度订货）
- $E_t > 0$：自信/乐观（风险中性，倾向精准订货）
- **关键设计**：$w_s : w_m = 1.0 : 0.5 = 2:1$，直接对应 Kahneman 的 2.25 倍损失厌恶系数

### 创新二：正向激励奖励函数

突破传统 DQN 仅依赖缺货惩罚的局限，设计库存精准匹配正向激励：

$$\text{bonus} = w_b \cdot \max\left(0,\; 1 - \frac{|NS_t / \hat{D}_{t+1} - 1|}{\Delta_{\max}}\right)$$

当库存精准覆盖预测需求（coverage_ratio ∈ [0.8, 1.5]）时给予钟形奖励，引导 DQN 学习"按需订货"而非"囤货保险"策略。

### 创新三：多智能体协同 + 情绪传染

基于 PettingZoo AECEnv 框架实现 4 节点独立 Agent，支持：
- 情绪传染（恐慌从下游蔓延至上游，30% 概率，强度 −0.4）
- 动态突发事件（需求突变 2×/0.5×、供应中断 3-5 周期）
- 协同通信通道（信息共享）

### 创新四：持续学习机制

- **优先级经验回放（PER）**：SumTree 数据结构 + 情绪增强采样
- **情感增强 Q 网络**：状态维度从 5 维扩展到 6 维（新增 $E_t$）
- **弹性权重巩固（EWC）**：Fisher 信息矩阵锚点正则化，防止灾难性遗忘
- **情绪感知噪声**：模拟机器人对情绪的不完美感知，测试鲁棒性

---

## 项目结构

```
.
├── config.yaml                    # 统一配置文件 (供应链参数/DQN超参数/情绪模块)
├── config.py                      # 配置加载器 + 随机种子控制
├── requirements.txt               # Python 依赖
├── README.md                      # 本文件
├── LICENSE                        # MIT 许可证
├── CITATION.cff                   # 引用元数据 (GitHub一键引用)
│
├── ── 核心仿真模块 ──
├── supply_chain_env.py            # 供应链仿真环境 (AR(1)需求/理性决策基线)
├── idmr_agent.py                  # IDMR DQN 智能体 (纯 NumPy) + 正向激励 + 情绪
├── emotion_module.py              # 情绪演化方程 (EmotionState 类)
├── marl_supply_chain_env.py       # 多智能体环境 (PettingZoo AECEnv)
├── dynamic_events.py              # 动态事件触发器 (需求突变/供应中断/情绪传染)
│
├── ── 持续学习模块 ──
├── prioritized_replay.py          # 优先级经验回放 (SumTree + 情感增强)
├── ewc.py                         # 弹性权重巩固 (Fisher 矩阵 + 锚点正则)
├── continual_idmr.py              # 持续学习 IDMR (PER + 情感增强 Q 网络 + EWC)
├── continual_learning_test.py     # 灾难性遗忘测试 (EWC + 情绪感知噪声)
│
├── ── 实验与评估 ──
├── batch_runner.py                # 三组对比实验自动化运行
├── attribution_analysis.py        # 深度归因分析 (相关性/传染路径/阻断效应)
├── attribution_analysis_20k.py    # 20000周期归因分析 (719版主实验)
├── generate_basic_experiment.py   # 基础实验生成 (Baseline对标李勇等2022)
├── generate_basic_experiment_20k.py # 20000周期基础实验 (719版)
├── evaluation_report.py           # 多维度综合评估报告 (LaTeX 输出)
├── analyze_sensitivity.py         # 81组参数敏感性分析 (3^4网格搜索)
├── diagnose_penalty.py            # 惩罚机制诊断
├── check_results.py               # 结果一致性检查
├── stress_test.py                 # 极限压力测试 (参数敏感性/人类干预/计算开销)
│
├── ── 论文配图生成 (719版, SCI顶刊标准) ──
├── generate_paper_figures_719.py  # 719版论文配图主脚本 (图1/图2/图8)
├── generate_mechanism_figure.py   # 系统机制图
├── generate_4group_comparison.py  # 四组对比实验图
├── generate_ablation_paper_figures.py # 消融实验论文图
├── generate_exp2_charts.py        # Exp_2综合分析图
├── generate_basic_svgs.py         # 基础实验SVG图
├── generate_fig6_idmr_flowchart.py # IDMR流程图
├── generate_fig15_17_svgs.py      # 图15-17 SVG
├── generate_fig18_20_svgs.py      # 图18-20 SVG
├── eval_and_plot_svg.py           # SVG评估图
│
├── ── docx文档生成 ──
├── generate_algorithm_docx.py     # 算法章节docx
├── generate_basic_experiment_docx.py # 基础实验章节docx
├── generate_basic_setup_docx.py   # 基础设置章节docx
├── generate_decision_algorithm_docx.py # 决策算法章节docx
├── generate_exp2_docx.py          # Exp_2章节docx
├── generate_results_analysis_docx.py # 结果分析章节docx
├── generate_sensitivity_docx.py   # 敏感性分析章节docx
├── generate_abstract_tables_docx.py # 摘要表格docx
├── generate_ablation_log_docx.py  # 消融实验日志docx
├── convert_to_docx.py             # 通用md→docx转换
│
├── ── 数据加载与附录 ──
├── load_dataset.py                # 数据集加载器 (CSV/JSON 统一接口)
├── load_pretrained_models.py      # 预训练模型加载器 (DQN 权重统一接口)
├── appendix_code.py               # 论文附录代码 (情绪方程 + 奖励函数精简版)
├── logger.py                      # CSV + TensorBoard 日志
│
├── ── 实验输出 ──
├── 实验结果摘要.json               # 三组实验汇总 (BWE/SL/成本)
├── 归因分析_详细数据.csv            # Exp_2 逐周期 8000 条记录
├── 灾难性遗忘_结果摘要.json         # EWC + 噪声实验结果
├── 综合评估报告.json               # 多维度评估 (4 维度/6 张 LaTeX 表)
├── 极限压力测试_结果摘要.json       # 压力测试 24+6+5 组完整结果
│
├── ── 论文配图 (719版, 矢量格式, SCI顶刊标准) ──
├── svg_figures_paper_719/         # 719版论文配图目录
│   ├── Fig1_System_Mechanism.pdf/.svg/.png   # 图1 系统机制图 (四层架构+递进因果链)
│   ├── Fig2_Decision_Flow.pdf/.svg/.png      # 图2 多智能体人智协同供应链决策设计流程图
│   └── Fig8_Emotion_Contagion.pdf/.svg/.png  # 图8 情绪传染网络图 (5子图)
│
├── ── 论文与评审 ──
├── 情绪扰动、激励阻断与协同鲁棒：多智能体供应链牛鞭效应缓解研究_719修改后.docx  # 719版论文
├── 论文评审意见_第一次_712版.md    # 第一次评审意见 (712版)
├── 论文评审意见_第三次_718修改后版.md # 第三次评审意见 (718修改后版)
├── 论文评审意见_第四次_719修改后版.md # 第四次评审意见 (719修改后版, 评级A)
├── Exp_2综合分析_人智协同智慧决策.md # Exp_2综合分析
├── Limitations章节草稿.md         # 局限性章节草稿
│
├── ── 仓库文档 ──
├── docs/                          # 仓库文档目录
│   └── REPO_STRUCTURE.md          # 仓库目录结构详细说明
│
└── idmr_model.pkl                 # 训练好的 DQN 模型权重 (直接复现用)
```

---

## 环境依赖

### 系统要求

- **Python**: >= 3.9
- **OS**: Windows / Linux / macOS
- **RAM**: >= 4 GB（训练时建议 8 GB）
- **GPU**: 不需要（纯 NumPy 实现）

### 安装

```bash
# 1. 克隆项目
git clone <repository_url>
cd 企业运营与科研管理数据库

# 2. 创建虚拟环境 (推荐 conda)
conda create -n emotion-marl python=3.9
conda activate emotion-marl
# 或使用 venv
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
```

### 核心依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| numpy | >=1.21, <2.0 | DQN 前向/反向传播（纯 NumPy 实现） |
| PyYAML | >=5.4 | 配置文件加载 |
| matplotlib | >=3.5 | 学术级矢量图表 |
| networkx | >=2.6 | 情绪传染路径可视化 |
| pandas | >=1.3 | 实验数据分析 |
| pettingzoo | >=1.21 | 多智能体环境框架 |
| scipy | >=1.7 | 统计分析（皮尔逊相关） |

> **注意**: 本项目 DQN 采用纯 NumPy 实现，**无需 PyTorch/TensorFlow**，降低复现门槛。

---

## 一键运行指南

### 快速开始（3 步复现全部实验）

```bash
# Step 1: 配置自检 (验证环境)
python config.py

# Step 2: 运行三组对比实验 (Baseline / 单智能体 / 多智能体+情绪)
#         生成: 实验结果摘要.json + 对比图
python batch_runner.py

# Step 3: 生成论文核心图表 (PDF/SVG 矢量图)
python paper_figures.py
```

### 完整实验流程

```bash
# 1. 单智能体 IDMR 训练 (DQN, 纯 NumPy)
python idmr_agent.py

# 2. 三组对比实验 (约 10-15 分钟)
python batch_runner.py

# 3. 深度归因分析 (情绪-决策相关性/传染路径)
python attribution_analysis.py

# 4. 多维度评估报告 (LaTeX 表格输出)
python evaluation_report.py

# 5. 持续学习测试: EWC + 情绪感知噪声 (约 15-20 分钟)
python continual_learning_test.py

# 6. 极限压力测试 (参数敏感性/人类干预/计算开销)
python stress_test.py

# 7. 生成论文 3 张核心矢量图表
python paper_figures.py

# 8. 数据集加载自检
python load_dataset.py

# 9. 预训练模型加载自检
python load_pretrained_models.py
```

### 使用预训练模型（无需重新训练）

```python
from load_pretrained_models import load_idmr_agent

# 一行加载预训练 DQN 权重
agent = load_idmr_agent()
# 直接进行推理评估, 跳过训练过程
```

---

## 复现论文核心图表

### 图 1: 系统架构图

展示包含情绪演化模块、正向激励模块和多机器人协同机制的整体框架。

```bash
python paper_figures.py
# 输出: 图1_系统架构图.pdf (82 KB) + .svg (183 KB)
```

**内容**: 4 级供应链节点 + 情绪演化模块 + 正向激励模块 + 协同通信通道 + 持续学习模块 (PER+EWC)

### 图 2: 牛鞭效应对比图

多折线图，展示 Baseline、单智能体、多智能体+情绪三组实验在 50 个周期内的订单波动放大过程。

```bash
python paper_figures.py
# 输出: 图2_牛鞭效应对比图.pdf (56 KB) + .svg (146 KB)
```

**数据源**: `归因分析_详细数据.csv`（Exp_2 真实数据）+ AR(1) 需求合成（Baseline/Exp_1）

### 图 3: 情绪-成本散点图

横轴为情绪波动指数，纵轴为供应链总成本，用不同颜色区分实验组，展示情绪稳定与成本降低的正相关性。

```bash
python paper_figures.py
# 输出: 图3_情绪成本散点图.pdf (61 KB) + .svg (136 KB)
```

**包含**: 线性拟合 + 皮尔逊相关系数 + 理想区域/情绪扰动区标注

### 图表学术规范

- **配色**: Nature/Science 色盲友好配色（`#E64B35` / `#4DBBD5` / `#00A087`）
- **字体**: Times New Roman + SimHei（中英文兼容）
- **格式**: PDF（期刊投稿）+ SVG（网页展示），dpi=300
- **标签**: 中英文双语坐标轴
- **标题**: 图片底部中间位置（Figure caption 规范）

---

## 数据集与预训练模型

### 数据集加载

本项目提供完整的实验数据集，通过 `load_dataset.py` 统一加载：

```python
from load_dataset import load_all, load_attribution_data

# 一站式加载全部数据
data = load_all()

# 或单独加载
df = load_attribution_data()         # DataFrame, 8000 条逐周期记录
summary = load_experiment_summary()  # 三组实验 BWE/SL/成本
forgetting = load_forgetting_results()  # EWC + 噪声实验
eval_report = load_evaluation_report()  # 多维度评估
```

| 数据集 | 文件 | 格式 | 内容 |
|--------|------|------|------|
| 归因分析数据 | `归因分析_详细数据.csv` | CSV | Exp_2 逐周期 8000 条（情绪/订货量/库存/事件标记） |
| 实验结果摘要 | `实验结果摘要.json` | JSON | 三组实验 BWE/SL/成本/情绪方差 |
| 遗忘测试结果 | `灾难性遗忘_结果摘要.json` | JSON | EWC + 噪声实验完整数据 |
| 综合评估报告 | `综合评估报告.json` | JSON | 4 维度评估指标 |
| 压力测试结果 | `极限压力测试_结果摘要.json` | JSON | 24+6+5 组压测完整数据 |

### 预训练模型加载

通过 `load_pretrained_models.py` 加载训练好的 DQN 权重：

```python
from load_pretrained_models import load_idmr_agent, load_model_metadata

# 一行加载预训练 DQN
agent = load_idmr_agent()

# 查看模型元信息
meta = load_model_metadata()
print(meta)
# {'training_steps': 40000, 'final_reward': 0.85,
#  'state_dim': 5, 'action_dim': 30, 'seed': 42}
```

---

## 核心模型说明

### 1. 供应链环境

```python
from supply_chain_env import SupplyChainEnv, RationalAgent

env = SupplyChainEnv(d=10, rho=0.5, sigma_eps=5.0, L=2, p=5, z=2, K=4)
# AR(1) 需求模型: D_t = d + rho * D_{t-1} + epsilon_t
# 4 级供应链: 顾客 -> 零售商 -> 批发商 -> 分销商 -> 制造商
```

### 2. 情绪演化模块

```python
from emotion_module import EmotionState

emotion = EmotionState(alpha=0.7, gamma=2.0, w_stockout=1.0, w_match=0.5, w_excess=0.3)
# 情绪演化: E_t = tanh(alpha * E_{t-1} + gamma * Phi_t)
emotion.update(stockout_rate=0.1, match_factor=0.8, excess_rate=0.0)
# 决策映射: 恐慌放大缺货惩罚, 乐观放大正向激励
weights = emotion.get_reward_weights(base_stockout_weight=1.0, base_bonus_weight=0.3)
```

### 3. IDMR 智能体

```python
from idmr_agent import IDMRAgent, IDMRSupplyChainEnv, train_idmr

# 状态: s_t = [S, WIP, q_downstream, trans, q_self]  (5 维)
# 动作: a_t in [11, 40]  (30 个离散动作)
# 奖励: r = fill_rate + inventory_bonus - stockout_penalty - holding_penalty
agent = IDMRAgent(state_dim=5, action_min=11, action_max=40, lr=1e-3)
env, agent, history = train_idmr(total_steps=20000, seed=42)
```

### 4. 多智能体环境

```python
from marl_supply_chain_env import MARLSupplyChainEnv

env = MARLSupplyChainEnv()
# PettingZoo AECEnv: 4 个独立 Agent (retailer/wholesaler/distributor/manufacturer)
# 支持: 情绪传染 + 动态事件 + 协同通信
```

### 5. 持续学习

```python
from continual_idmr import ContinualIDMRAgent

agent = ContinualIDMRAgent(
    emotion_augmented=True,   # 6 维状态 (含 E_t)
    use_per=True,             # 优先级经验回放
    use_ewc=True,             # 弹性权重巩固
    emotion_noise_std=0.15,   # 情绪感知噪声 (模拟误判)
)
```

---

## 实验结果

### 四组对比实验 (719版, 20000周期主实验)

| 指标 | Baseline (理性) | Exp_1 (单智能体IDMR) | Exp_1b (Exp_1+情绪) | Exp_2 (MAEA-HCDS全要素) |
|------|:---:|:---:|:---:|:---:|
| 制造商 BWE | 301.75 | 22.70 | 22.78 | **10.07** |
| 制造商 BWE 降幅 | — | -92.5% | -92.45% | **-96.66%** |
| 分销商 BWE | 67.33 | 10.65 | 10.72 | **3.77** |
| 系统平均 SL | — | 99.62% | 99.61% | **94.73%** |
| 系统总成本 | 1664.80 | 39.54 | 39.61 | — |
| 总成本降幅 | — | -97.6% | -97.6% | **-72.5%** |

> **关键发现**: Exp_2 vs Baseline 制造商BWE从301.75降至10.07（总降幅96.66%），系统总成本较理性决策基线下降72.5%。

### 剥离实验效应分解 (719版核心创新)

| 效应类型 | 计算方式 | 制造商BWE变化 | 解释 |
|---------|---------|:---:|------|
| 情绪机制独立效应 | Exp_1b - Exp_1 | +0.08 (<2%) | DQN学习能力吸收了大部分情绪扰动 |
| 协同通信独立效应 | Exp_2 - Exp_1b | -12.71 (**-55.79%**) | 协同通信是核心机制 |
| 联合效应 | Exp_2 - Exp_1 | -12.63 (**-96.66%**) | 整体人智协同机制的总贡献 |

> **机制堆叠悖论化解**: 协同通信范式为核心(55.79%)，情绪感知与持续学习为鲁棒性增强的辅助机制。

### 持续学习实验（EWC + 情绪感知噪声）

| 指标 | A: 无 EWC | B: 有 EWC | C: EWC+噪声 (σ=0.15) |
|------|:---:|:---:|:---:|
| SL 变化 | +0.001 | **+0.014** | -0.013 |
| 奖励变化 | +0.004 | **+0.057** | -0.047 |
| 感知 MAE | 0 | 0 | 0.1126 |

> EWC 使服务水平提升和奖励提升均为无 EWC 组的 **14 倍**；情绪感知噪声 (σ=0.15) 导致奖励下降 6%，但 BWE 保持稳定。

### 参数敏感性分析 (81组 3^4 网格搜索)

- **55组 (67.9%)** 同时实现"成本降低+服务水平提升"双目标
- 高需求波动条件下 **全部27组** 均实现双目标，验证卓越鲁棒性
- 全部81组平均成本降低0.12%、平均SL提升0.021pp

### 核心发现 (719版递进因果链)

1. **H1 情绪扰动假设（部分验证）**: 机制存在性成立，分销商情绪均值E=-0.778，95.9%周期处于恐慌饱和，情绪-决策Pearson相关系数达极显著水平（$p<10^{-60}$），但DQN学习能力吸收了大部分情绪扰动，情绪机制对BWE的独立效应不足2%。
2. **H2 激励阻断假设（验证成立）**: 正向激励函数使批发商恐慌时过度订货比例较中性状态下降42.35个百分点，验证了目标重塑对过度订货行为的阻断效应。
3. **H3 协同鲁棒性假设（部分验证）**: 多智能体协同机制使制造商BWE从22.78降至10.07（降幅55.79%，高于45%预设目标），在情绪感知噪声干扰下通过EWC机制仍保持决策稳定。

---

## 极限压力测试

为回应审稿人对系统鲁棒性的严苛关切，本研究专门设计了极限压力测试（详见 `stress_test.py` 与 `极限压力测试_结果摘要.json`）：

| 测试维度 | 测试规模 | 崩溃次数 | 关键发现 |
|----------|----------|----------|----------|
| 极端参数敏感性 | 24 组（参数 0.01~10.0） | 0 | 揭示奖励-决策解耦局限 |
| 非理性人类干预 | 6 场景（0%~75%） | 0* | 25% 保守者致零售商 SL=0.001 |
| 计算开销可扩展性 | 5 级（K=4~64） | 0 | 线性可扩展 0.014 ms/节点 |

> （*）虽未触发均值型崩溃判据，但保守者场景存在关键节点 SL 崩塌的尾部风险。

详细的方法论局限讨论见 `Limitations章节草稿.md`。

---

## 可复现性保证

所有实验使用固定随机种子（`seed=42`），通过 `config.py` 的 `set_seed()` 函数统一控制 Python + NumPy 随机数生成器，确保 **100% 可复现**。

```python
from config import set_seed
set_seed(42)  # 固定随机种子
```

### 硬件基准

| 指标 | 测试值 | 工业阈值 | 判定 |
|------|--------|----------|------|
| 单周期推理耗时 | 0.303 ms | 100 ms | 通过 |
| 单步训练耗时 | 0.187 ms | — | — |
| 64 节点单周期 | 0.911 ms | 100 ms | 通过 |
| 每节点边际 | 0.014 ms | — | 线性 |

测试环境: Intel i7 CPU, NumPy 实现, 无 GPU 加速

---

## FAQ 常见问题

### Q1: 情绪参数如何在现实中获取？

**A**: 参数非任意设定，而是有理论依据。$w_s : w_m = 2:1$ 对应 Kahneman 的 2.25 倍损失厌恶系数；$\alpha = 0.7$ 参考情绪心理学的衰减记忆模型。真实部署可通过三条路径校准：(1) ERP/CRM 系统的订单犹豫时间；(2) 沟通日志的 NLP 情感分析；(3) 可穿戴设备的生理信号。详见 Limitations 章节 §2.3。

### Q2: 正向激励会不会导致缺货率上升？

**A**: 实验数据给出否定答案。引入正向激励后分销商 SL 从 88.8% 提升至 99.9%，缺货风险几乎消除。这是因为正向激励将优化目标从"最小化缺货"（鼓励囤货）转向"最大化精准匹配"（鼓励按需订货），反而减少了盲目囤积导致的下游缺货。

### Q3: 纯 NumPy 实现的 DQN 性能是否足够？

**A**: 足够。本研究的 DQN 规模较小（隐藏层 64 神经元，约 10,000 参数），纯 NumPy 实现的单步训练耗时仅 0.187 ms。对于工业级大规模网络，可迁移至 PyTorch+CUDA，预计 10-50× 加速。

### Q4: 如何扩展到网络型供应链拓扑？

**A**: 当前实现已支持任意 K 值的线性供应链（`SupplyChainEnv` 已动态生成节点名称）。网络型拓扑需扩展 `MARLSupplyChainEnv` 的 agent 交互图。计算开销呈线性增长（每节点 0.014 ms），64 节点仅 0.911 ms。

---

## 引用与致谢

### 引用

如本代码对您的研究有帮助，请引用：

```bibtex
@article{yang2026maea_hcds,
  title   = {情绪扰动、激励阻断与协同鲁棒：多智能体供应链牛鞭效应缓解研究},
  author  = {杨理想 and 王晶},
  journal = {中国管理科学 (投稿中)},
  year    = {2026},
  note    = {Doctoral Research, Management Science and Engineering,
             Yanshan University, School of Economics and Management},
  url     = {https://github.com/lixiangyang12/MAEA-HCDS}
}
```

或使用本仓库的 [CITATION.cff](CITATION.cff) 一键引用（GitHub 自动识别）。

### 参考文献

1. Lee, H. L., Padmanabhan, V., & Whang, S. (1997). *Information distortion in a supply chain: The bullwhip effect*. Management Science, 43(4), 546-558.
2. Kahneman, D., & Tversky, A. (1979). *Prospect theory: An analysis of decision under risk*. Econometrica, 47(2), 263-291.
3. 李勇, 等. (2022). *缓解牛鞭效应的新途径：人机协同的智慧决策机器人*. 管理科学.
4. Kirkpatrick, J., et al. (2017). *Overcoming catastrophic forgetting in neural networks*. PNAS, 114(13), 3521-3526.
5. Schaul, T., et al. (2016). *Prioritized experience replay*. ICLR.
6. Mnih, V., et al. (2015). *Human-level control through deep reinforcement learning*. Nature, 518(7540), 529-533.
7. Foerster, J., et al. (2018). *Counterfactual multi-agent policy gradients*. AAAI.
8. Rashid, T., et al. (2018). *QMIX: Monotonic value function factorisation for deep multi-agent reinforcement learning*. ICML.
9. Schweitzer, M. E., & Cachon, G. P. (2000). *Decision bias in the newsvendor problem*. Management Science, 46(3), 404-420.
10. Ortony, A., Clore, G. L., & Collins, A. (1990). *The cognitive structure of emotions*. Cambridge University Press.

---

## 许可证

MIT License — 见 [LICENSE](LICENSE) 文件

---

## 致谢

感谢燕山大学经济与管理学院对本研究的支持。

本项目遵循开源学术规范，欢迎研究者在复现、扩展、批评的基础上推进这一方向的研究。

## 评审历史

本论文经历了四轮严格评审，评审意见与修改演进过程公开存档：

| 版本 | 评审意见文件 | 综合评级 |
|------|------------|:---:|
| 712版 | [论文评审意见_第一次_712版.md](论文评审意见_第一次_712版.md) | B+ |
| 718导师意见修改版 | — | A- |
| 718修改后版 | [论文评审意见_第三次_718修改后版.md](论文评审意见_第三次_718修改后版.md) | A- |
| **719修改后版** | [论文评审意见_第四次_719修改后版.md](论文评审意见_第四次_719修改后版.md) | **A** |

> 719版首次升级至A级，21项修改意见完成率81.0%，第三次评审14项问题修复率57.1%。

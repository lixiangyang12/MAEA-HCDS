# 仓库目录结构详细说明

本文档详细说明 MAEA-HCDS 仓库的目录组织、文件功能与复现路径，便于其他作者快速定位代码与数据。

## 顶层结构

```
MAEA-HCDS/
├── README.md                 # 项目主文档（含快速开始、实验结果、引用方式）
├── LICENSE                   # MIT 开源许可证
├── CITATION.cff              # GitHub 一键引用元数据
├── requirements.txt          # Python 依赖清单
├── config.yaml               # 统一配置文件（供应链参数/DQN超参数/情绪模块）
├── config.py                 # 配置加载器 + 随机种子控制
├── .gitignore                # Git 忽略规则
├── idmr_model.pkl            # 预训练 DQN 模型权重（直接复现用）
└── docs/                     # 仓库文档目录
    ├── REPO_STRUCTURE.md     # 本文件
    └── (其他说明文档)
```

## 核心仿真模块

| 文件 | 功能 | 关键类/函数 |
|------|------|------------|
| `supply_chain_env.py` | 四级供应链仿真环境（AR(1)需求/理性决策基线） | `SupplyChainEnv`, `RationalAgent`, `NodeState` |
| `idmr_agent.py` | IDMR DQN 智能体（纯 NumPy）+ 正向激励 + 情绪 | `IDMRAgent`, `IDMRSupplyChainEnv`, `train_idmr` |
| `emotion_module.py` | 情绪演化方程（EmotionState 类） | `EmotionState`（α=0.7, γ=2.0） |
| `marl_supply_chain_env.py` | 多智能体环境（PettingZoo AECEnv） | `MARLSupplyChainEnv` |
| `dynamic_events.py` | 动态事件触发器（需求突变/供应中断/情绪传染） | `DynamicEventTrigger` |

## 持续学习模块

| 文件 | 功能 | 关键类/函数 |
|------|------|------------|
| `prioritized_replay.py` | 优先级经验回放（SumTree + 情感增强） | `PrioritizedReplayBuffer`, `SumTree` |
| `ewc.py` | 弹性权重巩固（Fisher 矩阵 + 锚点正则） | `EWC` |
| `continual_idmr.py` | 持续学习 IDMR（PER + 情感增强 Q 网络 + EWC） | `ContinualIDMRAgent` |
| `continual_learning_test.py` | 灾难性遗忘测试（EWC + 情绪感知噪声） | `run_continual_learning_test` |

## 实验与评估模块

### 主实验

| 文件 | 功能 | 命令 |
|------|------|------|
| `batch_runner.py` | 三组对比实验自动化运行 | `python batch_runner.py` |
| `attribution_analysis.py` | 深度归因分析（8000周期） | `python attribution_analysis.py` |
| `attribution_analysis_20k.py` | 20000周期归因分析（719版主实验） | `python attribution_analysis_20k.py` |
| `generate_basic_experiment.py` | 基础实验生成（对标李勇等2022） | `python generate_basic_experiment.py` |
| `generate_basic_experiment_20k.py` | 20000周期基础实验（719版） | `python generate_basic_experiment_20k.py` |
| `evaluation_report.py` | 多维度综合评估报告（LaTeX 输出） | `python evaluation_report.py` |

### 子实验

| 文件 | 功能 |
|------|------|
| `analyze_sensitivity.py` | 81组参数敏感性分析（3^4 网格搜索） |
| `diagnose_penalty.py` | 惩罚机制诊断 |
| `check_results.py` | 结果一致性检查 |
| `stress_test.py` | 极限压力测试（参数敏感性/人类干预/计算开销） |

## 论文配图生成模块

### 719版主图（SCI顶刊标准）

| 文件 | 输出 | 说明 |
|------|------|------|
| `generate_paper_figures_719.py` | `svg_figures_paper_719/Fig1_*.pdf/.svg/.png` | 图1 系统机制图（四层架构+递进因果链） |
| `generate_paper_figures_719.py` | `svg_figures_paper_719/Fig2_*.pdf/.svg/.png` | 图2 多智能体人智协同供应链决策设计流程图 |
| `generate_paper_figures_719.py` | `svg_figures_paper_719/Fig8_*.pdf/.svg/.png` | 图8 情绪传染网络图（5子图） |

### 其他配图

| 文件 | 功能 |
|------|------|
| `generate_mechanism_figure.py` | 系统机制图（早期版本） |
| `generate_4group_comparison.py` | 四组对比实验图 |
| `generate_ablation_paper_figures.py` | 消融实验论文图 |
| `generate_exp2_charts.py` | Exp_2 综合分析图 |
| `generate_basic_svgs.py` | 基础实验 SVG 图 |
| `generate_fig6_idmr_flowchart.py` | IDMR 流程图 |
| `generate_fig15_17_svgs.py` | 图15-17 SVG |
| `generate_fig18_20_svgs.py` | 图18-20 SVG |
| `eval_and_plot_svg.py` | SVG 评估图 |

## docx 文档生成模块

| 文件 | 功能 |
|------|------|
| `generate_algorithm_docx.py` | 算法章节 docx |
| `generate_basic_experiment_docx.py` | 基础实验章节 docx |
| `generate_basic_setup_docx.py` | 基础设置章节 docx |
| `generate_decision_algorithm_docx.py` | 决策算法章节 docx |
| `generate_exp2_docx.py` | Exp_2 章节 docx |
| `generate_results_analysis_docx.py` | 结果分析章节 docx |
| `generate_sensitivity_docx.py` | 敏感性分析章节 docx |
| `generate_abstract_tables_docx.py` | 摘要表格 docx |
| `generate_ablation_log_docx.py` | 消融实验日志 docx |
| `convert_to_docx.py` | 通用 md→docx 转换 |

## 数据加载与附录

| 文件 | 功能 |
|------|------|
| `load_dataset.py` | 数据集加载器（CSV/JSON 统一接口） |
| `load_pretrained_models.py` | 预训练模型加载器（DQN 权重统一接口） |
| `appendix_code.py` | 论文附录代码（情绪方程 + 奖励函数精简版） |
| `logger.py` | CSV + TensorBoard 日志 |

## 实验输出文件

| 文件 | 格式 | 内容 |
|------|------|------|
| `实验结果摘要.json` | JSON | 三组实验汇总（BWE/SL/成本） |
| `归因分析_详细数据.csv` | CSV | Exp_2 逐周期 8000 条记录 |
| `灾难性遗忘_结果摘要.json` | JSON | EWC + 噪声实验结果 |
| `综合评估报告.json` | JSON | 多维度评估（4维度/6张LaTeX表） |
| `极限压力测试_结果摘要.json` | JSON | 压力测试 24+6+5 组完整结果 |

## 论文配图目录

```
svg_figures_paper_719/
├── Fig1_System_Mechanism.pdf/.svg/.png   # 图1 系统机制图
├── Fig2_Decision_Flow.pdf/.svg/.png      # 图2 决策设计流程图
└── Fig8_Emotion_Contagion.pdf/.svg/.png  # 图8 情绪传染网络图
```

**SCI 顶刊标准配置：**
- A4 竖版（8.27×11.69 inches）
- NMI pastel 低饱和配色
- 双语坐标轴（中文主+English副）
- 图标题底部居中
- 矢量输出（PDF + SVG + PNG @ 300 DPI）
- `svg.fonttype='none'`、`pdf.fonttype=42`（可编辑文本）

## 论文与评审文档

| 文件 | 内容 |
|------|------|
| `情绪扰动、激励阻断与协同鲁棒：多智能体供应链牛鞭效应缓解研究_719修改后.docx` | 719版论文主稿 |
| `论文评审意见_第一次_712版.md` | 第一次评审意见（712版，评级B+） |
| `论文评审意见_第三次_718修改后版.md` | 第三次评审意见（718修改后版，评级A-） |
| `论文评审意见_第四次_719修改后版.md` | 第四次评审意见（719修改后版，评级A） |
| `Exp_2综合分析_人智协同智慧决策.md` | Exp_2 综合分析 |
| `Limitations章节草稿.md` | 局限性章节草稿 |

## 复现路径

### 路径1：使用预训练模型（最快，1分钟）

```bash
python load_pretrained_models.py  # 自检预训练模型加载
python batch_runner.py            # 使用预训练模型运行三组实验
```

### 路径2：完整训练复现（约30分钟）

```bash
python config.py                  # 配置自检
python idmr_agent.py              # 训练 IDMR（DQN, 纯 NumPy）
python batch_runner.py            # 三组对比实验
python attribution_analysis_20k.py # 20000周期归因分析（719版主实验）
python continual_learning_test.py # 持续学习实验
python analyze_sensitivity.py     # 81组参数敏感性分析
python generate_paper_figures_719.py # 生成719版论文配图
```

### 路径3：图表演示（无需训练）

```bash
python generate_paper_figures_719.py  # 直接生成图1/图2/图8
```

## 依赖关系图

```
config.py / config.yaml
       │
       ▼
supply_chain_env.py ──────► idmr_agent.py
       │                        │
       ▼                        ▼
dynamic_events.py        emotion_module.py
       │                        │
       └──────┬─────────────────┘
              ▼
   marl_supply_chain_env.py
              │
              ▼
   continual_idmr.py ◄── prioritized_replay.py
              │       ◄── ewc.py
              ▼
       batch_runner.py
              │
              ▼
   attribution_analysis_20k.py
              │
              ▼
   generate_paper_figures_719.py
```

## 关键参数位置

| 参数 | 默认值 | 配置位置 |
|------|--------|---------|
| 随机种子 | 42 | `config.yaml: seed` |
| AR(1)需求 ρ | 0.5 | `config.yaml: supply_chain.rho` |
| AR(1)误差 σ_ε | 5.0 | `config.yaml: supply_chain.sigma_eps` |
| 提前期 L | 2 | `config.yaml: supply_chain.L` |
| DQN学习率 | 0.001 | `config.yaml: dqn.learning_rate` |
| 折扣因子 γ | 0.9 | `config.yaml: dqn.gamma` |
| 情绪惯性 α | 0.7 | `config.yaml: idmr.emotion_alpha` |
| 情绪敏感度 γ | 2.0 | `config.yaml: idmr.emotion_gamma` |
| 损失厌恶权重比 | 2:1 | `config.yaml: idmr.emotion_w_stockout / emotion_w_match` |
| 情绪传染概率 | 0.3 | `dynamic_events.py` |
| 训练步数 | 40000 | `config.yaml: training.total_steps` |
| 评估周期 | 20000 | `batch_runner.py: TOTAL_PERIODS` |
| 动态事件次数 | 76（53需求+23供应） | `marl_supply_chain_env.py` |

## 联系方式

- 作者：杨理想（燕山大学经济与管理学院）
- 论文版本：719修改后版
- 综合评级：A（第四次STORM评价）
- 开源许可：MIT

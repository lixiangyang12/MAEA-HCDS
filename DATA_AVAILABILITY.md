# 数据可用性声明

为促进学术透明与可复现研究，本研究全部仿真代码、实验数据生成脚本、预训练模型与论文配图已在 GitHub 公开仓库发布，遵循 MIT 开源许可证。仓库地址：https://github.com/lixiangyang12/MAEA-HCDS （版本 v719，提交标识 3790212）。其他研究者可通过上述地址获取全部工程文件，实现本文实验结果的完整复现与二次开发。

## 1. 数据来源

本研究未使用任何真实世界数据，全部实验数据均通过计算机仿真生成。仿真环境基于李勇等（2022）提出的四级供应链牛鞭效应模型构建，需求过程采用 AR(1) 自回归模型 D_t = d + ρ·D_{t-1} + ε_t，其中 d = 10、ρ = 0.5、ε ~ N(0, 5²)，订货提前期 L = 2，供应链层级 K = 4（零售商、批发商、分销商、制造商）。全部仿真参数详见仓库根目录的 config.yaml 配置文件。

为确保实验结果完全可复现，本研究采用固定随机种子 seed = 42，覆盖 NumPy 随机数生成器、DQN 经验回放采样、动态事件触发（需求突变、供应中断、情绪传染）等全部随机过程。在相同硬件与软件环境下，重复运行将得到数值完全一致的实验结果。

## 2. 代码与预训练模型

仓库包含 68 个 Python 脚本，覆盖仿真环境、智能体决策、持续学习、实验运行与论文配图生成等全部模块。核心模块包括：四级供应链仿真环境（supply_chain_env.py）、IDMR 智能体（idmr_agent.py）、情绪演化模块（emotion_module.py）、多智能体协同环境（marl_supply_chain_env.py）、动态事件触发器（dynamic_events.py）、优先级经验回放（prioritized_replay.py）、弹性权重巩固（ewc.py）、持续学习智能体（continual_idmr.py）以及三组对比实验自动化运行脚本（batch_runner.py）。

仓库同时提供预训练模型 idmr_model.pkl，保存了 DQN 神经网络权重、经验回放池状态与训练超参数。其他研究者可在无需重新训练的条件下，直接加载该模型完成全部评估实验。深度 Q 网络采用纯 NumPy 实现，前向传播与反向传播均不依赖 PyTorch、TensorFlow 等深度学习框架，降低了复现门槛。

## 3. 复现路径

结合不同研究需求，本仓库提供三条复现路径：

**（1）预训练模型快速复现（约 1 分钟）：** 直接加载 idmr_model.pkl，运行 batch_runner.py 即可复现全部四组对比实验的关键指标，包括牛鞭效应方差比、系统平均成本、服务水平、情绪波动指数与协同收益。

**（2）完整训练复现（约 30 分钟）：** 删除 idmr_model.pkl 后运行 batch_runner.py，从零开始训练 DQN 智能体。由于随机种子固定，所得结果与预训练模型评估结果完全一致，可验证训练过程的确定性。

**（3）图表演示（无需训练）：** 仓库 svg_figures_paper_719/ 目录直接提供论文图 1（系统机制图）、图 2（多智能体决策流程图）与图 8（情绪传染网络图）的 PDF、SVG 与 PNG 三种格式文件，其他研究者可不经任何计算直接查阅与引用。

## 4. 依赖环境

本仓库代码在 Python 3.9 及以上版本运行，依赖库详见仓库根目录的 requirements.txt 文件，主要包括：NumPy（1.21 及以上，数值计算与 DQN 实现）、Matplotlib（3.5 及以上，学术级矢量图表绘制）、NetworkX（2.6 及以上，情绪传染路径可视化）、Pandas（1.3 及以上，实验数据分析）、PettingZoo（1.21 及以上，多智能体环境框架）、SciPy（1.7 及以上，统计分析）、PyYAML（5.4 及以上，配置文件加载）。

推荐使用 Anaconda 或 Miniconda 创建独立虚拟环境以避免依赖冲突。安装命令为：pip install -r requirements.txt。本仓库已在 Windows 10/11、Ubuntu 20.04 与 macOS 12 平台完成兼容性测试。

## 5. 许可证

本仓库代码与配套实验数据采用 MIT 许可证（详见 LICENSE 文件）开源。MIT 许可证允许其他研究者自由复制、修改、合并、发布、分发、再授权与销售本仓库代码，仅需在所有副本中保留版权声明与许可声明。论文正文、图表与文字内容不在 MIT 许可证范围内，其版权由作者保留，引用须遵循学术规范。

## 6. 引用方式

若本仓库代码或实验方法对您的研究有帮助，请按以下 BibTeX 格式引用：

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

仓库根目录同时提供 CITATION.cff 元数据文件，GitHub 平台可自动识别并生成一键引用功能，支持 BibTeX、APA、Chicago 等多种引用格式。

## 7. 联系方式

通讯作者：杨理想，燕山大学经济与管理学院。

邮箱：yanglixiang@stdu.ysu.edu.cn

若在复现过程中遇到任何问题，或对代码改进存在建议，欢迎在 GitHub 仓库的 Issues 页面提交反馈（https://github.com/lixiangyang12/MAEA-HCDS/issues），作者将及时回应并维护代码更新。

## 8. 致谢

感谢燕山大学经济与管理学院对本研究提供的学术支持。感谢李勇教授及其团队在牛鞭效应人机协同决策领域的前瞻性工作，为本研究提供了重要的理论框架与基准模型。感谢匿名审稿人对论文修改提出的宝贵意见。

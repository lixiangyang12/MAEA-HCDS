# -*- coding: utf-8 -*-
"""
系统论综合学习手册生成器
整合：系统论、控制论、信息论、复杂性科学、前沿应用
"""
import os

output_dir = r"c:\个人资料\申博材料\东北财经大学"

def build_html():
    html = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>系统论完整学习手册 | 系统论·控制论·信息论·复杂性科学</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{
    font-family:'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;
    background:#f5f6fa;color:#2c3e50;line-height:1.8;display:flex;
}
/* ===== 左侧导航 ===== */
.sidebar{
    position:fixed;left:0;top:0;width:260px;height:100vh;
    background:linear-gradient(180deg,#0a0a2a 0%,#1a1a3a 50%,#0a1a2a 100%);
    color:#ccc;overflow-y:auto;z-index:100;padding:20px 0;
    box-shadow:2px 0 20px rgba(0,0,0,0.3);
}
.sidebar h2{
    text-align:center;color:#fff;font-size:1.2em;padding:0 16px 16px;
    border-bottom:1px solid rgba(255,255,255,0.15);margin-bottom:12px;
}
.sidebar h2 small{display:block;font-size:0.7em;opacity:0.6;margin-top:4px}
.sidebar a{
    display:block;padding:8px 20px;color:#aaa;text-decoration:none;
    font-size:0.85em;transition:all 0.2s;border-left:3px solid transparent;
}
.sidebar a:hover,.sidebar a.active{
    color:#fff;background:rgba(255,255,255,0.08);border-left-color:#ffd54f;
}
.sidebar .ch-title{
    color:#ffd54f;font-weight:bold;font-size:0.9em;padding:16px 20px 6px;
    margin-top:8px;border-top:1px solid rgba(255,255,255,0.1);
}
.sidebar .ch-title:first-of-type{margin-top:0;border-top:none}
/* ===== 主内容区 ===== */
.main{margin-left:260px;flex:1;min-height:100vh}
/* ===== 封面 ===== */
.cover{
    background:linear-gradient(135deg,#0a0a1a 0%,#1a2a4a 50%,#0a1a2a 100%);
    color:#fff;text-align:center;padding:80px 40px;position:relative;overflow:hidden;
}
.cover::before{
    content:'';position:absolute;top:-50%;left:-50%;width:200%;height:200%;
    background:radial-gradient(circle,rgba(255,255,255,0.03) 1px,transparent 1px);
    background-size:30px 30px;animation:drift 20s linear infinite;
}
@keyframes drift{0%{transform:translate(0,0)}100%{transform:translate(30px,30px)}}
.cover h1{font-size:3em;position:relative;z-index:1;margin-bottom:10px}
.cover .subtitle{font-size:1.3em;opacity:0.8;position:relative;z-index:1}
.cover .tagline{
    margin-top:30px;font-size:1.1em;color:#ffd54f;position:relative;z-index:1;
    max-width:700px;margin-left:auto;margin-right:auto;
}
.cover .meta{
    margin-top:40px;font-size:0.9em;opacity:0.5;position:relative;z-index:1;
}
/* ===== 章节样式 ===== */
.chapter{
    max-width:960px;margin:0 auto;padding:40px 30px;
}
.chapter-header{
    text-align:center;margin-bottom:40px;padding:30px;
    background:#fff;border-radius:16px;box-shadow:0 5px 20px rgba(0,0,0,0.06);
    border-top:5px solid #1a3a5a;
}
.chapter-header h2{font-size:2em;color:#1a3a5a;margin-bottom:8px}
.chapter-header .ch-num{
    display:inline-block;background:#1a3a5a;color:#fff;padding:4px 16px;
    border-radius:20px;font-size:0.8em;margin-bottom:12px;
}
.chapter-header .ch-core{
    color:#e17055;font-size:1.05em;margin-top:10px;
}
.chapter-header .formula-hero{
    background:#1a2a3a;color:#7ec8e3;padding:16px;border-radius:10px;
    margin-top:16px;font-size:1.1em;font-family:'Courier New',monospace;
}
/* ===== 知识卡片 ===== */
.knowledge-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:20px;margin-bottom:24px}
.k-card{
    background:#fff;border-radius:14px;padding:24px;box-shadow:0 5px 20px rgba(0,0,0,0.06);
    transition:all 0.3s;position:relative;overflow:hidden;
}
.k-card:hover{transform:translateY(-3px);box-shadow:0 12px 35px rgba(0,0,0,0.1)}
.k-card::before{content:'';position:absolute;top:0;left:0;width:100%;height:4px}
.k-card.theory::before{background:linear-gradient(90deg,#0984e3,#74b9ff)}
.k-card.control::before{background:linear-gradient(90deg,#6c5ce7,#a29bfe)}
.k-card.info::before{background:linear-gradient(90deg,#00b894,#55efc4)}
.k-card.complex::before{background:linear-gradient(90deg,#e17055,#fab1a0)}
.k-card.frontier::before{background:linear-gradient(90deg,#fdcb6e,#ffeaa7)}
.k-card h3{font-size:1.15em;color:#1a3a5a;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.k-card h3 .icon{
    width:28px;height:28px;border-radius:50%;display:inline-flex;align-items:center;
    justify-content:center;color:#fff;font-size:0.8em;font-weight:bold;flex-shrink:0;
}
.k-card ul{list-style:none;padding:0}
.k-card ul li{padding:5px 0;padding-left:16px;position:relative;font-size:0.92em}
.k-card ul li::before{content:'▸';position:absolute;left:0;color:#0984e3;font-size:0.8em}
/* ===== 特殊样式 ===== */
.highlight-box{
    background:linear-gradient(135deg,#f0f6fc,#e8f0f8);border-left:5px solid #0984e3;
    padding:16px 20px;border-radius:0 12px 12px 0;margin:16px 0;
}
.highlight-box.purple{border-left-color:#6c5ce7;background:linear-gradient(135deg,#f4f0fe,#ebe4f8)}
.highlight-box.green{border-left-color:#00b894;background:linear-gradient(135deg,#f0faf6,#e4f4ec)}
.highlight-box.red{border-left-color:#e17055;background:linear-gradient(135deg,#fef7f5,#fce8e4)}
.highlight-box strong{display:block;margin-bottom:4px;color:#1a3a5a}
.highlight-box p{color:#3a4a5a;font-size:0.92em}
.formula{
    background:#1a2a3a;color:#7ec8e3;padding:18px;border-radius:10px;margin:14px 0;
    text-align:center;font-size:1em;font-family:'Courier New',monospace;line-height:1.8;
}
.formula em{color:#ffd54f;font-style:normal}
.formula .big{font-size:1.15em}
.comparison-table{
    width:100%;border-collapse:collapse;margin:14px 0;background:#fff;
    border-radius:10px;overflow:hidden;box-shadow:0 3px 12px rgba(0,0,0,0.06);
}
.comparison-table th{
    background:#1a2a3a;color:#fff;padding:10px 12px;text-align:left;font-size:0.85em;
}
.comparison-table td{padding:10px 12px;border-bottom:1px solid #eee;font-size:0.88em}
.comparison-table tr:hover{background:#f8f9fa}
.comparison-table tr:last-child td{border-bottom:none}
.memory-card{
    background:linear-gradient(135deg,#fffde7,#fff8e1);border:2px solid #ffc107;
    padding:16px;border-radius:10px;margin:14px 0;
}
.memory-card h4{color:#f57f17;margin-bottom:6px;font-size:0.95em}
.memory-card p{color:#5a4a0a;font-size:0.92em}
.warning-card{
    background:linear-gradient(135deg,#fff5f5,#ffe0e0);border:2px solid #e74c3c;
    padding:16px;border-radius:10px;margin:14px 0;
}
.warning-card h4{color:#c0392b;margin-bottom:6px}
.warning-card p{color:#5a1a1a;font-size:0.92em}
.insight-card{
    background:linear-gradient(135deg,#e8f5e9,#c8e6c9);border:2px solid #4caf50;
    padding:16px;border-radius:10px;margin:14px 0;
}
.insight-card h4{color:#2e7d32;margin-bottom:6px}
.insight-card p{color:#1b5e20;font-size:0.92em}
/* ===== 流程图 ===== */
.flow-row{display:flex;justify-content:center;align-items:center;gap:10px;margin:12px 0;flex-wrap:wrap}
.flow-node{
    padding:10px 16px;border-radius:8px;font-weight:bold;font-size:0.85em;text-align:center;
}
.flow-node.blue{background:#f0f6fc;border:2px solid #0984e3;color:#0984e3}
.flow-node.purple{background:#f4f0fe;border:2px solid #6c5ce7;color:#6c5ce7}
.flow-node.green{background:#f0faf6;border:2px solid #00b894;color:#00b894}
.flow-node.red{background:#fef7f5;border:2px solid #e17055;color:#e17055}
.flow-node.gold{background:#fffde7;border:2px solid #f57f17;color:#f57f17}
.flow-arrow{font-size:1.4em;font-weight:bold;color:#888}
/* ===== 知识地图 ===== */
.knowledge-map{
    background:#fff;border-radius:14px;padding:24px;box-shadow:0 5px 20px rgba(0,0,0,0.06);
    margin-bottom:24px;text-align:center;
}
.knowledge-map h3{color:#1a3a5a;margin-bottom:16px;font-size:1.1em}
/* ===== 终极总结 ===== */
.final-summary{
    background:linear-gradient(135deg,#0a0a2a 0%,#1a2a4a 50%,#0a1a2a 100%);
    color:#e0e0e0;padding:50px 30px;text-align:center;margin-top:40px;
}
.final-summary h2{font-size:2em;color:#ffd54f;margin-bottom:20px}
.final-summary .final-formula{
    background:rgba(255,255,255,0.06);padding:24px;border-radius:14px;
    margin:20px auto;max-width:800px;font-size:1.1em;line-height:2.2;
}
.final-summary .final-credo{
    margin-top:24px;font-size:1em;opacity:0.8;max-width:700px;margin-left:auto;margin-right:auto;
}
/* ===== 响应式 ===== */
@media(max-width:768px){
    .sidebar{display:none}
    .main{margin-left:0}
    .knowledge-grid{grid-template-columns:1fr}
    .cover h1{font-size:1.8em}
    .chapter{padding:20px 15px}
}
/* ===== 打印 ===== */
@media print{
    .sidebar{display:none}
    .main{margin-left:0}
    .k-card{break-inside:avoid;box-shadow:none;border:1px solid #ddd}
    .chapter{page-break-before:always}
    body{font-size:11pt}
}
</style>
</head>
<body>

<!-- ==================== 侧边栏导航 ==================== -->
<nav class="sidebar">
    <h2>系统论完整学习手册<small>System Theory · Cybernetics · Information Theory · Complexity Science</small></h2>
    <a href="#cover" class="active">📖 封面</a>
    <div class="ch-title">第一章 · 系统论基础</div>
    <a href="#ch1">1.1 历史与哲学基础</a>
    <a href="#ch1-p2">1.2 本体论与核心概念</a>
    <a href="#ch1-p3">1.3 动力学与演化机制</a>
    <a href="#ch1-p4">1.4 信息、控制与通信</a>
    <a href="#ch1-p5">1.5 方法论与建模工具</a>
    <a href="#ch1-p6">1.6 应用领域与前沿</a>
    <div class="ch-title">第二章 · 梅多斯系统论</div>
    <a href="#ch2">2.1 系统基础结构</a>
    <a href="#ch2-p2">2.2 动力学机制</a>
    <a href="#ch2-p3">2.3 系统陷阱与基模</a>
    <a href="#ch2-p4">2.4 杠杆点12级</a>
    <a href="#ch2-p5">2.5 系统智慧</a>
    <div class="ch-title">第三章 · 控制论</div>
    <a href="#ch3">3.1 哲学与历史</a>
    <a href="#ch3-p2">3.2 核心基石</a>
    <a href="#ch3-p3">3.3 数学与工程基础</a>
    <a href="#ch3-p4">3.4 演化与分支</a>
    <a href="#ch3-p5">3.5 深远应用</a>
    <a href="#ch3-p6">3.6 局限与反思</a>
    <div class="ch-title">信息论专题</div>
    <a href="#info">信息论完整学习</a>
    <a href="#link">反馈与信息联动</a>
    <div class="ch-title">第四章 · 复杂性科学</div>
    <a href="#ch4">4.1 哲学基础</a>
    <a href="#ch4-p2">4.2 四大核心特征</a>
    <a href="#ch4-p3">4.3 三大演进脉络</a>
    <a href="#ch4-p4">4.4 混沌边缘与智慧</a>
    <a href="#ch4-p5">4.5 数字时代前沿</a>
    <div class="ch-title">第五章 · 前沿应用</div>
    <a href="#ch5">AI大模型与全球经济</a>
    <a href="#final">终极总结</a>
</nav>

<!-- ==================== 主内容区 ==================== -->
<div class="main">

<!-- ===== 封面 ===== -->
<section class="cover" id="cover">
    <h1>系统论完整学习手册</h1>
    <p class="subtitle">系统论 · 控制论 · 信息论 · 复杂性科学 · 前沿应用</p>
    <p class="tagline">从"还原论"到"系统论"，从"控制者"到"系统园丁"——<br>一门关于"整体、关系、涌现与演化"的完整科学</p>
    <p class="meta">共5章 · 26个学习模块 · 适用于博士入学考试与学术研究</p>
</section>

<!-- ================================================================ -->
<!-- 第一章：系统论基础 -->
<!-- ================================================================ -->
<section class="chapter" id="ch1">
<div class="chapter-header">
    <span class="ch-num">第一章</span>
    <h2>系统论基础</h2>
    <p class="ch-core">核心问题：为什么需要系统论？什么是系统？</p>
    <div class="formula-hero">系统论 = 历史(为什么) + 本体(是什么) + 动力(如何变) + 通信(如何对话) + 方法(如何研究) + 应用(有什么用)</div>
</div>

<div class="knowledge-grid">
<div class="k-card theory">
    <h3><span class="icon" style="background:#0984e3">1</span>1.1 历史背景与哲学基础</h3>
    <ul>
        <li><strong>还原论三支柱</strong>：笛卡尔（分解）→ 牛顿（可预测）→ 拉普拉斯（全知全能）</li>
        <li><strong>还原论的破产</strong>：钟表拆了能装，生态系统拆了就死——复杂系统的整体 > 部分之和</li>
        <li><strong>系统思想萌芽</strong>：亚里士多德"整体不同于部分之和"、黑格尔辩证法、格式塔心理学</li>
        <li><strong>贝塔朗菲贡献</strong>：从"机体系统论"到"一般系统论"，1968年里程碑著作</li>
    </ul>
    <div class="highlight-box">
        <strong>核心洞见</strong>
        <p>还原论说"整体=部分之和"，系统论说"整体>部分之和"——涌现是还原论无法解释的</p>
    </div>
</div>

<div class="k-card theory">
    <h3><span class="icon" style="background:#0984e3">2</span>1.2 本体论与核心概念</h3>
    <ul>
        <li><strong>系统定义</strong>：系统 = 要素(What) + 关系(How) + 结构(Pattern) + 边界(Where) + 功能(Why) + 环境(Context)</li>
        <li><strong>开放/封闭/孤立系统</strong>：开放=与外界交换；封闭=只交换能量；孤立=完全隔绝</li>
        <li><strong>核心属性</strong>：整体性（涌现·非加和）、层次性（上向/下向因果）、关联性（结构决定功能·反馈回路）</li>
        <li><strong>边界与环境</strong>：边界渗透性与选择性、环境约束与供给</li>
    </ul>
    <div class="highlight-box">
        <strong>核心隐喻</strong>
        <p>石墨 vs 金刚石：同一种碳原子，结构不同→功能完全不同——结构决定功能</p>
    </div>
</div>

<div class="k-card theory">
    <h3><span class="icon" style="background:#0984e3">3</span>1.3 动力学与演化机制</h3>
    <ul>
        <li><strong>稳态</strong>：不是静止，而是动态调节——负反馈维持稳定</li>
        <li><strong>自组织</strong>：没有中央指令，局部相互作用产生全局秩序；四个条件：远离平衡、开放、非线性、正反馈</li>
        <li><strong>耗散结构</strong>（普利高津）：远离平衡态+涨落→有序结构；贝纳德对流实验</li>
        <li><strong>协同论</strong>（哈肯）：序参量→伺服原理→快慢变量</li>
        <li><strong>适应性循环</strong>：r→K→Ω→α 四阶段，对应你的DLM生命周期</li>
    </ul>
    <div class="formula">系统活力 = <em>负反馈稳基</em> + <em>正反馈创新</em> + <em>耗散结构突破</em> + <em>协同序参量引领</em> + <em>适应性学习进化</em></div>
</div>

<div class="k-card theory">
    <h3><span class="icon" style="background:#0984e3">4</span>1.4 信息、控制与通信</h3>
    <ul>
        <li><strong>控制论基础</strong>（维纳）：反馈闭环、目的性=反馈机制、黑箱/白箱/灰箱方法</li>
        <li><strong>信息论视角</strong>（香农）：信息=消除不确定性=负熵、比特、信道容量/噪声/冗余</li>
        <li><strong>网络与拓扑</strong>：小世界网络（六度分隔）、无标度网络（富者愈富+Hub脆弱性）</li>
        <li><strong>1948年铁三角</strong>：维纳《控制论》+ 香农《通信的数学理论》+ 贝塔朗菲（一般系统论）</li>
    </ul>
    <div class="formula">系统对话 = <em>控制论</em>(反馈闭环) × <em>信息论</em>(负熵) × <em>网络科学</em>(拓扑) × <em>语义语用</em>(理解)</div>
</div>

<div class="k-card theory">
    <h3><span class="icon" style="background:#0984e3">5</span>1.5 方法论与建模工具</h3>
    <ul>
        <li><strong>软系统方法论</strong>（SSM）：处理人类活动系统中的模糊性与价值观（CATWOE分析）</li>
        <li><strong>硬系统方法论</strong>（HSM）：工程导向、目标明确的问题求解</li>
        <li><strong>因果回路图（CLD）</strong>：定性分析反馈回路 → <strong>存量流量图（SFD）</strong>：定量分析</li>
        <li><strong>系统动力学仿真（SD）</strong>：模拟长期行为 → <strong>多主体建模（ABM）</strong>：异质Agent微观→宏观涌现</li>
        <li><strong>同构性与同态性</strong>：不同领域间的数学映射</li>
    </ul>
    <div class="highlight-box">
        <strong>五个研究 × 方法匹配</strong>
        <p>DLM→SD仿真 | 人机信任→ABM | 混合代理→SSM | 液态组织→网络分析 | 智预算PRO→HSM+ABM</p>
    </div>
</div>

<div class="k-card theory">
    <h3><span class="icon" style="background:#0984e3">6</span>1.6 应用领域与当代发展</h3>
    <ul>
        <li><strong>社会与经济</strong>：组织管理、供应链（牛鞭效应）、宏观经济、城市系统（布雷斯悖论）</li>
        <li><strong>生态与环境</strong>：生态系统服务、气候变化临界点、行星边界（已跨越6个）</li>
        <li><strong>技术与AI</strong>：控制论社会、复杂自适应系统（CAS）、群体智能</li>
        <li><strong>前沿挑战</strong>：复杂性统一场论、意识=涌现（IIT）、伦理责任四原则</li>
    </ul>
    <div class="warning-card">
        <h4>伦理警告</h4>
        <p>当系统不可预测时，谁负责？——责任透明度机制 = 你的研究核心</p>
    </div>
</div>
</div>
</section>

<!-- ================================================================ -->
<!-- 第二章：梅多斯系统论 -->
<!-- ================================================================ -->
<section class="chapter" id="ch2">
<div class="chapter-header">
    <span class="ch-num">第二章</span>
    <h2>梅多斯系统论</h2>
    <p class="ch-core">核心问题：系统如何运转？如何改变系统？</p>
    <div class="formula-hero">系统智慧 = 懂结构 + 懂动力 + 识陷阱 + 知杠杆 + 有姿态</div>
</div>

<div class="knowledge-grid">
<div class="k-card theory">
    <h3><span class="icon" style="background:#0984e3">1</span>2.1 系统基础结构（解剖学）</h3>
    <ul>
        <li><strong>要素（Elements）</strong>：最易识别、最易替换、最不重要——换人不改公司</li>
        <li><strong>连接（Interconnections）</strong>：四类（物理流/信息流/制度/关系），信息流最重要</li>
        <li><strong>功能/目标（Purpose）</strong>：最隐蔽但最核心——真实目标看行为不看宣言</li>
    </ul>
    <div class="formula">系统 = <em>要素</em>(零件) + <em>连接</em>(关系) + <em>目标</em>(意义)<br>干预杠杆：<em>改变目标 > 改变连接 > 改变要素</em></div>
</div>

<div class="k-card theory">
    <h3><span class="icon" style="background:#0984e3">2</span>2.2 动力学机制</h3>
    <ul>
        <li><strong>存量与流量</strong>：存量=浴缸里的水，流量=进水/出水——人类擅长理解存量，不擅长理解流量</li>
        <li><strong>负反馈</strong>：系统的"恒温器"——偏差→反向调整→稳态</li>
        <li><strong>正反馈</strong>：系统的"放大器"——偏差→同向放大→指数增长或崩溃</li>
        <li><strong>时间延迟</strong>：导致震荡和超调的罪魁祸首——洗澡调水温忽冷忽热</li>
    </ul>
    <div class="formula">系统行为 = <em>存量流量</em>(骨架) + <em>反馈回路</em>(肌肉) + <em>时间延迟</em>(神经)</div>
</div>

<div class="k-card theory">
    <h3><span class="icon" style="background:#0984e3">3</span>2.3 系统陷阱与基模</h3>
    <ul>
        <li><strong>政策阻力</strong>：多方负反馈拉锯→放弃对抗，找共赢目标</li>
        <li><strong>公地悲剧</strong>：收益归己、成本分摊→建立规则/私有化/教育</li>
        <li><strong>目标侵蚀</strong>：降低标准代替解决问题→设定绝对标准、红线</li>
        <li><strong>竞争升级</strong>：威胁驱动正反馈→单方收手/外部调节</li>
        <li><strong>转嫁负担</strong>：止痛药替代根治→治标治本两手抓 <em>← 你的核心基模！</em></li>
    </ul>
    <div class="warning-card">
        <h4>转嫁负担 = 你的核心基模</h4>
        <p>"用AI替代人类决策"=经典转嫁负担陷阱。你的人机共生=破解方案——同时使用AI（止痛药）和建立人类能力（免疫力）</p>
    </div>
</div>

<div class="k-card theory">
    <h3><span class="icon" style="background:#0984e3">4</span>2.4 杠杆点：12级阶梯</h3>
    <ul>
        <li><strong>低效力 #12-9</strong>：参数→缓冲→物理结构→延迟（我们花80%时间的地方）</li>
        <li><strong>中等效力 #8-5</strong>：负反馈强度→正反馈增益→<em>信息流结构★</em>→系统规则</li>
        <li><strong>高效力 #4-2</strong>：自组织能力→系统目标→<em>社会范式</em></li>
        <li><strong>终极杠杆 #1</strong>：<em>超越范式</em>——保持开放与谦卑</li>
    </ul>
    <div class="insight-card">
        <h4>你的研究在杠杆阶梯的位置</h4>
        <p>DLM→#4自组织 | 人机信任→#6信息流 | 混合代理→#5规则 | 液态组织→#4+#2 | 智预算PRO→#3目标<br>——你不是在"调参数"，你是在改变<strong>规则、目标和范式</strong>！</p>
    </div>
</div>

<div class="k-card theory">
    <h3><span class="icon" style="background:#0984e3">5</span>2.5 系统智慧：与系统共舞</h3>
    <ul>
        <li><strong>不要试图控制</strong>：复杂系统不可预测、不可控制——只能"共舞"</li>
        <li><strong>保持谦卑</strong>：做系统的学习者而非主宰者</li>
        <li><strong>扩展时间视野</strong>：一天看波动，一年看周期，十年看趋势，百年看范式</li>
        <li><strong>关注整体</strong>：不要为优化局部而牺牲整体健康</li>
    </ul>
    <div class="highlight-box">
        <strong>梅多斯留给你的最后一句话</strong>
        <p>"系统论不会给你一个'答案'。它会给你一双新的眼睛——让你看到之前看不到的连接、反馈、延迟和涌现。然后，你要自己决定如何与这个更完整的世界共舞。"</p>
    </div>
</div>
</div>
</section>

<!-- ================================================================ -->
<!-- 第三章：控制论 -->
<!-- ================================================================ -->
<section class="chapter" id="ch3">
<div class="chapter-header">
    <span class="ch-num">第三章</span>
    <h2>控制论</h2>
    <p class="ch-core">核心问题：动物和机器为什么可以在同一门学科里研究？</p>
    <div class="formula-hero">控制论 = 哲学基础 + 核心基石(反馈+信息+目的性) + 数学工具 + 三阶演化 + 四大应用 + 三大局限</div>
</div>

<div class="knowledge-grid">
<div class="k-card control">
    <h3><span class="icon" style="background:#6c5ce7">1</span>3.1 哲学与历史背景</h3>
    <ul>
        <li><strong>维纳的洞见</strong>：生物和机器的底层逻辑都是"基于反馈的通信与控制"——kybernetes=舵手</li>
        <li><strong>打破对立</strong>：机械论说"生命是机器"，活力论说"生命有灵魂"——维纳说"底层都是反馈回路"</li>
        <li><strong>跨学科融合</strong>：数学+工程+生物+神经+心理+社会→梅西会议（1946-1953）</li>
    </ul>
    <div class="formula">控制论 = <em>反馈</em>(感知→比较→调整) × <em>通信</em>(信息传递) × <em>控制</em>(目标导向) = 生物与机器的统一语言</div>
</div>

<div class="k-card control">
    <h3><span class="icon" style="background:#6c5ce7">2</span>3.2 核心基石：反馈、信息、目的性</h3>
    <ul>
        <li><strong>负反馈</strong>：偏差→反向调整→稳态（恒温器、人体体温、免疫系统）</li>
        <li><strong>正反馈</strong>：偏差→同向放大→演化或崩溃（复利、病毒传播、军备竞赛）</li>
        <li><strong>信息</strong>：第三种基本存在——不是物质，不是能量，不守恒（可复制）</li>
        <li><strong>目的性</strong>：机器没有灵魂，但通过反馈表现出"目的性行为"——导弹追踪目标</li>
    </ul>
    <div class="formula">控制 = <em>信息</em>(感知偏差) → <em>反馈</em>(计算调整) → <em>目的性</em>(逼近目标) → 循环往复</div>
</div>

<div class="k-card control">
    <h3><span class="icon" style="background:#6c5ce7">3</span>3.3 数学与工程基础</h3>
    <ul>
        <li><strong>香农信息论</strong>：比特、熵 H=-Σp·log₂(p)、通信模型（信源→编码→信道→解码→信宿）</li>
        <li><strong>维纳滤波</strong>：从噪声中提取信号；卡尔曼滤波：预测→测量→更新</li>
        <li><strong>贝尔曼最优控制</strong>：V(s)=max[R+γ·V(s')]——动态规划→强化学习→AlphaGo</li>
        <li><strong>阿什比黑箱</strong>：f(输入)=输出，不打开箱子只看行为</li>
    </ul>
    <div class="highlight-box purple">
        <strong>1948年铁三角</strong>
        <p>维纳《控制论》+ 香农《通信的数学理论》+ 贝塔朗菲（一般系统论）= 系统科学三大基石</p>
    </div>
</div>

<div class="k-card control">
    <h3><span class="icon" style="background:#6c5ce7">4</span>3.4 三阶演化</h3>
    <ul>
        <li><strong>一阶控制论（1940s）</strong>：观察者在系统之外→控制客观系统（工程控制、自动导航）</li>
        <li><strong>二阶控制论（1970s）</strong>：观察者在系统之内→自指、认知、建构主义（冯·福斯特）</li>
        <li><strong>三阶控制论（2000s）</strong>：多个观察者之间的互动→社会规范、伦理反思（卢曼）</li>
    </ul>
    <div class="insight-card">
        <h4>你的研究的三阶定位</h4>
        <p>一阶（技术优化）+ 二阶（认知建构）+ 三阶（伦理治理）= 完整的人机共生系统理论<br>大多数AI研究只在一阶，你的研究同时站在三个阶上——这就是你的理论原创性。</p>
    </div>
</div>

<div class="k-card control">
    <h3><span class="icon" style="background:#6c5ce7">5</span>3.5 深远应用</h3>
    <ul>
        <li><strong>AI</strong>：神经网络=多层反馈、反向传播=误差反馈、强化学习=奖励反馈、RLHF=人类偏好反馈</li>
        <li><strong>生物学</strong>：大脑=信息处理系统、自创生（马图拉纳&瓦雷拉）</li>
        <li><strong>管理学</strong>：MBO=控制论回路、宏观调控=负反馈、PDCA=控制论实现</li>
        <li><strong>生态</strong>：盖亚假说=地球是超级恒温器、行星边界9→6已跨越</li>
    </ul>
    <div class="formula">AI·生物·管理·生态 = 全都是"反馈回路"在不同领域的不同实现</div>
</div>

<div class="k-card control">
    <h3><span class="icon" style="background:#6c5ce7">6</span>3.6 局限与反思</h3>
    <ul>
        <li><strong>过度简化</strong>：将情感、文化还原为"信息流"→忽视了意义建构和价值判断</li>
        <li><strong>控制的傲慢</strong>：用算法控制复杂社会→算法偏见、金融风险、社交成瘾</li>
        <li><strong>伦理困境</strong>：机器有自我学习能力→谁来为机器"目的"负责？→维纳"人在回路"</li>
    </ul>
    <div class="warning-card">
        <h4>维纳的三大警告（1950年）</h4>
        <p>1. 别把人当机器管 | 2. 别让机器做价值判断 | 3. 永远保留人在回路</p>
    </div>
</div>
</div>
</section>

<!-- ================================================================ -->
<!-- 信息论专题 -->
<!-- ================================================================ -->
<section class="chapter" id="info">
<div class="chapter-header">
    <span class="ch-num">信息论专题</span>
    <h2>信息论完整学习</h2>
    <p class="ch-core">核心问题：信息到底是什么？</p>
    <div class="formula-hero">信息 = 消除不确定性 = 负熵 = 第三种基本存在（不是物质，不是能量，不守恒）</div>
</div>

<div class="knowledge-grid">
<div class="k-card info">
    <h3><span class="icon" style="background:#00b894">I</span>信息论核心概念</h3>
    <ul>
        <li><strong>信息的本质</strong>：香农剥离"意义"——信息不是"有意义的内容"，而是"消除不确定性"</li>
        <li><strong>比特</strong>：一个二元决策的信息量；H=-ΣP(x)·log₂P(x)；公平硬币=1 bit，作弊硬币=0 bit</li>
        <li><strong>通信模型</strong>：信源→编码→信道→解码→信宿（全程伴随噪声Noise）</li>
        <li><strong>信道容量</strong>：通信管道传递信息的上限；冗余：为了对抗噪声必须加入"废话"</li>
        <li><strong>信息=负熵</strong>：薛定谔"生命以负熵为生"→维纳"信息=负熵"→对抗混乱的武器</li>
    </ul>
    <div class="formula">信息量 = -log₂(概率) → 越出乎意料，信息量越大<br>"太阳东升"≈0 bit | "太阳西升"→爆炸性信息量</div>
</div>

<div class="k-card info">
    <h3><span class="icon" style="background:#00b894">F</span>反馈与信息联动</h3>
    <ul>
        <li><strong>核心关系</strong>：信息=反馈的"内容"（血液），反馈=信息的"路径"（血管），目标=驱动的"动力"（心脏）</li>
        <li><strong>企业案例</strong>：市场信息→偏差信号→负反馈纠错/正反馈增长→大企业病=信息反馈回路断裂</li>
        <li><strong>AI案例</strong>：数据=信息输入→误差=负反馈信息→反向传播调整参数→强化学习奖惩</li>
        <li><strong>终极联动</strong>：感知环境（获取信息）→比较目标（产生偏差）→执行反馈（纠错/放大）→改变状态</li>
    </ul>
    <div class="formula"><em>没有信息→反馈盲目</em> | <em>没有反馈→信息死数据</em> | <em>没有目标→系统无方向</em></div>
</div>
</div>
</section>

<!-- ================================================================ -->
<!-- 第四章：复杂性科学 -->
<!-- ================================================================ -->
<section class="chapter" id="ch4">
<div class="chapter-header">
    <span class="ch-num">第四章</span>
    <h2>复杂性科学</h2>
    <p class="ch-core">核心问题：复杂系统为什么不可预测？</p>
    <div class="formula-hero">复杂性科学 = 哲学基础(超越还原论) + 四大特征(涌现·非线性·自组织·临界点) + 三大脉络 + 混沌边缘 + 数字时代</div>
</div>

<div class="knowledge-grid">
<div class="k-card complex">
    <h3><span class="icon" style="background:#e17055">1</span>4.1 哲学基础：超越还原论</h3>
    <ul>
        <li><strong>还原论破产</strong>：钟表拆了能装，生态系统拆了就死——复杂系统整体>部分之和</li>
        <li><strong>学科互涉</strong>：SFI圣塔菲研究所（1984）——寻找不同领域的共同复杂性规律</li>
        <li><strong>决定论→不可逆</strong>：蝴蝶效应（不可预测）、熵增定律（不可逆）、量子力学（本质随机）</li>
        <li><strong>普利高津</strong>：时间是创造性的，不可逆是真实世界的特征</li>
    </ul>
    <div class="formula">三大范式：<em>还原论</em>（拆开看零件）→ <em>系统论</em>（看整体关系）→ <em>复杂性科学</em>（看演化与涌现）</div>
</div>

<div class="k-card complex">
    <h3><span class="icon" style="background:#e17055">2</span>4.2 四大核心特征</h3>
    <ul>
        <li><strong>涌现</strong>：大量个体局部相互作用→宏观新特性（蚁群、大脑、市场）——"更多就是不同"</li>
        <li><strong>非线性</strong>：输入输出不成比例，蝴蝶效应（f(a+b)≠f(a)+f(b)）</li>
        <li><strong>自组织</strong>：没有中央指令，局部互动产生秩序（沙丘、白蚁丘、大脑）</li>
        <li><strong>临界点</strong>：越过阈值→不可逆的相变（湖泊富营养化：负反馈→逼近临界点→正反馈接管）</li>
    </ul>
    <div class="formula">复杂系统 = <em>涌现</em>(灵魂) + <em>非线性</em>(行为) + <em>自组织</em>(机制) + <em>临界点</em>(转折)</div>
</div>

<div class="k-card complex">
    <h3><span class="icon" style="background:#e17055">3</span>4.3 三大演进脉络</h3>
    <ul>
        <li><strong>莫兰（哲学）</strong>："来自噪声的有序"——无序=创造力的来源；三原则：对话·递归·全息</li>
        <li><strong>普利高津（物理）</strong>：耗散结构——远离平衡态+涨落+正反馈=有序；1977年诺贝尔奖</li>
        <li><strong>圣塔菲（计算）</strong>：CAS——个体有适应性，三大演化要素：基本规则·被冻结的偶然·适应性选择</li>
    </ul>
    <div class="formula">三条脉络：<em>莫兰</em>(认识论) → <em>普利高津</em>(机制论) → <em>SFI</em>(方法论) → <em>你的研究</em>(应用论)</div>
</div>

<div class="k-card complex">
    <h3><span class="icon" style="background:#e17055">4</span>4.4 混沌边缘与系统智慧</h3>
    <ul>
        <li><strong>混沌边缘</strong>：晶体（僵化）↔液态水（混沌边缘·生命）↔气体（混乱）——最大计算力·适应性·创造性</li>
        <li><strong>放弃优化，转向理解</strong>：五个放弃五个拥抱——预测→感知，最优→适应，控制→引导，指令→规则，确定性→可能性</li>
        <li><strong>从"控制者"到"共舞者"</strong>：传统科学=控制者态度，复杂性科学=共舞者态度</li>
    </ul>
    <div class="insight-card">
        <h4>混沌边缘 = 液态组织的理论基石</h4>
        <p>传统组织=层级晶体（太僵化），无政府状态=气体（太混乱），液态组织=液态水（混沌边缘）——既有结构又有流动性</p>
    </div>
</div>

<div class="k-card complex">
    <h3><span class="icon" style="background:#e17055">5</span>4.5 数字时代的复杂性科学</h3>
    <ul>
        <li><strong>解决已知复杂</strong>：AI学习替代穷举——AlphaFold2预测2亿+蛋白质结构（组合爆炸→模式识别）</li>
        <li><strong>揭示未知关系</strong>：AI关联发现替代人类假设——新药研发、GNoME材料发现</li>
        <li><strong>洞察颗粒化</strong>：AI个体化替代平均化——"平均值"暴政→个性化医疗·精准推送·实时校正</li>
    </ul>
    <div class="formula">数字时代 = <em>AI解决已知</em>(学习) + <em>AI揭示未知</em>(关联) + <em>AI洞察颗粒</em>(个体) = 复杂性科学从"哲学"走向"工程"</div>
</div>
</div>
</section>

<!-- ================================================================ -->
<!-- 第五章：前沿应用 -->
<!-- ================================================================ -->
<section class="chapter" id="ch5">
<div class="chapter-header">
    <span class="ch-num">第五章</span>
    <h2>前沿应用：AI大模型与全球经济的复杂系统视角</h2>
    <p class="ch-core">核心问题：当我们用复杂性科学审视AI和全球经济，会发现什么？</p>
    <div class="formula-hero">AI大模型(硅基涌现) + 全球经济(非均衡系统) → 人机共生(三层涌现) → 系统园丁(终极态度)</div>
</div>

<div class="knowledge-grid">
<div class="k-card frontier">
    <h3><span class="icon" style="background:#fdcb6e">AI</span>AI大模型：硅基的涌现系统</h3>
    <ul>
        <li><strong>涌现与相变</strong>：参数规模越过临界点→推理/规划/翻译能力突然出现（量变→质变→相变）</li>
        <li><strong>知识输入（KI）涌现</strong>：PB级数据→TB级参数→不是简单规则的涌现，而是"知识压缩的涌现"</li>
        <li><strong>反脆弱性</strong>：模块化+多样性+冗余→构建多样化AI生态，对抗系统性风险</li>
        <li><strong>学术争议</strong>：涌现 vs 测量错觉——你的立场：底层连续，宏观离散=层级跃迁</li>
    </ul>
    <div class="formula">大模型不是"被设计的"，而是<em>"被涌现的"</em>——就像十亿个水分子在0°C突然结成冰</div>
</div>

<div class="k-card frontier">
    <h3><span class="icon" style="background:#fdcb6e">E</span>全球经济：非均衡系统</h3>
    <ul>
        <li><strong>旧范式→新范式</strong>：均衡·负反馈·收敛 → 非均衡·正反馈·发散</li>
        <li><strong>三大正反馈循环</strong>：美债高企·日元弹性·通胀预期——普利高津的"远离平衡态"</li>
        <li><strong>供应链重构</strong>：多中心模块化→健壮但脆弱——耦合震荡传播引发跨区域共振</li>
        <li><strong>自适应</strong>：危机打破旧结构→释放锁定资源→数字化转型+AI+绿色转型=新增长动能</li>
    </ul>
    <div class="formula">全球经济正在经历一次<em>"耗散结构"式的相变</em>——旧均衡被打破，新秩序在涌现</div>
</div>

<div class="k-card frontier">
    <h3><span class="icon" style="background:#fdcb6e">S</span>人机共生：终极推演</h3>
    <ul>
        <li><strong>三层涌现</strong>：能力涌现（1+1>2）→知识涌现（人类↔AI正反馈）→文明涌现（认知结构改变）</li>
        <li><strong>风险</strong>：能力退化（转嫁负担）+ 自主性受损（算法引导）</li>
        <li><strong>破解</strong>：共同演化 + 与AI共舞——不是控制，是共舞</li>
        <li><strong>终极态度</strong>：从"绝对控制者"到"系统园丁"</li>
    </ul>
    <div class="insight-card">
        <h4>系统园丁五信条</h4>
        <p>1. 我不是在"控制"系统，我是在"培育"系统<br>2. 我不是在"消除"不确定性，我是在"拥抱"不确定性<br>3. 我不是在"寻找"最优解，我是在"维持"适应性<br>4. 我不是在"设计"结果，我是在"创造"涌现的条件<br>5. 我不是"主宰者"，我是"共舞者"</p>
    </div>
</div>
</div>
</section>

<!-- ================================================================ -->
<!-- 终极总结 -->
<!-- ================================================================ -->
<section class="final-summary" id="final">
    <h2>系统论学习之旅 · 终极总结</h2>
    <div class="final-formula">
        <strong style="color:#ffd54f;font-size:1.2em">全部系统论学习 = 五章 · 五大支柱</strong><br><br>
        <em style="color:#74b9ff">第一章 系统论基础</em> = 认识系统（为什么需要系统论？什么是系统？）<br>
        <em style="color:#a29bfe">第二章 梅多斯系统论</em> = 理解系统（系统如何运转？如何改变系统？）<br>
        <em style="color:#55efc4">第三章 控制论 + 信息论</em> = 控制与通信（反馈+信息+目的性+三阶演化）<br>
        <em style="color:#fab1a0">第四章 复杂性科学</em> = 拥抱复杂性（涌现+非线性+自组织+临界点+混沌边缘）<br>
        <em style="color:#ffeaa7">第五章 前沿应用</em> = 应用AI与经济（硅基涌现+非均衡系统+人机共生）<br><br>
        <strong style="color:#ffd54f;font-size:1.1em">= 从"控制者"到"系统园丁"的完整转变</strong>
    </div>

    <div class="final-formula" style="margin-top:16px">
        <strong style="color:#ffd54f;font-size:1.1em">你的博士论文"终极叙事"</strong><br><br>
        在AI时代，传统的"控制式管理"已经失效——因为AI和人类共同构成了不可预测的复杂适应系统。<br><br>
        我的研究提出一种新的管理范式：<strong style="color:#ffd54f">"系统园丁"式管理</strong>——<br>
        不是控制人机系统，而是理解人机系统的涌现规律，<br>
        创造涌现的条件，引导人机系统的共同演化。<br><br>
        这一范式建立在<strong style="color:#74b9ff">系统论、控制论、信息论和复杂性科学</strong>的理论基础之上，<br>
        并通过五个相互关联的研究（DLM·人机信任·混合代理·液态组织·智预算PRO）加以实现。
    </div>

    <div class="final-credo" style="margin-top:30px">
        <p style="color:#ffd54f;font-size:1.1em"><strong>核心理论脉络</strong></p>
        <div class="flow-row" style="margin-top:12px">
            <span class="flow-node blue">还原论<br>（拆开看零件）</span>
            <span class="flow-arrow">→</span>
            <span class="flow-node purple">系统论<br>（看整体关系）</span>
            <span class="flow-arrow">→</span>
            <span class="flow-node green">控制论<br>（反馈+信息）</span>
            <span class="flow-arrow">→</span>
            <span class="flow-node red">复杂性科学<br>（涌现+演化）</span>
            <span class="flow-arrow">→</span>
            <span class="flow-node gold">系统园丁<br>（终极态度）</span>
        </div>
    </div>

    <p style="margin-top:24px;opacity:0.6;font-size:0.9em">
        系统论 · 控制论 · 信息论 · 复杂性科学 · 前沿应用<br>
        共5章 · 26个学习模块 · 完整知识体系
    </p>
</section>

</div><!-- .main -->

<script>
// 侧边栏高亮
const sections=document.querySelectorAll('section[id]');
const navLinks=document.querySelectorAll('.sidebar a');
window.addEventListener('scroll',()=>{
    let current='';
    sections.forEach(s=>{
        const top=s.offsetTop-100;
        if(window.scrollY>=top)current=s.getAttribute('id');
    });
    navLinks.forEach(a=>{
        a.classList.remove('active');
        if(a.getAttribute('href')==='#'+current)a.classList.add('active');
    });
});
</script>
</body>
</html>'''
    return html


def main():
    html = build_html()
    html_path = os.path.join(output_dir, "系统论_完整学习手册.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"HTML saved: {html_path}")

    # Try to generate PDF
    pdf_path = os.path.join(output_dir, "系统论_完整学习手册.pdf")
    try:
        from weasyprint import HTML
        HTML(filename=html_path).write_pdf(pdf_path)
        print(f"PDF saved: {pdf_path}")
    except ImportError:
        print("weasyprint not installed, trying alternative...")
        try:
            import pdfkit
            pdfkit.from_file(html_path, pdf_path, options={
                'enable-local-file-access': '',
                'page-size': 'A4',
                'margin-top': '10mm',
                'margin-bottom': '10mm',
                'margin-left': '10mm',
                'margin-right': '10mm',
            })
            print(f"PDF saved via pdfkit: {pdf_path}")
        except ImportError:
            print("Neither weasyprint nor pdfkit available. Please install one:")
            print("  pip install weasyprint")
            print("  or")
            print("  pip install pdfkit")
            print("PDF generation skipped.")


if __name__ == '__main__':
    main()
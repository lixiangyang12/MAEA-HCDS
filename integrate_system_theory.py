# -*- coding: utf-8 -*-
"""系统论学习内容整合脚本：合并所有HTML -> 统一HTML -> PDF"""

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup

BASE_DIR = Path(r"c:\个人资料\申博材料\东北财经大学")

# 定义所有文件的顺序和标签
CHAPTERS = [
    {
        "title": "第一章：系统论的理论基础",
        "parts": [
            ("系统论第一章第一部分.html", "第一部分：历史背景与哲学基础", "为什么需要系统论？"),
            ("系统论第一章第二部分.html", "第二部分：系统的本体论与核心概念", "什么是系统？"),
            ("系统论第一章第三部分.html", "第三部分：系统动力学与演化机制", "系统如何维持和变化？"),
            ("系统论第一章第四部分.html", "第四部分：信息、控制与通信", "系统如何「对话」？"),
            ("系统论第一章第五部分.html", "第五部分：方法论与建模工具", "如何研究和描述系统？"),
            ("系统论第一章第六部分.html", "第六部分：应用领域与当代发展", "系统论有什么用？"),
        ]
    },
    {
        "title": "第二章：梅多斯《系统之美》核心框架",
        "parts": [
            ("系统论第二章第一部分.html", "第一部分：系统的基础结构", "系统由什么构成？"),
            ("系统论第二章第二部分.html", "第二部分：系统如何运转", "系统如何随时间变化？"),
            ("系统论第二章第三部分.html", "第三部分：系统的陷阱与对策", "系统为什么失败？"),
            ("系统论第二章第四部分.html", "第四部分：系统的杠杆点", "哪里下刀最有效？"),
            ("系统论第二章第五部分.html", "第五部分：与系统共舞", "我们该以什么姿态？"),
        ]
    },
]

def extract_main_content(html_path):
    """从HTML文件中提取主要内容区域"""
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    # 提取所有card-section
    sections = soup.find_all('div', class_='card-section')
    if not sections:
        return ""
    
    # 提取所有knowledge-card
    cards = []
    for section in sections:
        section_cards = section.find_all('div', class_='knowledge-card')
        for card in section_cards:
            cards.append(str(card))
    
    return "\n".join(cards)


def build_unified_html():
    """构建统一的HTML文件"""
    
    # 收集所有内容
    all_content = []
    toc_items = []
    global_counter = 1
    
    for ch_idx, chapter in enumerate(CHAPTERS):
        ch_num = ch_idx + 1
        toc_items.append(f'<li class="toc-chapter"><a href="#ch{ch_num}">{chapter["title"]}</a><ul>')
        
        for part_idx, (filename, part_title, core_q) in enumerate(chapter["parts"]):
            filepath = BASE_DIR / filename
            if not filepath.exists():
                print(f"警告: {filename} 不存在，跳过")
                continue
            
            print(f"处理: {filename}")
            content = extract_main_content(filepath)
            
            part_num = part_idx + 1
            section_id = f"ch{ch_num}p{part_num}"
            toc_items.append(f'<li class="toc-part"><a href="#{section_id}">{part_title}</a></li>')
            
            all_content.append(f"""
            <section id="{section_id}" class="chapter-section">
                <div class="section-header">
                    <span class="section-badge">第{ch_num}章 · 第{part_num}部分</span>
                    <h2>{part_title}</h2>
                    <p class="core-question">核心问题：{core_q}</p>
                </div>
                <div class="card-grid">{content}</div>
            </section>
            """)
            global_counter += 1
        
        toc_items.append('</ul></li>')
    
    # 构建完整HTML
    html_template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>系统论 · 完整学习手册</title>
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{
            font-family:'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;
            background:#f5f5f5;color:#333;line-height:1.6;
        }}
        
        /* 目录侧边栏 */
        .sidebar{{
            position:fixed;top:0;left:0;width:280px;height:100vh;
            background:linear-gradient(180deg,#1a1a2e 0%,#16213e 100%);
            color:#e0e0e0;overflow-y:auto;z-index:100;
            padding:20px 0;box-shadow:2px 0 20px rgba(0,0,0,0.3);
        }}
        .sidebar h1{{
            font-size:1.3em;text-align:center;padding:0 20px 16px;
            border-bottom:1px solid rgba(255,255,255,0.15);margin-bottom:12px;
            color:#ffd54f;
        }}
        .sidebar .toc{{list-style:none;padding:0}}
        .sidebar .toc-chapter{{
            margin:8px 0;
        }}
        .sidebar .toc-chapter > a{{
            display:block;padding:10px 20px;color:#ffd54f;font-weight:bold;
            font-size:0.95em;text-decoration:none;transition:background 0.2s;
        }}
        .sidebar .toc-chapter > a:hover{{background:rgba(255,255,255,0.08)}}
        .sidebar .toc-chapter ul{{list-style:none;padding:0}}
        .sidebar .toc-part a{{
            display:block;padding:7px 20px 7px 32px;color:#b0b8c0;font-size:0.88em;
            text-decoration:none;transition:all 0.2s;
        }}
        .sidebar .toc-part a:hover{{color:#fff;background:rgba(255,255,255,0.05)}}
        
        /* 主内容区 */
        .main-content{{
            margin-left:280px;padding:30px 40px;max-width:1100px;
        }}
        .page-title{{
            text-align:center;padding:30px 0;margin-bottom:20px;
            border-bottom:3px solid #1a1a2e;
        }}
        .page-title h1{{font-size:2.2em;color:#1a1a2e;margin-bottom:8px}}
        .page-title p{{font-size:1.1em;color:#666}}
        
        .chapter-section{{
            margin-bottom:30px;padding:20px;
            background:#fff;border-radius:12px;
            box-shadow:0 4px 15px rgba(0,0,0,0.08);
        }}
        .section-header{{
            text-align:center;padding:16px;margin-bottom:20px;
            border-bottom:2px dashed #e0e0e0;
        }}
        .section-badge{{
            display:inline-block;padding:4px 14px;background:#1a1a2e;
            color:#ffd54f;border-radius:15px;font-size:0.85em;margin-bottom:10px;
        }}
        .section-header h2{{font-size:1.5em;color:#1a1a2e;margin:8px 0}}
        .core-question{{
            color:#666;font-style:italic;font-size:0.95em;
            padding:8px 16px;background:#f8f8f8;border-radius:8px;
            display:inline-block;
        }}
        
        /* 卡片网格 */
        .card-grid{{
            display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));
            gap:18px;
        }}
        
        /* 知识卡片样式 */
        .knowledge-card{{
            background:#fff;border-radius:12px;padding:22px;
            box-shadow:0 3px 12px rgba(0,0,0,0.06);
            border:1px solid #e8e8e8;transition:all 0.3s;
            position:relative;overflow:hidden;
        }}
        .knowledge-card::before{{
            content:'';position:absolute;top:0;left:0;width:100%;height:4px;
            background:linear-gradient(90deg,#1a1a2e,#3a3a6e);
        }}
        .knowledge-card:hover{{
            transform:translateY(-3px);box-shadow:0 8px 25px rgba(0,0,0,0.12);
        }}
        .card-title{{
            font-size:1.15em;font-weight:bold;color:#1a1a2e;margin-bottom:12px;
            display:flex;align-items:center;gap:8px;
        }}
        .card-icon{{
            width:30px;height:30px;background:linear-gradient(135deg,#1a1a2e,#3a3a6e);
            border-radius:50%;display:flex;align-items:center;justify-content:center;
            color:#fff;font-size:0.8em;font-weight:bold;flex-shrink:0;
        }}
        .card-content{{color:#444;font-size:0.93em;line-height:1.7}}
        
        /* 通用样式 */
        .key-point,.key-point2,.key-point3,.key-point4,.key-point5{{
            padding:10px 14px;margin:8px 0;border-radius:0 8px 8px 0;font-size:0.9em;
        }}
        .key-point{{background:#f0f4ff;border-left:4px solid #1a1a2e}}
        .key-point2{{background:#fef9f2;border-left:4px solid #f39c12}}
        .key-point3{{background:#fef5f4;border-left:4px solid #e74c3c}}
        .key-point4{{background:#f8f2fc;border-left:4px solid #8e44ad}}
        .key-point5{{background:#f0faf6;border-left:4px solid #00b894}}
        
        .highlight{{background:linear-gradient(120deg,#d5e8fc,#d5e8fc);padding:2px 5px;border-radius:3px;font-weight:600}}
        .highlight2{{background:linear-gradient(120deg,#fef0d0,#fef0d0);padding:2px 5px;border-radius:3px;font-weight:600}}
        .highlight3{{background:linear-gradient(120deg,#fdd8d5,#fdd8d5);padding:2px 5px;border-radius:3px;font-weight:600}}
        .highlight4{{background:linear-gradient(120deg,#e8d8f5,#e8d8f5);padding:2px 5px;border-radius:3px;font-weight:600}}
        .highlight5{{background:linear-gradient(120deg,#c8f0d8,#c8f0d8);padding:2px 5px;border-radius:3px;font-weight:600}}
        
        .formula-box,.formula-box2{{
            padding:14px;border-radius:10px;margin:10px 0;text-align:center;
            font-family:'Courier New',monospace;font-size:0.95em;
        }}
        .formula-box{{background:#1a1a2e;color:#a0c0f0}}
        .formula-box2{{background:#2a1a1a;color:#f0a0a0}}
        
        .score-tips{{
            padding:12px;border-radius:10px;margin-top:10px;font-size:0.88em;
        }}
        .score-tips h4{{margin-bottom:6px;font-size:0.92em}}
        .score-tips ul{{padding-left:18px}}
        .score-tips li{{margin:3px 0}}
        
        .framework-box{{
            border:2px dashed #b0b8bc;padding:16px;border-radius:10px;margin:10px 0;text-align:center;
        }}
        .framework-box h4{{margin-bottom:8px}}
        
        .memory-trick{{
            padding:12px;border-radius:10px;margin:10px 0;font-size:0.9em;
            background:linear-gradient(135deg,#f0f4ff,#e0e8f8);
        }}
        .memory-trick h4{{margin-bottom:5px}}
        
        .wisdom-box{{
            border:2px solid #52b788;padding:18px;border-radius:12px;margin:10px 0;
            background:linear-gradient(135deg,#f5fdf8,#e8f8f0);
        }}
        .wisdom-box h4{{text-align:center;margin-bottom:8px}}
        
        .quote-box{{
            background:#f8f8f8;border-left:4px solid #ffd54f;padding:12px 16px;
            margin:8px 0;border-radius:0 8px 8px 0;font-style:italic;color:#555;font-size:0.9em;
        }}
        
        .trap-box{{
            background:linear-gradient(135deg,#fff5f5,#ffe0e0);border:2px solid #e17055;
            padding:14px;border-radius:10px;margin:8px 0;
        }}
        .trap-box h4{{text-align:center;margin-bottom:6px;color:#a03020}}
        .trap-cause{{color:#6d1a10;font-size:0.88em}}
        
        .cure-box{{
            background:linear-gradient(135deg,#f0fdf6,#d0f8e0);border:2px solid #00b894;
            padding:14px;border-radius:10px;margin:8px 0;
        }}
        .cure-box h4{{text-align:center;margin-bottom:6px;color:#0d4a2a}}
        .cure-solution{{color:#1a5a3a;font-size:0.88em}}
        
        .lever-badge{{
            display:inline-block;padding:3px 10px;border-radius:12px;font-size:0.8em;font-weight:bold;color:#fff;margin-left:6px;
        }}
        .lever-badge.low{{background:#95a5a6}}
        .lever-badge.mid{{background:#f39c12}}
        .lever-badge.high{{background:#e74c3c}}
        .lever-badge.ultra{{background:#8e44ad}}
        
        .level-bar{{
            display:flex;align-items:center;margin:8px 0;gap:8px;
        }}
        .level-label{{width:80px;font-size:0.8em;color:#555;text-align:right}}
        .level-track{{flex:1;height:8px;background:#e0e0e0;border-radius:4px;overflow:hidden}}
        .level-fill{{height:100%;border-radius:4px}}
        .level-fill.low{{background:linear-gradient(90deg,#95a5a6,#bdc3c7);width:10%}}
        .level-fill.mid{{background:linear-gradient(90deg,#f39c12,#e67e22);width:45%}}
        .level-fill.high{{background:linear-gradient(90deg,#e74c3c,#c0392b);width:80%}}
        .level-fill.ultra{{background:linear-gradient(90deg,#8e44ad,#6c3483);width:100%}}
        
        .comparison-table{{
            width:100%;border-collapse:collapse;margin:10px 0;background:#fff;
            border-radius:8px;overflow:hidden;box-shadow:0 3px 10px rgba(0,0,0,0.06);
            font-size:0.88em;
        }}
        .comparison-table th{{
            background:#1a1a2e;color:#fff;padding:10px;text-align:left;font-size:0.88em;
        }}
        .comparison-table td{{padding:9px;border-bottom:1px solid #e0e0e0}}
        .comparison-table tr:hover{{background:#f8f9fa}}
        
        .step-flow{{
            display:flex;justify-content:center;align-items:center;margin:12px 0;flex-wrap:wrap;gap:8px;
        }}
        .step,.step2,.step3,.step4,.step5{{
            background:#fff;padding:6px 12px;border-radius:20px;border:2px solid #1a1a2e;
            color:#1a1a2e;font-weight:600;font-size:0.83em;
        }}
        .step2{{border-color:#00cec9;color:#00cec9}}
        .step3{{border-color:#fdcb6e;color:#b8860b}}
        .step4{{border-color:#e17055;color:#e17055}}
        .step5{{border-color:#00b894;color:#00b894}}
        .arrow,.arrow2{{color:#1a1a2e;font-size:1.2em;font-weight:bold}}
        
        .bathtub-diagram{{
            background:#f0f4ff;padding:16px;border-radius:10px;margin:10px 0;text-align:center;
        }}
        .bathtub-diagram .tub{{
            display:inline-block;width:200px;height:80px;border:3px solid #1a1a2e;
            border-radius:0 0 30px 30px;position:relative;
            background:linear-gradient(to top,rgba(26,26,46,0.15),rgba(26,26,46,0.03));
        }}
        .bathtub-diagram .tub-label{{
            position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-weight:bold;color:#1a1a2e;
        }}
        .bathtub-diagram .inflow{{color:#1a1a2e;font-weight:bold;margin-bottom:4px}}
        .bathtub-diagram .outflow{{color:#d63031;font-weight:bold;margin-top:4px}}
        
        /* 打印样式 */
        @media print{{
            .sidebar{{display:none}}
            .main-content{{margin-left:0;padding:0}}
            .chapter-section{{break-inside:avoid;box-shadow:none;border:1px solid #ddd}}
            body{{background:#fff}}
        }}
        
        @media(max-width:768px){{
            .sidebar{{display:none}}
            .main-content{{margin-left:0;padding:15px}}
            .card-grid{{grid-template-columns:1fr}}
            .step-flow{{flex-direction:column}}
        }}
    </style>
</head>
<body>

<!-- 侧边栏导航 -->
<nav class="sidebar">
    <h1>系统论 · 完整学习手册</h1>
    <ul class="toc">
        {''.join(toc_items)}
    </ul>
</nav>

<!-- 主内容 -->
<div class="main-content">
    <div class="page-title">
        <h1>系统论 · 完整学习手册</h1>
        <p>第一章：系统论的理论基础 &nbsp;|&nbsp; 第二章：梅多斯《系统之美》核心框架</p>
        <p style="opacity:0.7;font-size:0.9em;margin-top:8px">共11个部分 · 涵盖系统论从理论到实践的全部核心内容</p>
    </div>

    {''.join(all_content)}

    <div style="text-align:center;padding:40px 0;color:#999;font-size:0.9em">
        <p>系统论 · 完整学习手册</p>
        <p>第一章：系统论的理论基础（6部分） | 第二章：梅多斯《系统之美》核心框架（5部分）</p>
    </div>
</div>

</body>
</html>'''
    
    return html_template


def main():
    print("=" * 60)
    print("系统论学习内容整合工具")
    print("=" * 60)
    
    # 1. 构建统一HTML
    print("\n[1/3] 正在合并所有HTML文件...")
    unified_html = build_unified_html()
    
    html_output = BASE_DIR / "系统论_完整学习手册.html"
    with open(html_output, 'w', encoding='utf-8') as f:
        f.write(unified_html)
    print(f"  [OK] HTML已生成: {html_output}")
    print(f"    文件大小: {html_output.stat().st_size / 1024:.1f} KB")
    
    # 2. 转换为PDF
    print("\n[2/3] 正在转换为PDF...")
    pdf_output = BASE_DIR / "系统论_完整学习手册.pdf"
    
    try:
        from weasyprint import HTML
        HTML(filename=str(html_output)).write_pdf(str(pdf_output))
        print(f"  [OK] PDF已生成: {pdf_output}")
        print(f"    文件大小: {pdf_output.stat().st_size / 1024:.1f} KB")
    except Exception as e:
        print(f"  [FAIL] weasyprint转换失败: {e}")
        print("  尝试使用pdfkit...")
        try:
            import pdfkit
            pdfkit.from_file(str(html_output), str(pdf_output))
            print(f"  [OK] PDF已生成(pdfkit): {pdf_output}")
        except Exception as e2:
            print(f"  [FAIL] pdfkit也失败了: {e2}")
            print("  请手动用浏览器打开HTML文件，然后Ctrl+P打印为PDF")
    
    print("\n[3/3] 完成!")
    print(f"  HTML: {html_output}")
    print(f"  PDF:  {pdf_output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
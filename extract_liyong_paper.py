"""
提取李勇教授论文PDF的"2.经典订货决策"章节文本
用于参考其章节框架和分析逻辑
"""
import fitz  # PyMuPDF

pdf_path = r'c:\个人资料\申博材料\企业运营与科研管理数据库\缓解牛鞭效应的新途径：人机协同的智慧决策机器人-李勇.pdf'

doc = fitz.open(pdf_path)
print(f"总页数: {len(doc)}")
print("=" * 80)

# 先输出目录/前2页，定位"经典订货决策"章节
full_text = ""
for i, page in enumerate(doc):
    text = page.get_text()
    full_text += f"\n===== PAGE {i+1} =====\n{text}"

# 搜索"经典订货决策"位置
import re
matches = list(re.finditer(r'经典订货决策|经典订货|2\.\s*经典|2\s*经典订货', full_text))
print(f"\n找到 '经典订货决策' 相关关键词位置: {len(matches)} 处")
for m in matches:
    start = max(0, m.start() - 50)
    end = min(len(full_text), m.end() + 100)
    print(f"  位置{m.start()}: ...{full_text[start:end]}...")

# 输出前3页内容（目录+引言）
print("\n" + "=" * 80)
print("前3页内容：")
print("=" * 80)
for i in range(min(3, len(doc))):
    print(f"\n----- PAGE {i+1} -----")
    print(doc[i].get_text())

doc.close()

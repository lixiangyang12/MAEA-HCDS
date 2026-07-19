"""
提取李勇论文第3-7页内容（2.3牛鞭效应 + 3.人机协同章节 + 实验部分）
"""
import fitz

pdf_path = r'c:\个人资料\申博材料\企业运营与科研管理数据库\缓解牛鞭效应的新途径：人机协同的智慧决策机器人-李勇.pdf'
doc = fitz.open(pdf_path)

# 输出第3-7页
for i in range(2, min(8, len(doc))):
    print(f"\n{'='*80}")
    print(f"===== PAGE {i+1} =====")
    print(f"{'='*80}")
    print(doc[i].get_text())

doc.close()

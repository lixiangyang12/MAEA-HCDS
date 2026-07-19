"""
PDF文本提取脚本
提取PDF文本内容，分页保存
"""
import pdfplumber
import json
import os

pdf_path = r"c:\个人资料\申博材料\企业运营与科研管理数据库\Adaptive Inventory Strategies using Deep Reinforcement Learning for Dynamic Agri-Food Supply Chains.pdf"
output_dir = r"c:\个人资料\申博材料\企业运营与科研管理数据库"

# 提取文本
pages_data = []

with pdfplumber.open(pdf_path) as pdf:
    total_pages = len(pdf.pages)
    print(f"总页数: {total_pages}")

    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        tables = page.extract_tables() or []

        page_info = {
            "page_num": i + 1,
            "text": text,
            "tables_count": len(tables),
            "tables": tables
        }
        pages_data.append(page_info)
        print(f"第 {i+1} 页: 文本长度 {len(text)}, 表格数 {len(tables)}")

# 保存为JSON
output_json = os.path.join(output_dir, "pdf_extracted_content.json")
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(pages_data, f, ensure_ascii=False, indent=2)

print(f"\n提取完成，保存至: {output_json}")
print(f"总页数: {len(pages_data)}")

# 打印前2页文本预览
print("\n" + "="*60)
print("前2页文本预览:")
print("="*60)
for page in pages_data[:2]:
    print(f"\n--- 第 {page['page_num']} 页 ---")
    print(page['text'][:2000])
    print(f"\n[表格数: {page['tables_count']}]")

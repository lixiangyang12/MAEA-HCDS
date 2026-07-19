# -*- coding: utf-8 -*-
"""Generate PDF from HTML using Playwright"""
import os
from playwright.sync_api import sync_playwright

html_path = r"c:\个人资料\申博材料\东北财经大学\系统论_完整学习手册.html"
pdf_path = r"c:\个人资料\申博材料\东北财经大学\系统论_完整学习手册.pdf"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f"file:///{html_path.replace(chr(92), '/')}", wait_until="networkidle")
    page.pdf(path=pdf_path, format="A4", print_background=True, margin={
        "top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"
    })
    browser.close()
    print(f"PDF saved: {pdf_path}")
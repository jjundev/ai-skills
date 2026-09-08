#!/usr/bin/env python3
"""
Exam Worksheet & Answer Key PDF Generator
- Input: JSON file containing exam title, metadata, and list of questions with Korean chunked translations.
- Output: Single-page A4 Question Sheet PDF and Answer Key PDF.
- Design: 1-column minimal black & white layout, default gothic font, 2-line handwriting blanks, vertical justification.
"""

import sys
import os
import json
import argparse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors

def setup_font():
    font_candidates = [
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/NanumGothic.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf"
    ]
    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("DefaultGothic", font_path))
                return "DefaultGothic"
            except Exception:
                continue
    return "Helvetica"

def wrap_text(c, text, font_name, font_size, max_width):
    words = text.split(' ')
    lines, current_line = [], []
    for word in words:
        test_line = ' '.join(current_line + [word])
        w = c.stringWidth(test_line, font_name, font_size)
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    if current_line:
        lines.append(' '.join(current_line))
    return lines

def generate_pdfs(data, out_test_path, out_ans_path):
    font_name = setup_font()
    title = data.get("title", "영어 해석 시험")
    questions = data.get("questions", [])
    
    page_w, page_h = A4 # 595.27 x 841.89 pt
    margin_left = 38
    margin_right = 38
    margin_top = 34
    margin_bottom = 28
    header_bottom_gap = 26.0
    content_w = page_w - margin_left - margin_right
    
    def render_doc(filename, is_answer):
        c = canvas.Canvas(filename, pagesize=A4)
        
        # 1. Header (Minimalist B&W)
        c.saveState()
        curr_y = page_h - margin_top
        c.setFont(font_name, 14.0)
        c.setFillColor(colors.black)
        
        doc_title = title + (" [정답지]" if is_answer else "")
        c.drawString(margin_left, curr_y, doc_title)
        
        c.setFont(font_name, 9.5)
        if is_answer:
            c.drawRightString(page_w - margin_right, curr_y, "※ 끊어 읽기(/) 직독직해 모범 정답")
        else:
            c.drawRightString(page_w - margin_right, curr_y, f"이름: _________________    점수: ______ / {len(questions)}")
            
        curr_y -= 8
        c.setStrokeColor(colors.black)
        c.setLineWidth(1.0)
        c.line(margin_left, curr_y, page_w - margin_right, curr_y)
        c.restoreState()
        
        content_top = curr_y - header_bottom_gap
        content_bottom = margin_bottom
        available_h = content_top - content_bottom
        
        # 2. Layout & Vertical Justification
        font_en = 9.4
        line_h_en = 12.8
        
        if is_answer:
            font_ko = 9.0
            line_h_ko = 12.8
            items_data = []
            total_items_h = 0.0
            
            for item in questions:
                full_en = f'{item["num"]}  "{item["en"]}"'
                en_lines = wrap_text(c, full_en, font_name, font_en, content_w)
                
                full_ko = f'해석:  {item["ko_chunks"]}'
                ko_lines = wrap_text(c, full_ko, font_name, font_ko, content_w)
                
                item_h = len(en_lines) * line_h_en + 2.0 + len(ko_lines) * line_h_ko + 3.0
                items_data.append((en_lines, ko_lines, item_h))
                total_items_h += item_h
                
            gap = (available_h - total_items_h) / max(1, len(questions) - 1)
            
            render_y = content_top
            for idx, (en_lines, ko_lines, item_h) in enumerate(items_data):
                c.saveState()
                c.setFont(font_name, font_en)
                c.setFillColor(colors.black)
                for el in en_lines:
                    c.drawString(margin_left, render_y, el)
                    render_y -= line_h_en
                render_y -= 2.0
                
                c.setFont(font_name, font_ko)
                for kl in ko_lines:
                    c.drawString(margin_left, render_y, kl)
                    render_y -= line_h_ko
                render_y -= 3.0
                
                if idx < len(questions) - 1:
                    sep_y = render_y - (gap / 2.0)
                    c.setStrokeColor(colors.HexColor("#E5E5E5"))
                    c.setLineWidth(0.4)
                    c.line(margin_left, sep_y, page_w - margin_right, sep_y)
                    render_y -= gap
                c.restoreState()
        else:
            blank_line_gap = 18.5
            items_data = []
            total_items_h = 0.0
            
            for item in questions:
                full_en = f'{item["num"]}  "{item["en"]}"'
                en_lines = wrap_text(c, full_en, font_name, font_en, content_w)
                item_h = len(en_lines) * line_h_en + 2.0 + blank_line_gap + 7.0
                items_data.append((en_lines, item_h))
                total_items_h += item_h
                
            gap = (available_h - total_items_h) / max(1, len(questions) - 1)
            
            render_y = content_top
            for idx, (en_lines, item_h) in enumerate(items_data):
                c.saveState()
                c.setFont(font_name, font_en)
                c.setFillColor(colors.black)
                for el in en_lines:
                    c.drawString(margin_left, render_y, el)
                    render_y -= line_h_en
                render_y -= 2.0
                
                c.setFont(font_name, 8.8)
                c.drawString(margin_left, render_y, "해석:")
                label_w = c.stringWidth("해석:", font_name, 8.8) + 4
                
                c.setStrokeColor(colors.HexColor("#777777"))
                c.setLineWidth(0.5)
                # Line 1
                c.line(margin_left + label_w, render_y - 2, page_w - margin_right, render_y - 2)
                render_y -= blank_line_gap
                # Line 2
                c.line(margin_left, render_y - 2, page_w - margin_right, render_y - 2)
                render_y -= 5.0
                
                if idx < len(questions) - 1:
                    sep_y = render_y - (gap / 2.0)
                    c.setStrokeColor(colors.HexColor("#E5E5E5"))
                    c.setLineWidth(0.4)
                    c.line(margin_left, sep_y, page_w - margin_right, sep_y)
                    render_y -= gap
                c.restoreState()
                
        c.showPage()
        c.save()
        
    render_doc(out_test_path, is_answer=False)
    render_doc(out_ans_path, is_answer=True)
    print(f"Generated test: {out_test_path}")
    print(f"Generated answer: {out_ans_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate Translation Test & Answer PDF")
    parser.add_argument("input_json", help="Path to input JSON specification file")
    parser.add_argument("--test-out", default="test_sheet.pdf", help="Output path for test sheet PDF")
    parser.add_argument("--ans-out", default="answer_sheet.pdf", help="Output path for answer sheet PDF")
    args = parser.parse_args()
    
    with open(args.input_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    generate_pdfs(data, args.test_out, args.ans_out)

if __name__ == "__main__":
    main()

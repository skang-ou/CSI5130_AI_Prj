#!/usr/bin/env python3
"""Build the English final-report PDF from its editable Markdown source.

Requires requirements-report.txt. No model calls or scoring changes occur.
The small Markdown subset supports this report's headings, tables, links,
figures, code blocks, and explicit page breaks.
"""
import argparse
import hashlib
import json
import re
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether

ROOT = Path(__file__).resolve().parents[1]
WIDTH = 512


def inline(text):
    text = escape(text)
    text = re.sub(r'`([^`]+)`', r'<font name="Courier" size="8.3">\1</font>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'<link href="\2" color="#174f73"><u>\1</u></link>', text)
    return text


def styles():
    normal = ParagraphStyle('Body', fontName='Times-Roman', fontSize=10.5, leading=14,
                            textColor=colors.black, spaceAfter=8, splitLongWords=True,
                            allowWidows=0, allowOrphans=0)
    return dict(body=normal,
                title=ParagraphStyle('Title', parent=normal, fontName='Times-Bold', fontSize=21,
                                     leading=24, spaceBefore=2, spaceAfter=15, keepWithNext=True),
                h2=ParagraphStyle('Heading', parent=normal, fontName='Times-Bold', fontSize=13,
                                  leading=16, spaceBefore=8, spaceAfter=8, keepWithNext=True),
                h3=ParagraphStyle('Subheading', parent=normal, fontName='Times-Bold', fontSize=11,
                                  leading=14, spaceBefore=7, spaceAfter=6, keepWithNext=True),
                caption=ParagraphStyle('Caption', parent=normal, fontName='Times-Italic', fontSize=9,
                                       leading=11.5, spaceAfter=9, alignment=TA_LEFT),
                cell=ParagraphStyle('Cell', parent=normal, fontSize=9.3, leading=11.6, spaceAfter=0),
                code=ParagraphStyle('Code', parent=normal, fontName='Courier', fontSize=8.2,
                                    leading=11, spaceAfter=0),
                reference=ParagraphStyle('Reference', parent=normal, fontSize=9.4, leading=12,
                                         spaceAfter=7))


def column_widths(header):
    if header[0] == 'Difficulty': return [70, 40, 402]
    if header[0] == 'Criterion': return [145, 367]
    if header[0].startswith('Comparison'): return [210, 92, 70, 70, 70]
    if len(header) == 4: return [98, 60, 190, 164]
    return [92, 420]


def make_table(raw_rows, ss):
    rows = [[Paragraph(inline(cell), ss['cell']) for cell in row] for row in raw_rows]
    table = Table(rows, colWidths=column_widths(raw_rows[0]), repeatRows=1, hAlign='LEFT')
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8edf0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d9d9d9')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    # Numeric columns receive centered paragraph alignment, while narratives stay left aligned.
    for row_index, row in enumerate(raw_rows):
        for col_index, value in enumerate(row):
            if re.fullmatch(r'[+\-]?\d+(?:\.\d+)?', value):
                rows[row_index][col_index].style = ParagraphStyle(
                    'Numeric', parent=ss['cell'], alignment=TA_CENTER)
    return table


def build_flowables(source, ss):
    lines = source.read_text(encoding='utf-8').splitlines()
    story = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1; continue
        if line == '<!-- pagebreak -->':
            story.append(PageBreak()); index += 1; continue
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            story.append(Paragraph(inline(line[level:].strip()), ss[{1: 'title', 2: 'h2', 3: 'h3'}[level]]))
            index += 1; continue
        if line.startswith('```'):
            code = []
            index += 1
            while index < len(lines) and not lines[index].startswith('```'):
                code.append(Paragraph(escape(lines[index]).replace(' ', '&#160;'), ss['code']))
                index += 1
            story += [KeepTogether(code), Spacer(1, 8)]
            index += 1; continue
        figure = re.fullmatch(r'!\[(.*?)\]\((.*?)\)', line)
        if figure:
            image_path = (source.parent / figure[2]).resolve()
            width, height = ImageReader(str(image_path)).getSize()
            target_width = 480
            image = Image(str(image_path), width=target_width, height=target_width * height / width)
            image.hAlign = 'CENTER'
            story.append(KeepTogether([image, Paragraph(inline(figure[1]), ss['caption'])]))
            index += 1; continue
        if line.startswith('|'):
            raw = []
            while index < len(lines) and lines[index].strip().startswith('|'):
                row = [cell.strip() for cell in lines[index].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', cell) for cell in row): raw.append(row)
                index += 1
            story += [make_table(raw, ss), Spacer(1, 10)]
            continue
        paragraph = [line]
        index += 1
        while index < len(lines) and lines[index].strip() and not lines[index].lstrip().startswith(('#', '|', '```', '![', '<!--')):
            paragraph.append(lines[index].strip()); index += 1
        text = ' '.join(paragraph)
        story.append(Paragraph(inline(text), ss['reference'] if re.match(r'^\[\d+\]', text) else ss['body']))
    return story


def footer(canvas, document):
    canvas.saveState()
    canvas.setFillColor(colors.black)
    canvas.setFont('Helvetica', 8)
    canvas.drawString(50, 767, 'Requirement to Test Case Generation')
    canvas.drawRightString(562, 767, 'CSI-4130/5130')
    canvas.drawString(50, 26, 'Sangkook Kang')
    canvas.drawRightString(562, 26, str(document.page))
    canvas.restoreState()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render-dir', type=Path, help='Optional private directory for rendered page PNGs.')
    args = parser.parse_args()
    source = ROOT / 'report/final_report.md'
    output = ROOT / 'report/final_report.pdf'
    # Check that underlying generation and scoring artifacts still match the analysis.
    analysis = json.loads((ROOT / 'results/analysis/analysis_summary.json').read_text())
    for name, expected in analysis['source_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Analysis provenance mismatch: {name}')
    document = SimpleDocTemplate(str(output), pagesize=(612, 792), leftMargin=50,
                                 rightMargin=50, topMargin=47, bottomMargin=45,
                                 title='LLM Based Requirement to Test Case Generation for Embedded Systems',
                                 author='Sangkook Kang', subject='Artificial Intelligence Course Project')
    document.build(build_flowables(source, styles()), onFirstPage=footer, onLaterPages=footer)
    import pymupdf
    pdf = pymupdf.open(output)
    if args.render_dir:
        args.render_dir.mkdir(parents=True, exist_ok=True)
        for index, page in enumerate(pdf):
            page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(args.render_dir / f'page-{index+1}.png')
    print(f'Built {output}: {len(pdf)} pages.')


if __name__ == '__main__':
    main()

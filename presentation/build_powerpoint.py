#!/usr/bin/env python3
"""Build an editable 16:9 PowerPoint from the saved presentation content.

Uses standard Office Open XML with native tables, charts, embedded chart
workbooks and speaker notes. No API calls or changes to experimental data.
Run with the report dependencies: python presentation/build_powerpoint.py

Decorative background: OpenAI built-in image generation. Prompt: restrained
midnight navy academic slide background with subtle teal circuit traces and
a microcontroller at the far right, clean space on the left, no text or logos.
"""
import hashlib
import io
import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.pdfbase.pdfmetrics import stringWidth

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
C = 'http://schemas.openxmlformats.org/drawingml/2006/chart'
NS = f'xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}"'
WHITE, TEAL, MUTED = 'F2F7FC', '66D4C3', 'A9BECF'
NAVY, HEADER, ROW, ALT = '0A192B', '144658', '10283C', '122D42'
EMU = 12700


def emu(value):
    return str(round(value * EMU))


def slide_notes_text(slide):
    """Format presenter notes independently of the local HTML/PDF builder."""
    preparation = slide.get('preparation')
    if not preparation:
        return slide['notes']
    return '\n\n'.join([
        'BEFORE PRESENTING: BACKGROUND\n' + preparation['background'],
        'EXAMPLE TO HELP YOU UNDERSTAND\n' + preparation['example'],
        'WHAT TO SAY DURING THE PRESENTATION\n' + slide['notes'],
        'IF ASKED: ' + preparation['question'] + '\n' + preparation['answer'],
    ])


def wrap(text, width, size, bold=False):
    font = 'Helvetica-Bold' if bold else 'Helvetica'
    lines = []
    for paragraph in text.split('\n'):
        line = ''
        for word in paragraph.split():
            candidate = (line + ' ' + word).strip()
            if line and stringWidth(candidate, font, size) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


def paragraphs(lines, size, color=WHITE, bold=False):
    return ''.join(
        '<a:p><a:pPr><a:lnSpc><a:spcPct val="110000"/></a:lnSpc>'
        '<a:spcAft><a:spcPts val="0"/></a:spcAft></a:pPr>'
        f'<a:r><a:rPr lang="en-US" sz="{round(size * 100)}" b="{int(bold)}">'
        f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
        '<a:latin typeface="Arial"/><a:ea typeface="Arial"/>'
        f'</a:rPr><a:t>{escape(line)}</a:t></a:r>'
        f'<a:endParaRPr lang="en-US" sz="{round(size * 100)}"/></a:p>'
        for line in lines
    )


def transform(x, y, w, h, tag='a:xfrm'):
    return f'<{tag}><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></{tag}>'


def textbox(ident, name, text, x, y, w, size, color=WHITE, bold=False):
    lines = wrap(text, w, size, bold)
    height = len(lines) * size * 1.1 + 5
    xml = (
        '<p:sp><p:nvSpPr>'
        f'<p:cNvPr id="{ident}" name="{escape(name)}"/>'
        '<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr>{transform(x, y, w, height)}'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
        '<a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>'
        '<p:txBody><a:bodyPr wrap="square" lIns="0" rIns="0" tIns="0" bIns="0" anchor="t">'
        f'<a:noAutofit/></a:bodyPr><a:lstStyle/>{paragraphs(lines, size, color, bold)}</p:txBody></p:sp>'
    )
    return xml, height


def table_layout(block, width, size, slide_number):
    count = len(block['headers'])
    if count == 2:
        ratios = [.55, .45] if slide_number == 11 else [.25, .75]
    elif count == 3:
        ratios = [.20, .65, .15] if slide_number == 8 else [.20, .20, .60] if slide_number == 3 else [.40, .30, .30]
    else:
        ratios = [.37] + [.63 / (count - 1)] * (count - 1)
    widths = [width * ratio for ratio in ratios]
    rows = [block['headers']] + block['rows']
    padding = 12 if slide_number == 14 else 18
    heights = [max(len(wrap(value, widths[j] - 24, size, i == 0)) for j, value in enumerate(row)) * size * 1.1 + padding for i, row in enumerate(rows)]
    return widths, heights


def table(ident, block, x, y, width, size, slide_number):
    widths, heights = table_layout(block, width, size, slide_number)
    rows = []
    for i, values in enumerate([block['headers']] + block['rows']):
        cells = []
        for j, value in enumerate(values):
            fill = HEADER if i == 0 else ROW if i % 2 else ALT
            lines = wrap(value, widths[j] - 24, size, i == 0)
            cells.append(
                '<a:tc><a:txBody><a:bodyPr wrap="square"/><a:lstStyle/>'
                + paragraphs(lines, size, TEAL if i == 0 else WHITE, i == 0)
                + f'</a:txBody><a:tcPr marL="152400" marR="152400" marT="{76200 if slide_number == 14 else 114300}" marB="{76200 if slide_number == 14 else 114300}" anchor="ctr">'
                + f'<a:lnB w="6350"><a:solidFill><a:srgbClr val="23465C"/></a:solidFill></a:lnB>'
                + f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill></a:tcPr></a:tc>'
            )
        rows.append(f'<a:tr h="{emu(heights[i])}">' + ''.join(cells) + '</a:tr>')
    xml = (
        f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{ident}" name="Editable table {ident}"/>'
        '<p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>'
        + transform(x, y, width, sum(heights), 'p:xfrm')
        + '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
        '<a:tbl><a:tblPr firstRow="1" bandRow="0"/><a:tblGrid>'
        + ''.join(f'<a:gridCol w="{emu(w)}"/>' for w in widths)
        + '</a:tblGrid>' + ''.join(rows) + '</a:tbl></a:graphicData></a:graphic></p:graphicFrame>'
    )
    return xml, sum(heights)


def chart_frame(ident, chart_id, x, y, w, h):
    return (
        f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{ident}" name="Editable chart"/>'
        '<p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr>'
        + transform(x, y, w, h, 'p:xfrm')
        + f'<a:graphic><a:graphicData uri="{C}"><c:chart xmlns:c="{C}" r:id="rIdChart{chart_id}"/>'
        '</a:graphicData></a:graphic></p:graphicFrame>'
    )


def relationships(items):
    return '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(
        f'<Relationship Id="{ident}" Type="{R}/{kind}" Target="{target}"/>' for ident, kind, target in items
    ) + '</Relationships>'


def slide_xml(number, slide):
    shapes = []
    ident = 2

    def text(value, x, y, width, size, color=WHITE, bold=False, name='Text'):
        nonlocal ident
        xml, height = textbox(ident, name, value, x, y, width, size, color, bold)
        shapes.append(xml)
        ident += 1
        return height

    if number == 1:
        text('Requirements\nto test cases', 56, 116, 730, 52, WHITE, True, 'Title')
        text(slide['blocks'][0]['text'], 58, 272, 720, 25, TEAL)
        text('Sangkook Kang', 58, 363, 700, 21)
        text('CSI-4130/5130 Artificial Intelligence', 58, 396, 740, 18, MUTED)
        text(slide['blocks'][-1]['text'], 58, 444, 740, 15, MUTED)
    else:
        text(slide['title'], 56, 40, 848, 32, WHITE, True, 'Title')
        if number == 6:
            shapes.append(chart_frame(ident, 1, 48, 135, 505, 290)); ident += 1
            xml, _ = table(ident, slide['blocks'][1], 577, 150, 327, 17, number)
            shapes.append(xml); ident += 1
            text(slide['blocks'][2]['text'], 58, 444, 848, 17, MUTED)
            text(slide['blocks'][3]['text'], 58, 477, 848, 19, TEAL)
        elif number == 9:
            shapes.append(chart_frame(ident, 2, 48, 122, 855, 225)); ident += 1
            y = 363
            for block in slide['blocks'][1:]:
                size = 21 if block['type'] == 'lead' else 16 if block['type'] == 'small' else 18
                color = TEAL if block['type'] == 'accent' else MUTED if block['type'] == 'small' else WHITE
                y += text(block['text'], 58, y, 830, size, color) + 11
        else:
            size, gap = (17, 13) if number in [5, 14] else (18, 16)
            def height(block):
                if block['type'] == 'table':
                    return sum(table_layout(block, 848, size, number)[1])
                pts = 16 if block['type'] == 'small' else 22 if block['type'] == 'lead' else 20
                return len(wrap(block['text'], 848, pts)) * pts * 1.1 + 5
            required = sum(height(block) for block in slide['blocks']) + gap * (len(slide['blocks']) - 1)
            if required > 384:
                size, gap = 17, 10
                required = sum(height(block) for block in slide['blocks']) + gap * (len(slide['blocks']) - 1)
            y = 120 if required <= 384 else 110
            for block in slide['blocks']:
                if block['type'] == 'table':
                    xml, h = table(ident, block, 56, y, 848, size, number)
                    shapes.append(xml); ident += 1
                else:
                    pts = 16 if block['type'] == 'small' else 22 if block['type'] == 'lead' else 20
                    color = TEAL if block['type'] == 'accent' else MUTED if block['type'] == 'small' else WHITE
                    h = text(block['text'], 56, y, 848, pts, color)
                y += h + gap
            if y - gap > 508:
                raise ValueError(f'Slide {number} content extends to {y - gap:.1f} points')
    text(f'{number:02d}', 874, 516, 35, 11, MUTED, name='Slide number')
    bg = '<p:bg><p:bgPr><a:blipFill><a:blip r:embed="rIdBackground"/><a:stretch><a:fillRect/></a:stretch></a:blipFill><a:effectLst/></p:bgPr></p:bg>'
    group = '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
    return f'<p:sld {NS}><p:cSld>{bg}<p:spTree>{group}' + ''.join(shapes) + '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'


def workbook(categories, series):
    out = io.BytesIO()
    main = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr('_rels/.rels', relationships([('rId1', 'officeDocument', 'xl/workbook.xml')]))
        z.writestr('xl/workbook.xml', f'<workbook xmlns="{main}" xmlns:r="{R}"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', relationships([('rId1', 'worksheet', 'worksheets/sheet1.xml')]))
        data = [['Strategy'] + [s[0] for s in series]] + [[cat] + [s[1][i] for s in series] for i, cat in enumerate(categories)]
        rows = []
        for i, row in enumerate(data, 1):
            cells = []
            for j, value in enumerate(row):
                ref = f'{chr(65 + j)}{i}'
                cells.append(f'<c r="{ref}"><v>{value}</v></c>' if isinstance(value, (int, float)) else f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
            rows.append(f'<row r="{i}">' + ''.join(cells) + '</row>')
        z.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{main}"><sheetData>' + ''.join(rows) + '</sheetData></worksheet>')
    return out.getvalue()


def chart_xml(categories, series, stacked=False):
    cache = lambda values, tag: f'<c:{tag}><c:ptCount val="{len(values)}"/>' + ''.join(f'<c:pt idx="{i}"><c:v>{escape(str(value))}</c:v></c:pt>' for i, value in enumerate(values)) + f'</c:{tag}>'
    tx = '<c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr sz="1400"><a:solidFill><a:srgbClr val="A9BECF"/></a:solidFill><a:latin typeface="Arial"/></a:defRPr></a:pPr><a:endParaRPr lang="en-US"/></a:p></c:txPr>'
    items = []
    for i, (name, values, color) in enumerate(series):
        col = chr(66 + i)
        xml = f'<c:ser><c:idx val="{i}"/><c:order val="{i}"/><c:tx><c:strRef><c:f>Sheet1!${col}$1</c:f>{cache([name], "strCache")}</c:strRef></c:tx><c:spPr><a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:ln><a:noFill/></a:ln></c:spPr>'
        if not stacked:
            xml += ''.join(f'<c:dPt><c:idx val="{j}"/><c:spPr><a:solidFill><a:srgbClr val="{c}"/></a:solidFill></c:spPr></c:dPt>' for j, c in enumerate(['609BC0', TEAL, 'E6B96D']))
        xml += '<c:dLbls>'
        for j, value in enumerate(values):
            if value == 0:
                xml += f'<c:dLbl><c:idx val="{j}"/><c:delete val="1"/></c:dLbl>'
        label_tx = tx.replace('A9BECF', NAVY).replace('sz="1400"', 'sz="1400" b="1"')
        xml += f'<c:numFmt formatCode="{"0" if stacked else "0.0000"}" sourceLinked="0"/>{label_tx}<c:dLblPos val="{"ctr" if stacked else "inEnd"}"/><c:showLegendKey val="0"/><c:showVal val="1"/><c:showCatName val="{1 if not stacked or i == 0 else 0}"/><c:showSerName val="0"/><c:separator> </c:separator></c:dLbls>'
        xml += f'<c:cat><c:strRef><c:f>Sheet1!$A$2:$A$4</c:f>{cache(categories, "strCache")}</c:strRef></c:cat><c:val><c:numRef><c:f>Sheet1!${col}$2:${col}$4</c:f>{cache(values, "numCache")}</c:numRef></c:val></c:ser>'
        items.append(xml)
    line = '<c:spPr><a:ln w="6350"><a:solidFill><a:srgbClr val="294457"/></a:solidFill></a:ln></c:spPr>'
    cat = f'<c:catAx><c:axId val="100"/><c:scaling><c:orientation val="{"maxMin" if stacked else "minMax"}"/></c:scaling><c:delete val="0"/><c:axPos val="{"l" if stacked else "b"}"/><c:majorTickMark val="none"/><c:minorTickMark val="none"/><c:tickLblPos val="nextTo"/>{line}{tx}<c:crossAx val="200"/><c:crosses val="autoZero"/><c:auto val="1"/><c:lblAlgn val="ctr"/><c:lblOffset val="100"/></c:catAx>'
    val = f'<c:valAx><c:axId val="200"/><c:scaling><c:orientation val="minMax"/><c:max val="{30 if stacked else 10}"/><c:min val="0"/></c:scaling><c:delete val="0"/><c:axPos val="{"b" if stacked else "l"}"/><c:majorGridlines>{line}</c:majorGridlines><c:numFmt formatCode="0" sourceLinked="0"/><c:majorTickMark val="none"/><c:minorTickMark val="none"/><c:tickLblPos val="nextTo"/>{line}{tx}<c:crossAx val="100"/><c:crosses val="autoZero"/><c:crossBetween val="between"/><c:majorUnit val="{5 if stacked else 2}"/></c:valAx>'
    legend = f'<c:legend><c:legendPos val="r"/><c:layout/><c:overlay val="0"/>{tx}</c:legend>' if stacked else ''
    return f'<c:chartSpace xmlns:c="{C}" xmlns:a="{A}" xmlns:r="{R}"><c:lang val="en-US"/><c:chart><c:autoTitleDeleted val="1"/><c:plotArea><c:layout/><c:barChart><c:barDir val="{"bar" if stacked else "col"}"/><c:grouping val="{"stacked" if stacked else "clustered"}"/><c:varyColors val="{0 if stacked else 1}"/>' + ''.join(items) + f'<c:gapWidth val="90"/><c:overlap val="{100 if stacked else 0}"/><c:axId val="100"/><c:axId val="200"/></c:barChart>{cat}{val}</c:plotArea>{legend}<c:plotVisOnly val="1"/><c:dispBlanksAs val="gap"/></c:chart><c:spPr><a:noFill/><a:ln><a:noFill/></a:ln></c:spPr>{tx}<c:externalData r:id="rIdWorkbook"><c:autoUpdate val="0"/></c:externalData></c:chartSpace>'


def build(output):
    content = json.loads((HERE / 'content.json').read_text())
    summary = json.loads((ROOT / 'results/analysis/analysis_summary.json').read_text())
    for name, expected in summary['source_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Changed experiment source: {name}')
    assert len(content['slides']) == 14
    parts = {}
    overrides = []
    def put(name, data, kind=None):
        parts[name] = data
        if kind:
            overrides.append(f'<Override PartName="/{name}" ContentType="application/vnd.openxmlformats-officedocument.{kind}+xml"/>')
    group = '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
    clr = 'accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" bg1="lt1" bg2="lt2" folHlink="folHlink" hlink="hlink" tx1="dk1" tx2="dk2"'
    theme_colors = [('dk1',NAVY),('lt1',WHITE),('dk2',ROW),('lt2',MUTED),('accent1',TEAL),('accent2','609BC0'),('accent3','E6B96D'),('accent4','E39188'),('accent5','8592C5'),('accent6','599C95'),('hlink',TEAL),('folHlink','8592C5')]
    put('ppt/theme/theme1.xml', f'<a:theme xmlns:a="{A}" name="Circuit study"><a:themeElements><a:clrScheme name="Midnight teal">' + ''.join(f'<a:{n}><a:srgbClr val="{v}"/></a:{n}>' for n,v in theme_colors) + '</a:clrScheme><a:fontScheme name="Arial"><a:majorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme><a:fmtScheme name="Simple"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>', 'theme')
    # DrawingML style lists require three entries even when all shapes use
    # explicit fills and borders. Keep the theme valid in native Office apps.
    from xml.etree import ElementTree as ET
    import copy
    theme = ET.fromstring(parts['ppt/theme/theme1.xml'])
    for name in ['fillStyleLst', 'lnStyleLst', 'effectStyleLst', 'bgFillStyleLst']:
        styles = theme.find('.//{' + A + '}' + name)
        while len(styles) < 3:
            styles.append(copy.deepcopy(styles[0]))
    parts['ppt/theme/theme1.xml'] = ET.tostring(theme, encoding='unicode')
    put('ppt/slideMasters/slideMaster1.xml', f'<p:sldMaster {NS}><p:cSld><p:spTree>{group}</p:spTree></p:cSld><p:clrMap {clr}/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rIdLayout"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>', 'presentationml.slideMaster')
    put('ppt/slideMasters/_rels/slideMaster1.xml.rels', relationships([('rIdTheme','theme','../theme/theme1.xml'),('rIdLayout','slideLayout','../slideLayouts/slideLayout1.xml')]))
    put('ppt/slideLayouts/slideLayout1.xml', f'<p:sldLayout {NS} type="blank" preserve="1"><p:cSld name="Blank"><p:spTree>{group}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>', 'presentationml.slideLayout')
    put('ppt/slideLayouts/_rels/slideLayout1.xml.rels', relationships([('rIdMaster','slideMaster','../slideMasters/slideMaster1.xml')]))
    put('ppt/notesMasters/notesMaster1.xml', f'<p:notesMaster {NS}><p:cSld><p:spTree>{group}</p:spTree></p:cSld><p:clrMap {clr}/><p:notesStyle/></p:notesMaster>', 'presentationml.notesMaster')
    put('ppt/notesMasters/_rels/notesMaster1.xml.rels', relationships([('rIdTheme','theme','../theme/theme1.xml')]))
    ids = ''.join(f'<p:sldId id="{255+i}" r:id="rIdSlide{i}"/>' for i in range(1,15))
    put('ppt/presentation.xml', f'<p:presentation {NS}><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rIdMaster"/></p:sldMasterIdLst><p:notesMasterIdLst><p:notesMasterId r:id="rIdNotesMaster"/></p:notesMasterIdLst><p:sldIdLst>{ids}</p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>', 'presentationml.presentation.main')
    put('ppt/_rels/presentation.xml.rels', relationships([('rIdMaster','slideMaster','slideMasters/slideMaster1.xml'),('rIdNotesMaster','notesMaster','notesMasters/notesMaster1.xml')] + [(f'rIdSlide{i}','slide',f'slides/slide{i}.xml') for i in range(1,15)]))
    for i, slide in enumerate(content['slides'],1):
        put(f'ppt/slides/slide{i}.xml', slide_xml(i, slide), 'presentationml.slide')
        rels = [('rIdLayout','slideLayout','../slideLayouts/slideLayout1.xml'),('rIdBackground','image','../media/circuit-background.png'),('rIdNotes','notesSlide',f'../notesSlides/notesSlide{i}.xml')]
        if i in [6,9]:
            chart_id = 1 if i == 6 else 2
            rels.append((f'rIdChart{chart_id}','chart',f'../charts/chart{chart_id}.xml'))
        put(f'ppt/slides/_rels/slide{i}.xml.rels', relationships(rels))
        notes = slide_notes_text(slide) + '\n\nSuggested time: ' + str(slide['seconds']) + ' s (spoken script only)\n\nSources: ' + ', '.join(slide['sources'])
        notes += '\n\nDecorative circuit background: OpenAI image generation. Experimental figures remain from the saved project results.'
        note_shape = f'<p:sp><p:nvSpPr><p:cNvPr id="2" name="Speaker notes"/><p:cNvSpPr/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>{paragraphs(notes.splitlines(),12,"000000")}</p:txBody></p:sp>'
        put(f'ppt/notesSlides/notesSlide{i}.xml', f'<p:notes {NS}><p:cSld><p:spTree>{group}{note_shape}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>', 'presentationml.notesSlide')
        put(f'ppt/notesSlides/_rels/notesSlide{i}.xml.rels', relationships([('rIdSlide','slide',f'../slides/slide{i}.xml'),('rIdMaster','notesMaster','../notesMasters/notesMaster1.xml')]))
    categories = ['Zero-Shot','Structured','Few-Shot']
    groups = [summary['strategies'][key] for key in ['zero_shot','structured','few_shot']]
    datasets = [ [('Mean total /10',[g['mean_total'] for g in groups],TEAL)], [(name,[g['criterion_counts']['unsupported_behavior'][str(score)] for g in groups],color) for score,name,color in [(2,'None (2)',TEAL),(1,'Minor (1)','E6B96D'),(0,'Material (0)','E39188')]] ]
    for i, series in enumerate(datasets,1):
        put(f'ppt/charts/chart{i}.xml', chart_xml(categories,series,i==2), 'drawingml.chart')
        put(f'ppt/charts/_rels/chart{i}.xml.rels', relationships([('rIdWorkbook','package',f'../embeddings/chart{i}.xlsx')]))
        put(f'ppt/embeddings/chart{i}.xlsx',workbook(categories,series))
    put('ppt/media/circuit-background.png',(HERE/'assets/circuit-background.png').read_bytes())
    put('_rels/.rels',relationships([('rId1','officeDocument','ppt/presentation.xml')]))
    defaults = '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Default Extension="xlsx" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"/>'
    put('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'+defaults+''.join(overrides)+'</Types>')
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in parts.items():
            archive.writestr(name,data)
    print(f'Built {output}: 14 slides, native tables, 2 editable charts, speaker notes.')


if __name__ == '__main__':
    build(HERE/'project_presentation.pptx')

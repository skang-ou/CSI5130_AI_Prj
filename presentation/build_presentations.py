#!/usr/bin/env python3
"""Build browser and PDF final decks from editable content JSON.

Default output is the English kit in the presentation folder.
PDF generation reuses the report dependencies.
No API calls, new semantic ratings, or changes to experimental data occur.
"""
import argparse
import base64
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def paragraph(text, cls='text'):
    return f'<p class="{cls}">{html.escape(text)}</p>'


def body_html(block):
    if block['type'] == 'table':
        return '<table><thead><tr>' + ''.join(f'<th>{html.escape(v)}</th>' for v in block['headers']) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{html.escape(v)}</td>' for v in row) + '</tr>' for row in block['rows']) + '</tbody></table>'
    if block['type'] == 'chart':
        data = base64.b64encode((ROOT / block['path']).read_bytes()).decode()
        return f'<img class="chart" src="data:image/png;base64,{data}" alt="{html.escape(block["path"])}">'
    return paragraph(block['text'], block['type'])


def build_html(content, output):
    ui = content['ui']
    sections = []
    for i, slide in enumerate(content['slides']):
        blocks = slide['blocks']
        if i == 5:
            body = '<div class="split"><div>' + body_html(blocks[0]) + '</div><div class="right">' + ''.join(body_html(b) for b in blocks[1:]) + '</div></div>'
        else:
            body = ''.join(body_html(b) for b in blocks)
        sections.append(f'<section class="slide {"cover" if i == 0 else ""}" aria-label="{i+1}"><h1>{html.escape(slide["title"])}</h1><div class="body">{body}</div><span class="page">{i+1}</span></section>')
    css = '''
*{box-sizing:border-box}body{margin:0;background:#e8ecea;color:#142e38;font-family:Arial,"Apple SD Gothic Neo","Malgun Gothic",sans-serif}main{height:calc(100dvh - 58px);position:relative;overflow:hidden}.stage{width:1280px;height:720px;position:absolute;left:50%;top:50%;transform:translate(-50%,-50%) scale(var(--scale,1));transform-origin:center}.slide{display:none;background:#fff;width:1280px;height:720px;padding:50px 64px 48px;position:relative}.slide.active{display:block}h1{font-size:42px;line-height:1.15;letter-spacing:-.025em;margin:0 0 28px;font-weight:650}.body{display:flex;flex-direction:column;gap:17px;max-height:540px}p{font-size:27px;line-height:1.35;margin:0}.lead{font-size:32px;line-height:1.3}.small{font-size:20px;color:#526b74;line-height:1.35}.accent{font-size:27px;color:#176e68;line-height:1.35}.cover h1{font-size:64px;max-width:1000px;margin:75px 0 38px}.cover .body{gap:22px}.cover .lead{font-size:37px;margin-bottom:20px}table{border-collapse:collapse;width:100%;font-size:23px;line-height:1.35}th{text-align:left;color:#176e68;font-weight:600;padding:10px 16px 12px 0;border-bottom:2px solid #a8bbb9}td{padding:11px 18px 11px 0;border-bottom:1px solid #d8e1de;vertical-align:top}td:first-child,th:first-child{width:25%}.chart{display:block;max-width:100%;height:275px;object-fit:contain;object-position:center}.split{display:grid;grid-template-columns:700px 1fr;gap:30px;align-items:center;min-height:440px}.split .chart{width:700px;height:420px}.right{display:flex;flex-direction:column;gap:24px}.right table{font-size:23px}.right td:first-child{width:42%}.right .accent{font-size:26px}.page{position:absolute;bottom:22px;right:40px;font-size:16px;color:#526b74}nav{height:58px;display:flex;align-items:center;justify-content:center;gap:12px;background:#142e38;color:white;font-size:14px}button{background:transparent;border:1px solid #8da5a5;border-radius:4px;padding:7px 12px;color:inherit;font:inherit;cursor:pointer}button:focus-visible{outline:3px solid #8cceba;outline-offset:2px}button:disabled{opacity:.35;cursor:default}#count{min-width:56px;text-align:center}#notes{display:none;height:30dvh;overflow:auto;background:#fff;padding:16px 8vw;line-height:1.6}#notes p,#notes li{font-size:16px}body.notes main{height:calc(70dvh - 58px)}body.notes #notes{display:block}#help{font-size:12px;opacity:.8;margin-left:8px}html[lang="ko"] h1,html[lang="ko"] p,html[lang="ko"] td{word-break:keep-all}html[lang="ko"] table{font-size:22px}@media(max-width:700px){#help{display:none}nav{gap:5px;font-size:12px}button{padding:7px 8px}}@media print{@page{size:13.333in 7.5in;margin:0}body{background:white}main{height:auto;overflow:visible}.stage{position:static;transform:none;width:auto;height:auto}.slide,.slide.active{display:block;break-after:page}nav,#notes{display:none!important}}
'''
    data = json.dumps(dict(slides=content['slides'], ui=ui), ensure_ascii=False).replace('</', '<\\/')
    js = '''
const data=DECKDATA;const slides=[...document.querySelectorAll('.slide')];let current=0;
function resize(){const m=document.querySelector('main');document.documentElement.style.setProperty('--scale',Math.min(m.clientWidth/1280,m.clientHeight/720));}
function show(n){current=Math.max(0,Math.min(slides.length-1,n));slides.forEach((s,i)=>{s.classList.toggle('active',i===current);s.setAttribute('aria-hidden',i!==current)});document.querySelector('#count').textContent=`${current+1} / ${slides.length}`;document.querySelector('#prev').disabled=current===0;document.querySelector('#next').disabled=current===slides.length-1;document.querySelector('#note-text').textContent=data.slides[current].notes;document.querySelector('#note-time').textContent=data.ui.time+': '+data.slides[current].seconds+' s';const sources=document.querySelector('#sources');sources.replaceChildren();for(const source of data.slides[current].sources){const item=document.createElement('li');item.textContent=source;sources.append(item)}history.replaceState(null,'','#'+(current+1));}
function notes(){const on=document.body.classList.toggle('notes');document.querySelector('#toggle').setAttribute('aria-expanded',on);resize();}
async function fullscreen(){try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen()}catch(error){document.querySelector('#help').textContent=data.ui.fullscreenFallback;}}
document.querySelector('#prev').onclick=()=>show(current-1);document.querySelector('#next').onclick=()=>show(current+1);document.querySelector('#toggle').onclick=notes;document.querySelector('#full').onclick=fullscreen;document.querySelector('#print').onclick=()=>window.print();document.addEventListener('keydown',event=>{if(event.ctrlKey||event.metaKey||event.altKey)return;if(['ArrowRight','PageDown',' '].includes(event.key)){event.preventDefault();show(current+1)}else if(['ArrowLeft','PageUp'].includes(event.key)){event.preventDefault();show(current-1)}else if(event.key==='Home')show(0);else if(event.key==='End')show(slides.length-1);else if(event.key.toLowerCase()==='n')notes();else if(event.key.toLowerCase()==='f')fullscreen();});window.addEventListener('resize',resize);show((parseInt(location.hash.slice(1),10)||1)-1);resize();
'''.replace('DECKDATA', data)
    output.write_text(f'<!doctype html><html lang="{content["language"]}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(content["slides"][0]["title"])}</title><style>{css}</style></head><body><main><div class="stage">'+''.join(sections)+f'</div></main><nav><button id="prev" aria-label="{ui["previous"]}">←</button><span id="count" aria-live="polite"></span><button id="next" aria-label="{ui["next"]}">→</button><button id="toggle" aria-expanded="false" aria-controls="notes">{ui["notes"]}</button><button id="full">{ui["fullscreen"]}</button><button id="print">{ui["print"]}</button><span id="help">{ui["help"]}</span></nav><aside id="notes"><p id="note-time"></p><p id="note-text"></p><ul id="sources"></ul></aside><script>'+js+'</script></body></html>',encoding='utf-8')


def build_pdf(content, output, render_dir=None, korean_font=None):
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Table, TableStyle
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    regular, bold = 'Helvetica', 'Helvetica-Bold'
    if content['language'] == 'ko':
        path = korean_font or Path('/System/Library/Fonts/Supplemental/AppleGothic.ttf')
        if not path.is_file(): raise ValueError('Provide a Korean TrueType font with --korean-font.')
        pdfmetrics.registerFont(TTFont('DeckKorean', str(path)))
        regular = bold = 'DeckKorean'
    ink, accent = colors.HexColor('#142e38'), colors.HexColor('#176e68')
    c = canvas.Canvas(str(output), pagesize=(1280,720))
    c.setTitle(content['slides'][0]['title']);c.setAuthor(content['author'])

    def write(text, x, y, width, size=25, color=ink, strong=False):
        style=ParagraphStyle('Slide',fontName=bold if strong else regular,fontSize=size,leading=size*1.3,textColor=color,wordWrap=None)
        p=Paragraph(html.escape(text),style);_,h=p.wrap(width,1000)
        if y-h<58:raise ValueError(f'Text does not fit: {text[:60]}')
        p.drawOn(c,x,y-h);return y-h-18

    def draw_table(block,x,y,width,compact=False):
        count=len(block['headers'])
        if count==2: proportions=[.25,.75]
        elif count==3: proportions=[.24,.56,.20] if 'scenario' in block['headers'][1] or content['slides'][7]['blocks'][1] is block else [.38,.31,.31]
        else: proportions=[.37,.21,.21,.21]
        size=20 if compact or count==4 else 23
        if width<500:size=22;proportions=[.45,.29,.26]
        rows=[]
        for index,row in enumerate([block['headers']]+block['rows']):
            rows.append([Paragraph(html.escape(value),ParagraphStyle('Cell',fontName=bold if index==0 else regular,fontSize=size,leading=size*1.27,textColor=accent if index==0 else ink,wordWrap=None)) for value in row])
        t=Table(rows,colWidths=[width*p for p in proportions])
        t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),16),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),('LINEBELOW',(0,0),(-1,0),1.4,colors.HexColor('#a8bbb9')),('LINEBELOW',(0,1),(-1,-1),.5,colors.HexColor('#d8e1de'))]))
        _,h=t.wrap(width,1000)
        if y-h<58:raise ValueError(f'Table does not fit: {block["headers"]}')
        t.drawOn(c,x,y-h);return y-h-20

    for number,slide in enumerate(content['slides'],1):
        y=write(slide['title'],64,610 if number==1 else 666,1152,58 if number==1 else 39,strong=True)
        if number==1:y-=24
        if number==6:
            block=slide['blocks'][0];w,h=ImageReader(str(ROOT/block['path'])).getSize()
            c.drawImage(str(ROOT/block['path']),64,y-700*h/w,width=700,height=700*h/w)
            right=y
            for block in slide['blocks'][1:]:
                if block['type']=='table':right=draw_table(block,794,right,420)
                else:right=write(block['text'],794,right,420,20 if block['type']=='small' else 26,accent if block['type']=='accent' else ink)
        else:
            for block in slide['blocks']:
                if block['type']=='table':y=draw_table(block,64,y,1152,number==14)
                elif block['type']=='chart':
                    w,h=ImageReader(str(ROOT/block['path'])).getSize();target=960;actual=target*h/w
                    if y-actual<58:raise ValueError('Chart does not fit')
                    c.drawImage(str(ROOT/block['path']),160,y-actual,width=target,height=actual);y-=actual+16
                else:
                    size=20 if block['type']=='small' else 30 if block['type']=='lead' else 25
                    y=write(block['text'],64,y,1152,size,accent if block['type']=='accent' else ink)
        c.setFillColor(colors.HexColor('#526b74'));c.setFont(regular,15);c.drawRightString(1230,24,str(number));c.showPage()
    c.save()
    if render_dir:
        import pymupdf
        render_dir.mkdir(parents=True,exist_ok=True)
        with pymupdf.open(output) as pdf:
            for i,page in enumerate(pdf):page.get_pixmap().save(render_dir/f'slide-{i+1}.png')


def build_notes(content, output):
    title=content['ui']['notes']
    lines=['# '+title,'',f"{content['author']} · {content['course']}",'',content['ui']['timingNote'],'']
    for i,s in enumerate(content['slides'],1):
        lines += [f"## {i}. {s['title']}",'',s['notes'],'',content['ui']['time']+f": {s['seconds']} s",'',content['ui']['sources']+': '+', '.join(s['sources']),'']
    output.write_text('\n'.join(lines),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content',type=Path,default=Path(__file__).with_name('content.json'))
    parser.add_argument('--output-stem',type=Path,default=Path(__file__).with_name('project_presentation'))
    parser.add_argument('--render-dir',type=Path)
    parser.add_argument('--korean-font',type=Path)
    args=parser.parse_args()
    content=json.loads(args.content.read_text())
    if len(content['slides'])!=14:raise ValueError('Expected 14 slides including two appendices.')
    analysis=json.loads((ROOT/'results/analysis/analysis_summary.json').read_text())
    for name,expected in analysis['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError(f'Changed source: {name}')
    args.output_stem.parent.mkdir(parents=True,exist_ok=True)
    build_html(content,args.output_stem.with_suffix('.html'))
    build_pdf(content,args.output_stem.with_suffix('.pdf'),args.render_dir,args.korean_font)
    notes_path = args.output_stem.with_name('speaker_notes.md') if args.output_stem.name == 'project_presentation' else args.output_stem.with_name(args.output_stem.name+'_notes.md')
    build_notes(content,notes_path)
    print(f"Built {content['language']} HTML/PDF deck and notes: 14 slides.")


if __name__=='__main__':main()

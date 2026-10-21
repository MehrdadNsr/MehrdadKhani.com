"""Build the two-page, text-based product/project coordinator resume.
Run with Python + reportlab. Source facts: resume-content.json and verified projects.
"""
from pathlib import Path
import json
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont('ResumeSans','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('ResumeSans-Bold','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
pdfmetrics.registerFontFamily('ResumeSans',normal='ResumeSans',bold='ResumeSans-Bold')
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Mehrdad_Khani_Resume.pdf'
ink=HexColor('#172019');muted=HexColor('#445047');green=HexColor('#365329')
styles={
'name':ParagraphStyle('name',fontName='ResumeSans-Bold',fontSize=25,leading=29,textColor=ink,spaceAfter=5),
'headline':ParagraphStyle('headline',fontName='ResumeSans-Bold',fontSize=10.5,leading=15,textColor=green,spaceAfter=8),
'contact':ParagraphStyle('contact',fontName='ResumeSans',fontSize=8.5,leading=12,textColor=muted,spaceAfter=12),
'section':ParagraphStyle('section',fontName='ResumeSans-Bold',fontSize=10,leading=14,textColor=green,spaceBefore=12,spaceAfter=7),
'body':ParagraphStyle('body',fontName='ResumeSans',fontSize=9.5,leading=13.6,textColor=ink,spaceAfter=7),
'job':ParagraphStyle('job',fontName='ResumeSans-Bold',fontSize=10.5,leading=14,textColor=ink,spaceAfter=3),
'meta':ParagraphStyle('meta',fontName='ResumeSans',fontSize=8.8,leading=12,textColor=muted,spaceAfter=6),
'bullet':ParagraphStyle('bullet',fontName='ResumeSans',fontSize=9.1,leading=12.8,textColor=ink,leftIndent=10,firstLineIndent=-9,spaceAfter=5),
}
story=[]
def para(text,kind='body'):return Paragraph(text,styles[kind])
def add(text,kind='body'):story.append(para(text,kind))
def section(text):add(text.upper(),'section')
def bullet(text):return para('- '+escape(text),'bullet')
def project(title,meta,items):
 story.append(KeepTogether([para(title,'job'),para(meta,'meta')]+[bullet(x) for x in items]));story.append(Spacer(1,8))
add('MEHRDAD KHANI','name')
add('PRODUCT &amp; PROJECT COORDINATION | APPLIED AI','headline')
add('Mississauga, Ontario | (437) 663-7790 | M.NasrollahKhani@gmail.com<br/>mehrdadkhani.com | linkedin.com/in/Mehrdad-Khani | github.com/MehrdadNsr','contact')
section('Professional profile')
add('Independent AI product builder with a background in pharmaceutical operations, quality assurance and cross-functional coordination. Experience translating work into clear tasks, training colleagues, documenting decisions and resolving operational issues. Currently in Production Compounding at Apotex; targeting Product and Project Coordinator roles in AI.')
section('Core capabilities')
add('Feature prioritization &bull; Iterative delivery &bull; Cross-functional coordination &bull; Technical communication &bull; Training &bull; Issue follow-up &bull; Risk assessment &bull; Process improvement','body')
section('Selected AI & product projects | 2026')
project('Vazne | Independent Product Builder','Workout companion for iOS and Android | In testing | vazne.app',[
'Directed the product experience for a bilingual workout app covering plan import, set logging, rest timing and progress tracking.',
'Prioritized core workout flows and guided AI-assisted implementation; iterated on navigation, input controls and visual consistency.',
'Reviewed builds and refined usability through repeated testing, balancing new features with a simpler workout experience.'
])
project('Trafactor | Independent AI Studio','AI products, open-source tools and experiments | trafactor.com',[
'Defined project direction and product positioning for an independent portfolio of AI tools and applications.',
'Coordinated AI-assisted design, development and review, turning broad ideas into specific features and clearer user experiences.'
])
project('Matrix Agent Room | Workflow Design & Experimentation','Open-source multi-model workspace | github.com/MehrdadNsr/matrix-agent-room',[
'Designed and ran a shared workspace for AI assistants using Supabase and automated model bridges.',
'Defined coordination rules, tested communication workflows and documented reliability gaps, decisions and follow-up fixes.'
])
section('Working tools')
add('AI-assisted development, GitHub, Supabase, Python, Excel and PowerPoint. Practical experience defining tasks, reviewing outputs and documenting issues across AI-supported workflows. English and Persian.')
story.append(PageBreak())
add('MEHRDAD KHANI','job');add('Product &amp; Project Coordination | Professional Experience','meta')
section('Professional experience')
roles=json.loads((ROOT/'resume-content.json').read_text())['roles']
for date,org,title,loc,bullets in roles:
 title=title.replace(' · ',' - ')
 story.append(KeepTogether([para(escape(org+' | '+title),'job'),para(escape(date+' | '+loc),'meta')]+[bullet(x) for x in bullets]))
 story.append(Spacer(1,8))
section('Education & credentials')
add('<b>BSc Biotechnology</b> | University of Amol, Iran | 2015-2019<br/>WES evaluated | BioReady Certified Process Development Technician, BioTalent Canada','body')
section('Selected domain expertise')
add('Vaccine and API production; bioprocess development; GMP documentation; risk assessment; root-cause analysis; CAPA; process validation.','body')

def footer(c,doc):
 c.setStrokeColor(HexColor('#d1d9cd'));c.setLineWidth(.5);c.line(44,39,568,39)
 c.setFont('ResumeSans',8);c.setFillColor(muted);c.drawString(44,26,'Mehrdad Khani | mehrdadkhani.com');c.drawRightString(568,26,f'{doc.page} / 2')
doc=SimpleDocTemplate(str(OUT),pagesize=letter,rightMargin=44,leftMargin=44,topMargin=38,bottomMargin=49,title='Mehrdad Khani - Product and Project Coordination',author='Mehrdad Khani')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)

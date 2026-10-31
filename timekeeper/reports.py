"""Client-facing PDF reports. Private notes and documents are never inputs to the PDF."""
from collections import OrderedDict
from datetime import datetime, timezone
import io
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether


def groups_for(entries):
    groups = OrderedDict()
    for entry in sorted(entries, key=lambda row: (row['name'].casefold(), row['client_id'], row['started_at'])):
        group = groups.setdefault(entry['client_id'], {'name': entry['name'], 'entries': [], 'seconds': 0, 'amount': 0})
        group['entries'].append(entry)
        group['seconds'] += entry['seconds']
        group['amount'] += entry['amount']
    return list(groups.values())


def pdf_report(entries, zone, currency, start_text='', end_text='', client_name=None):
    fonts = Path(reportlab.__file__).parent / 'fonts'
    if 'IAReport' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('IAReport', str(fonts / 'Vera.ttf')))
        pdfmetrics.registerFont(TTFont('IAReportBold', str(fonts / 'VeraBd.ttf')))
    tz = ZoneInfo(zone)
    styles = getSampleStyleSheet()
    normal = ParagraphStyle('Body', fontName='IAReport', fontSize=9, leading=14, spaceAfter=9, textColor=colors.HexColor('#202820'))
    small = ParagraphStyle('Small', parent=normal, fontSize=8, leading=12, textColor=colors.HexColor('#556055'))
    heading = ParagraphStyle('Heading', parent=normal, fontName='IAReportBold', fontSize=17, leading=22, spaceBefore=17, spaceAfter=10, keepWithNext=True)
    subheading = ParagraphStyle('Subheading', parent=normal, fontName='IAReportBold', fontSize=11, leading=16, spaceBefore=12, keepWithNext=True)
    def p(text, style=normal):
        # ReportLab markup is escaped; URLs stay text and cannot fetch resources.
        clean = ''.join(char for char in str(text) if ord(char) >= 32 or char in '\n\t')
        return Paragraph(escape(clean).replace('\n', '<br/>'), style)
    def elapsed(seconds):
        return f'{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}'
    def amount(cents):
        return f'{currency} {cents/100:,.2f}'
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=(8.5*inch,11*inch), leftMargin=48,rightMargin=48,topMargin=48,bottomMargin=48,
        title='Client work report', author='Inflection Architectures')
    total_seconds, total_amount = sum(row['seconds'] for row in entries), sum(row['amount'] for row in entries)
    period = f'{start_text or "Beginning of records"} through {end_text or "Latest recorded session"}'
    story = [p('INFLECTION ARCHITECTURES', small), p('Work report', heading), p(client_name or 'All clients', subheading),
        p(period + ' · ' + zone, small), p('Grand total', subheading),
        p(f'{total_seconds/3600:,.4f} hours ({elapsed(total_seconds)}) | {amount(total_amount)} estimated | {len(entries)} sessions'),
        p('Totals include only time within the selected period. Sessions crossing a date boundary are prorated using their recorded hourly rate. Only completed work logs are included. Estimates exclude taxes and payments.', small)]
    groups = groups_for(entries)
    if groups:
        data = [[p('Client', small), p('Hours', small), p('Estimated earnings', small)]]
        data.extend([[p(group['name']), p(f"{group['seconds']/3600:,.4f}"), p(amount(group['amount']))] for group in groups])
        table = Table(data, colWidths=[280,80,156], repeatRows=1, hAlign='LEFT')
        table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9f7e5')),
            ('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#81b86c')),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8)]))
        story.extend([Spacer(1,12), table])
    else:
        story.append(p('No completed work in this period.'))
    for group in groups:
        story.extend([p(group['name'], heading), p(f"Client subtotal: {group['seconds']/3600:,.4f} hours ({elapsed(group['seconds'])}) | {amount(group['amount'])}", small)])
        last_day = None
        for entry in group['entries']:
            day = datetime.fromtimestamp(entry['started_at'], tz).strftime('%A, %B %d, %Y')
            if day != last_day:
                story.append(p(day, subheading))
                last_day = day
            start = datetime.fromtimestamp(entry['started_at'], tz).strftime('%Y-%m-%d %H:%M:%S %Z')
            end = datetime.fromtimestamp(entry['ended_at'], tz).strftime('%Y-%m-%d %H:%M:%S %Z')
            story.extend([p(entry['summary'], subheading), p(f"{start} → {end}\n{elapsed(entry['seconds'])} | {amount(entry['rate_cents'])}/hour | {amount(entry['amount'])} estimated\nSession reference: {entry['id']}", small)])
            if entry.get('partial'):
                story.append(p('Partial session: only the time overlapping the selected period is counted.', small))
            story.extend([p('Work completed & deliverables', small), p(entry['deliverables'])])
            if entry['next_steps']:
                story.extend([p('Next steps', small), p(entry['next_steps'])])
            story.append(Spacer(1,10))
    def footer(canvas, _doc):
        canvas.saveState()
        canvas.setFont('IAReport',7)
        canvas.setFillColor(colors.HexColor('#556055'))
        canvas.drawString(48,27,'Inflection Architectures · Work report')
        canvas.drawRightString(564,27,f'Page {canvas.getPageNumber()}')
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)
    return buffer

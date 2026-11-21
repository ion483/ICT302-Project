"""Generate an offline PDF report from the completed CopyQ analysis.

Uses ReportLab to avoid relying on a browser, network, or HTML-to-PDF engine.
All indicators are descriptive and must not be treated as a misconduct verdict.
"""
import re
from datetime import datetime
from html import escape
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from core.rsid_palette import build_rsid_palette

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, HRFlowable, Flowable


class _ColourRow(Flowable):
    """One splittable-by-row line of the text-free RSID map."""

    def __init__(self, segments):
        super().__init__()
        self.segments = segments
        self.width = sum(width for width, _, _ in segments)
        self.height = 12

    def draw(self):
        offset = 0
        badges = []
        for width, colour, number in self.segments:
            self.canv.setFillColor(colour)
            self.canv.rect(offset, 2, width, 10, stroke=0, fill=1)
            if number is not None:
                label = str(number)
                size = 6
                badge_width = stringWidth(label, 'Helvetica-Bold', size) + size
                # Narrow blocks retain their width; their readable badge sits left.
                badge_x = offset if width >= badge_width else offset - badge_width
                badges.append((badge_x, badge_width, label))
            offset += width
        # Draw labels last so later colour blocks cannot cover them.
        for badge_x, badge_width, label in badges:
            self.canv.setFillColor(colors.white)
            self.canv.roundRect(badge_x, 3.6, badge_width, 8.4, 1.2, stroke=0, fill=1)
            self.canv.setFillColor(colors.HexColor('#21384e'))
            self.canv.setFont('Helvetica-Bold', 6)
            self.canv.drawString(badge_x + 3, 5.4, label)


def _colour_map_rows(paragraphs, width):
    """Pack text widths continuously, without preserving paragraph/line breaks."""
    palette = build_rsid_palette(paragraphs)
    segments = []
    used = 0
    for paragraph in paragraphs:
        runs = paragraph.get('runs') or [{'text': paragraph.get('text', '')}]
        for run in runs:
            rsid = (run.get('rsidR') or '').strip().upper()
            if re.fullmatch(r'[0-9A-F]{8}', rsid) and rsid != '00000000':
                indicator = palette.get(rsid)
                if indicator is None:
                    continue
                colour = colors.HexColor(indicator['colour'])
                number = indicator['number']
            else:
                colour = colors.HexColor('#e5e7eb')
                number = None
            for character in run.get('text', ''):
                if character in '\r\n':
                    continue
                remaining = stringWidth(' ' if character.isspace() else character, 'Helvetica', 8.6)
                while remaining > 0:
                    amount = min(remaining, width - used)
                    if segments and segments[-1][1:] == (colour, number):
                        segments[-1] = (segments[-1][0] + amount, colour, number)
                    else:
                        segments.append((amount, colour, number))
                    used += amount
                    remaining -= amount
                    if used >= width - 1e-8:
                        yield _ColourRow(segments)
                        segments, used = [], 0
    if segments:
        yield _ColourRow(segments)


def _display(value: Any) -> str:
    if value is None or value == "":
        return "Not available"
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    return str(value)


def _format_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return "Not available"
    try:
        parsed = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
        return parsed.strftime('%Y-%m-%d %H:%M:%S %z').strip()
    except ValueError:
        return value


def _safe_text(text) -> str:
    return escape(_display(text)).replace('\n', '<br/>')


def generate_pdf_report(analysis_result: dict[str, Any], destination: str | Path) -> Path:
    """Produce a PDF report with metadata, descriptive metrics and text-run grouping.

    Output is generated in a temporary file and atomically moved into place.
    """
    if not isinstance(analysis_result, dict) or not analysis_result.get('ok'):
        raise ValueError('A successful analysis is required to generate a report.')
    document = analysis_result.get('document') or {}
    metadata = document.get('metadata') or {}
    metrics = analysis_result.get('metrics') or {}
    integrity = analysis_result.get('integrity') or {}
    top_sessions = analysis_result.get('top_sessions') or []
    paragraphs = analysis_result.get('paragraphs') or []
    notices = analysis_result.get('analysis_notices') or []
    output = Path(destination)
    if output.suffix.lower() != '.pdf':
        raise ValueError('Report destination must end in .pdf.')
    output.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CopyQTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=19, leading=24, spaceAfter=14))
    styles.add(ParagraphStyle(name='CopyQSmall', fontName='Helvetica', fontSize=8.8, leading=12.5, spaceAfter=8))
    styles.add(ParagraphStyle(name='CopyQBody', fontName='Helvetica', fontSize=9.2, leading=13, spaceAfter=7))
    styles.add(ParagraphStyle(name='CopyQSection', parent=styles['Heading2'], spaceBefore=15, spaceAfter=8))
    styles.add(ParagraphStyle(name='CopyQText', fontName='Helvetica', fontSize=8.6, leading=12, spaceAfter=8, borderPadding=5))

    story = [Paragraph('CopyQ — Forensic Document Analysis', styles['CopyQTitle'])]
    story.append(Paragraph('Local, descriptive evidence summary. This document does not determine authorship, pasting, or academic misconduct.', styles['CopyQBody']))
    report_date = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')
    story.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#999999')))
    story.append(Paragraph('Document metadata and integrity', styles['CopyQSection']))

    metadata_rows = [
        ('Document / session ID', document.get('document_id')),
        ('Original SHA-256', integrity.get('original_sha256')),
        ('Working copy verified', integrity.get('working_copy_verified')),
        ('Root RSID', document.get('rsid_root')),
        ('Creator', metadata.get('creator')),
        ('Last modified by', metadata.get('last_modified_by')),
        ('Created', _format_timestamp(metadata.get('creation_date'))),
        ('Last modified', _format_timestamp(metadata.get('modified_date'))),
        ('Application', metadata.get('application')),
        ('Application version', metadata.get('app_version')),
        ('Reported editing time (min)', metadata.get('editing_time_minutes')),
        ('Recorded page count', metadata.get('page_count')),
        ('Shared document', metadata.get('shared_document')),
    ]
    measurement_rows = [
        ('Total extracted words', metrics.get('total_word_count')),
        ('Recorded revision count', metrics.get('revision_count')),
        ('Distinct usable RSIDs', metrics.get('unique_rsid_count')),
        ('Nonempty OOXML text runs', metrics.get('text_run_count')),
        ('Words attributed to usable RSIDs', metrics.get('attributed_word_count')),
        ('Words / recorded revision', metrics.get('word_to_revision_ratio')),
        ('RSIDs / recorded revision', metrics.get('unique_rsid_to_revision_ratio')),
        ('Largest RSID group (words)', metrics.get('largest_rsid_word_count')),
        ('Largest RSID group (%)', metrics.get('largest_rsid_share_percent')),
        ('Avg characters / usable RSID', metrics.get('average_characters_per_rsid')),
        ('Avg characters / nonempty run', metrics.get('average_characters_per_run')),
    ]

    def add_table(rows):
        cells = [[Paragraph(_safe_text(label), styles['CopyQSmall']),
                  Paragraph(_safe_text(value), styles['CopyQSmall'])] for label, value in rows]
        table = Table(cells, colWidths=[62 * mm, 114 * mm], hAlign='LEFT')
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f2f2f5')),
            ('LINEBELOW', (0, 0), (-1, -1), .3, colors.HexColor('#dddddd')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(table)

    add_table(metadata_rows)
    story.append(Paragraph('Descriptive document measurements', styles['CopyQSection']))
    add_table(measurement_rows)
    story.append(Paragraph('Analysis limitations and observations', styles['CopyQSection']))
    if metrics.get('unique_rsid_count') == 0:
        story.append(Paragraph('No usable RSIDs were found; zero-filled or missing identifiers cannot distinguish editing sessions.', styles['CopyQBody']))
    else:
        share = metrics.get('largest_rsid_share_percent')
        if share is not None:
            story.append(Paragraph(f'The largest usable RSID group accounts for {share}% of extracted words. This does not demonstrate misconduct or a paste event.', styles['CopyQBody']))
    for indicator in metrics.get('descriptive_indicators') or []:
        story.append(Paragraph('Review indicator: ' + _safe_text(indicator.get('description')), styles['CopyQBody']))
    if metrics.get('revision_count') is None:
        story.append(Paragraph('Revision count was absent or unusable, so division by revision count was not performed.', styles['CopyQBody']))
    for note in notices:
        story.append(Paragraph(_safe_text(note), styles['CopyQBody']))
    story.append(Paragraph('RSID values have no reliable per-session timestamps; any coloured text below follows current document order, not a verified editing chronology.', styles['CopyQBody']))
    story.append(Paragraph('Largest RSID-associated text groups', styles['CopyQSection']))
    if top_sessions:
        groups = [['RSID', 'Attributed words', 'Group']]
        for entry in top_sessions:
            groups.append([_display(entry.get('rsid')), _display(entry.get('word_count')), _display(entry.get('session_type'))])
        group_table = Table(groups, colWidths=[80 * mm, 48 * mm, 48 * mm], repeatRows=1)
        group_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8e8ed')),
            ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#dddddd')),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(group_table)
    else:
        story.append(Paragraph('No usable RSID groups available.', styles['CopyQBody']))

    if paragraphs:
        story.append(Paragraph('RSID colour overview', styles['CopyQSection']))
        story.append(Paragraph('Colours follow current document order, without text or paragraph breaks. Grey indicates an unavailable RSID. Groups are not verified edit times.', styles['CopyQBody']))
        # Match the usable frame width, including ReportLab's default frame padding.
        map_width = A4[0] - 34 * mm - 12
        story.extend(_colour_map_rows(paragraphs, map_width))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#666666'))
        if doc.page == 1:
            canvas.drawRightString(A4[0] - 17 * mm, A4[1] - 10 * mm,
                                   'Report date: ' + report_date)
        canvas.drawRightString(A4[0] - 16 * mm, 12 * mm, f'CopyQ · Page {doc.page}')
        canvas.restoreState()

    with NamedTemporaryFile(mode='wb', suffix='.pdf', dir=output.parent, delete=False) as file:
        temp = Path(file.name)
    try:
        pdf = SimpleDocTemplate(str(temp), pagesize=A4, leftMargin=17 * mm,
                                rightMargin=17 * mm, topMargin=18 * mm, bottomMargin=20 * mm)
        pdf.build(story, onFirstPage=footer, onLaterPages=footer)
        if not temp.read_bytes().startswith(b'%PDF-'):
            raise ValueError('PDF report generation failed.')
        temp.replace(output)
    finally:
        temp.unlink(missing_ok=True)
    return output


# Retain the previous symbol for older code paths, while the output is a PDF.
generate_html_report = generate_pdf_report

"""PDF output regression test: this used to test .html, but the report is PDF."""
import tempfile
from pathlib import Path

from core.report_generator import generate_pdf_report
from core.report_generator import _colour_map_rows, _ColourRow
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth


def test_report_generator_standalone():
    mock = {
        'ok': True,
        'document': {'document_id': 'synthetic-test', 'rsid_root': None, 'metadata': {}},
        'integrity': {'original_sha256': '0' * 64, 'working_copy_verified': True},
        'metrics': {'total_word_count': 2, 'revision_count': None, 'unique_rsid_count': 0},
        'top_sessions': [],
        'paragraphs': [{'text': 'Hello world', 'word_count': 2, 'runs': [{'text': 'Hello world', 'rsidR': None}]}],
    }
    with tempfile.TemporaryDirectory() as folder:
        destination = Path(folder) / 'forensic-report.pdf'
        saved_path = generate_pdf_report(mock, destination)
        assert saved_path.read_bytes().startswith(b'%PDF-')
        assert saved_path.stat().st_size > 500


def test_colour_map_packs_paragraphs_without_text_or_line_breaks():
    paragraphs = [
        {'runs': [{'text': 'AB\n', 'rsidR': '00abcdef'}]},
        {'runs': [{'text': 'CD', 'rsidR': '00ABCDEF'},
                  {'text': 'EF', 'rsidR': '00123456'}]},
    ]
    rows = list(_colour_map_rows(paragraphs, 20))
    expected = stringWidth('ABCDEF', 'Helvetica', 8.6)
    assert abs(sum(row.width for row in rows) - expected) < 1e-8
    assert all(abs(row.width - 20) < 1e-8 for row in rows[:-1])
    assert rows[0].segments[0][1] == rows[1].segments[0][1]
    assert rows[0].segments[0][2] == rows[1].segments[0][2] == 1
    assert rows[-1].segments[-1][2] == 2

    labels = []

    class ColourMapCanvas:
        def setFillColor(self, colour):
            pass

        def rect(self, x, y, width, height, stroke, fill):
            assert width > 0 and height > 0
            assert stroke == 0 and fill == 1

        def roundRect(self, x, y, width, height, radius, stroke, fill):
            assert width > 0 and height > 0

        def setFont(self, name, size):
            assert name == 'Helvetica-Bold' and 0 < size <= 6

        def drawString(self, x, y, text):
            labels.append(text)

    for row in rows:
        row.canv = ColourMapCanvas()
        row.draw()
    assert set(labels) == {'1', '2'}


def test_narrow_colour_block_places_readable_badge_on_left():
    badges = []

    class Canvas:
        def setFillColor(self, colour):
            pass

        def rect(self, *args, **kwargs):
            pass

        def roundRect(self, x, y, width, *args, **kwargs):
            badges.append((x, width))

        def setFont(self, name, size):
            assert size == 6

        def drawString(self, *args):
            pass

    row = _ColourRow([(40, colors.red, 1), (2, colors.blue, 34)])
    row.canv = Canvas()
    row.draw()
    assert badges[0][0] == 0
    assert abs(sum(badges[1]) - 40) < 1e-8
    assert row.width == 42

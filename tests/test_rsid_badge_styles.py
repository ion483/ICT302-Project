"""Regression: numbered RSID labels remain visible after player removal."""
from pathlib import Path
import re


PROJECT = Path(__file__).resolve().parents[1]


def test_secondary_numbered_rsid_labels_have_valid_css_and_js():
    css = (PROJECT / 'ui' / 'style.css').read_text(encoding='utf-8')
    js = (PROJECT / 'ui' / 'script.js').read_text(encoding='utf-8')

    # The removed player previously left a dangling declaration (`color: ...; }`)
    # immediately before this pseudo-element, preventing the browser from
    # recognizing numbered RSID markers. Keep the selector at rule level.
    assert re.search(
        r'\}\s*/\*[^*]*\*/\s*'
        r'\.document-content \.rsid-run\[data-rsid-number\]::before\s*\{'
        r'\s*content:\s*attr\(data-rsid-number\);', css
    ), 'The numbered RSID ::before rule must remain a valid CSS rule'
    assert 'run.dataset.rsidNumber = String(indicator.number)' in js
    assert 'documentContent.querySelectorAll(".rsid-run")' in js

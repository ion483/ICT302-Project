from pathlib import Path
import os

# Use the browser engine shipped with the application, rather than WebView2.
os.environ["QT_API"] = "pyside6"

import webview
from core.document_reader import read_docx

class Api:
    def read_docx(self, filename, encoded_file):
        return read_docx(filename, encoded_file)

if __name__ == "__main__":
    api = Api()

    webview.create_window(
        title="Document Metadata Extractor",
        url=str(Path(__file__).resolve().parent / "ui" / "index.html"),
        js_api=api,
        width=1200,
        height=800,
        min_size=(900, 600),
        resizable=True
    )

    webview.start(gui="qt", debug=False)

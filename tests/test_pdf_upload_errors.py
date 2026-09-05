"""Deterministic test: uploading a PDF with no extractable text (a scan
with no OCR layer) must return a clean 400, never an unhandled 500.

Rather than constructing a real scanned PDF -- unnecessary and fragile --
this monkeypatches ingest_pdf to raise the exact ValueError it already
raises for that case. The actual PDF-parsing behaviour isn't what this
test checks; api.py's error handling around it is.

NOTE: importing api.py pulls in nodes.tools, which registers MCP tools
against a real server at import time (same side effect as everywhere
else in this project). Expect a real network call and a
"[MCP] registered..." line when this test runs.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

import api as api_module


def test_scanned_pdf_returns_clean_400_not_500(monkeypatch, tmp_path):
    def fake_ingest_pdf(file_path):
        raise ValueError(
            "No extractable text found. This PDF is probably a scan and needs OCR."
        )

    # Patch the name INSIDE api.py's own namespace, not the original
    # function in nodes.tools.rag -- api.py already holds its own
    # reference from `from nodes.tools.rag import ingest_pdf`, so
    # patching the original elsewhere wouldn't be seen here. Same
    # principle as patching tn.interrupt instead of langgraph's, earlier.
    monkeypatch.setattr(api_module, "ingest_pdf", fake_ingest_pdf)
    monkeypatch.setattr(api_module, "UPLOAD_DIR", str(tmp_path))

    with TestClient(api_module.app) as client:
        fake_pdf_bytes = b"%PDF-1.4 fake content, never actually parsed"
        response = client.post(
            "/upload_pdf",
            files={"pdf": ("scanned.pdf", fake_pdf_bytes, "application/pdf")},
        )

    assert response.status_code == 400
    assert "OCR" in response.json()["detail"]
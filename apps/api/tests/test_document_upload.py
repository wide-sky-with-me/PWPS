"""Tests for document upload API."""

from pathlib import Path

from fastapi.testclient import TestClient

from pwps_agent_api.main import app


def test_upload_json_document(tmp_path: Path) -> None:
    client = TestClient(app)
    content = (
        b'[{"source_type": "local_document", "source_id": "test",'
        b' "title": "Test", "content": "test content",'
        b' "target_fields": ["consumable"]}]'
    )
    response = client.post(
        "/api/documents/upload",
        files={"file": ("test.json", content, "application/json")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.json"
    assert data["content_type"] == "application/json"
    assert data["size_bytes"] == str(len(content))
    assert "file_id" in data
    assert "checksum_sha256" in data


def test_upload_rejects_unsupported_type() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/documents/upload",
        files={"file": ("test.exe", b"binary", "application/x-msdownload")},
    )
    assert response.status_code == 415
    assert response.json()["error_code"] == "UNSUPPORTED_FILE_TYPE"


def test_upload_rejects_empty_file() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/documents/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "EMPTY_FILE"


def test_upload_accepts_pdf() -> None:
    client = TestClient(app)
    # Minimal valid PDF header
    content = b"%PDF-1.4 minimal"
    response = client.post(
        "/api/documents/upload",
        files={"file": ("doc.pdf", content, "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["content_type"] == "application/pdf"


def test_upload_accepts_markdown() -> None:
    client = TestClient(app)
    content = "# Welding Standard\n\nER50-6 is a GMAW wire."
    response = client.post(
        "/api/documents/upload",
        files={"file": ("standard.md", content.encode(), "text/markdown")},
    )
    assert response.status_code == 200
    assert response.json()["filename"] == "standard.md"


def test_upload_generates_unique_ids() -> None:
    client = TestClient(app)
    id1 = client.post(
        "/api/documents/upload",
        files={"file": ("a.txt", b"content-a", "text/plain")},
    ).json()["file_id"]
    id2 = client.post(
        "/api/documents/upload",
        files={"file": ("b.txt", b"content-b", "text/plain")},
    ).json()["file_id"]
    assert id1 != id2

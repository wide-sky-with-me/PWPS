"""Document upload API endpoints."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, UploadFile

from pwps_agent_api.core.config import get_settings
from pwps_agent_api.schemas.api import ErrorResponse

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Allowed MIME types and their extensions
_ALLOWED_TYPES: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/json": ".json",
    "text/plain": ".txt",
    "text/markdown": ".md",
}

_MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
_ALLOWED_EXTENSIONS = set(_ALLOWED_TYPES.values())


class DocumentApiError(Exception):
    def __init__(self, *, status_code: int, error: ErrorResponse) -> None:
        self.status_code = status_code
        self.error = error


@router.post(
    "/upload",
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
    },
)
async def upload_document(file: UploadFile) -> dict[str, str]:
    """Upload a document for knowledge ingestion.

    Security measures:
    - File type whitelist (PDF, Word, JSON, TXT, Markdown)
    - 20 MB size limit
    - Unique file ID to prevent path traversal
    - Isolated storage directory
    """
    # Validate file type
    if file.content_type not in _ALLOWED_TYPES:
        raise _doc_error(
            415,
            "UNSUPPORTED_FILE_TYPE",
            f"File type '{file.content_type}' is not supported. "
            f"Allowed: {', '.join(_ALLOWED_TYPES.keys())}",
        )

    # Validate extension
    ext = Path(file.filename or "").suffix.lower()
    if ext and ext not in _ALLOWED_EXTENSIONS:
        raise _doc_error(
            400,
            "UNSUPPORTED_FILE_TYPE",
            f"File extension '{ext}' is not allowed.",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise _doc_error(
            413,
            "FILE_TOO_LARGE",
            f"File size ({len(content)} bytes) exceeds the 20 MB limit.",
        )

    if len(content) == 0:
        raise _doc_error(400, "EMPTY_FILE", "Uploaded file is empty.")

    # Generate unique file ID and store
    file_id = f"doc-{uuid4()}"
    resolved_ext = ext or _ALLOWED_TYPES.get(file.content_type, ".bin")
    storage_dir = _get_upload_dir()
    storage_dir.mkdir(parents=True, exist_ok=True)
    file_path = storage_dir / f"{file_id}{resolved_ext}"

    file_path.write_bytes(content)

    # Compute checksum for integrity verification
    checksum = hashlib.sha256(content).hexdigest()

    return {
        "file_id": file_id,
        "filename": file.filename or "unknown",
        "content_type": file.content_type or "application/octet-stream",
        "size_bytes": str(len(content)),
        "checksum_sha256": checksum,
    }


def _get_upload_dir() -> Path:
    settings = get_settings()
    return settings.local_artifact_dir / "uploads"


def _doc_error(status_code: int, error_code: str, message: str) -> DocumentApiError:
    return DocumentApiError(
        status_code=status_code,
        error=ErrorResponse(
            error_code=error_code,
            message=message,
            details={},
        ),
    )

"""Document upload validation (RF-03, RF-04)."""

from dataclasses import dataclass
from pathlib import Path

MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

PDF_SIGNATURE = b"%PDF"
DOCX_SIGNATURE = b"PK\x03\x04"


@dataclass(frozen=True)
class ValidatedDocument:
    """Validated upload ready for persistence."""

    file_name: str
    mime_type: str
    content: bytes
    file_size_bytes: int


class DocumentValidationError(Exception):
    """Raised when an uploaded file fails validation."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def validate_upload(
    file_name: str,
    content: bytes,
    content_type: str | None = None,
    max_size_bytes: int = MAX_UPLOAD_SIZE_BYTES,
) -> ValidatedDocument:
    """Validate file extension, size, MIME type and magic bytes."""
    if not file_name:
        raise DocumentValidationError("File name is required")

    extension = Path(file_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise DocumentValidationError(
            "Only PDF and DOCX files are allowed",
            status_code=400,
        )

    file_size = len(content)
    if file_size == 0:
        raise DocumentValidationError("Uploaded file is empty", status_code=400)

    if file_size > max_size_bytes:
        raise DocumentValidationError(
            "File exceeds the maximum allowed size of 25 MB",
            status_code=413,
        )

    mime_type = _resolve_mime_type(extension, content_type)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise DocumentValidationError(
            "Only PDF and DOCX files are allowed",
            status_code=400,
        )

    if not _matches_signature(extension, content):
        raise DocumentValidationError(
            "File content does not match the declared format",
            status_code=400,
        )

    return ValidatedDocument(
        file_name=Path(file_name).name,
        mime_type=mime_type,
        content=content,
        file_size_bytes=file_size,
    )


def _resolve_mime_type(extension: str, content_type: str | None) -> str:
    if content_type:
        normalized = content_type.split(";")[0].strip().lower()
        if normalized in ALLOWED_MIME_TYPES:
            return normalized

    if extension == ".pdf":
        return "application/pdf"
    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _matches_signature(extension: str, content: bytes) -> bool:
    if extension == ".pdf":
        return content.startswith(PDF_SIGNATURE)
    return content.startswith(DOCX_SIGNATURE)

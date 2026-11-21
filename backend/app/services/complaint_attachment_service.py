"""Evidence attached to a complaint (UC-L1-04): the original message, a scan, a photo.

Files go to disk under settings.upload_dir, in a folder per complaint, under a
random name; the name the client sent is only kept for display. Removal is soft
(removed_at) and, like adding, is allowed only while the complaint is a Draft
or Incomplete.
"""

from datetime import datetime
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timezone import LOCAL
from app.models import ComplaintAttachment
from app.schemas.l1_complaints import AttachmentOut
from app.services import audit_service
from app.services.auth_service import Principal
from app.services.complaint_intake_service import ComplaintError, find_editable

MB = 1024 * 1024
MAX_BYTES = 10 * MB  # images, PDFs, text and emails
MAX_AUDIO_BYTES = 25 * MB
MAX_VIDEO_BYTES = 50 * MB
MAX_PER_COMPLAINT = 10
EXTENSIONS = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "text/plain": ".txt",
    "message/rfc822": ".eml",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/ogg": ".ogg",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _matches_type(mime_type: str, content: bytes) -> bool:
    """Whether the file's own bytes fit the type the browser claimed (the claim alone is not trusted)."""
    if mime_type == "application/pdf":
        return content.startswith(b"%PDF-")
    if mime_type == "image/jpeg":
        return content.startswith(b"\xff\xd8\xff")
    if mime_type == "image/png":
        return content.startswith(b"\x89PNG\r\n\x1a\n")
    if mime_type == "image/webp":
        return content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    if mime_type == "audio/mpeg":
        return content.startswith(b"ID3") or (len(content) > 1 and content[0] == 0xFF and content[1] & 0xE0 == 0xE0)
    if mime_type in ("audio/wav", "audio/x-wav"):
        return content[:4] == b"RIFF" and content[8:12] == b"WAVE"
    if mime_type == "audio/ogg":
        return content.startswith(b"OggS")
    if mime_type in ("audio/mp4", "audio/x-m4a", "video/mp4", "video/quicktime"):
        return content[4:8] == b"ftyp"
    if mime_type == "video/webm":
        return content.startswith(b"\x1a\x45\xdf\xa3")
    return b"\x00" not in content  # text and .eml are plain text: no NUL bytes


def storage_root() -> Path:
    return BACKEND_DIR / settings.upload_dir  # an absolute upload_dir is used as it is


def add_attachment(
    db: Session,
    principal: Principal,
    complaint_id: int,
    *,
    file: BinaryIO,
    file_name: str,
    mime_type: str,
    description: str | None,
) -> AttachmentOut:
    complaint = find_editable(db, complaint_id)
    extension = EXTENSIONS.get(mime_type)
    if extension is None:
        raise ComplaintError(
            415, "file_type_not_allowed", "Attach an image (JPG, PNG, WebP), a PDF, audio (MP3, M4A, WAV, OGG), video (MP4, WebM, MOV), a text file or an email (.eml)."
        )

    in_use = db.scalar(
        select(func.count()).where(
            ComplaintAttachment.complaint_id == complaint.id, ComplaintAttachment.removed_at.is_(None)
        )
    )
    if in_use >= MAX_PER_COMPLAINT:
        raise ComplaintError(409, "too_many_files", f"A complaint can have at most {MAX_PER_COMPLAINT} files.")

    limit = MAX_VIDEO_BYTES if mime_type.startswith("video/") else MAX_AUDIO_BYTES if mime_type.startswith("audio/") else MAX_BYTES
    content = file.read(limit + 1)
    if not content:
        raise ComplaintError(422, "empty_file", "That file is empty.")
    if len(content) > limit:
        raise ComplaintError(413, "file_too_large", f"That kind of file can be at most {limit // MB} MB.")

    if not _matches_type(mime_type, content):
        raise ComplaintError(415, "file_type_mismatch", "That file's contents do not match its type.")

    stored = Path("complaints") / str(complaint.id) / f"{uuid4().hex}{extension}"
    target = storage_root() / stored
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)

    attachment = ComplaintAttachment(
        complaint_id=complaint.id,
        file_name=(Path(file_name).name or "file")[:200],
        storage_path=stored.as_posix(),
        mime_type=mime_type,
        size_bytes=len(content),
        description=(description or "").strip()[:200] or None,
        uploaded_by_user_id=principal.id,
    )
    db.add(attachment)
    db.flush()
    audit_service.record(
        db, principal, action="attachment.add", entity_type="complaint_attachments", entity_id=attachment.id,
        complaint_id=complaint.id, details={"file_name": attachment.file_name},
    )
    db.commit()
    return AttachmentOut.model_validate(attachment, from_attributes=True)


def remove_attachment(db: Session, principal: Principal, complaint_id: int, attachment_id: int) -> None:
    complaint = find_editable(db, complaint_id)
    attachment = db.scalar(
        select(ComplaintAttachment).where(
            ComplaintAttachment.id == attachment_id,
            ComplaintAttachment.complaint_id == complaint.id,
            ComplaintAttachment.removed_at.is_(None),
        )
    )
    if attachment is None:
        raise ComplaintError(404, "not_found", "That file does not exist.")
    attachment.removed_at = datetime.now(LOCAL)
    audit_service.record(
        db, principal, action="attachment.remove", entity_type="complaint_attachments", entity_id=attachment.id,
        complaint_id=complaint.id, details={"file_name": attachment.file_name},
    )
    db.commit()

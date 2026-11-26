"""Admin edits the wording of the messages complainants receive (UC-AD, manage message templates).

There is one template per message and channel: MSG-1, MSG-2, MSG-3 and the verification code, each as a text
message and as an email. A template Admin never edited shows (and sends) the default wording of the messaging
service. Saving checks that the text only uses the placeholders that message offers.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import MessageChannel, MessageType
from app.models import MessageTemplate, User
from app.schemas.message_templates import TemplateBody, TemplateOut
from app.services import audit_service
from app.services.auth_service import Principal
from app.services.messaging_service import KINDS, REQUIRED, placeholders_in, template


class TemplateError(Exception):
    """A rule the request breaks; the route turns it into a clean HTTP error."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def _out(db: Session, t: MessageTemplate) -> TemplateOut:
    kind = KINDS[t.message_type]
    editor = db.get(User, t.updated_by_user_id) if t.updated_by_user_id else None
    return TemplateOut(
        message_type=t.message_type,
        channel=t.channel,
        label=kind.label,
        when=kind.when,
        placeholders=list(kind.placeholders),
        subject=t.subject,
        body=t.body,
        is_active=t.is_active,
        can_switch_off=t.message_type not in REQUIRED,
        edited=t.id is not None,
        updated_at=t.updated_at,
        updated_by=editor.full_name if editor else None,
    )


def list_templates(db: Session) -> list[TemplateOut]:
    return [_out(db, template(db, kind, channel)) for kind in KINDS for channel in MessageChannel]


def _check(message_type: MessageType, subject: str | None, body: str) -> None:
    """The subject and body may use only the placeholders this message offers, and the body must hold any it needs."""
    allowed = KINDS[message_type].placeholders
    try:
        names = placeholders_in(subject or "") | placeholders_in(body)
    except ValueError:
        raise TemplateError(
            422, "bad_braces", "Use { and } only around a placeholder, for example {reference_number}."
        ) from None
    unknown = sorted(names - set(allowed))
    if unknown:
        offered = ", ".join(f"{{{name}}}" for name in allowed)
        raise TemplateError(422, "unknown_placeholder", f"{{{unknown[0]}}} cannot be used here. Use only {offered}.")
    needed = REQUIRED.get(message_type)
    if needed and needed not in placeholders_in(body):
        raise TemplateError(422, "missing_placeholder", f"The text must contain {{{needed}}}.")


def save_template(
    db: Session, admin: Principal, message_type: MessageType, channel: MessageChannel, data: TemplateBody
) -> TemplateOut:
    email = channel is MessageChannel.EMAIL
    subject = ((data.subject or "").strip() or None) if email else None
    body = data.body.strip()
    if email and subject is None:
        raise TemplateError(422, "subject_required", "An email needs a subject.")
    if not data.is_active and message_type in REQUIRED:
        raise TemplateError(
            422, "always_on", "The verification code is needed to sign up and to reset a password, so it stays on."
        )
    _check(message_type, subject, body)

    saved = db.scalar(
        select(MessageTemplate)
        .where(MessageTemplate.message_type == message_type, MessageTemplate.channel == channel)
        .with_for_update()
    )
    before = saved or template(db, message_type, channel)  # the default wording until it is first saved
    changed = {
        field: {"from": getattr(before, field), "to": value}
        for field, value in (("subject", subject), ("body", body), ("is_active", data.is_active))
        if getattr(before, field) != value
    }
    if saved is None:
        saved = MessageTemplate(message_type=message_type, channel=channel)
        db.add(saved)
    saved.subject, saved.body, saved.is_active = subject, body, data.is_active
    saved.updated_by_user_id = admin.id
    db.flush()
    if changed:
        audit_service.record(
            db, admin, action="message_template.update", entity_type="message_templates", entity_id=saved.id,
            details={"message_type": message_type.value, "channel": channel.value, "changed": changed},
        )
    db.commit()
    db.refresh(saved)
    return _out(db, saved)

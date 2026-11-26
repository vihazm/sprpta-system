"""Messages to complainants (System Flow Document 5.2): MSG-1, MSG-2, MSG-3 and the one-time code.

The text of each message comes from its template, which Admin can edit. A template that was never edited uses the
default wording below, so nothing has to be seeded.

Delivery: email goes out through SMTP when SMTP_* is set in backend/.env. Until an SMS gateway (and SMTP) is
connected, a message is printed in the backend terminal instead. Printing is only allowed in development; anywhere
else the message is logged as failed. Every attempt is written to outbound_messages, and a message that could not
be sent never holds up the case.
"""

import html
from dataclasses import dataclass
from string import Formatter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import MessageChannel, MessageState, MessageType
from app.models import Complaint, MessageTemplate, OutboundMessage
from app.services import email_sender


@dataclass(frozen=True)
class Kind:
    label: str  # as Admin and the terminal see it
    when: str
    placeholders: tuple[str, ...]  # the only {names} its text may use
    subject: str  # the default email subject
    sms: str  # the default text message
    email: str  # the default email text


KINDS: dict[MessageType, Kind] = {
    MessageType.REGISTERED: Kind(
        label="MSG-1 Registered",
        when="When the complaint gets its reference number (forwarded or kept as incomplete).",
        placeholders=("reference_number",),
        subject="Your complaint {reference_number} is registered",
        sms="SPRPTA: your complaint is registered. Reference {reference_number}.",
        email="Your complaint to SPRPTA is registered.\n\nReference number: {reference_number}\n\n"
        "Keep this number to follow your complaint.",
    ),
    MessageType.DECIDED: Kind(
        label="MSG-2 Decided",
        when="When the officer creates the solution document.",
        placeholders=("reference_number", "solution_text"),
        subject="A decision on your complaint {reference_number}",
        sms="SPRPTA: a decision was made on complaint {reference_number}. {solution_text}",
        email="A decision was made on your complaint {reference_number}.\n\n{solution_text}",
    ),
    MessageType.CLOSED: Kind(
        label="MSG-3 Closed",
        when="When the case is approved and closed.",
        placeholders=("reference_number",),
        subject="Your complaint {reference_number} is closed",
        sms="SPRPTA: complaint {reference_number} is closed. Thank you for helping us improve our service.",
        email="Your complaint {reference_number} has been dealt with and is now closed.\n\n"
        "Thank you for telling us. Complaints and suggestions help us improve our service.",
    ),
    MessageType.OTP: Kind(
        label="Verification code",
        when="When someone signs up or resets a forgotten password.",
        placeholders=("code", "minutes"),
        subject="Your SPRPTA verification code",
        sms="Your SPRPTA verification code is {code}. It works for {minutes} minutes.",
        email="Your SPRPTA verification code is {code}.\n\nIt works for {minutes} minutes. "
        "If you did not ask for it, you can ignore this email.",
    ),
}
REQUIRED = {MessageType.OTP: "code"}  # a code message without the code would be useless
SIGNATURE = "Southern Provincial Road Passenger Transport Authority"


# ---------------------------------------------------------------- templates


def placeholders_in(text: str) -> set[str]:
    """The {names} a text uses. Raises ValueError when its braces do not pair up."""
    return {name for _, name, _, _ in Formatter().parse(text) if name is not None}


def template(db: Session, message_type: MessageType, channel: MessageChannel) -> MessageTemplate:
    """The saved template, or (when Admin never edited it) an unsaved one holding the default wording."""
    saved = db.scalar(
        select(MessageTemplate).where(MessageTemplate.message_type == message_type, MessageTemplate.channel == channel)
    )
    if saved is not None:
        return saved
    kind = KINDS[message_type]
    email = channel is MessageChannel.EMAIL
    return MessageTemplate(
        message_type=message_type,
        channel=channel,
        subject=kind.subject if email else None,
        body=kind.email if email else kind.sms,
        is_active=True,
    )


def _fill(text: str, values: dict[str, str]) -> str:
    return text.format_map(values)


# ---------------------------------------------------------------- delivery


def _email_html(text: str) -> str:
    paragraphs = "".join(
        f'<p style="margin:0 0 1rem">{html.escape(p).replace(chr(10), "<br>")}</p>' for p in text.split("\n\n")
    )
    return (
        '<div style="font-family:Arial,sans-serif;max-width:32rem;color:#16181d">'
        '<p style="margin:0 0 .75rem;font-size:.8rem;letter-spacing:.08em;color:#b3112f;font-weight:bold">SPRPTA</p>'
        f"{paragraphs}"
        f'<p style="margin:0;color:#5b6574;font-size:.85rem">{SIGNATURE}</p>'
        "</div>"
    )


def _deliver(channel: MessageChannel, recipient: str, subject: str | None, text: str, label: str) -> str | None:
    """Send one message. Returns None when it went out, or a short reason when it did not."""
    if channel is MessageChannel.EMAIL and settings.email_configured:
        try:
            email_sender.send_email(recipient, subject or "SPRPTA", f"{text}\n\n{SIGNATURE}", _email_html(text))
        except email_sender.EmailError as exc:
            return str(exc)
        return None
    if settings.is_development:
        # Console mode: the message appears in the backend terminal (SMS for now, and email until SMTP is set up).
        if channel is MessageChannel.EMAIL:
            print("[SPRPTA] No email was sent: SMTP_HOST and SMTP_USER are not set in backend/.env.", flush=True)
        heading = f" | {subject}" if subject else ""
        print(f"[SPRPTA {label}] {channel.value} to {recipient}{heading}\n    {text}", flush=True)
        return None
    return "No SMS or email provider is connected."


def send_code(
    db: Session, account_id: int, channel: MessageChannel, recipient: str, code: str, label: str
) -> str | None:
    """Send a one-time code and log it with the code masked. Returns None when sent, or why it was not.

    The code message is always sent, even if its template was switched off: sign-up and password reset need it.
    """
    t = template(db, MessageType.OTP, channel)
    values = {"code": code, "minutes": str(settings.otp_minutes)}
    error = _deliver(channel, recipient, t.subject and _fill(t.subject, values), _fill(t.body, values), label)
    db.add(
        OutboundMessage(
            complainant_account_id=account_id,
            message_type=MessageType.OTP,
            channel=channel,
            recipient=recipient,
            body=_fill(t.body, {**values, "code": "******"}),
            state=MessageState.FAILED if error else MessageState.SENT,
            error_detail=error,
        )
    )
    return error


def send_case_message(db: Session, complaint: Complaint, message_type: MessageType, **values: str) -> None:
    """Send MSG-1, MSG-2 or MSG-3 for a case, once, and commit the log row.

    Called after the change that triggers it is saved, so a message never goes out for a change that was undone.
    It is skipped when no phone or email is on record, when Admin switched the message off, or when it was already
    sent. A text message goes to the phone when there is one, otherwise an email goes to the email address.
    """
    recipient = complaint.contact_phone or complaint.contact_email
    if recipient is None or complaint.id in sent_to(db, [complaint.id], message_type):
        return
    channel = MessageChannel.SMS if complaint.contact_phone else MessageChannel.EMAIL
    t = template(db, message_type, channel)
    if not t.is_active:
        return
    values = {"reference_number": complaint.reference_number or "", **values}
    text = _fill(t.body, values)
    error = _deliver(channel, recipient, t.subject and _fill(t.subject, values), text, KINDS[message_type].label)
    db.add(
        OutboundMessage(
            complaint_id=complaint.id,
            message_type=message_type,
            channel=channel,
            recipient=recipient,
            body=text,
            state=MessageState.FAILED if error else MessageState.SENT,
            error_detail=error,
        )
    )
    db.commit()


def sent_to(db: Session, complaint_ids: list[int], message_type: MessageType) -> set[int]:
    """Which of these complaints were sent this message."""
    if not complaint_ids:
        return set()
    return set(
        db.scalars(
            select(OutboundMessage.complaint_id).where(
                OutboundMessage.complaint_id.in_(complaint_ids),
                OutboundMessage.message_type == message_type,
                OutboundMessage.state == MessageState.SENT,
            )
        )
    )

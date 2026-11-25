"""Sends email through an SMTP server (any provider: Gmail, Outlook, the authority's own mail server).

Settings come from backend/.env (SMTP_*). Only Python's standard library is used. A failure raises EmailError with a
short reason that is safe to store in the message log; the password is never part of it.
"""

import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


class EmailError(Exception):
    """The mail server could not be reached or refused the message."""


def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    if html:
        message.add_alternative(html, subtype="html")

    try:
        if settings.smtp_ssl:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15)
        with server:
            if not settings.smtp_ssl:
                server.starttls(context=ssl.create_default_context())
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
    except smtplib.SMTPAuthenticationError:
        raise EmailError("The mail server refused the SMTP user name or password.") from None
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailError(f"The mail server could not send the message ({type(exc).__name__}).") from None

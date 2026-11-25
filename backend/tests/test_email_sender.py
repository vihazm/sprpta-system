"""The SMTP sender, with the mail server replaced by a fake."""

import smtplib

import pytest

from app.core.config import settings
from app.services import email_sender


class FakeServer:
    log: list = []
    fail_login = False

    def __init__(self, host, port, timeout=None, context=None):
        self.log = FakeServer.log
        self.log.append(("connect", host, port))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.log.append(("starttls",))

    def login(self, user, password):
        if FakeServer.fail_login:
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")
        self.log.append(("login", user))

    def send_message(self, message):
        self.log.append(("send", message["To"], message["Subject"], message["From"]))


@pytest.fixture
def smtp(monkeypatch):
    FakeServer.log = []
    FakeServer.fail_login = False
    monkeypatch.setattr(smtplib, "SMTP", FakeServer)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeServer)
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_user", "sprpta@test.example")
    monkeypatch.setattr(settings, "smtp_password", "secret-app-password")
    monkeypatch.setattr(settings, "smtp_from", "SPRPTA <sprpta@test.example>")
    monkeypatch.setattr(settings, "smtp_ssl", False)
    return FakeServer


def test_the_message_is_sent_over_starttls_after_logging_in(smtp):
    email_sender.send_email("client@example.com", "Hello", "Body", "<p>Body</p>")
    assert smtp.log == [
        ("connect", "smtp.test", 587),
        ("starttls",),
        ("login", "sprpta@test.example"),
        ("send", "client@example.com", "Hello", "SPRPTA <sprpta@test.example>"),
    ]


def test_a_wrong_password_is_reported_without_the_password(smtp):
    smtp.fail_login = True
    with pytest.raises(email_sender.EmailError) as caught:
        email_sender.send_email("client@example.com", "Hello", "Body")
    assert "user name or password" in str(caught.value)
    assert "secret-app-password" not in str(caught.value)


def test_an_unreachable_server_is_an_email_error(monkeypatch, smtp):
    def refuse(*args, **kwargs):
        raise ConnectionRefusedError("no route")

    monkeypatch.setattr(smtplib, "SMTP", refuse)
    with pytest.raises(email_sender.EmailError):
        email_sender.send_email("client@example.com", "Hello", "Body")


def test_email_counts_as_set_up_only_with_a_host_and_a_sender(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "")
    assert not settings.email_configured
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(settings, "smtp_user", "")
    monkeypatch.setattr(settings, "smtp_from", "")
    assert not settings.email_configured
    monkeypatch.setattr(settings, "smtp_from", "sprpta@test.example")
    assert settings.email_configured

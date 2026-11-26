"""Messages to complainants (MSG-1, MSG-2) and the templates Admin edits."""

from sqlalchemy import select

from app.core.enums import MessageState, MessageType
from app.core.roles import UserRole
from app.models import AuditLog, Complaint, OutboundMessage
from tests.conftest import make_user, sign_in
from tests.test_l1_complaints import URL as L1_URL
from tests.test_l1_complaints import form, lists  # noqa: F401  (lists is a fixture)
from tests.test_l2_cases import URL as L2_URL
from tests.test_l2_cases import area, decide, forwarded  # noqa: F401  (area is a fixture)

TEMPLATES = "/api/admin/message-templates"


def messages(db, message_type=None) -> list[OutboundMessage]:
    db.expire_all()
    query = select(OutboundMessage).where(OutboundMessage.complaint_id.is_not(None)).order_by(OutboundMessage.id)
    if message_type:
        query = query.where(OutboundMessage.message_type == message_type)
    return list(db.scalars(query))


def save(client, message_type, channel, **body):
    return client.put(f"{TEMPLATES}/{message_type}/{channel}", json=body)


def as_admin(client, db):
    make_user(db, "admin@sprpta.test", UserRole.ADMIN, full_name="System Admin")
    sign_in(client, "admin@sprpta.test")


# ---------------------------------------------------------------- MSG-1 and MSG-2


def test_forwarding_sends_the_registration_message_once(client, db, lists, capsys):
    draft = client.post(L1_URL, json=form(lists)).json()
    kept = client.post(f"{L1_URL}/{draft['id']}/incomplete").json()
    assert kept["registration_message_sent"] is True
    client.post(f"{L1_URL}/{draft['id']}/forward")

    [sent] = messages(db)
    assert sent.message_type == MessageType.REGISTERED and sent.state == MessageState.SENT
    assert sent.channel.value == "sms" and sent.recipient == "+94771234567"  # the phone wins over the email
    assert kept["reference_number"] in sent.body
    out = capsys.readouterr().out
    assert "[SPRPTA MSG-1 Registered] sms to +94771234567" in out and kept["reference_number"] in out


def test_no_contact_means_no_message(client, db, lists):
    draft = client.post(L1_URL, json=form(lists, is_anonymous=True)).json()
    forwarded_case = client.post(f"{L1_URL}/{draft['id']}/forward").json()
    assert forwarded_case["status"] == "forwarded" and forwarded_case["registration_message_sent"] is False
    assert messages(db) == []


def test_an_email_only_complainant_is_emailed(client, db, lists, capsys):
    draft = client.post(L1_URL, json=form(lists, mobile=None)).json()
    client.post(f"{L1_URL}/{draft['id']}/forward")
    [sent] = messages(db)
    assert sent.channel.value == "email" and sent.recipient == "kamala@example.lk"
    assert "is registered" in capsys.readouterr().out


def test_the_solution_document_sends_the_decision_with_the_solution(client, db, area):
    case = forwarded(db, area)
    decide(client, case.id)
    body = {"summary": "Reckless overtaking.", "solution_details": "The driver is suspended for 3 days."}
    assert client.post(f"{L2_URL}/{case.id}/solution-document", json=body).status_code == 201

    [sent] = messages(db, MessageType.DECIDED)
    assert sent.state == MessageState.SENT and "The driver is suspended for 3 days." in sent.body
    assert case.reference_number in sent.body


# ---------------------------------------------------------------- the templates


def test_admin_sees_every_message_with_its_default_wording(client, db):
    as_admin(client, db)
    listed = client.get(TEMPLATES).json()
    assert len(listed) == 8  # four messages, each as a text message and an email
    first = listed[0]
    assert first["label"] == "MSG-1 Registered" and first["channel"] == "sms" and not first["edited"]
    assert "{reference_number}" in first["body"] and first["placeholders"] == ["reference_number"]
    email = listed[1]
    assert email["channel"] == "email" and email["subject"]


def test_an_edited_template_is_used_and_audited(client, db, lists):
    as_admin(client, db)
    saved = save(client, "registered", "sms", body="Hello! Your case number is {reference_number}.")
    assert saved.status_code == 200 and saved.json()["edited"] and saved.json()["updated_by"] == "System Admin"
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "message_template.update"))
    assert audit.details["changed"]["body"]["to"] == "Hello! Your case number is {reference_number}."

    sign_in(client, "office@sprpta.test")
    draft = client.post(L1_URL, json=form(lists)).json()
    reference = client.post(f"{L1_URL}/{draft['id']}/forward").json()["reference_number"]
    assert messages(db)[0].body == f"Hello! Your case number is {reference}."


def test_a_switched_off_message_is_not_sent(client, db, lists):
    as_admin(client, db)
    save(client, "registered", "sms", body="Reference {reference_number}.", is_active=False)
    sign_in(client, "office@sprpta.test")
    draft = client.post(L1_URL, json=form(lists)).json()
    client.post(f"{L1_URL}/{draft['id']}/forward")
    assert messages(db) == []
    assert db.scalar(select(Complaint.status)) == "forwarded"


def test_a_template_may_use_only_its_own_placeholders(client, db):
    as_admin(client, db)
    refused = {
        "unknown_placeholder": save(client, "registered", "sms", body="Solved: {solution_text}"),
        "bad_braces": save(client, "registered", "sms", body="Reference {reference_number"),
        "missing_placeholder": save(client, "otp", "sms", body="Your code is coming."),
        "subject_required": save(client, "closed", "email", body="Closed.", subject=" "),
        "always_on": save(client, "otp", "sms", body="Code {code}", is_active=False),
    }
    for code, response in refused.items():
        assert response.status_code == 422 and response.json()["detail"]["code"] == code, code


def test_the_code_message_uses_its_template(client, db, capsys):
    as_admin(client, db)
    save(client, "otp", "email", subject="Your code", body="Use {code} within {minutes} minutes.")
    client.post("/api/auth/logout")
    client.post("/api/auth/signup", json={"name": "Nimali", "identifier": "nimali@sprpta.test", "password": "long-enough-1"})
    out = capsys.readouterr().out
    assert "Use " in out and "within 10 minutes." in out
    logged = db.scalar(select(OutboundMessage).where(OutboundMessage.message_type == MessageType.OTP))
    assert logged.body == "Use ****** within 10 minutes."


def test_only_admin_may_edit_templates(client, db, lists):
    assert client.get(TEMPLATES).status_code == 403  # signed in as Level 1
    assert save(client, "registered", "sms", body="x {reference_number}").status_code == 403

"""Request and response shapes of the message templates screen (UC-AD, manage message templates)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.core.enums import MessageChannel, MessageType
from app.schemas.admin_users import NoNul

Text = Annotated[str, NoNul]


class TemplateOut(BaseModel):
    message_type: MessageType
    channel: MessageChannel
    label: str  # for example "MSG-1 Registered"
    when: str  # when the system sends it
    placeholders: list[str]  # the {names} its text may use
    subject: str | None  # email only
    body: str
    is_active: bool
    can_switch_off: bool  # the verification code is always sent
    edited: bool  # False while it still has the default wording
    updated_at: datetime | None
    updated_by: str | None


class TemplateBody(BaseModel):
    subject: Text | None = Field(default=None, max_length=200)  # ignored for text messages
    body: Text = Field(min_length=1, max_length=2000, pattern=r"\S")
    is_active: bool = True

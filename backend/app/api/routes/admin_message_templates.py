"""Message templates: /api/admin/message-templates (admin only)."""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deps import error, get_current_principal, require_roles
from app.core.enums import MessageChannel, MessageType
from app.db.session import get_db
from app.schemas.message_templates import TemplateBody, TemplateOut
from app.services import message_template_service as templates
from app.services.auth_service import Principal
from app.services.message_template_service import TemplateError

router = APIRouter(
    prefix="/api/admin/message-templates", tags=["admin"], dependencies=[Depends(require_roles("admin"))]
)


def _fail(exc: TemplateError) -> HTTPException:
    return error(exc.status, exc.code, exc.message)


@router.get("", response_model=list[TemplateOut])
def list_templates(response: Response, db: Session = Depends(get_db)) -> list[TemplateOut]:
    response.headers["Cache-Control"] = "no-store"
    return templates.list_templates(db)


@router.put("/{message_type}/{channel}", response_model=TemplateOut)
def save_template(
    message_type: MessageType,
    channel: MessageChannel,
    body: TemplateBody,
    admin: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> TemplateOut:
    try:
        return templates.save_template(db, admin, message_type, channel, body)
    except TemplateError as exc:
        raise _fail(exc) from None

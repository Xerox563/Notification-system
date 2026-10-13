from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models import Template
from app.schemas.template import TemplateCreate, TemplateOut
from app.services.notification_service import find_template
from app.services.template_service import extract_variables

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("", response_model=TemplateOut, status_code=201)
async def create_template(data: TemplateCreate, session: AsyncSession = Depends(get_session)):
    template = Template(
        name=data.name,
        channel=data.channel.value,
        subject=data.subject,
        body=data.body,
        variables=extract_variables(data.subject, data.body),
    )
    session.add(template)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "a template with this name already exists") from None
    return template


@router.get("", response_model=list[TemplateOut])
async def list_templates(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Template).order_by(Template.name))
    return list(result.scalars())


@router.get("/{name}", response_model=TemplateOut)
async def get_template(name: str, session: AsyncSession = Depends(get_session)):
    return await find_template(session, name)

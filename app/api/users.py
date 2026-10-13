from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.constants import Channel
from app.models import User
from app.schemas.user import PreferenceIn, PreferenceOut, UserCreate, UserOut
from app.services import preference_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=201)
async def create_user(data: UserCreate, session: AsyncSession = Depends(get_session)):
    user = User(**data.model_dump())
    session.add(user)
    await session.commit()
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: str, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(404, "user not found")
    return user


@router.put("/{user_id}/preferences/{channel}", response_model=PreferenceOut)
async def set_preference(
    user_id: str, channel: Channel, data: PreferenceIn, session: AsyncSession = Depends(get_session)
):
    pref = await preference_service.set_preference(session, user_id, channel.value, data)
    return PreferenceOut(channel=channel, enabled=pref.enabled, quiet_start=pref.quiet_start, quiet_end=pref.quiet_end)


@router.get("/{user_id}/preferences", response_model=list[PreferenceOut])
async def list_preferences(user_id: str, session: AsyncSession = Depends(get_session)):
    prefs = await preference_service.list_preferences(session, user_id)
    return [
        PreferenceOut(channel=p.channel, enabled=p.enabled, quiet_start=p.quiet_start, quiet_end=p.quiet_end)
        for p in prefs
    ]

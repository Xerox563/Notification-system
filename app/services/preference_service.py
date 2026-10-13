from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserPreference
from app.schemas.user import PreferenceIn
from app.services.errors import NotFoundError


async def get_preference(session: AsyncSession, user_id: str, channel: str) -> UserPreference | None:
    result = await session.execute(
        select(UserPreference).where(UserPreference.user_id == user_id, UserPreference.channel == channel)
    )
    return result.scalar_one_or_none()


async def list_preferences(session: AsyncSession, user_id: str) -> list[UserPreference]:
    if await session.get(User, user_id) is None:
        raise NotFoundError("user not found")
    result = await session.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    return list(result.scalars())


async def set_preference(
    session: AsyncSession, user_id: str, channel: str, data: PreferenceIn
) -> UserPreference:
    if await session.get(User, user_id) is None:
        raise NotFoundError("user not found")
    pref = await get_preference(session, user_id, channel)
    if pref is None:
        pref = UserPreference(user_id=user_id, channel=channel)
        session.add(pref)
    pref.enabled = data.enabled
    pref.quiet_start = data.quiet_start
    pref.quiet_end = data.quiet_end
    await session.commit()
    return pref

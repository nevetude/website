from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from music_backend.enums import UserRole
from music_backend.models import AppUser


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def current_user(request: Request, session: SessionDep) -> AppUser:
    """The single place that decides who is calling. Real login (cookie or Bearer) replaces the body."""
    if not request.app.state.settings.dev_auto_login:
        raise HTTPException(401, "Not authenticated")
    user = await session.scalar(select(AppUser).where(AppUser.login == "admin"))
    if user is None:
        # "!" is not a valid hash, so this account cannot log in until real auth sets a password.
        user = AppUser(login="admin", password_hash="!", role=UserRole.ADMIN)  # noqa: S106
        session.add(user)
        await session.commit()
    return user


async def require_editor(user: Annotated[AppUser, Depends(current_user)]) -> AppUser:
    if user.role not in (UserRole.EDITOR, UserRole.ADMIN):
        raise HTTPException(403, "Editor role required")
    return user


UserDep = Annotated[AppUser, Depends(current_user)]
EditorDep = Annotated[AppUser, Depends(require_editor)]

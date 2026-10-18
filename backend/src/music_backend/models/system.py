from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from music_backend.enums import RevisionAction, UserRole
from music_backend.models.base import (
    ORDER_TIMESTAMPS,
    Base,
    IdMixin,
    Timestamps,
    enum_column,
    fk,
)


class AppUser(Base, IdMixin, Timestamps):
    # Not "user": that is a reserved word in PostgreSQL.
    __tablename__ = "app_user"

    login: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    role: Mapped[UserRole] = enum_column(
        UserRole, default=UserRole.VIEWER, server_default=UserRole.VIEWER.value
    )


class UserSession(Base):
    __tablename__ = "user_session"

    token_hash: Mapped[str] = mapped_column(
        primary_key=True
    )  # hash of the cookie value, never the value
    user_id: Mapped[int] = fk("app_user", index=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), sort_order=ORDER_TIMESTAMPS
    )
    expires_at: Mapped[datetime]


class Revision(Base, IdMixin):
    """History of changes. Deliberately polymorphic: no foreign key to the changed entity."""

    __tablename__ = "revision"
    __table_args__ = (Index("ix_revision_entity", "entity_type", "entity_id"),)

    entity_type: Mapped[str]
    entity_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int | None] = fk("app_user", nullable=True)  # NULL means system
    action: Mapped[RevisionAction] = enum_column(RevisionAction)
    changes: Mapped[dict[str, Any]] = mapped_column(JSONB)  # {field: [old, new]}
    reason: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), sort_order=ORDER_TIMESTAMPS
    )

import re
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    MetaData,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedColumn, mapped_column

from music_backend.enums import ImportState

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map = {datetime: DateTime(timezone=True)}  # noqa: RUF012


def enum_column[E: StrEnum](enum: type[E], **kwargs: object) -> MappedColumn[E]:
    """Enum stored as text, not as a Postgres ENUM (painful to alter) and without a CHECK.

    The length leaves room for new values, so adding one needs no migration.
    """
    sa_enum = Enum(
        enum,
        name=re.sub(r"(?<!^)(?=[A-Z])", "_", enum.__name__).lower(),
        native_enum=False,
        length=40,
        values_callable=lambda e: [member.value for member in e],
    )
    return mapped_column(sa_enum, **kwargs)  # type: ignore[arg-type]


def fk(table: str, **kwargs: object) -> MappedColumn[int]:
    return mapped_column(BigInteger, ForeignKey(f"{table}.id"), **kwargs)  # type: ignore[arg-type]


# Column order, the same in every table (PostgreSQL cannot reorder columns later, only a rebuild can):
#   1. key and external id      2. name parts (name, variant, base_name, disambiguator)
#   3. type and import state    4. the entity's own columns (declaration order)
#   5. timestamps
# SQLAlchemy sorts columns by `sort_order` first, so mixins can place theirs anywhere.
ORDER_KEY, ORDER_EXTERNAL_ID, ORDER_NAME = -100, -90, -80  # -79 is left for `variant`
ORDER_TYPE, ORDER_STATE = -70, -60
ORDER_TIMESTAMPS = 900


class IdMixin:
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True, sort_order=ORDER_KEY)


class Timestamps:
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), sort_order=ORDER_TIMESTAMPS
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), sort_order=ORDER_TIMESTAMPS + 1
    )


class GeniusEntity:
    """Columns shared by artist, album and song."""

    genius_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, sort_order=ORDER_EXTERNAL_ID
    )
    import_state: Mapped[ImportState] = enum_column(
        ImportState,
        default=ImportState.FULL,
        server_default=ImportState.FULL.value,
        sort_order=ORDER_STATE,
    )


class Named:
    name: Mapped[str] = mapped_column(sort_order=ORDER_NAME)
    base_name: Mapped[str] = mapped_column(sort_order=ORDER_NAME + 2)
    disambiguator: Mapped[str | None] = mapped_column(sort_order=ORDER_NAME + 3)

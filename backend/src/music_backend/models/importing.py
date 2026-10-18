from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from music_backend.enums import ImportKind, JobStatus
from music_backend.models.base import (
    ORDER_TIMESTAMPS,
    Base,
    IdMixin,
    Timestamps,
    enum_column,
    fk,
)


class ImportJob(Base, IdMixin, Timestamps):
    __tablename__ = "import_job"
    __table_args__ = (
        # One active job per target: a second request returns the running one.
        Index(
            "uq_import_job_active_target",
            "kind",
            "genius_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
    )

    kind: Mapped[ImportKind] = enum_column(ImportKind)
    genius_id: Mapped[int] = mapped_column(BigInteger)
    subject_name: Mapped[
        str | None
    ]  # name of the imported entity, known once its first request is done
    albums_limit: Mapped[int | None]  # discography only: how many of the newest albums; empty = all
    status: Mapped[JobStatus] = enum_column(
        JobStatus, default=JobStatus.QUEUED, server_default=JobStatus.QUEUED.value
    )
    progress_done: Mapped[int] = mapped_column(server_default=text("0"))
    progress_total: Mapped[int | None]
    message: Mapped[str | None]  # what the job is doing right now
    error: Mapped[str | None]
    result_id: Mapped[int | None] = mapped_column(BigInteger)  # id of the imported entity
    created_by: Mapped[int | None] = fk("app_user", nullable=True)
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]


class ImportRequest(Base, IdMixin):
    """One request to Genius made by a job; kept for analysing 4XX responses."""

    __tablename__ = "import_request"

    job_id: Mapped[int] = mapped_column(ForeignKey("import_job.id", ondelete="CASCADE"), index=True)
    # The task the request was made for, as it was named when queued (kind and name are for reading).
    task_kind: Mapped[ImportKind | None] = enum_column(ImportKind, nullable=True)
    task_genius_id: Mapped[int | None] = mapped_column(BigInteger)
    task_name: Mapped[str | None]
    attempt: Mapped[int]  # 1 for the first try, then the retries
    url: Mapped[str]
    status_code: Mapped[int | None]  # NULL when the request never got a response
    elapsed_ms: Mapped[int]
    size_bytes: Mapped[int | None]
    error: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("now()"), sort_order=ORDER_TIMESTAMPS
    )


class GeniusResponse(Base, Timestamps):
    """The untouched Genius response an entity was last imported from, kept for replaying an import and
    for fields we do not store. A separate table (and not a column) keeps the entity rows small and
    needs no lazy loading. Polymorphic like `revision`: no foreign key to the entity."""

    __tablename__ = "genius_response"

    entity_type: Mapped[str] = mapped_column(primary_key=True)  # artist, album, song
    entity_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB)

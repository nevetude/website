from collections.abc import Sequence
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from music_backend.api.deps import EditorDep, SessionDep
from music_backend.api.schemas import Page
from music_backend.enums import ImportKind, JobStatus
from music_backend.imports.runner import ENTITY_MODEL, Progress
from music_backend.models import Album, Artist, ImportJob, ImportRequest, Song

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])

RECENT_REQUESTS = 10  # the short log shown on the job card


class ImportRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_kind: ImportKind | None
    task_genius_id: int | None
    task_name: str | None
    attempt: int
    url: str
    status_code: int | None
    elapsed_ms: int
    size_bytes: int | None
    error: str | None
    created_at: datetime
    # The Genius page of the task's entity once we have saved it; the client falls back to `url`.
    page_url: str | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: ImportKind
    genius_id: int
    name: str | None


class CountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: ImportKind
    done: int
    total: int


class ProgressOut(BaseModel):
    """A running job only. `units` and `items` have totals that never grow (see `Progress`)."""

    model_config = ConfigDict(from_attributes=True)

    root: TaskOut | None
    units: list[CountOut]
    unit: TaskOut | None
    items: list[CountOut]
    active: TaskOut | None


class ImportJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: ImportKind
    genius_id: int
    subject_name: str | None
    albums_limit: int | None
    status: JobStatus
    progress_done: int
    progress_total: int | None
    message: str | None
    error: str | None
    result_id: int | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    progress: ProgressOut | None = None
    requests_total: int = 0
    recent_requests: list[ImportRequestOut] = []


class ImportCreate(BaseModel):
    kind: ImportKind
    genius_id: int
    albums_limit: int | None = None  # discography only; empty = all albums


async def _requests_out(
    session: AsyncSession, rows: Sequence[ImportRequest]
) -> list[ImportRequestOut]:
    """The log rows with the page of each entity, looked up in a few queries for the whole batch."""
    ids: dict[type[Artist] | type[Album] | type[Song], set[int]] = {}
    for row in rows:
        if row.task_kind is not None and row.task_genius_id is not None:
            ids.setdefault(ENTITY_MODEL[row.task_kind], set()).add(row.task_genius_id)
    urls: dict[tuple[type[Artist] | type[Album] | type[Song], int | None], str | None] = {}
    for model, genius_ids in ids.items():
        result = await session.execute(
            select(model.genius_id, model.genius_url).where(model.genius_id.in_(genius_ids))
        )
        urls.update({(model, genius_id): url for genius_id, url in result})
    out = [ImportRequestOut.model_validate(row) for row in rows]
    for item in out:
        if item.task_kind is not None and item.task_genius_id is not None:
            item.page_url = urls.get((ENTITY_MODEL[item.task_kind], item.task_genius_id))
    return out


async def _out(request: Request, session: AsyncSession, job: ImportJob) -> ImportJobOut:
    recent = await session.scalars(
        select(ImportRequest)
        .where(ImportRequest.job_id == job.id)
        .order_by(ImportRequest.id.desc())
        .limit(RECENT_REQUESTS)
    )
    out = ImportJobOut.model_validate(job)
    live: Progress | None = request.app.state.imports.live.get(job.id)
    out.progress = ProgressOut.model_validate(live) if live else None
    out.requests_total = (
        await session.scalar(
            select(func.count()).select_from(ImportRequest).where(ImportRequest.job_id == job.id)
        )
        or 0
    )
    out.recent_requests = await _requests_out(session, list(reversed(recent.all())))
    return out


async def _get_job(session: AsyncSession, job_id: int) -> ImportJob:
    job = await session.get(ImportJob, job_id)
    if job is None:
        raise HTTPException(404, "Import job not found")
    return job


@router.post("", status_code=202)
async def create_import(
    body: ImportCreate, request: Request, session: SessionDep, user: EditorDep
) -> ImportJobOut:
    job = await request.app.state.imports.submit(
        session, body.kind, body.genius_id, user.id, body.albums_limit
    )
    return await _out(request, session, job)


@router.get("")
async def list_imports(
    request: Request,
    session: SessionDep,
    _: EditorDep,
    active: bool = False,
    limit: int = 20,
) -> list[ImportJobOut]:
    query = select(ImportJob).order_by(ImportJob.id.desc()).limit(limit)
    if active:
        query = query.where(ImportJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))
    return [await _out(request, session, job) for job in await session.scalars(query)]


@router.get("/{job_id}")
async def get_import(
    job_id: int, request: Request, session: SessionDep, _: EditorDep
) -> ImportJobOut:
    return await _out(request, session, await _get_job(session, job_id))


@router.get("/{job_id}/requests")
async def list_import_requests(
    job_id: int,
    session: SessionDep,
    _: EditorDep,
    limit: int = 100,
    offset: int = 0,
    after_id: int = 0,
) -> Page[ImportRequestOut]:
    """Oldest first. `after_id` returns only newer requests, so a page that shows the log of a
    running job can ask for what is new instead of reloading everything."""
    await _get_job(session, job_id)
    total = await session.scalar(
        select(func.count()).select_from(ImportRequest).where(ImportRequest.job_id == job_id)
    )
    rows = await session.scalars(
        select(ImportRequest)
        .where(ImportRequest.job_id == job_id, ImportRequest.id > after_id)
        .order_by(ImportRequest.id)
        .limit(limit)
        .offset(offset)
    )
    return Page(
        items=await _requests_out(session, rows.all()),
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.post("/{job_id}/cancel")
async def cancel_import(
    job_id: int, request: Request, session: SessionDep, _: EditorDep
) -> ImportJobOut:
    job = await _get_job(session, job_id)
    if not await request.app.state.imports.cancel(job_id):
        raise HTTPException(409, "Job is not running")
    await session.refresh(job)
    return await _out(request, session, job)

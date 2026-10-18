import asyncio
import logging
from dataclasses import asdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from music_backend.enums import ImportKind, JobStatus
from music_backend.imports.common import Context, Task
from music_backend.imports.runner import ENTITY_MODEL, Progress, run_tasks
from music_backend.models import ImportJob, ImportRequest

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from music_backend.imports.client import GeniusClient, RequestLog

log = logging.getLogger(__name__)

ACTIVE = (JobStatus.QUEUED, JobStatus.RUNNING)


def _now() -> datetime:
    return datetime.now(UTC)


class ImportManager:
    """Runs import jobs in the background of the API process, one at a time."""

    def __init__(
        self, sessionmaker: async_sessionmaker[AsyncSession], client: GeniusClient
    ) -> None:
        self._sessionmaker = sessionmaker
        self._client = client
        self._tasks: dict[int, asyncio.Task[None]] = {}
        # In memory only: the totals are fixed and cheap to rebuild, and a restart ends the job anyway.
        self.live: dict[int, Progress] = {}
        self._one_at_a_time = asyncio.Semaphore(1)

    async def recover(self) -> None:
        """Jobs that were active when the server stopped can never finish: close them."""
        async with self._sessionmaker() as session:
            await session.execute(
                update(ImportJob)
                .where(ImportJob.status.in_(ACTIVE))
                .values(
                    status=JobStatus.FAILED,
                    error="Interrupted by a server restart",
                    finished_at=_now(),
                )
            )
            await session.commit()

    async def submit(
        self,
        session: AsyncSession,
        kind: ImportKind,
        genius_id: int,
        user_id: int | None,
        albums_limit: int | None = None,
    ) -> ImportJob:
        """Create a job and start it; if one is already active for this target, return that one."""
        job = ImportJob(
            kind=kind, genius_id=genius_id, albums_limit=albums_limit, created_by=user_id
        )
        session.add(job)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return await session.scalar(
                select(ImportJob).where(
                    ImportJob.kind == kind,
                    ImportJob.genius_id == genius_id,
                    ImportJob.status.in_(ACTIVE),
                )
            )  # type: ignore[return-value]
        self._tasks[job.id] = asyncio.create_task(self._run(job.id))
        return job

    async def cancel(self, job_id: int) -> bool:
        """Cancel an active job; False when it is not running in this process."""
        task = self._tasks.get(job_id)
        if task is None or task.done():
            return False
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        # A task cancelled before its first step never runs its own handler, so close the job here too.
        await self._set_if_active(
            job_id, status=JobStatus.CANCELLED, finished_at=_now(), message="Cancelled"
        )
        return True

    async def shutdown(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)

    async def _record(self, job_id: int, entry: RequestLog) -> None:
        # Own session and commit: the log must be visible to polling clients while the job runs.
        async with self._sessionmaker() as session:
            session.add(ImportRequest(job_id=job_id, **asdict(entry)))
            await session.commit()

    async def _set(self, job_id: int, **values: object) -> None:
        async with self._sessionmaker() as session:
            await session.execute(update(ImportJob).where(ImportJob.id == job_id).values(**values))
            await session.commit()

    async def _set_if_active(self, job_id: int, **values: object) -> None:
        async with self._sessionmaker() as session:
            await session.execute(
                update(ImportJob)
                .where(ImportJob.id == job_id, ImportJob.status.in_(ACTIVE))
                .values(**values)
            )
            await session.commit()

    async def _run(self, job_id: int) -> None:
        try:
            await self._run_job(job_id)
        finally:
            self.live.pop(job_id, None)

    async def _run_job(self, job_id: int) -> None:
        try:
            async with self._one_at_a_time:
                await self._set(
                    job_id, status=JobStatus.RUNNING, started_at=_now(), message="Starting"
                )
                result_id, failures = await self._execute(job_id)
            await self._set(
                job_id,
                status=JobStatus.SUCCEEDED,
                finished_at=_now(),
                message=f"Done, {len(failures)} failed" if failures else "Done",
                error="; ".join(failures[:5]) or None,
                result_id=result_id,
            )
        except asyncio.CancelledError:
            await asyncio.shield(
                self._set(
                    job_id, status=JobStatus.CANCELLED, finished_at=_now(), message="Cancelled"
                )
            )
        except Exception as error:
            log.exception("import job %s crashed", job_id)
            await self._set(job_id, status=JobStatus.FAILED, finished_at=_now(), error=str(error))

    async def _execute(self, job_id: int) -> tuple[int | None, list[str]]:
        async with self._sessionmaker() as session:
            job = await session.get_one(ImportJob, job_id)
            root = Task(job.kind, job.genius_id, limit=job.albums_limit)

        async def record(entry: RequestLog) -> None:
            await self._record(job_id, entry)

        async def on_progress(state: Progress) -> None:
            self.live[job_id] = state
            active = state.active
            subject = {"subject_name": state.root.name} if state.root and state.root.name else {}
            await self._set(
                job_id,
                **subject,
                progress_done=state.done,
                progress_total=state.total,
                message=f"{active.kind.value} {active.name or active.genius_id}"
                if active
                else "Done",
            )

        failures = await run_tasks(
            self._sessionmaker, Context(self._client, record), root, on_progress
        )
        model = ENTITY_MODEL[root.kind]
        async with self._sessionmaker() as session:
            result_id = await session.scalar(
                select(model.id).where(model.genius_id == root.genius_id)
            )
        return result_id, failures

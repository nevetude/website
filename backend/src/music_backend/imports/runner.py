import asyncio
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from sqlalchemy import select

from music_backend.enums import ImportKind
from music_backend.imports.album import handle_album
from music_backend.imports.artist import handle_artist, handle_discography
from music_backend.imports.client import RateLimitedError
from music_backend.imports.song import handle_song
from music_backend.models import Album, Artist, Song

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from music_backend.imports.common import Context, Handler, Task


log = logging.getLogger(__name__)

# Entities handled at the same time. A request waits ~0.8 s for its answer, so this many keep the
# client's request interval (`genius_min_interval_s`) full; more would only queue behind it.
WORKERS = 4

HANDLERS: dict[ImportKind, Handler] = {
    ImportKind.DISCOGRAPHY: handle_discography,
    ImportKind.ARTIST: handle_artist,
    ImportKind.ALBUM: handle_album,
    ImportKind.SONG: handle_song,
}
# The entity a task is "about": the name in the progress, `result_id` of a job, the page of a request.
ENTITY_MODEL: dict[ImportKind, type[Artist] | type[Album] | type[Song]] = {
    ImportKind.DISCOGRAPHY: Artist,
    ImportKind.ARTIST: Artist,
    ImportKind.ALBUM: Album,
    ImportKind.SONG: Song,
}


@dataclass(slots=True)
class Count:
    kind: ImportKind
    done: int = 0
    total: int = 0


@dataclass(slots=True)
class Progress:
    """What a client sees while a job runs. Only two levels are counted, because only those totals
    are known in advance and never grow:

    - `units`: the things the first task found (a discography: the artist and every album);
    - `items`: what the current unit found when it was read (an album: its songs, artists, ...).

    Everything deeper (the artists of a song, ...) is imported as part of its item and only shows as
    `active`.
    """

    root: Task | None = None
    units: list[Count] = field(default_factory=list)
    unit: Task | None = None
    items: list[Count] = field(default_factory=list)
    active: Task | None = None

    @property
    def done(self) -> int:
        return sum(c.done for c in self.units)

    @property
    def total(self) -> int | None:
        return sum(c.total for c in self.units) if self.units else None


type OnProgress = Callable[[Progress], Awaitable[None]]


def _counts(tasks: list[Task], done: int = 0) -> list[Count]:
    counts: dict[ImportKind, Count] = {}
    for task in tasks:
        counts.setdefault(task.kind, Count(task.kind)).total += 1
    if done and tasks:
        counts[tasks[0].kind].done = done
    return list(counts.values())


def _bump(counts: list[Count], kind: ImportKind) -> None:
    next(c for c in counts if c.kind is kind).done += 1


async def _name_of(sessionmaker: async_sessionmaker[AsyncSession], task: Task) -> str | None:
    model = ENTITY_MODEL[task.kind]
    async with sessionmaker() as session:
        name: str | None = await session.scalar(
            select(model.name).where(model.genius_id == task.genius_id)
        )
    return name


async def run_tasks(
    sessionmaker: async_sessionmaker[AsyncSession],
    ctx: Context,
    root: Task,
    on_progress: OnProgress,
    workers: int = WORKERS,
) -> list[str]:
    """Process `root` and everything the handlers queue, each entity once.

    One entity is one transaction: stopping (cancel, crash, restart) keeps everything already
    finished and loses only the entity being written. A failure of the root task raises; a failure
    of any other task is logged and returned, and the run goes on.

    The root's children are the job's units and are done one after another, each with its whole
    surroundings, so a stop leaves complete albums and not half of every album. The items of one unit
    (the songs of an album, ...) run in parallel, `workers` entities at a time, each item with its own
    surroundings depth first.
    """
    state = Progress(root=root)
    seen = {root.key}
    if root.kind is ImportKind.DISCOGRAPHY:
        seen.add((ImportKind.ARTIST, root.genius_id))  # imported by the root itself
    failures: list[str] = []
    slots = asyncio.Semaphore(workers)

    async def handle(task: Task) -> list[Task]:
        """Save one entity; the tasks it found, minus the ones already known."""
        state.active = task
        await on_progress(state)
        try:
            async with slots, sessionmaker() as session, session.begin():
                children = await HANDLERS[task.kind](ctx.for_task(task), session, task)
        except RateLimitedError:
            raise  # not a failure of this entity: the whole import stops here
        except Exception as error:
            if task is root:
                raise
            log.warning("import of %s %s failed: %r", task.kind.value, task.genius_id, error)
            failures.append(f"{task.kind.value} {task.genius_id}: {error}")
            return []
        new = [child for child in dict.fromkeys(children) if child.key not in seen]
        seen.update(child.key for child in new)
        return new

    async def walk(start: Task) -> None:
        queue = deque([start])
        while queue:
            queue.extendleft(reversed(await handle(queue.popleft())))  # depth first

    async def finish(item: Task) -> None:
        await walk(item)
        _bump(state.items, item.kind)
        await on_progress(state)

    units = await handle(root)
    state.root = replace(root, name=await _name_of(sessionmaker, root))
    # A discography is the artist plus a list: its units are what they found. Any other root is itself the first unit.
    counted = units if root.kind is ImportKind.DISCOGRAPHY else [root, *units]
    state.units = _counts(counted, done=0 if root.kind is ImportKind.DISCOGRAPHY else 1)

    for unit in units:
        state.unit = unit
        state.items = []
        items = await handle(unit)
        state.unit = replace(unit, name=unit.name or await _name_of(sessionmaker, unit))
        state.items = _counts(items)
        running = [asyncio.create_task(finish(item)) for item in items]
        try:
            await asyncio.gather(*running)
        except BaseException:
            # A 429, a crash or a cancel: stop the siblings too, and raise the first error as it is
            # (a TaskGroup would wrap it in an ExceptionGroup).
            for task in running:
                task.cancel()
            await asyncio.gather(*running, return_exceptions=True)
            raise
        _bump(state.units, unit.kind)
        await on_progress(state)

    state.unit = state.active = None
    state.items = []
    await on_progress(state)
    return failures

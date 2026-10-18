from dataclasses import dataclass
from datetime import date, datetime
from typing import Annotated, Any, Literal

from fastapi import Depends, Query
from pydantic import BaseModel

from music_backend.enums import (
    ArtistType,
    DatePrecision,
    ImportKind,
    ImportState,
    JobStatus,
    RevisionAction,
)


@dataclass(slots=True)
class Paging:
    limit: Annotated[int, Query(ge=1, le=200)] = 60
    offset: Annotated[int, Query(ge=0)] = 0


PagingDep = Annotated[Paging, Depends()]
# Several roles must all match (see the lists of songs and albums of an artist).
RolesQuery = Annotated[list[str], Query(default_factory=list)]


class Page[T](BaseModel):
    """The one pagination shape used by every list endpoint."""

    items: list[T]
    total: int
    limit: int
    offset: int

    @classmethod
    def of(cls, items: list[T], total: int, paging: Paging) -> Page[T]:
        return cls(items=items, total=total, limit=paging.limit, offset=paging.offset)


class ArtistRef(BaseModel):
    id: int
    genius_id: int | None
    base_name: str
    cover_url: str | None
    artist_type: ArtistType | None
    import_state: ImportState


class ImportRef(BaseModel):
    id: int
    kind: ImportKind
    status: JobStatus
    albums_limit: int | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None


class ChangeOut(BaseModel):
    id: int
    action: RevisionAction
    changes: dict[str, Any]  # {field: [old, new]}
    created_at: datetime


class ArtistAlbum(BaseModel):
    id: int
    genius_id: int | None
    base_name: str
    variant: str | None
    album_type: str | None
    release_date: date | None
    release_date_precision: DatePrecision | None
    is_released: bool | None
    cover_url: str | None
    genius_url: str | None
    tracks_count: int
    import_state: ImportState
    artists: list[str]  # the main artists of the album, in the order Genius lists them
    labels: list[str]  # the artists credited as the label of the album
    roles: list[str]  # of the artist whose list this is; empty elsewhere


class DomNode(BaseModel):
    """A node of a Genius `dom` tree (a description): the tags we have seen are p, em, strong, i, b, a,
    blockquote, hr, br, img, small, center. A child is a node or a piece of text. `br`, `hr` and `img`
    have no children; `a` has `attributes.href` and sometimes `data.api_path` (a page of Genius)."""

    tag: str
    attributes: dict[str, Any] | None = None
    data: dict[str, Any] | None = None
    children: list[DomNode | str] | None = None


class DomRef(BaseModel):
    """An `api_path` found in a description (`/artists/42`) and the page of ours it leads to."""

    api_path: str
    kind: Literal["artist", "album"]
    id: int

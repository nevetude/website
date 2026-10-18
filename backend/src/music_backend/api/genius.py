from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from music_backend.api.deps import EditorDep, SessionDep
from music_backend.enums import ImportState
from music_backend.imports.client import GeniusError
from music_backend.models import Artist

router = APIRouter(prefix="/api/v1/genius", tags=["genius"])


class ArtistSearchHit(BaseModel):
    genius_id: int
    name: str
    image_url: str | None
    # None: not in our database yet; STUB or FULL: already there.
    db_state: ImportState | None
    artist_id: int | None


@router.get("/search/artists")
async def search_genius_artists(
    q: str,
    request: Request,
    session: SessionDep,
    _: EditorDep,
) -> list[ArtistSearchHit]:
    try:
        data = await request.app.state.genius.get("/search/artist", {"q": q})
    except GeniusError as error:
        raise HTTPException(502, str(error)) from error

    results = [
        hit["result"]
        for section in data["sections"]
        if section["type"] == "artist"
        for hit in section["hits"]
    ]
    known = {
        artist.genius_id: artist
        for artist in await session.scalars(
            select(Artist).where(Artist.genius_id.in_([r["id"] for r in results]))
        )
    }
    return [
        ArtistSearchHit(
            genius_id=r["id"],
            name=r["name"],
            image_url=r["image_url"],
            db_state=known[r["id"]].import_state if r["id"] in known else None,
            artist_id=known[r["id"]].id if r["id"] in known else None,
        )
        for r in results
    ]

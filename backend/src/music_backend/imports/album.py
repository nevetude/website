from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from music_backend.enums import AlbumRelationType, AlbumType, ImportKind, ImportState
from music_backend.imports.common import (
    Context,
    Follow,
    Task,
    add_credits,
    add_if_missing,
    apply_fields,
    description_of,
    find_placement,
    get_or_create_album_stub,
    get_or_create_artist_stub,
    get_or_create_song_stub,
    log_changes,
    partial_date,
    upsert,
)
from music_backend.models import (
    Album,
    AlbumArtist,
    AlbumCoverArt,
    AlbumCredit,
    AlbumRelationship,
    AlbumTrack,
)
from music_backend.names import split_name

if TYPE_CHECKING:
    from collections.abc import Mapping

    from sqlalchemy.ext.asyncio import AsyncSession

# Genius lists every relation from both sides ("deluxe_edition_of" and "deluxe_editions"); we store
# each link once, in the "of" direction. True means the listed albums are the ones pointing at us.
RELATIONS: dict[str, tuple[AlbumRelationType, bool]] = {
    "deluxe_edition_of": (AlbumRelationType.DELUXE_EDITION_OF, False),
    "deluxe_editions": (AlbumRelationType.DELUXE_EDITION_OF, True),
    "alternate_version_of": (AlbumRelationType.ALTERNATE_VERSION_OF, False),
    "alternate_versions": (AlbumRelationType.ALTERNATE_VERSION_OF, True),
    "reissue_of": (AlbumRelationType.REISSUE_OF, False),
    "reissues": (AlbumRelationType.REISSUE_OF, True),
    "remix_version_of": (AlbumRelationType.REMIX_VERSION_OF, False),
    "remixes": (AlbumRelationType.REMIX_VERSION_OF, True),
}


async def handle_album(ctx: Context, session: AsyncSession, task: Task) -> list[Task]:
    """The album and its tracklist. Queues its songs and artists; with `follow`, also the albums it is
    related to (whose own relations then stay stubs)."""
    raw = (await ctx.get(f"/albums/{task.genius_id}"))["album"]
    name = split_name(raw["name"])
    release_date, precision = partial_date(raw["release_date_components"])

    album, changes = await upsert(
        session,
        Album,
        task.genius_id,
        {
            "name": raw["name"],
            "base_name": name.base_name,
            "disambiguator": name.disambiguator,
            "variant": name.variant,
            "album_type": AlbumType(raw["album_type"]),
            "language": raw["language"],
            "release_date": release_date,
            "release_date_precision": precision,
            # Genius has no flag for an album that is not out yet: it has no date at all, or the author
            # marks the title with an asterisk (`OFF THE STRENGTH*`).
            "is_released": release_date is not None and "*" not in raw["name"],
            # Albums have no `description` field; the text is the body of the description annotation (it
            # also holds the URLs of embedded cards, which `description_preview` leaves out).
            "description": description_of(
                raw["description_annotation"]["annotations"][0]["body"]["dom"]
            ),
            "genius_url": raw["url"],
            "cover_url": raw["cover_art_url"],
            "cover_thumbnail_url": raw["cover_art_thumbnail_url"],
            "cover_primary_color": raw["album_art_primary_color"],
            "cover_secondary_color": raw["album_art_secondary_color"],
            "import_state": ImportState.FULL,
        },
    )

    artists: list[dict[str, Any]] = list(raw["primary_artists"])
    for position, artist in enumerate(raw["primary_artists"], start=1):
        stub = await get_or_create_artist_stub(session, artist)
        await add_if_missing(
            session, AlbumArtist, {"album_id": album.id, "artist_id": stub.id}, position=position
        )

    for position, cover in enumerate(raw["cover_arts"], start=1):
        await _save_cover_art(session, album.id, position, cover)

    artists += await add_credits(
        session, AlbumCredit, {"album_id": album.id}, raw["performance_groups"]
    )

    related: list[dict[str, Any]] = []
    for relation in raw["album_relationships"]:
        relation_type, inverted = RELATIONS[relation["relationship_type"]]
        for other in relation["albums"]:
            other_album = await get_or_create_album_stub(session, other)
            source, target = (other_album, album) if inverted else (album, other_album)
            await add_if_missing(
                session,
                AlbumRelationship,
                {"album_id": source.id, "related_album_id": target.id, "type": relation_type},
            )
            related.append(other)

    tracks = await _fetch_tracks(ctx, task.genius_id)
    await _save_tracks(session, album, tracks)

    await log_changes(session, "album", album, raw, changes)
    # Any artist found walks to its groups (and their members), the same as in a song.
    queued = [Task(ImportKind.ARTIST, a["id"], Follow.GROUPS, name=a["name"]) for a in artists]
    queued += [
        Task(ImportKind.SONG, item["song"]["id"], name=item["song"]["title"]) for item in tracks
    ]
    if Follow.RELATED in task.follow:
        queued += [Task(ImportKind.ALBUM, a["id"], Follow.NONE, name=a["name"]) for a in related]
    return queued


async def _fetch_tracks(ctx: Context, album_id: int) -> list[dict[str, Any]]:
    tracks: list[dict[str, Any]] = []
    page: int | None = 1
    while page:
        data = await ctx.get(f"/albums/{album_id}/tracks", {"page": page})
        tracks += data["tracks"]
        page = data["next_page"]
    return tracks


async def _save_cover_art(
    session: AsyncSession, album_id: int, position: int, raw: Mapping[str, Any]
) -> None:
    values = {
        "album_id": album_id,
        "position": position,
        "image_url": raw["image_url"],
        "thumbnail_image_url": raw["thumbnail_image_url"],
        "genius_url": raw["url"],
    }
    cover = await session.scalar(select(AlbumCoverArt).where(AlbumCoverArt.genius_id == raw["id"]))
    if cover is None:
        session.add(AlbumCoverArt(genius_id=raw["id"], **values))
    else:
        apply_fields(cover, values)


async def _save_tracks(session: AsyncSession, album: Album, tracks: list[dict[str, Any]]) -> None:
    for order, item in enumerate(tracks, start=1):
        raw_song = item["song"]
        song = await get_or_create_song_stub(session, raw_song)
        track = await find_placement(session, album.id, song.id)
        values = {
            "disc_number": item["disc_number"],
            "position": item["disc_track_number"],
            "sort_order": order,
        }
        if track is None:
            session.add(AlbumTrack(album_id=album.id, song_id=song.id, **values))
        else:
            apply_fields(track, values)

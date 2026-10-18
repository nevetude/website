from typing import TYPE_CHECKING, Any

from music_backend.enums import ImportKind, ImportState, SongArtistRole, SongRelationType
from music_backend.imports.common import (
    Context,
    Follow,
    Task,
    add_credits,
    add_if_missing,
    description_of,
    find_or_insert,
    find_placement,
    get_or_create_album_stub,
    get_or_create_artist_stub,
    get_or_create_song_stub,
    log_changes,
    partial_date,
    upsert,
)
from music_backend.models import (
    AlbumTrack,
    Genre,
    Song,
    SongArtist,
    SongAudio,
    SongCredit,
    SongRelationship,
    SongTag,
    SongVideo,
    Tag,
)
from music_backend.names import split_name

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Same idea as for albums: Genius lists each relation from both sides, we store it once.
RELATIONS: dict[str, tuple[SongRelationType, bool]] = {
    "samples": (SongRelationType.SAMPLES, False),
    "sampled_in": (SongRelationType.SAMPLES, True),
    "interpolates": (SongRelationType.INTERPOLATES, False),
    "interpolated_by": (SongRelationType.INTERPOLATES, True),
    "cover_of": (SongRelationType.COVER_OF, False),
    "covered_by": (SongRelationType.COVER_OF, True),
    "remix_of": (SongRelationType.REMIX_OF, False),
    "remixed_by": (SongRelationType.REMIX_OF, True),
    "live_version_of": (SongRelationType.LIVE_VERSION_OF, False),
    "performed_live_as": (SongRelationType.LIVE_VERSION_OF, True),
    "translation_of": (SongRelationType.TRANSLATION_OF, False),
    "translations": (SongRelationType.TRANSLATION_OF, True),
}


async def handle_song(ctx: Context, session: AsyncSession, task: Task) -> list[Task]:
    """The song with its artists, credits, tags, links and relations. Queues every artist found
    (each walks to its groups); related songs and the song's albums are stubs."""
    raw = (await ctx.get(f"/songs/{task.genius_id}"))["song"]
    name = split_name(raw["title"])
    release_date, precision = partial_date(raw["release_date_components"])
    genre = await _dictionary_row(session, Genre, raw["primary_tag"])
    stats = raw["stats"]

    song, changes = await upsert(
        session,
        Song,
        task.genius_id,
        {
            "name": raw["title"],
            "base_name": name.base_name,
            "disambiguator": name.disambiguator,
            "variant": name.variant,
            "language": raw["language"],
            "release_date": release_date,
            "release_date_precision": precision,
            "description": description_of(raw["description"]["dom"]),
            "recording_location": raw["recording_location"],
            "explicit": raw["explicit"],
            "instrumental": raw["instrumental"],
            "is_music": raw["is_music"],
            "hidden": raw["hidden"],
            "published": raw["published"],
            "lyrics_state": raw["lyrics_state"],
            "genre_id": genre.id,
            "genius_url": raw["url"],
            "cover_url": raw["song_art_image_url"],
            "cover_thumbnail_url": raw["song_art_image_thumbnail_url"],
            "cover_primary_color": raw["song_art_primary_color"],
            "cover_secondary_color": raw["song_art_secondary_color"],
            "view_count": stats.get("pageviews"),  # Genius leaves it out for most songs
            "import_state": ImportState.FULL,
        },
    )

    artists: list[dict[str, Any]] = []
    for role, key in (
        (SongArtistRole.PRIMARY, "primary_artists"),
        (SongArtistRole.FEATURED, "featured_artists"),
    ):
        for position, artist in enumerate(raw[key], start=1):
            stub = await get_or_create_artist_stub(session, artist)
            await add_if_missing(
                session,
                SongArtist,
                {"song_id": song.id, "artist_id": stub.id, "role": role},
                position=position,
            )
            artists.append(artist)

    credit_groups = [
        {"label": "Writer", "artists": raw["writer_artists"]},
        {"label": "Producer", "artists": raw["producer_artists"]},
        *raw["custom_performances"],
    ]
    artists += await add_credits(session, SongCredit, {"song_id": song.id}, credit_groups)

    for tag in raw["tags"]:
        row = await _dictionary_row(session, Tag, tag)
        await add_if_missing(session, SongTag, {"song_id": song.id, "tag_id": row.id})

    for relation in raw["song_relationships"]:
        relation_type, inverted = RELATIONS[relation["relationship_type"]]
        for other in relation["songs"]:
            other_song = await get_or_create_song_stub(session, other)
            source, target = (other_song, song) if inverted else (song, other_song)
            await add_if_missing(
                session,
                SongRelationship,
                {"song_id": source.id, "related_song_id": target.id, "type": relation_type},
            )

    for media in raw["media"]:
        if media["type"] == "video":
            await add_if_missing(
                session,
                SongVideo,
                {"song_id": song.id, "url": media["url"]},
                start_seconds=media.get("start"),
            )
        else:
            await add_if_missing(
                session,
                SongAudio,
                {"song_id": song.id, "provider": media["provider"], "url": media["url"]},
                native_uri=media.get("native_uri"),  # not every provider has these two
                attribution=media.get("attribution"),
            )

    await _save_placements(session, song, raw)

    await log_changes(session, "song", song, raw, changes)
    # Any artist found, credits included, walks to its groups: each is imported with its members.
    return [Task(ImportKind.ARTIST, a["id"], Follow.GROUPS, name=a["name"]) for a in artists]


async def _dictionary_row(
    session: AsyncSession, model: type[Genre] | type[Tag], raw: dict[str, Any]
) -> Any:
    """The genre or tag with this Genius id; created the first time it is seen."""
    name = split_name(raw["name"])
    return await find_or_insert(
        session,
        model,
        {"genius_id": raw["id"]},
        name=raw["name"],
        base_name=name.base_name,
        disambiguator=name.disambiguator,
    )


async def _save_placements(session: AsyncSession, song: Song, raw: dict[str, Any]) -> None:
    """The albums the song is on. Genius gives no track numbers here, so a placement is created
    without a position; the album's own import fills it in."""
    primary_id = raw["album"]["id"] if raw["album"] else None  # singles have no album
    for raw_album in raw["albums"]:
        album = await get_or_create_album_stub(session, raw_album)
        track = await find_placement(session, album.id, song.id)
        if track is None:
            track = AlbumTrack(album_id=album.id, song_id=song.id)
            session.add(track)
        is_primary = raw_album["id"] == primary_id
        if track.is_primary != is_primary:
            track.is_primary = is_primary

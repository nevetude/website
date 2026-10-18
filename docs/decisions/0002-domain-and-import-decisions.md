# ADR 0002: Domain and import decisions (agreed with the user)

Status: accepted for domain modeling. Open items are listed at the end.
The resulting schema draft is in `docs/domain-model.md`.

## Naming and language
- Use Genius terms: `artist`, `song`, `album` (with `album_type`), `album_track`. No `release`.
- UI and internals are in English; comments and logs may be in Russian where the logic is hard.

## Editing, history, deletion
- Full revision history (who, when, what changed, rollback), stored as per-field diffs. Import changes are written to history too (author "genius-import"). Details to revisit later.
- No moderation for now: a single admin edits directly.
- No delete function for big entities (artist, album) for now. Deletion exists only for smaller things (track placement, credits, relations, tags, reviews, ratings), as soft delete.
- Manual edits and deletions (never overwritten by re-import, per-field tracking) are **postponed**: the columns and the detach service were removed and will be designed with the edit mode in the frontend.

## Songs and albums
- One `song` can appear on many albums through `album_track` (album, song, disc, position). `genius_id` is a separate unique nullable column.
- **Detach** (postponed together with editing; the code and `manually_overridden` / `source_genius_song_id` were removed, the description is kept as the plan): for one `album_track`, create a new `song` (copy of fields, credits and tags; not media or annotations; `genius_id = NULL`, source manual), repoint that row's `song_id`, always add a `song_relationship` new -> original. The row gets `manually_overridden` and remembers `source_genius_song_id`. One history entry. Detach offers `remix_of` and `interpolates` for now.
- `song_relationship`: store all Genius types, one direction only (samples, interpolates, cover_of, remix_of, live_version_of, translation_of); inverse sides are derived. Type is plain text, not a Postgres ENUM and without a CHECK.
- Missing related entities (songs, albums, artists) are created as stubs. One field `import_state` (`stub` | `full`) on song, album and artist. Manually created entities are `full`.
- Album types and album-to-album relations come from the API and are stored. `album_track.is_primary` marks the song's primary album.
- Credits: separate `song_credit` and `album_credit` tables; normalized role dictionary, original label text kept.
- Dates: `date` + precision (year, month, day).
- Descriptions: the `dom` tree stays in the stored response (ADR 0005), `description` is the plain text built from it. No `fetched_at`.

## Artists
- One `artist` table with an `artist_type` column for now (named like `album_type`). The user dislikes labels and groups being "artists" and wants them separated later: **to be reworked** (keep the split cheap).

## Genres and tags
- No tag classification. `genre` = Genius `primary_tag` (one per song). `tags` = all Genius tags. Own tables. Manual override is only possible from the existing sets of genres and tags.

## Names
- Original full name kept as is. A script splits it into three fields: `base_name`, `variant` (Freestyle, Remix, Live, feat. X) and `disambiguator` (alternative-language name). Example: `Надоела (Freestyle) (Tired of you)` -> `Надоела` / `Freestyle` / `Tired of you`. Applies to artist, song, album, genre and tag.
- **Artists** use Genius's own `name_components` (every artist is fetched by id); a stub keeps the full name in `base_name` until it is imported in full. UI shows `base_name` by default; frontend settings (`localStorage`) toggle showing the extra parts.

## Content
- Lyrics and annotations: tables and UI areas with placeholders for now, no logic. Later they will be loaded from local JSON files supplied by the user. Timecodes are required: lyrics are stored as lines with optional `start_ms`/`end_ms` for line switching during playback.
- Ratings: integer 1-10, real tables and logic, no seeded data. Reviews: real tables, empty.
- No scraping of genius.com pages.

## Import (principle, details later)
- Importing a song also saves all albums that contain it and other versions of those albums, fully, but not recursively (depth one). Tracks of these extra albums are stubs.
- Access: anonymous public API first; official API with a user OAuth token as fallback for 403 (Missing Lyrics). Track lists come from `/albums/{id}/tracks`.
- **Groups (rule for the future pipeline):** when an imported artist is a group, all its members are imported in full. If a member is itself a group, it is not processed in full: it stays a `stub`. Today members are always stubs.
- **Artist type:** an artist with members is a `group`; every artist without members is a `person` by default (also the column default and the type of stubs; a stub that is really a group is corrected when it is imported in full).
- Parsing pipelines are a separate large topic, to be designed later. The user is undecided on the import details.

## Frontend routing
- Clean path URLs without `#`, e.g. `/artists/1`, using internal ids. SvelteKit path routing with SSR so deep links survive refresh.

## Open items
- Import details and parsing pipelines.

## Resolved later
- Integer `bigint` ids. `notes` field on artist, album and song (postponed, removed with the other editing columns); links typed by the user are shown without the scheme. Everything added through forms (artists, genres, tags, roles) must exist as database rows.
- `variant` is always shown, only `disambiguator` is hidden by default.
- Frontend on port 8080, backend on 8000, `/api` proxied through Vite.
- Genres of album/artist are derived from tracks. `tags` includes the primary tag. Song is not deletable. Lyric timecodes belong to the song.

## Trust policy (2026-10-12)
The user prefers to trust the Genius API and write the minimum of checks; a check is added only when a test or a real run shows a problem. All existing code and the schema were rewritten that way (see CLAUDE.md, principle 3, and "Constraints policy" in `docs/domain-model.md`).

- Artist descriptions: an empty text and Genius's placeholder "?" are stored as `NULL` (6 of 98 sampled artists had "?"). This is the one value check the 100-artist run justified.

## Album decisions (2026-10-12)
Columns, cover arts table, four relation types stored once, all credits, and the parked-fields file are described in `docs/domain-model.md` and `docs/parked-fields.md`.

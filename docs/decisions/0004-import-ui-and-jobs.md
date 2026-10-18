# ADR 0004: Import from the site (search, background jobs, progress)

Status: accepted. "Import" is the name for pulling data from Genius into our database (ETL).

## Decisions
- Imports are started from the site, not the console. Entry is **search for artists only** (via `genius.com/api/search/artist`); other entity types are added later. Results show cover and a state: not in the database, `stub`, or `full`.
- Pasting Genius page URLs is not supported (no numeric id in them; extracting it means parsing HTML). Entry is search or a numeric id.
- **No preview step.** The import runs right away.
- Imports run as **background jobs** inside the API process (asyncio, no Redis or Celery), one job at a time, with at least one second between Genius requests.
- The site shows a collapsed widget (bottom left): progress bar plus a minimal log of the latest requests, visible on every page. The full job page shows the whole log. Progress is read by **polling once a second**.
- Every Genius request of a job is logged (URL, status, time, size) for later analysis of 4XX responses.
- Genius account connection ("Connect Genius account") is done from settings, replacing the console OAuth script. The token is stored in the database. This arrives together with the frontend because the registered redirect URI is `http://localhost:8080/callback` (a frontend route).

## API (follows ADR 0003)
- `GET  /api/v1/genius/search/artists?q=`
- `POST /api/v1/imports` (`{kind, genius_id}`, returns 202 and the job; an active job for the same target is returned instead of a duplicate)
- `GET  /api/v1/imports`, `GET /api/v1/imports/{id}`, `GET /api/v1/imports/{id}/requests`, `POST /api/v1/imports/{id}/cancel`

## Tables
`import_job` (kind, genius_id, status, progress, message, error, result id, author, timestamps) and `import_request` (one row per Genius request).

## Auth placeholder
Import endpoints require an editor. Real login is not built yet: `current_user` auto-logs in as `admin` when `DEV_AUTO_LOGIN` is on (default on for local work), exactly the single switch described in CLAUDE.md.

## Open
What exactly an artist import pulls in (only the artist and its members, or also albums) is still to be decided with the user. The first version imports the artist and its members (members as stubs).

## Findings from the 100-artist run (2026-10-12)
Run: 100 artists searched and imported through the API (English, Russian, Japanese, Korean, Spanish and other names; groups, producers, labels), all jobs queued at once, two cancelled from the queue.
- 98 of 98 imports succeeded, 196 s in total; a request takes 614 ms median, 7.8 s worst. Names in Cyrillic, Japanese and Korean round-trip correctly; Genius's `name_components` gave the right base name and disambiguator in all 18 cases that have one.
- **Labels have no artist links on Genius.** None of the 23 label pages had any `artist_relationships`. The artist-to-label link will have to come from song and album credits (`Label`), not from the artist import. Genius gives no artist type either, so labels are imported as `person` until typed by hand.
- **`member_of` exists next to `members`** (13 of 98 artists, 26 links: Kendrick Lamar is a member of Black Hippy). The import now stores it: the group becomes a stub of type `group` and is linked.
- No group in the sample contained another group, so the "nested group stays a stub" rule is untested on real data.
- Search is unreliable for the first hit, especially for labels and short names (Sub Pop -> "Sub Pop Bionic", Оксимирон -> "Оксиминог"). The UI must show the whole result list.
- Genius uses "?" as an empty description (6 of 98, all small pages).

## Fixed because of the run
- Re-importing unchanged data wrote an UPDATE, touched `updated_at` and added an empty history entry. Now nothing is written unless a stored field changes; the raw copy is refreshed only together with a real change.
- Network errors, 429 and 5xx are retried twice with a growing pause (every attempt is logged); other 4xx are final.

## Import form and the big import (decisions 2026-10-12, design stage)
- **Form.** The default mode is **Discography** (our own pipeline: artist, then every album, then every song); it is not a single Genius endpoint, so it has no URL. It takes the artist id and an optional **albums limit** (empty = all), and the limit exists only in this mode. The other modes are single endpoints: `[https://genius.com/api] [endpoint ▾] [id]` with the endpoints artists/{id}, albums/{id}, songs/{id} (the tracks-only mode was dropped: it needs an album that is already in the database).
- **No `include_songs` switch.** Songs are always parsed fully.
- **Stopping is always safe.** Every entity is saved in its own transaction (all or nothing per entity). Cancelling, a crash or a restart keeps everything already finished and rolls back only the entity being written; running the import again continues without duplicates (re-import of unchanged data writes nothing). The request log is committed separately, so it survives too. Note: the current single-entity importers use one transaction per job; the big import must commit per entity.
- **Artists found anywhere in the import are parsed in full** (own endpoint, fields, aliases, links) and every one of them walks to its groups (`Follow.GROUPS`): each group is imported in full with all its members; the other groups of those members are stubs. Related albums found are parsed in full (album, tracklist, songs); their own relations are stubs.
- Order of albums for the limit: as Genius returns them (newest first; `sort=release_date` is the default).

## Import architecture (implemented 2026-10-12)
Package `music_backend/imports/`:
- `client.py`: anonymous Genius client (pacing, retries, request log).
- `common.py`: `Task`, `Context` and the shared helpers (`upsert`, `get_or_create_stub`, `add_if_missing`, `partial_date`, ...).
- `artist.py`, `album.py`, `song.py`: one small handler per entity. A handler fetches one endpoint, saves that one entity and returns the tasks for the entities that must be imported in full. Everything it does not return stays a stub.
- `runner.py`: `run_tasks` (one flat loop, depth first, each entity once, **one transaction per entity**) and `ImportManager` (jobs, cancel, restart recovery, request log).
A job kind is the first task: `discography` (the artist first, with its walk over members and groups, then the list of its newest albums up to `albums_limit`; the units of the job are what that walk found and the albums, the listing itself is not a unit and not highlighted in the log), `artist`, `album`, `song`. A failure of the first task fails the job; a failure of any other task is listed in the job's `error` and the run goes on (status stays `succeeded`, message "Done, N failed").
Following rules (the `follow` flag of a task): the artist you import imports its members in full and the groups they belong to in full **with all members of those groups**, and its own groups the same way (`Follow` flag: `ALL` -> members get `GROUPS`, groups get `MEMBERS`, members of a group get `NONE`); the groups of those last members stay stubs, that is the stop; an album followed imports the albums it is related to (their own relations stay stubs). Artists found anywhere are imported in full without following; songs of a tracklist are imported in full; related songs are stubs.
Live check: 2 songs, 1 unreleased song and a discography with limit 1 (Radiohead: 54 tasks, 56 requests) all succeeded; a closed song (403) fails its job as expected (needs the user token).

## Import page (rewritten 2026-10-13)
The frontend was restarted on Svelte UX 2.x (Tailwind 4), dark and monochrome. The page: one import block on top (artist search, a mode menu with the default "Discography of an artist", the id with the URL prefix for a single entity, the albums limit) next to a separate Monitor block (elapsed, time left, requests, requests per minute of the running job), then the job cards. Progress is **two fixed levels** because the old single counter grew all the time: `units` (what the first task found: for a discography the artist and every album, known right after the listing) and `items` (what the current unit found when it was read: for an album its songs, artists and related albums). Deeper work (the artists of a song, ...) is imported as part of its item and shows only as the line `active`. A running job returns it as `progress` (in memory in `ImportManager.live`, null for finished jobs); `progress_done/progress_total` in the database are the units. A job stores `subject_name`. The request log has `task_kind/task_genius_id/task_name` (which task the request was for) and `attempt`; the API adds `page_url` (the Genius page of the entity once saved; the client falls back to the API url). Columns: Time, Status, Task (the name only), Link, Request, Took (faint green under 1 s, orange from 1 s, red from 3 s: `SLOW_MS`, `VERY_SLOW_MS` in `imports.ts`), Size; the attempt is only a tooltip. The table is a CSS grid with fixed column widths (a long name is cut with an ellipsis and never moves a column), Took and Size sort on a click (biggest first, smallest first, back to arrival order); new rows appear at once: there are no animations in the frontend for now. The card shows the last 10, a dialog of a fixed height shows all of them, updates live (`GET /imports/{id}/requests?after_id=`), filters by text and by Problems (an error, a retry, or a red Took). A finished job collapses its last requests. Time left is a guess after three finished units.

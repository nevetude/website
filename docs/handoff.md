# Handoff (state of the work)

Read it at the start of a session; shrink it when its open items are closed. Settled decisions live in `docs/decisions/` and `docs/domain-model.md`; this file adds the state and the lessons.

## 1. State
- Backend: 121 tests, `ruff` and `mypy --strict` clean. Frontend: `check`, `lint`, 35 unit tests, 2 e2e, `build` pass.
- Working: models and migrations, the Genius import (artist, album, song, discography) with its API and a page at `/import`, the artist search, a test home page of artists, the artist page and the album page (with its clips: `GET /albums/{id}/videos`, one YouTube player, a playlist in the order of the tracklist).
- Not built: login and sessions (dev auto-login as `admin`), Genius OAuth for closed songs (403), `refresh`, the progress widget on every page, edit mode, the player and local mp3.
- Postgres in Docker (`compose.yaml`, user/password/database `music`); the container stops when WSL restarts: `docker compose up -d db`. `make reset` wipes the local database and rebuilds it from the migrations. One migration (`initial_schema`): while there is no data worth keeping, the schema is changed by regenerating it (`make reset`); once data matters, a migration must keep it (ADR 0005).

## 2. Architecture in short
- **Import** (`backend/src/music_backend/imports/`): one handler per entity returns the `Task`s it found; `run_tasks` (`runner.py`) walks them, one transaction per entity, the items of one unit in parallel (`WORKERS`); `ImportManager` (`manager.py`) runs jobs one at a time inside the API process. A failure of the root task fails the job, any other failure is listed in `error`. A 429 stops the whole import. Everything not queued stays a stub (`import_state='stub'`); `Follow` says which links a task may follow (members, groups, related albums).
- **API** (`api/`): `queries.py` holds what several routers share (roles, album card, ordering, counting, 404), `schemas.py` the shared schemas and `Paging`. `operationId` is the function name. Every request is `admin` while `DEV_AUTO_LOGIN` is on; permissions are enforced on the backend (`require_editor`).
- **Frontend**: detail pages load in `+page.ts`, the site is client-only; lists use `PagedList`; the card geometry is in `lib/albums.ts`, formatting in `lib/format.ts`. No animations (one exception, see `CLAUDE.md`).
- **Data rules**: unknown is NULL (stubs store only what the list said); descriptions are kept as Genius `dom` trees (default `text_format`, nothing is asked for), the text in `description` is built from the tree (`plain_text`); names are split by `names.py`; dates keep their precision; the Genius response is kept per entity in `genius_response` and replaced whenever it differs; the history only gets a real change of the stored fields.

## 3. Lessons (do not repeat)
1. A migration must keep the data: back up (`pg_dump`) before changing a database that holds an import.
2. Alembic renders an Enum CHECK several times: no CHECKs.
3. Dates are not JSON serialisable in history: `to_jsonable_python`.
4. `stats.pageviews` is missing for most songs: use `.get`.
5. `pkill -f` with a pattern that appears in your own command line kills your own shell: kill by pid.
6. Genius search often ranks a wrong page first; show the whole list. Labels have no artist links on Genius: take them from the `Label` credits.
7. Svelte UX removes `<html data-theme>` unless a theme is registered with `settings()`; `core.css` derives the `neutral-*` shades from `--color-neutral`, so a theme must not refer to them.
8. Headless Chromium needs `libnspr4`, `libnss3`, `libasound2`: unpack them from `apt-get download` into a folder and run with `LD_LIBRARY_PATH`. The e2e config starts its own server on 8080: stop the dev server first.
9. Console and build must stay free of warnings: the build uses `adapter-static` (fallback `index.html`), the favicon is a static link in `app.html`, and element sizes are read through `ui/watchSize.ts` (`watchWidth`, `watchHeight`, deferred with `requestAnimationFrame`), not `bind:clientWidth`, which makes the browser report "ResizeObserver loop completed with undelivered notifications".
10. `TypeError: Cannot read properties of undefined (reading 'call')` in the browser console during development comes from Vite: a new import of an icon (`@lucide/svelte/icons/...`) was pre-bundled, the dev server reloaded the page and two copies of the Svelte runtime met. `optimizeDeps.exclude: ['@lucide/svelte']` in `vite.config.ts` stops it; a page that is already broken needs a reload by hand.

Genius API facts: `docs/genius-api-notes.md`. Fields we do not store: `docs/parked-fields.md`.

## 4. Next steps
0. **Open bug:** in the full-screen mode of the embedded YouTube player (clips on the album page) the controls hide after a while but the cursor does not. The code was checked (the frame is reset to the whole screen, nothing touches the cursor). `docs/experiments/youtube-fullscreen-cursor.html` is an A/B page (plain embed, as on the site, without the scaling): copy it into `frontend/static/`, open `/youtube-fullscreen-cursor.html` in `pnpm dev`, and see which variant hides the cursor; delete it afterwards.
1. The import order "oldest first": the default order and whether albums without a date go first or last (needs a new job column).
2. Bigger topics: login and sessions (cookie + Bearer), the other catalog endpoints and pages, edit mode and creation forms, Genius OAuth, the player.
3. Parked tooling ideas (do not add without agreement): extra ruff rules (`FAST`, `DTZ`, `T20`, `LOG`, `G`) and the `pydantic.mypy` plugin; `hypothesis` tests for `split_name` and `partial_date`; logging setup (`structlog` for prod). Check current versions before adding anything.
4. Open questions: `per_page=50` for the tracks request (one line), merging `song_artist` and `song_credit`, how editing, deleting and detach should work, a "finished with errors" status.

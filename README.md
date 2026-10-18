# Music

A web app that is two things at once:

- a **streaming player** (Spotify / Yandex Music style): playback, library, playlists, queue;
- an **encyclopedic catalog** (Genius / AlbumOfTheYear / RateYourMusic style): detailed artist, album and
  song pages with credits, genres, descriptions, clips, ratings and reviews.

**Phase 1 is the catalog**, filled from the public [Genius](https://genius.com) API. Playing local mp3 folders from the site
comes later, and the data model is already prepared for it (a media file belongs to the placement of a song on an
album). The project is local-first, but written so that going to production means replacing or removing a few things,
not rewriting.

> The site is **one client** of the HTTP API. An Android app is planned and will use the same OpenAPI contract.

## Contents

1. [What works today](#what-works-today)
2. [Stack](#stack)
3. [Run it locally](#run-it-locally)
4. [Architecture](#architecture)
5. [Backend](#backend)
6. [Frontend](#frontend)
7. [Engineering approach](#engineering-approach)
8. [Quality gates](#quality-gates)
9. [Documentation map](#documentation-map)
10. [Not built yet](#not-built-yet)
11. [Using Genius responsibly](#using-genius-responsibly)
12. [Troubleshooting](#troubleshooting)

## What works today

- **Import from Genius** (`/import`): search an artist by name, then import one artist, one album, one song, or a whole
  **discography** (the newest N albums or all). The import runs as a background job with progress, a request log and
  cancel. It is idempotent: a second run changes only what changed.
- **Artist page** (`/artists/{id}`): a round portrait, facts (type, followers, real name, born/died, aliases), genres as
  tiles, popular tracks, the description (rich text), links to streaming services and social networks (grouped, with brand
  colours), members and groups, then the discography (albums by type, grid or rows, filters by role, Released / Alphabet
  sorting, a toggle for unreleased albums), clips and all songs (filters by role, sorting by Released / Alphabet / Views).
- **Album page** (`/albums/{id}`): the cover with the covers behind it, the facts, the tracklist (discs, numbers,
  most-viewed track, featured artists, producers, views), credits summed up from the songs, the description, clips
  played in one embedded player, other editions of the album, and mock-ups for what comes later (rating, reviews, lists,
  gallery).
- **Home page** (`/`): a test page of artists in five blocks (imported by hand, groups, artists, stub groups, stub
  artists), each with its own sorting and role filters. It is kept isolated because it may be dropped.
- **Technical block** on every page: import jobs of the entity, history of changes, the raw Genius response.

## Stack

| Layer | Choice |
|---|---|
| Backend | Python 3.14, FastAPI, Pydantic v2, async everywhere |
| Database | PostgreSQL 18 only (no SQLite, not even for dev), SQLAlchemy 2.1 async (asyncpg) + Alembic |
| HTTP client | httpx (the Genius importer) |
| Frontend | TypeScript (strict), SvelteKit with Svelte 5 (runes only), Vite |
| UI | Svelte UX on Tailwind 4, one dark, nearly monochrome theme; Lucide and Simple Icons |
| API types | generated from the OpenAPI schema (`openapi-typescript`, `openapi-fetch`) |
| Tooling | `uv` (Python), `pnpm` (JS), `ruff`, `mypy --strict`, `pytest`, `svelte-check`, `eslint` + `prettier`, `vitest`, `playwright` |
| Infra | monorepo, Docker Compose for the local database |

Exact versions live in `backend/pyproject.toml` / `uv.lock` and `frontend/package.json` / `pnpm-lock.yaml`.

## Run it locally

You need Docker, [uv](https://docs.astral.sh/uv/), Node 24 and pnpm.

```bash
# 1. the database
docker compose up -d db

# 2. the API (http://localhost:8000, docs at /docs)
cd backend
uv sync
uv run alembic upgrade head
uv run fastapi dev

# 3. the site (http://localhost:8080, /api is proxied to :8000)
cd frontend
pnpm install
pnpm dev
```

Open <http://localhost:8080/import>, search for an artist and start a discography import. In development the site works
without login: `DEV_AUTO_LOGIN` (on by default) makes every request act as the user `admin`.

Useful commands:

| Command | What it does |
|---|---|
| `make reset` (repo root) | wipes the local database and rebuilds it from the migrations, without asking (stop the API first; the script refuses a non-local host) |
| `cd backend && uv run alembic revision --autogenerate -m "..."` | a new migration |
| `cd frontend && pnpm gen:api` | regenerates `src/lib/api/schema.d.ts` after an API change |

Settings are environment variables (see [`.env.example`](.env.example) for the database container and
[`backend/.env.example`](backend/.env.example) for the API): `DATABASE_URL`, `GENIUS_BASE_URL`,
`GENIUS_MIN_INTERVAL_S`, `GENIUS_RETRY_BACKOFF_S`, `DEV_AUTO_LOGIN`. Never commit a real `.env`.

## Architecture

```
                 ┌────────────┐   HTTPS    ┌───────────────────────────────┐
                 │  Genius    │ <───────── │ importer (background job)     │
                 │ public API │            │ handlers → task queue → DB    │
                 └────────────┘            └──────────────┬────────────────┘
                                                          │ SQLAlchemy (async)
 ┌───────────────┐   /api/v1 (OpenAPI)   ┌────────────────▼───────────────┐
 │ SvelteKit site│ <──────────────────── │ FastAPI                        │ ──> PostgreSQL
 │ (client-only) │                       │ routers · schemas · queries.py │     (normalized data
 └───────────────┘   Android app later   └────────────────────────────────┘      + raw responses)
```

Repository layout:

```
backend/        FastAPI app, importer, models, migrations, tests (uv project)
  src/music_backend/
    api/        routers, response schemas, the SQL pieces they share (queries.py)
    imports/    one handler per Genius entity, the task runner, the job manager, the Genius client
    models/     SQLAlchemy models (catalog, content, importing, system)
    bio.py      reads "real name / born / died" from the start of an artist description
    names.py    splits a title into name, variant and disambiguator
  migrations/   Alembic (one initial migration while there is no data worth keeping)
  scripts/      reset_db.py, openapi.py (used by `pnpm gen:api`)
frontend/       SvelteKit app (pnpm project)
  src/routes/   /, /import, /artists/[id], /albums/[id]
  src/lib/      album/, artist/, artists/, import/, entity/, ui/, layout/, api/ (generated types)
docs/           domain model, decisions (ADRs), Genius API notes, parked fields and UI, experiments
compose.yaml    local PostgreSQL
Makefile        `make reset`
CLAUDE.md       the rules of the project for the AI assistant (also a good summary of the code principles)
```

### The data flow in one paragraph

A user starts an import job through the API. The `ImportManager` runs it in the background of the API process. A handler
per entity (artist, album, song, discography) reads one Genius endpoint, writes the entity and returns the **tasks** for
the related entities that must be imported in full; everything else is saved as a **stub** (only what the list said).
Every entity is one database transaction, so a stop (cancel, crash, restart) keeps everything already finished. The API
reads the normalized tables and serves facts; the site decides how to show them.

## Backend

### Layers

| Layer | Where | Responsibility |
|---|---|---|
| Models | `models/` | tables, column order, enum columns; no logic |
| Importer | `imports/` | Genius → database; idempotent, per-entity transactions |
| API | `api/` | routers, Pydantic response models, shared SQL (`queries.py`); no presentation logic |
| Settings | `config.py` | `pydantic-settings`, loaded once |

### The importer

- **Handlers.** `handle_artist`, `handle_discography`, `handle_album`, `handle_song` (one file per entity). A handler
  saves its entity with `upsert` and returns `Task(kind, genius_id, follow, ...)` objects.
- **Stubs.** An entity known only from a list (a member of a group, a credit, a related album) is created with
  `import_state = 'stub'` and only what the list says. A later import of it fills the rest and sets `full`.
- **`follow` flags.** `Follow` (an enum flag) limits how far the walk goes. An artist follows its members and the groups
  it belongs to, each exactly one step, so a discography never turns into the whole of Genius. An album can follow its
  other editions (`Follow.RELATED`); its relations stay stubs.
- **Runner** (`runner.py`). `run_tasks` handles the root task, then the *units* it found (for a discography: each album)
  one after another, so a stop leaves complete albums. The *items* of one unit (its songs and artists) run in parallel,
  `WORKERS` at a time, each item with its own surroundings depth first. A failure of the root task fails the job; any
  other failure is logged and listed, and the job goes on ("Done, N failed").
- **Races.** Parallel handlers meet the same new rows (an artist in two songs, the role "Writer"), so stubs and
  dictionary rows are created with `INSERT ... ON CONFLICT DO NOTHING` and then read (`find_or_insert`).
- **Manager** (`manager.py`). `ImportManager` runs one job at a time, supports cancel, closes jobs that were active
  when the server stopped, records every request in `import_request`, and keeps live progress in memory (two levels
  only, because only those totals are known in advance and never grow).
- **Genius client** (`client.py`). Anonymous, an honest `User-Agent`, requests spaced by `GENIUS_MIN_INTERVAL_S`
  (serialized through a lock, so parallel handlers share one pace), two retries on network errors and 5xx, **a 429 stops
  the whole import** at once (so the request log ends exactly where the limit was hit).
- **Idempotency.** Re-importing unchanged data writes nothing: no new row, no history entry. The raw response is
  refreshed only together with a real change. Hand-made aliases are never removed.
- **What the importer decides on its own.** Artist type (members → group, otherwise person; `member_of` turns a stub into
  a group), unreleased albums (`is_released` is false when the album has no date or its title has a `*`), titles split into
  `name` / `variant` / `disambiguator` (`names.py`), descriptions (below), media (`song_video`: every Genius video is a
  YouTube video; `song_audio`: SoundCloud and Spotify).

### Descriptions

The importer does not ask Genius for a text format: the default is `dom`, a tree of `{tag, attributes, data, children}`
that keeps links and embeds. The tree stays in `genius_response`; the plain text in `description` (for search and for
`bio.py`) is built from it by `plain_text`. The API gives `description_dom` and `description_refs` (which links lead to
our own artists and albums). The site draws the tree with a whitelist of tags (`RichText`), and a paragraph that holds
only a YouTube link becomes a player.

### Data model (summary)

Details and every decision: [`docs/domain-model.md`](docs/domain-model.md).

- **Entities**: `artist` (+ `artist_alias`, `artist_member`), `album` (+ `album_artist`, `album_cover_art`,
  `album_credit`, `album_relationship`, `album_folder`), `song` (+ `song_artist`, `song_credit`, `song_tag`,
  `song_relationship`, `song_audio`, `song_video`), `album_track` (the placement of a song on an album: disc, position,
  primary album), dictionaries (`genre`, `tag`, `credit_role`), placeholders for later (`lyrics`, `lyric_line`,
  `annotation`, `album_rating`, `album_review`, `song_rating`, `song_review`, `app_user`, `user_session`,
  `media_file`), history (`revision`), and import bookkeeping (`import_job`, `import_request`, `genius_response`).
- **Genius terms.** `album`, not `release`; ids are Genius ids kept in `genius_id` (unique), our own keys are bigint
  identities.
- **Raw responses** live in their own table, `genius_response(entity_type, entity_id, raw)`, so entity rows stay small
  and an import can be replayed.
- **Unknown is NULL.** A stub stores only what its list said; nothing is filled with a guess or a default. A flag that
  a stub cannot know (`explicit`, `is_music`, `is_released`, ...) is nullable.
- **Hand-set flags** are never touched by the import: `explicit` on clips and alternative covers, `official` on clips.
- **No CHECK constraints, no range or format validation, no business-rule indexes.** The database holds keys, `NOT NULL`
  and the uniqueness the code looks things up by.
- **Enums are plain text** (`enum_column()`, no CHECK, room for new values), so adding a value needs no migration.
- **Column order is part of the design**: `id`, `genius_id`, name parts (`name`, `variant`, `base_name`,
  `disambiguator`), type and `import_state`, the entity's own columns, timestamps. PostgreSQL cannot reorder columns
  later, so the order is fixed by `sort_order` bands in `models/base.py`.
- **Pictures**: every entity keeps only `cover_url` and, where Genius gives one, `cover_thumbnail_url`. The rest
  (headers, custom covers) is parked in the raw response ([`docs/parked-fields.md`](docs/parked-fields.md)).

### API

`/api/v1`. The OpenAPI schema is the contract (`/docs` when the API runs); `operationId` equals the function name, so
generated clients get stable method names.

| Group | Endpoints |
|---|---|
| Health | `GET /health` |
| Genius | `GET /genius/search/artists?q=` |
| Imports | `POST /imports`, `GET /imports`, `GET /imports/{id}`, `GET /imports/{id}/requests`, `POST /imports/{id}/cancel` |
| Artists (home page) | `GET /artists`, `GET /artists/roles` |
| Artist page | `GET /artists/{id}`, `/songs`, `/albums`, `/videos`, `/raw` |
| Album page | `GET /albums/{id}`, `/tracks`, `/videos`, `/raw` |

Conventions: explicit response models (never ORM objects), one paging format for every list (`limit`, `offset`,
`total`), 404 for a missing entity, 409 for a conflict, ISO 8601 timestamps, no presentation logic (names come as
parts, descriptions as trees, the order of blocks is the client's decision). "A role" (what an artist is on a song or
an album: main, featured, or a credit such as Writer or Producer) has one definition in `api/queries.py`.

Auth is a placeholder: one `current_user` dependency decides who calls; with `DEV_AUTO_LOGIN` it is always `admin`.
Editor-only routes (the import) depend on the role, so permissions are enforced on the backend and the site only
reflects them.

## Frontend

- **Client-only SvelteKit** (`ssr = false`, `adapter-static`, fallback `index.html`). A detail page loads its entity
  in `+page.ts` through `loaded()` (`lib/load.ts`): a 404 or a stopped backend becomes `+error.svelte`. Server rendering
  would need a data path of its own on the SvelteKit server, which the API-first rule forbids.
- **Generated API client.** `pnpm gen:api` turns the backend OpenAPI schema into `src/lib/api/schema.d.ts`; calls go
  through `openapi-fetch`. API types are never written by hand.
- **Lists** read from a paged endpoint use `PagedList` (`lib/paged.svelte.ts`): reload, load more, or load everything,
  and an answer to an older request never replaces the answer to a newer one.
- **Svelte 5 runes only** (`$state`, `$derived`, `$effect`, snippets); no legacy stores or `$:` in new code. Svelte UX
  components are written in the old syntax inside: bind props and pass children, but do not use `on:` or `slot=` from
  runes code.
- **Design system.** One dark, nearly monochrome theme (`[data-theme='music']` in `app.css`); colour only for meaning
  (success, warning, danger) and for brand marks of links. Own small components live in `lib/ui/`, feature
  components in `lib/<feature>/`. Imports use the `#lib/...` alias (TypeScript modules with `.js`, Svelte files with
  `.svelte`).
- **Sizes do not depend on content or state.** One place holds a geometry that two states share (for example `CARD`
  and `perRow` in `lib/artists.ts` serve both the strip and the opened grid of an album category). The size of an
  element is read with the `watchWidth` / `watchHeight` actions, not `bind:clientWidth` (it logs a ResizeObserver error).
- **No animations by default** (a deliberate decision). The exceptions are listed in `CLAUDE.md`: an album card
  height easing between Grid and Rows, `ClampList` and `Collapse`, link hover colour, the cover viewer, the clip
  player, and a few others.
- **Page layout.** The artist page and the album page share one idea: the top is a grid with a coloured panel (the
  round portrait or the cover with covers behind it) and the facts beside it, the tracklist (or popular tracks) lying
  over the lower edge of the panel, and the description and credits below. `NotchedCard` is the card with a bite in its
  corner; `Collapse` and `ClampList` cut long text and open it smoothly; `FactRow` is one row of facts.
- **Clips.** The album page plays YouTube clips in one embedded player (`youtube-nocookie.com`) in the main place; the
  other clips glide to their places (`lib/glide.ts`); the button of the playing clip pauses it and follows its state
  through the player's `postMessage` API.

## Engineering approach

These are the rules the code follows. They are also written down in [`CLAUDE.md`](CLAUDE.md) for the AI assistant that
helps with the project.

1. **Trust the data, write the minimum of checks.** Genius is trusted: its fields are read directly
   (`raw["name_components"]["base_name"]`), without `.get(...)`, `or default`, `isinstance` or "just in case" fallbacks.
   A check is added only after a test or a real run shows a problem, and the commit says what showed it. This
   found real bugs honestly (for example a song whose `release_date_components` is `null`, not a dict).
2. **API-first.** All data and logic go through `/api/v1`; the site has no private data path. See
   [`docs/decisions/0003-api-first-for-multiple-clients.md`](docs/decisions/0003-api-first-for-multiple-clients.md).
3. **Idempotent, interruptible imports.** One transaction per entity, each entity once per job, unchanged data writes
   nothing, a stop loses at most the entity being written.
4. **Newest stable idioms.** Python 3.14 typing (`X | None`, `type` aliases, PEP 695 generics, `match`,
   `dataclass(slots=True)`), Svelte 5 runes, current community-endorsed tools over legacy ones, no deprecated APIs.
   Before a dependency is added or upgraded, its current version and docs are checked.
5. **Readable, not over-split.** Modules where they help readability; no one-function files and no abstraction layer
   without a second use case (a shared component is extracted when the second user appears, as `NotchedCard` was).
6. **Comments say why, never what.**
7. **Be polite to Genius.** Honest user agent, a request pace set in one place, a 429 stops the import. Lyrics are not
   in the API and are never scraped.
8. **Ask before architecture.** New infrastructure, new top-level dependencies and design of unplanned parts are
   discussed first; decisions are recorded as ADRs in `docs/decisions/`.
9. **Migrations keep data** once an import is worth keeping; until then the schema is regenerated from scratch
   (`make reset`).
10. **Tests at the HTTP level** where practical, against a real PostgreSQL database built through the real migrations;
    Genius is replaced by a fake client with complete default payloads.

## Quality gates

```bash
# backend (needs `docker compose up -d db`; the tests build their own `music_test` database through the migrations)
cd backend
uv run ruff format --check . && uv run ruff check . && uv run mypy && uv run pytest

# frontend
cd frontend
pnpm lint && pnpm check && pnpm test:unit --run && pnpm build
pnpm test:e2e            # starts its own server on :8080; stop `pnpm dev` first; needs Chromium
```

Backend: `mypy --strict`, async tests (`pytest-asyncio`, auto mode), coverage on. Frontend: `svelte-check`, `eslint` +
`prettier`, `vitest` (pure functions in Node; components in a Playwright browser), Playwright e2e tests of the import page.

## Documentation map

| File | What is in it |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | the rules of the project: stack, product decisions, code principles, commands |
| [`docs/handoff.md`](docs/handoff.md) | the state of the work, lessons learned, next steps (read it first when you come back) |
| [`docs/domain-model.md`](docs/domain-model.md) | every table, column order, naming, constraints policy |
| [`docs/decisions/`](docs/decisions) | ADRs: ORM, domain and import decisions, API-first, import UI and jobs, refactoring decisions |
| [`docs/genius-api-notes.md`](docs/genius-api-notes.md) | verified facts about the Genius API (hosts, access, pagination, shapes) |
| [`docs/parked-fields.md`](docs/parked-fields.md) | fields we deliberately do not store, and why |
| [`docs/parked-ui.md`](docs/parked-ui.md) | UI that was designed and set aside |
| [`docs/rate-limit/`](docs/rate-limit) | logs of a rate-limit measurement of the public API |
| [`docs/experiments/`](docs/experiments) | small test pages for open questions |
| [`notes.txt`](notes.txt) | the owner's own list of ideas (not built without agreement) |

## Not built yet

- Login and sessions (cookie for the browser, Bearer for apps); until then `DEV_AUTO_LOGIN`.
- Edit mode and creation forms (the admin will see an edit button on any page; later an `editor` role).
- The player and local mp3 folders (the tables for media files and album folders exist).
- Genius OAuth, to import songs that answer 403 to anonymous users ("Missing Lyrics").
- Ratings, reviews, lists, lyrics annotations (the tables and mock-ups exist).
- A progress widget on every page and a page of the request log.
- A real job queue (a database queue or Redis) instead of jobs inside the API process; ADR 0005 explains why not now.
- Ideas from `notes.txt`: study credits, personal grouping of albums, track numbering modes (A1/B1), tracklists split by
  discs, unusual release types, a personal library.

## Using Genius responsibly

The importer reads the public Genius API at a low, fixed pace and identifies itself honestly. It does not scrape
lyrics or pages. Check Genius's terms before you run big imports, keep `GENIUS_MIN_INTERVAL_S` reasonable, and
remember that a 429 means "stop". `docs/genius-api-notes.md` records what was verified, and the rate-limit
measurement in `docs/rate-limit/` was done on purpose and in small amounts.

## Troubleshooting

- **The database is not there after a restart of WSL.** The container stops with it: `docker compose up -d db`.
- **`make reset` fails.** Stop the API first (it holds connections), and make sure the database container is up.
- **`TypeError: Cannot read properties of undefined (reading 'call')` in the browser console during development.**
  Vite pre-bundled a new icon import and reloaded the page while two copies of Svelte were around; restart `pnpm dev`.
- **The e2e test cannot start Chromium.** Install it with `pnpm exec playwright install chromium`; on a bare Linux
  also the system libraries it needs.
- **An import stops with "429".** Genius limited the pace. Wait, raise `GENIUS_MIN_INTERVAL_S`, and start again: the
  import is idempotent and continues where the data is missing.
- **A closed song (403).** It needs a Genius user token (OAuth), which is not built yet; the import of the rest goes on.

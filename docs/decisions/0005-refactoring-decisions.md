# ADR 0005: Decisions of the refactoring of 2026-10-17

Status: accepted. Each decision answers a question raised by a review of the whole code.

## Done
1. **Detail pages load through SvelteKit `load`** (`+page.ts`), and the site is client-only (`ssr = false` in `routes/+layout.ts`). A missing entity or a stopped backend becomes the error page (`routes/+error.svelte`, helper `lib/load.ts`). Server rendering would need a data path of its own on the SvelteKit server, which ADR 0003 forbids. Lists inside a page (songs, albums, artists) still load on the client with `PagedList`, because they react to filters.
2. **Genius responses live in their own table** `genius_response(entity_type, entity_id, raw)`, not in a column of each entity. Entity rows stay small, no lazy loading (`undefer`) is needed, and a response is written only with a real change, together with the `revision` entry. The migration copies the existing responses.
3. **`ImportManager` is split from `run_tasks`** (`imports/manager.py` and `imports/runner.py`). Jobs still run inside the API process.
4. **The temporary table `tmp_album_song_performance` is removed.** It held Genius's album-level summary of song credits. The album page already sums the credits of the songs itself, and the summary stays in the stored response, so nothing is lost.
5. **`Follow.RELATED`** is the flag for the other editions of an album. An album task no longer reuses "any value but NONE" as a boolean.

## Decided not to do now
- **A real job queue** (Postgres `SKIP LOCKED`, `arq`). The project is local and runs one job at a time in one process. The progress of a running job (`ImportManager.live`) is in memory, so a second API process would not see it. Revisit together with the move to prod: the queue and the progress then go to the database or Redis.
- **A table of roles per artist** (`artist_work_role`, filled by the importer). The roles are now a `UNION` over the credits on every request; on 1000 artists and 3000 songs a request takes about 10 ms. Revisit when the home page gets slow; the single definition of a role in `api/queries.py` is the place to replace.
- **Mockup blocks** (`Gallery`, `Videos` on the album page) stay: they are the agreed design of features that come later.

## Descriptions as trees (2026-10-18)
The importer no longer asks for `text_format`: the default is `dom`, a tree of `{tag, attributes, data, children}`. It stays in `genius_response`; `description` (text for search and for `bio.py`) is built from it by `plain_text`, which gives the text of Genius's own `plain` for 92 of 95 sampled descriptions (the rest differ by blank lines at the end), and `bio.py` found the same on all 45 sampled artists. The API gives `description_dom` (read from the stored response, no new column) and `description_refs` (which `api_path` of the links lead to our artists and albums). `RichText` draws a whitelist of tags; a paragraph holding only a YouTube link becomes a player (`youtube-nocookie.com`). Entities imported before this have no tree until they are imported again: the pages show their text meanwhile.

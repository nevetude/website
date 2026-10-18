# Genius API notes (verified by live requests, 2026-10)

Reference for anyone touching the importer. Everything here was checked against the real API; see `docs/parked-fields.md` for the fields we leave out.

## Two hosts
- **Public:** `https://genius.com/api/...`, no token. The richest answers. Needs an honest `User-Agent` (a fake browser one got 403).
- **Official:** `https://api.genius.com/...`, `Authorization: Bearer <token>`. Answers carry fewer fields than the public API (no `albums`, `explicit`, `tags`, ...) and a rate limit header (`x-ratelimit-limit: 10000`). A token of the app (client token) sees the same as an anonymous user.
- `genius.com/api` called with a Bearer token answers like the official API (same body, fewer fields).

## Access
- **Closed songs** (page shows "Missing Lyrics", `lyrics_state: incomplete`) answer **403 to anonymous users**, on both hosts. "Unreleased" songs are fine. A **user** token (OAuth) lifts the 403 on both hosts.
- OAuth (authorization code): open `https://api.genius.com/oauth/authorize?client_id=...&redirect_uri=...&scope=me&state=...&response_type=code`; Genius redirects with `code`; `POST https://api.genius.com/oauth/token` with form fields `code, client_id, client_secret, redirect_uri, response_type=code, grant_type=authorization_code` returns `access_token`. The redirect URI of our app is `http://localhost:8080/callback`.
- `/albums/{id}/appearances` is 403 on the official API even with a user token; use `/albums/{id}/tracks`.
- Closed-song 403s and slow answers (up to ~10 s) happen; the network to Genius is sometimes unreachable for a few seconds.

## Pagination
`response.next_page` is the next page number or null. `per_page` is at most **50** (51 or more answers 422). `page` and `per_page` are optional (page 1 by default). `/artists/{id}/albums` returns the newest first (`sort=release_date`, the default); `sort=popularity` also exists. The album list holds editions as separate albums.

## Text fields (`text_format`)
`dom` (default), `plain`, `html`, `markdown`; several at once with commas. It changes only text bodies: `artist.description`, `song.description` and the bodies of `description_annotation.annotations[]` (artist, song, album, and each `album.cover_arts[]`). An album has no `description` field. We use `plain`. `description_preview` is always plain text without links and is not truncated; it lacks the URLs of embedded cards that `plain` contains. Plain text uses `\n\n` between paragraphs, single `\n` inside lists, runs of 3 to 6 newlines before headings, and `\xa0`; no indentation. Only `dom` and `html` keep links.

## Shapes worth remembering
- **Artist:** `name_components {base_name, disambiguator}` is given; `artist_relationships[]` has `members` (for groups) and `member_of` (groups the artist belongs to). Genius gives no artist type. **Labels have no artist links at all**; the label to artist link comes from `Label` credits of albums and songs. List entries (members, credits) carry only `id, name, image_url, ...`, no `name_components`.
- **Album:** `release_date` is padded with 1 for unknown parts, the truth is in `release_date_components`. `album_relationships[]` has 8 names, 4 pairs: `deluxe_edition_of/deluxe_editions`, `alternate_version_of/alternate_versions`, `reissue_of/reissues`, `remix_version_of/remixes`. `performance_groups[]` (Label, Copyright, Phonographic Copyright) is often empty. `song_performances[]` summarises all song credits. `cover_arts[]` has 0 to 3 items (the separate `/cover_arts` endpoint is 404).
- **Tracklist** `/albums/{id}/tracks`: `disc_number`, `disc_track_number`, `number` (overall); on some albums they are null.
- **Song:** `release_date` can be null while `release_date_components` has a year (unreleased). `stats.pageviews` is missing for most songs. `media[]` (YouTube always, sometimes SoundCloud and Spotify; `native_uri` and `attribution` are optional) duplicates `youtube_url`, `soundcloud_url`, `spotify_uuid`, `youtube_start`. `translation_songs` duplicates the `translations` relation. `song_relationships[]` has 12 names, 6 pairs (samples/sampled_in, interpolates/interpolated_by, cover_of/covered_by, remix_of/remixed_by, live_version_of/performed_live_as, translation_of/translations). `tags[]` always contains the `primary_tag`. `album` (primary) is not always `albums[0]`. Singles have no album. Lyrics text is not in the API (only `lyrics_state`); do not scrape genius.com pages.
- **Search** (`/search/artist?q=`) ranks wrongly often, especially labels and short names (Sub Pop gives "Sub Pop Bionic"). Show the whole list; import by id.

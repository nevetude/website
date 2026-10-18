# Parked fields (seen in the Genius API, deliberately not stored yet)

Fields we looked at and left out for now, kept here so they can be added later, or be useful for debugging.
Nothing in this file is stored in the database, except where noted. Add a field by writing a migration
and reading it in the importer (`raw["field"]`).

## Artist (`GET /artists/{id}`)
- `social_links` (Spotify, YouTube, SoundCloud, Apple Music, Twitter, Instagram, Facebook, website, ...): not stored in a table: `GET /artists/{id}` reads it from the stored response (`genius_response`) (empty strings skipped, bare handles turned into URLs) and the artist page shows it as Links.
- `twitter_name`, `instagram_name`, `facebook_name`: duplicates of `social_links`.
- `slug`, `index_character`, `api_path`, `links_config`, `translation_artist`.
- `user` (the Genius account of the artist, including `iq`), `description_annotation` (authors, votes, rich text tree).
- `current_user_metadata`, `tracking_paths`: noise.

## Album (`GET /albums/{id}`)
Remembered as possible future additions, also useful for debugging:
- `song_pageviews`, `updated_at` (Genius's own change time, unix seconds).
- Counters `comment_count`, `contributors_count`, `pyongs_count` (stored for a while, removed by the user's decision).
- `hidden` (always false in every sampled album), `lock_state` ("locked" / "editable": whether Genius lets users edit it).
- `album_art_text_color`.
- `translation_albums`, `translation_of`: translations of the album (empty in every sample).
- `description_preview` (we read the full text from the description annotation instead), `description_annotation` authors and votes.
- `full_title`, `name_with_artist`, `primary_artist_names`: derived text.
- `artist`: the first of `primary_artists[]`, so it is not read separately.
- `api_path`, `pusher_channel`, `tracking_paths`, `current_user_metadata`, `viewable_by_roles`: noise.
- `song_performances` (summary of all song credits of the album): not stored: the album page sums up the credits of the songs itself (`_credits`), and the response keeps the summary (`genius_response`).

## Album tracklist (`GET /albums/{id}/tracks`)
- `number` (overall track number across discs): derivable from disc and position, not stored.
- Most `song` fields in the list (`lyrics_state`, `primary_artists`, `featured_artists`, `song_art_image_url`, release date components, ...): songs are created as stubs; the full song import will read them.

## Song (`GET /songs/{id}`)
- Duplicates of `media[]` (checked equal on 41 songs): `youtube_url`, `youtube_start`, `soundcloud_url`, `spotify_uuid`. `translation_songs` duplicates the `translations` relation.
- `apple_music_id`, `apple_music_player_url`.
- Counters and stats other than the view count: `comment_count`, `pyongs_count`, `annotation_count`, `stats.*` (accepted_annotations, contributors, iq_earners, transcribers, unreviewed_annotations, verified_annotations, hot).
- Lyrics metadata: `lyrics_owner_id`, `lyrics_updated_at`, `lyrics_verified`, `pending_lyrics_edits_count`, `lyrics_marked_complete_by`, `lyrics_marked_staff_approved_by`, `verified_lyrics_by`.
- `song_art_source_album`, `song_art_text_color`, `verified_annotations_by`, `verified_contributors`, `top_scholar`, `description_annotation`.
- Derived or noise: `full_title`, `title_with_featured`, `artist_names`, `primary_artist_names`, `primary_artist` (first of `primary_artists[]`), `album` is used only to mark the primary album, `embed_content`, share messages, `tracking_*`, `current_user_metadata`, `transcription_priority`, `metadata_fields_na`, `has_instagram_reel_annotations`, `vttp_id`, `viewable_by_roles`, `pusher_channel`, `api_path`, `path`, `url` duplicates (`share_url`), `relationships_index_url`, `updated_at`, `updated_by_human_at`.

## Pictures (parked 2026-10-19; to be looked at again and tested)
Every entity keeps only `cover_url` and, where Genius gives one, `cover_thumbnail_url`. The artist's `image_url` became `cover_url`. These fields were removed from the tables; the values stay in `genius_response`:
- Artist: `header_image_url` (the wide picture; on 1000 sampled artists it equalled `image_url` in 245).
- Album: `header_image_url`, `custom_header_image_url` (an album's header equalled the cover in 10 of 10 random albums that had one; where the addresses differed, half were a different picture).
- Song: `custom_cover_url`, `header_image_url`, `header_thumbnail_url`, `custom_header_image_url` (the header equalled the cover on 1000 of 1000 sampled songs).
To test again: compare the pictures by pixels (not by address) on a bigger sample before bringing any of them back.

Hand-set flags (boolean, default false, never touched by the import): `explicit` and `official` on `song_video` (the clips, right after `song_id`) and on `album_cover_art` (the alternative covers, right after `position`).

## Open items found by live runs
- Closed songs (403 for anonymous users, "Missing Lyrics") need the Genius user token; the OAuth connect is not built yet.

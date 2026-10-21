import type { AlbumTrack, AlbumVideo, CreditGroup, SongDetail } from '#lib/api.js';

const OF = {
	samples: 'Samples',
	interpolates: 'Interpolates',
	cover_of: 'Cover of',
	remix_of: 'Remix of',
	live_version_of: 'Live version of',
	translation_of: 'Translation of'
} as const;

const PLURAL = {
	samples: 'Sampled in',
	interpolates: 'Interpolated in',
	cover_of: 'Covers',
	remix_of: 'Remixes',
	live_version_of: 'Live versions',
	translation_of: 'Translations'
} as const;

/** "Remix of" when this song is the remix, "Remixes" when the others are. */
export const songRelationTitle = ({ type, inverse }: { type: keyof typeof OF; inverse: boolean }) =>
	(inverse ? PLURAL : OF)[type];

// The clips of the album page are made for the tracks of an album. A song is one track of its own.
// `Videos` finds the track of a clip by the id of the song, so the song gives it this one.
export const songTrack = (song: SongDetail): AlbumTrack => ({
	id: song.id,
	song_id: song.id,
	disc_number: null,
	position: 1,
	base_name: song.base_name,
	variant: song.variant,
	genius_url: song.genius_url,
	cover_thumbnail_url: song.cover_url,
	import_state: song.import_state,
	explicit: song.explicit,
	view_count: song.view_count,
	is_primary: null,
	artists: song.artists,
	featured: song.featured,
	producers: song.credits.find((group) => group.role === 'Producer')?.artists ?? []
});

export const songVideos = (song: SongDetail): AlbumVideo[] =>
	song.videos.map((video) => ({
		...video,
		song_id: song.id,
		song_name: song.base_name,
		release_date: song.release_date,
		release_date_precision: song.release_date_precision
	}));

/** The credits of a song in the shape of the credits of an album (`Credits`). */
export const songCredits = (song: SongDetail): CreditGroup[] =>
	song.credits.map(({ role, artists }) => ({
		role,
		from_album: false,
		artists: artists.map((artist) => ({ artist, tracks: null }))
	}));

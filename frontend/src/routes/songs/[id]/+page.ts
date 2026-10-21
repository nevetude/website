import { api } from '#lib/api.js';
import { loaded } from '#lib/load.js';
import type { PageLoad } from './$types';

// The lyrics are null when the song has no file for them (see `lyrics.py`).
export const load: PageLoad = async ({ params, fetch }) => {
	const path = { song_id: Number(params.id) };
	const [song, lyrics] = await Promise.all([
		loaded('song', api.GET('/api/v1/songs/{song_id}', { params: { path }, fetch })),
		api.GET('/api/v1/songs/{song_id}/lyrics', { params: { path }, fetch })
	]);
	return { song, lyrics: lyrics.data ?? null };
};

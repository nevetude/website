import { api } from '#lib/api.js';
import { loaded } from '#lib/load.js';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const path = { album_id: Number(params.id) };
	const [album, tracks, videos] = await Promise.all([
		loaded('album', api.GET('/api/v1/albums/{album_id}', { params: { path }, fetch })),
		loaded('album', api.GET('/api/v1/albums/{album_id}/tracks', { params: { path }, fetch })),
		loaded('album', api.GET('/api/v1/albums/{album_id}/videos', { params: { path }, fetch }))
	]);
	return { album, tracks, videos };
};

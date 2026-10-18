import { api } from '#lib/api.js';
import { loaded } from '#lib/load.js';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => ({
	artist: await loaded(
		'artist',
		api.GET('/api/v1/artists/{artist_id}', {
			params: { path: { artist_id: Number(params.id) } },
			fetch
		})
	)
});

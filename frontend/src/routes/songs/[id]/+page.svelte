<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import SongPage from '#lib/song/SongPage.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	// The album the visitor came through shows in the breadcrumbs, between the artist and the song. Nothing is in the
	// address for it: it is the page the visitor left. A reload or a link opened by hand has no such page.
	let albumId = $state<number | null>(null);
	afterNavigate(({ from }) => {
		albumId = from?.route.id === '/albums/[id]' ? Number(from.params?.id) : null;
	});
</script>

<SongPage song={data.song} lyrics={data.lyrics} {albumId} />

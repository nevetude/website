<script lang="ts">
	import type { SongDetail } from '#lib/api.js';
	import AlbumCategory from '#lib/album/AlbumCategory.svelte';

	let { albums }: { albums: SongDetail['albums'] } = $props();
</script>

<!-- Like the other versions of an album (`OtherVersions`): a strip of albums, two in view, the rest by scrolling. -->
<section class="space-y-4 rounded-xl bg-surface-200 p-4">
	<AlbumCategory
		title="Appears on"
		albums={albums.map((placement) => placement.album)}
		view="grid"
		openAll={false}
		resetKey=""
		columns={2}
	/>
</section>

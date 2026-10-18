<script lang="ts">
	import type { RelatedAlbums } from '#lib/api.js';
	import AlbumCategory from '#lib/album/AlbumCategory.svelte';

	let { related }: { related: RelatedAlbums[] } = $props();
</script>

<!-- Like the releases of an artist: a strip per kind of version, two albums in view, the rest by scrolling. -->
<section class="space-y-4 rounded-xl bg-surface-200 p-4">
	{#each related as group (`${group.type}:${group.inverse}`)}
		<AlbumCategory albums={group.albums} view="grid" openAll={false} resetKey="" columns={2} />
	{/each}
</section>

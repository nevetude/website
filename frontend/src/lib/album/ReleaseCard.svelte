<script lang="ts">
	import type { AlbumDetail } from '#lib/api.js';
	import { coverTint } from '#lib/albums.js';
	import AlbumCover from '#lib/album/AlbumCover.svelte';
	import CoverViewer from '#lib/album/CoverViewer.svelte';
	import ReleaseControls from '#lib/album/ReleaseControls.svelte';

	type Props = { album: AlbumDetail; covers: string[] };

	let { album, covers }: Props = $props();

	let viewing = $state(false); // the covers are open in the overlay
	let index = $state(0); // which one
	const tint = $derived(coverTint(album));
</script>

<!-- The coloured part: 400px wide and 380px high (the last 3rem of its height are under the tracklist, which the
     page lays over its lower edge). In its visible part, from the top down: a space, the cover, a space, the row
     of the panel of buttons, a space down to the tracklist; the numbers are pixels at this height (57.5, 25 and
     16.5 of the 99 left by the cover and the row). The panel is 20px lower than the equal spaces would put it, the cover 20px lower than it was. The
     panel stands exactly under the middle of the cover; the songs and the time are in the tracklist. -->
<section
	class="relative aspect-square h-full rounded-xl bg-surface-200 min-[1000px]:aspect-auto min-[1000px]:min-h-[calc(380px+3rem)]"
	style:background-color={tint}
>
	<div class="absolute inset-x-0 top-0 flex h-full flex-col min-[1000px]:h-[calc(100%-3rem)]">
		<div class="flex-[57.5]"></div>
		<AlbumCover
			{covers}
			onopen={() => {
				index = 0;
				viewing = true;
			}}
		/>
		<div class="flex-[25]"></div>
		<ReleaseControls />
		<div class="flex-[16.5]"></div>
	</div>
</section>

{#if viewing}
	<CoverViewer {covers} bind:index onclose={() => (viewing = false)} />
{/if}

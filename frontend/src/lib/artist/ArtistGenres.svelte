<script lang="ts">
	import type { ArtistDetail } from '#lib/api.js';
	import ClampList from '#lib/ui/ClampList.svelte';

	let { genres }: { genres: ArtistDetail['genres'] } = $props();
</script>

<!-- The genres of the songs of the artist as tiles with the number of songs; two rows, the rest opens over the page. -->
{#if genres.length}
	<ClampList items={genres} lines={2} tiles float>
		{#snippet item({ genre, songs })}<span
				class="inline-flex items-center gap-1 rounded-md bg-surface-100 px-1.5 py-0.5 text-xs whitespace-nowrap text-surface-content/80"
				>{genre}<span class="font-mono text-surface-content/40">{songs}</span></span
			>{/snippet}
	</ClampList>
{/if}

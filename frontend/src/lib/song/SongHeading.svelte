<script lang="ts">
	import { resolve } from '$app/paths';
	import type { SongDetail } from '#lib/api.js';
	import ExplicitMark from '#lib/ui/ExplicitMark.svelte';
	import ExtLink from '#lib/ui/ExtLink.svelte';

	let { song }: { song: SongDetail } = $props();

	const name = (list: { base_name: string }[]) => list.map((one) => one.base_name);
</script>

<!-- The title of the song and its artists: what stands at the top of the header, with or without a container around it. -->
<div class="space-y-2">
	<!-- One line, always: a long title is cut with "…" (the whole of it is in the tooltip). -->
	<h1
		title={[song.base_name, song.variant, song.disambiguator].filter(Boolean).join(' ')}
		class="truncate text-2xl leading-tight font-bold text-surface-content xl:text-3xl"
	>
		{#if song.genius_url}
			<ExtLink href={song.genius_url} title="Open on Genius">{song.base_name}</ExtLink>
		{:else}{song.base_name}{/if}
		{#if song.variant}<span class="font-normal text-surface-content/45">{song.variant}</span>{/if}
		{#if song.explicit}<ExplicitMark
				class="ml-2 inline-block size-4 text-surface-content/60"
			/>{/if}
		{#if song.disambiguator}
			<span class="text-base font-normal text-surface-content/45">{song.disambiguator}</span>
		{/if}
	</h1>
	{#if song.artists.length}
		<p
			title={name([...song.artists, ...song.featured]).join(', ')}
			class="truncate text-lg font-medium text-surface-content/90"
		>
			{#each song.artists as artist, i (artist.id)}{#if i}<span
						class="mr-[0.3em] text-surface-content/40">,</span
					>{/if}<a href={resolve('/artists/[id]', { id: String(artist.id) })} class="artist"
					>{artist.base_name}</a
				>{/each}{#if song.featured.length}<span class="mx-[0.3em] text-surface-content/65"
					>feat.</span
				>{#each song.featured as artist, i (artist.id)}{#if i}<span
							class="mr-[0.3em] text-surface-content/40">,</span
						>{/if}<a href={resolve('/artists/[id]', { id: String(artist.id) })}
						>{artist.base_name}</a
					>{/each}{/if}
		</p>
	{/if}
</div>

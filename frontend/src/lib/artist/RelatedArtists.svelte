<script lang="ts">
	import { resolve } from '$app/paths';
	import type { ArtistRef } from '#lib/api.js';
	import Thumb from '#lib/ui/Thumb.svelte';
	import Chip from '#lib/ui/Chip.svelte';

	let { title, artists }: { title: string; artists: ArtistRef[] } = $props();
</script>

{#if artists.length}
	<section class="space-y-3">
		<h2 class="flex items-baseline gap-3 text-base font-semibold text-surface-content">
			{title}
			<span class="tabular font-mono text-xs font-normal text-surface-content/40"
				>{artists.length}</span
			>
		</h2>
		<div class="grid grid-cols-[repeat(auto-fill,minmax(14rem,1fr))] gap-3">
			{#each artists as artist (artist.id)}
				<a
					href={resolve('/artists/[id]', { id: String(artist.id) })}
					class="flex items-center gap-3 rounded-xl border border-white/8 bg-surface-200 p-2.5 hover:bg-surface-100/60"
				>
					<Thumb src={artist.cover_url} name={artist.base_name} class="size-10 rounded-lg" />
					<span class="min-w-0 flex-1 truncate text-sm text-surface-content"
						>{artist.base_name}</span
					>
					{#if artist.import_state === 'stub'}<Chip>Stub</Chip>{/if}
				</a>
			{/each}
		</div>
	</section>
{/if}

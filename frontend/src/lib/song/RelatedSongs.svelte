<script lang="ts">
	import { resolve } from '$app/paths';
	import type { RelatedSongs } from '#lib/api.js';
	import { songRelationTitle } from '#lib/song.js';
	import CommaList from '#lib/ui/CommaList.svelte';
	import Thumb from '#lib/ui/Thumb.svelte';

	let { related }: { related: RelatedSongs[] } = $props();
</script>

<!-- The songs this one is tied to (samples, remixes, covers), a list per kind of tie, in the look of the rows of a tracklist. -->
<section class="space-y-3 rounded-xl bg-surface-200 p-4">
	{#each related as group (`${group.type}:${group.inverse}`)}
		<div class="space-y-1">
			<h3 class="text-sm font-medium text-surface-content">{songRelationTitle(group)}</h3>
			<ul>
				{#each group.songs as song (song.id)}
					<li>
						<a
							href={resolve('/songs/[id]', { id: String(song.id) })}
							class="-mx-1.5 grid grid-cols-[2rem_minmax(0,1fr)] items-center gap-2 rounded-lg px-1.5 py-1.5 hover:bg-black/20"
						>
							<Thumb src={song.cover_thumbnail_url} name="" class="size-8 rounded-md" />
							<span class="min-w-0">
								<span class="block truncate text-sm leading-snug text-surface-content">
									{song.base_name}{#if song.variant}<span class="ml-1.5 text-surface-content/65"
											>{song.variant}</span
										>{/if}
								</span>
								<span class="block truncate text-xs leading-snug text-surface-content/65">
									<CommaList items={song.artists} wrap={false} />
								</span>
							</span>
						</a>
					</li>
				{/each}
			</ul>
		</div>
	{/each}
</section>

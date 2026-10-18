<script lang="ts">
	import { api, type ArtistSong } from '#lib/api.js';
	import { formatCount } from '#lib/format.js';
	import { PagedList } from '#lib/paged.svelte.js';
	import SongTitle from '#lib/ui/SongTitle.svelte';
	import Thumb from '#lib/ui/Thumb.svelte';

	// `Artist` keeps credits (producer, writer) of other people's songs out of the "top"; an artist
	// who is only credited has no such role and gets all the songs.
	let { artistId, ownSongs }: { artistId: number; ownSongs: boolean } = $props();

	const COUNT = 10;
	const list = new PagedList<ArtistSong>(async (offset) => {
		const { data } = await api.GET('/api/v1/artists/{artist_id}/songs', {
			params: {
				path: { artist_id: artistId },
				query: { roles: ownSongs ? ['Artist'] : [], sort: 'views', limit: COUNT, offset }
			}
		});
		return data;
	});

	$effect(() => {
		void list.reload();
	});
</script>

<!-- The popular tracks in the container of the tracklist of an album, without its bite, its gear and its top row. The most
     viewed track has the big dot. -->
{#if list.items.length}
	<section class="rounded-xl bg-surface-200 p-2">
		<ol>
			{#each list.items as song, index (song.id)}
				<li
					class="grid grid-cols-[1.25rem_2rem_minmax(0,1fr)_auto] items-center gap-2 rounded-lg px-1.5 py-1.5 hover:bg-black/20"
				>
					<span class="block text-center text-sm leading-snug text-surface-content/60">
						{#if index === 0}
							<span
								title="The most viewed track"
								class="relative -top-[0.6px] inline-block size-[6px] rounded-full bg-current align-baseline"
							></span>
						{:else}
							<span class="tabular text-[10px]">{index + 1}</span>
						{/if}
					</span>
					<Thumb src={song.cover_thumbnail_url} name="" class="size-8 rounded-md" />
					<div class="min-w-0">
						<SongTitle {song} class="block leading-snug" />
						{#if song.album}
							<div class="truncate text-xs leading-snug text-surface-content/65">{song.album}</div>
						{/if}
					</div>
					<span class="tabular min-w-[2.5rem] text-right text-[11px] text-surface-content">
						{song.view_count ? formatCount(song.view_count) : ''}
					</span>
				</li>
			{/each}
		</ol>
	</section>
{/if}

<script lang="ts">
	import { resolve } from '$app/paths';
	import { api, type ArtistSong } from '#lib/api.js';
	import { formatCount } from '#lib/format.js';
	import { PagedList } from '#lib/paged.svelte.js';
	import CommaList from '#lib/ui/CommaList.svelte';
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

	const ROW =
		'grid h-full grid-cols-[2rem_minmax(0,1fr)] items-stretch gap-2 rounded-lg px-3.5 py-1.5 hover:bg-black/20';
</script>

{#snippet row(song: ArtistSong)}
	{@const producers = song.producers.map((producer) => producer.base_name)}
	<span class="flex items-center"
		><Thumb src={song.cover_thumbnail_url} name="" class="size-8 rounded-md" /></span
	>
	<div class="flex min-w-0 items-center">
		<div class="flex w-full min-w-0 items-baseline gap-1.5 pr-0.5">
			<div class="flex min-w-0 flex-1 flex-col">
				<span class="truncate text-sm leading-snug text-surface-content">
					{song.base_name}{#if song.variant}<span class="ml-1.5 text-surface-content/65"
							>{song.variant}</span
						>{/if}
				</span>
				{#if song.album}
					<div class="mt-0.5 truncate text-xs leading-snug text-surface-content/65">
						{song.album}
					</div>
				{/if}
			</div>
			<span
				class="-mr-[5px] max-w-[6.25rem] truncate text-right text-[11px] text-surface-content/65"
				title={producers.join(', ')}
			>
				<CommaList items={producers} wrap={false} />
			</span>
			<span class="tabular -ml-0.5 min-w-[2rem] text-right text-[10px] text-surface-content/65">
				{song.view_count ? formatCount(song.view_count) : ''}
			</span>
		</div>
	</div>
{/snippet}

<!-- The popular tracks in the container of the tracklist of an album, without its bite, its gear and its top row, and
     with the rows of that tracklist (see `Tracklist`: the same classes). The card has no padding of its own, like there: the
     rows run to its edges and carry the room (`px-3.5`), so the cover stands where it stood. No numbers: the order is the order of views. -->
{#if list.items.length}
	<section class="rounded-xl bg-surface-200">
		<ul class="py-2">
			{#each list.items as song (song.id)}
				<li>
					<a href={resolve('/songs/[id]', { id: String(song.id) })} class={ROW}>
						{@render row(song)}
					</a>
				</li>
			{/each}
		</ul>
	</section>
{/if}

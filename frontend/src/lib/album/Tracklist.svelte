<script lang="ts">
	import { resolve } from '$app/paths';
	import type { AlbumTrack } from '#lib/api.js';
	import { byDisc, differs, ofAlbum, popularity, trackNumbers } from '#lib/albums.js';
	import { formatCount } from '#lib/format.js';
	import Chip from '#lib/ui/Chip.svelte';
	import ExplicitMark from '#lib/ui/ExplicitMark.svelte';
	import CommaList from '#lib/ui/CommaList.svelte';
	import Thumb from '#lib/ui/Thumb.svelte';

	type Props = { tracks: AlbumTrack[]; artists: { id: number }[] };

	let { tracks, artists }: Props = $props();

	const discs = $derived(byDisc(tracks));
	const numbers = $derived(trackNumbers(tracks));
	// The most viewed track gets the dot instead of its number.
	const rank = $derived(popularity(tracks));

	const names = (list: { base_name: string }[]) => list.map((a) => a.base_name);

	const ROW =
		'grid h-full grid-cols-[1rem_2rem_minmax(0,1fr)] items-stretch gap-1.5 rounded-lg px-1 py-1.5 hover:bg-black/20';
</script>

{#snippet row(track: AlbumTrack, number: number)}
	{@const place = rank.get(track.song_id)}
	{@const second = differs(track.artists, artists)}
	<!-- The number and the picture are centred in the row. Everything written (the title,
	     the featured artists, the producers, the views) stands on ONE baseline, the baseline of the title: it
	     is a row of its own, aligned by baseline and centred as a whole. -->
	<!-- A row with a second line (other artists) has the title above the middle; the number stands beside the
	     title all the same: it has the same two lines, the second one invisible. -->
	<span class="flex flex-col items-center justify-center">
		<!-- The line has the size of the title (the small number stands in it), so its baseline is the baseline of the
		     title. The most viewed track has a small dot of the colour of the numbers instead of its number (standing on the baseline). -->
		<span class="block text-center text-sm leading-snug text-surface-content/60">
			{#if place === 1}
				<span
					title="The most viewed track"
					class="relative -top-[0.6px] inline-block size-[4px] rounded-full bg-current align-baseline"
				></span>
			{:else}
				<span class="tabular text-[10px]">{number}</span>
			{/if}
		</span>
		{#if second}<span aria-hidden="true" class="invisible mt-0.5 text-xs leading-snug">.</span>{/if}
	</span>
	<span class="flex items-center"
		><Thumb src={track.cover_thumbnail_url} name="" class="size-8 rounded-md" /></span
	>
	<div class="flex min-w-0 items-center">
		<div class="flex w-full min-w-0 items-baseline gap-1.5 pr-0.5">
			<div class="flex min-w-0 flex-1 flex-col">
				<!-- One line, always: what does not fit is cut with "…" (the title last, then the featured artists). -->
				<div class="flex min-w-0 items-baseline gap-1.5">
					<span class="truncate text-sm leading-snug text-surface-content">
						{track.base_name}{#if track.variant}<span class="ml-1.5 text-surface-content/65"
								>{track.variant}</span
							>{/if}
					</span>
					{#if track.featured.length}
						<span class="min-w-0 shrink-[3] truncate text-xs text-surface-content/65"
							>feat. <CommaList
								items={names(track.featured)}
								wrap={false}
								tinted={ofAlbum(track.featured, artists)}
							/></span
						>
					{/if}
					{#if track.import_state === 'stub'}<Chip>Stub</Chip>{/if}
				</div>
				<!-- The artists of the album are known from the header: only a different line is worth showing. -->
				{#if second}
					<div class="mt-0.5 truncate text-xs leading-snug text-surface-content/65">
						<CommaList
							items={names(track.artists)}
							wrap={false}
							tinted={ofAlbum(track.artists, artists)}
						/>
					</div>
				{/if}
			</div>
			<span
				class="-mr-[5px] max-w-[6.25rem] truncate text-right text-[11px] text-surface-content/65"
				title={names(track.producers).join(', ')}
			>
				<CommaList
					items={names(track.producers)}
					wrap={false}
					tinted={ofAlbum(track.producers, artists)}
				/>
			</span>
			<!-- The explicit mark stands between the producers and the views, 4px from each, centred on the line of the numbers
			     (not on its baseline). It is part of the group of the views and follows their width, so the views still end
			     every row at the same place. The views come first in the group (and the group runs backwards), so that the
			     group stands on their baseline like everything else in the row. -->
			<span
				class="flex min-w-[2rem] shrink-0 flex-row-reverse items-center gap-[4px] {track.explicit
					? 'ml-[3.75px]'
					: '-ml-[1.75px]'}"
			>
				<span
					class="tabular text-[10px] text-surface-content/65"
					title={place ? `Top ${place} by views` : undefined}
				>
					{track.view_count ? formatCount(track.view_count) : ''}
				</span>
				{#if track.explicit}
					<!-- The numbers and the producers stand on one baseline, but their lines are not equally high: their centres are
					     2.3px apart, and the mark is put between them (measured). -->
					<ExplicitMark class="size-[10px] translate-y-[1.1px] text-surface-content/60" />
				{/if}
			</span>
		</div>
	</div>
{/snippet}

{#if !tracks.length}
	<p class="p-3 text-center text-sm text-surface-content/60">No tracks</p>
{:else}
	{#each discs as disc (disc.number)}
		{#if discs.length > 1}
			<h3 class="pt-3 pb-1 pl-[0.55rem] text-xs text-surface-content/60">Disc {disc.number}</h3>
		{/if}
		<ol>
			{#each disc.tracks as track (track.id)}
				<li>
					<a href={resolve('/songs/[id]', { id: String(track.song_id) })} class={ROW}>
						{@render row(track, numbers[track.id])}
					</a>
				</li>
			{/each}
		</ol>
	{/each}
{/if}

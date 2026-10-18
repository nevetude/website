<script lang="ts">
	import type { AlbumTrack } from '#lib/api.js';
	import { byDisc, differs, popularity, trackNumbers } from '#lib/albums.js';
	import { formatCount } from '#lib/format.js';
	import Chip from '#lib/ui/Chip.svelte';
	import CommaList from '#lib/ui/CommaList.svelte';
	import ExtLink from '#lib/ui/ExtLink.svelte';
	import Thumb from '#lib/ui/Thumb.svelte';

	type Props = { tracks: AlbumTrack[]; artists: { id: number }[] };

	let { tracks, artists }: Props = $props();

	const discs = $derived(byDisc(tracks));
	const numbers = $derived(trackNumbers(tracks));
	// The five best-viewed tracks show their views in the full colour, the others dimmed.
	const rank = $derived(popularity(tracks));

	const names = (list: { base_name: string }[]) => list.map((a) => a.base_name);

	const ROW =
		'grid h-full grid-cols-[1.25rem_2rem_minmax(0,1fr)] items-stretch gap-2 rounded-lg px-1.5 py-1.5 hover:bg-black/20';
</script>

{#snippet row(track: AlbumTrack, number: number)}
	{@const place = rank.get(track.song_id)}
	{@const second = differs(track.artists, artists)}
	<!-- The number and the picture are centred in the row. Everything written (the title, the explicit mark,
	     the featured artists, the producers, the views) stands on ONE baseline, the baseline of the title: it
	     is a row of its own, aligned by baseline and centred as a whole. -->
	<!-- A row with a second line (other artists) has the title above the middle; the number stands beside the
	     title all the same: it has the same two lines, the second one invisible. -->
	<span class="flex flex-col items-center justify-center">
		<!-- The line has the size of the title (the small number stands in it), so its baseline is the baseline of the
		     title. The most viewed track has a big dot of the colour of the numbers instead of its number (about as tall as a digit, standing on the baseline). -->
		<span class="block text-center text-sm leading-snug text-surface-content/60">
			{#if place === 1}
				<span
					title="The most viewed track"
					class="relative -top-[0.6px] inline-block size-[6px] rounded-full bg-current align-baseline"
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
		<div class="flex w-full min-w-0 items-baseline gap-2 pr-1">
			<div class="flex min-w-0 flex-1 flex-col">
				<!-- One line, always: what does not fit is cut with "…" (the title last, then the featured artists). -->
				<div class="flex min-w-0 items-baseline gap-1.5">
					<span class="truncate text-sm leading-snug text-surface-content">
						{track.base_name}{#if track.variant}<span class="ml-1.5 text-surface-content/65"
								>{track.variant}</span
							>{/if}
					</span>
					{#if track.explicit}
						<!-- The Tabler `explicit` icon, cropped to its frame, with rounder corners (radius 3 of 16). Nothing of its own in the flow, so its baseline is its bottom edge: it stands on the baseline of the
						     title, about as tall as its capitals. Then 0.45px down: measured on the pixels, the frame is
						     that much higher than the capitals, which is what the eye sees, so its centre is put on theirs. -->
						<svg
							viewBox="3.5 3.5 17 17"
							role="img"
							aria-label="Explicit"
							class="size-[10px] shrink-0 translate-y-[0.45px] text-surface-content/60"
							fill="none"
							stroke="currentColor"
							stroke-width="1.5"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<title>Explicit</title>
							<path
								d="M4 7a3 3 0 0 1 3 -3h10a3 3 0 0 1 3 3v10a3 3 0 0 1 -3 3h-10a3 3 0 0 1 -3 -3z"
							/>
							<path d="M14 8h-4v8h4" />
							<path d="M14 12h-4" />
						</svg>
					{/if}
					{#if track.featured.length}
						<span class="min-w-0 shrink-[3] truncate text-xs text-surface-content/65"
							>feat. <CommaList items={names(track.featured)} wrap={false} /></span
						>
					{/if}
					{#if track.import_state === 'stub'}<Chip>Stub</Chip>{/if}
				</div>
				<!-- The artists of the album are known from the header: only a different line is worth showing. -->
				{#if second}
					<div class="mt-0.5 truncate text-xs leading-snug text-surface-content/65">
						<CommaList items={names(track.artists)} wrap={false} />
					</div>
				{/if}
			</div>
			<span
				class="-mr-[5px] max-w-[5.5rem] truncate text-right text-[11px] text-surface-content/65"
				title={names(track.producers).join(', ')}
			>
				<CommaList items={names(track.producers)} wrap={false} />
			</span>
			<span
				class="tabular -ml-0.5 min-w-[2rem] text-right text-[10px] {place
					? 'text-surface-content'
					: 'text-surface-content/65'}"
				title={place ? `Top ${place} by views` : undefined}
			>
				{track.view_count ? formatCount(track.view_count) : ''}
			</span>
		</div>
	</div>
{/snippet}

{#if !tracks.length}
	<p class="p-3 text-center text-sm text-surface-content/60">No tracks</p>
{:else}
	{#each discs as disc (disc.number)}
		{#if discs.length > 1}
			<h3 class="px-2 pt-3 pb-1 text-xs font-medium text-surface-content/60">Disc {disc.number}</h3>
		{/if}
		<ol>
			{#each disc.tracks as track (track.id)}
				<li>
					{#if track.genius_url}
						<ExtLink href={track.genius_url} class={ROW}>
							{@render row(track, numbers[track.id])}
						</ExtLink>
					{:else}
						<div class={ROW}>{@render row(track, numbers[track.id])}</div>
					{/if}
				</li>
			{/each}
		</ol>
	{/each}
{/if}

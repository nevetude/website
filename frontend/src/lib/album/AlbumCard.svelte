<script lang="ts">
	import PanelTop from '@lucide/svelte/icons/panel-top';
	import { resolve } from '$app/paths';
	import type { ArtistAlbum } from '#lib/api.js';
	import { formatFullDate, formatRelease } from '#lib/format.js';
	import CommaList from '#lib/ui/CommaList.svelte';

	// `note` is a third line under the artists of a grid card (how the album is related to the one on the page).
	type Props = {
		album: ArtistAlbum;
		layout?: 'grid' | 'list';
		height: number;
		cover: number;
		note?: string;
	};

	let { album, layout = 'grid', height, cover, note }: Props = $props();

	const year = $derived(formatRelease(album.release_date, 'year'));
	// Credited only (a remix, a production): nobody is listed on the album, so show the artist's roles.
	const byline = $derived(album.artists.length ? album.artists : [...album.roles].sort());
	const labels = $derived(album.labels);
	const fullDate = $derived(formatFullDate(album.release_date, album.release_date_precision));
	const tracks = $derived(`${album.tracks_count} ${album.tracks_count === 1 ? 'Track' : 'Tracks'}`);
	// Hovering the name shows the whole title with the addition in brackets; the icon shows only the addition.
	const tip = $derived(album.variant ? `${album.base_name} (${album.variant})` : album.base_name);

	const list = $derived(layout === 'list');
</script>

{#snippet title()}
	<!-- The addition to the title (Live, Deluxe, ...) stays as text of the same size, darker, and the icon marks it. -->
	<span
		class="min-w-0 flex-1 text-[13px] leading-5 font-medium {list ? 'line-clamp-2' : 'truncate'}"
		title={tip}
	>
		{album.base_name}
		{#if album.variant}<span class="font-normal text-surface-content/50">{album.variant}</span>{/if}
	</span>
	{#if album.variant}
		<span title={album.variant} class="shrink-0 text-surface-content/50">
			<PanelTop class="size-4" aria-label={album.variant} />
		</span>
	{/if}
{/snippet}

<a
	href={resolve('/albums/[id]', { id: String(album.id) })}
	style:height="{height}px"
	style:transition="height 200ms ease-out, color 150ms ease-out"
	class="group/card flex overflow-hidden rounded-lg p-3 text-left text-surface-content hover:bg-white/8 hover:text-white {list
		? ''
		: 'flex-col items-stretch gap-1'}"
>
	<!-- The rows view stands where two cards of the grid stood, with the same padding around it. -->
	<div
		class={list ? 'flex min-w-0 flex-1 overflow-hidden rounded-lg' : 'contents'}
		style:height={list ? `${cover}px` : undefined}
	>
		<!-- In the rows view the cover has its size in px, whatever the card height is doing: when the
		     height eases between the views the cover is cut off below, never squeezed. -->
		<div
			class="overflow-hidden bg-surface-300 {list ? 'shrink-0' : 'aspect-square w-full rounded-lg'}"
			style:width={list ? `${cover}px` : undefined}
			style:height={list ? `${cover}px` : undefined}
		>
			{#if album.cover_url}
				<img src={album.cover_url} alt="" loading="lazy" class="block size-full object-cover" />
			{/if}
		</div>

		{#if !list}
			<div class="flex items-start gap-1.5">{@render title()}</div>
			<div
				class="flex items-baseline justify-between gap-2 text-xs leading-4 text-surface-content/50"
			>
				<span class="truncate"><CommaList items={byline} /></span>
				{#if year}<span class="tabular shrink-0">{year}</span>{/if}
			</div>
			{#if note}<div class="truncate text-left text-xs leading-4 text-surface-content/50">
					{note}
				</div>{/if}
		{:else}
			<!-- A rectangle that continues the cover, on a darker ground that lights up on hover. The card is only as tall as
			     the cover: a long title or many artists are cut short and never make it taller. -->
			<div
				class="flex min-w-0 flex-1 flex-col gap-1 bg-surface-300 px-3 py-2.5 group-hover/card:bg-surface-100"
			>
				<div class="flex items-start gap-1.5">{@render title()}</div>
				<div class="truncate text-[11px] text-surface-content/70" title={byline.join(', ')}>
					<CommaList items={byline} />
				</div>
				{#if labels.length}
					<div class="truncate text-[11px] text-surface-content/50" title={labels.join(', ')}>
						<CommaList items={labels} />
					</div>
				{/if}
				<div class="tabular mt-auto shrink-0 text-[11px] leading-snug text-surface-content/50">
					<div>{fullDate ?? 'No date'}</div>
					{#if album.tracks_count}<div>{tracks}</div>{/if}
					{#if album.import_state === 'stub'}<div>Stub</div>{/if}
				</div>
			</div>
		{/if}
	</div>
</a>

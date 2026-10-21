<script lang="ts">
	import { resolve } from '$app/paths';
	import type { AlbumDetail } from '#lib/api.js';
	import { languageName } from '#lib/albums.js';
	import { formatFullDate } from '#lib/format.js';
	import FactRow from '#lib/entity/FactRow.svelte';
	import Chip from '#lib/ui/Chip.svelte';
	import ClampList from '#lib/ui/ClampList.svelte';
	import CommaList from '#lib/ui/CommaList.svelte';
	import ExtLink from '#lib/ui/ExtLink.svelte';

	let { album }: { album: AlbumDetail } = $props();

	// A mockup: what will come from another source is written as the name of its field.
	const MOCK = {
		collective: 'Collective',
		country: 'Country',
		scenes: 'Scenes',
		genres: ['Genre', 'Genre'],
		subgenres: ['Genre', 'Genre', 'Genre']
	};

	// "ep" is an abbreviation; any other type is written with a capital letter.
	const typeName = (type: string) => (type === 'ep' ? 'EP' : type[0].toUpperCase() + type.slice(1));

	const labels = $derived(album.credits.find((group) => group.role === 'Label')?.artists ?? []);
	const date = $derived(formatFullDate(album.release_date, album.release_date_precision));
</script>

<!-- Two blocks, for the two rows of the grid of the page: the title with the facts of the release, and the facts about it. -->
<header
	class="space-y-5 rounded-t-xl bg-surface-200 px-4 pt-4 min-[1200px]:col-start-1 min-[1200px]:row-start-1"
>
	<div class="space-y-2">
		<!-- One line, always: a long title is cut with "…" (the whole of it is in the tooltip), so the header keeps its height. -->
		<h1
			title={[album.base_name, album.variant, album.disambiguator].filter(Boolean).join(' ')}
			class="truncate text-2xl leading-tight font-bold text-surface-content xl:text-3xl"
		>
			<!-- For now the title leads to the album on Genius. -->
			{#if album.genius_url}
				<ExtLink href={album.genius_url} title="Open on Genius">
					{album.base_name}
				</ExtLink>
			{:else}{album.base_name}{/if}
			{#if album.variant}<span class="font-normal text-surface-content/45">{album.variant}</span
				>{/if}
			{#if album.disambiguator}
				<span class="text-base font-normal text-surface-content/45">{album.disambiguator}</span>
			{/if}
		</h1>
		{#if album.artists.length}
			<p
				title={album.artists.map((artist) => artist.base_name).join(', ')}
				class="truncate text-lg font-medium text-surface-content/90"
			>
				<!-- No <wbr>: it would let the line break although it is "nowrap". -->
				{#each album.artists as artist, i (artist.id)}{#if i}<span
							class="mr-[0.3em] text-surface-content/40">,</span
						>{/if}<a href={resolve('/artists/[id]', { id: String(artist.id) })} class="artist"
						>{artist.base_name}</a
					>{/each}
			</p>
		{/if}
	</div>

	<!-- Two groups: the facts of the release itself and the facts about it. The first one always has its four rows
	     (an unknown label is a dash), so the second one starts at the same place on every album. -->
	<dl>
		<FactRow label="Type">
			{#if album.album_type}{typeName(album.album_type)}{:else}<span class="text-surface-content/40"
					>—</span
				>{/if}
			{#if album.is_released === false}<Chip tone="warn">Unreleased</Chip>{/if}
			{#if album.import_state === 'stub'}<Chip tone="warn">Stub: not imported in full</Chip>{/if}
		</FactRow>
		<FactRow label="Released">{date ?? 'No date'}</FactRow>
		<FactRow label="Label">
			{#if labels.length}
				<ClampList items={labels} lines={1} float>
					{#snippet item({ artist })}<a href={resolve('/artists/[id]', { id: String(artist.id) })}
							>{artist.base_name}</a
						>{/snippet}
				</ClampList>
			{:else}<span class="text-surface-content/40">—</span>{/if}
		</FactRow>
		<FactRow label="Collective">{MOCK.collective}</FactRow>
	</dl>
</header>

<!-- The facts about the release, in two parts for two rows of the grid of the page: the tiles of the descriptors
     stand beside the second one, whatever the first one holds. The title and the groups share one grey panel: the
     gap before this group is padding, not margin, so the grey has no seam. -->
<dl class="bg-surface-200 px-4 pt-[12.8px] min-[1200px]:col-start-1 min-[1200px]:row-start-2">
	<FactRow label="Country">{MOCK.country}</FactRow>
	{#if album.language}<FactRow label="Language">{languageName(album.language)}</FactRow>{/if}
</dl>
<dl class="rounded-b-xl bg-surface-200 px-4 min-[1200px]:col-start-1 min-[1200px]:row-start-3">
	<FactRow label="Scenes">{MOCK.scenes}</FactRow>
	<FactRow label="Genres">
		<CommaList items={MOCK.genres} />
		<div class="text-xs leading-snug text-surface-content/65">
			<CommaList items={MOCK.subgenres} />
		</div>
	</FactRow>
</dl>

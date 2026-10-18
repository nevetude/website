<script lang="ts">
	import type { ArtistDetail } from '#lib/api.js';
	import FactRow from '#lib/entity/FactRow.svelte';
	import { formatCount, formatFullDate } from '#lib/format.js';
	import Chip from '#lib/ui/Chip.svelte';
	import ClampList from '#lib/ui/ClampList.svelte';
	import ExtLink from '#lib/ui/ExtLink.svelte';

	let { artist }: { artist: ArtistDetail } = $props();

	const typeName = (type: string) => type[0].toUpperCase() + type.slice(1);
	// The full name, when the page shows the short one; or what tells two artists of one name apart.
	const subtitle = $derived(
		artist.disambiguator ?? (artist.name !== artist.base_name ? artist.name : null)
	);
	const works = $derived(
		[
			artist.albums_count &&
				`${artist.albums_count} ${artist.albums_count === 1 ? 'album' : 'albums'}`,
			artist.songs_count && `${artist.songs_count} ${artist.songs_count === 1 ? 'song' : 'songs'}`
		].filter(Boolean)
	);
	// Only the facts that are known: Genius has no place of birth or death as a field, so there is no row for them.
	const person = $derived(
		[
			{ label: 'Real name', value: artist.real_name },
			{
				label: 'Born',
				value: artist.born && formatFullDate(artist.born.date, artist.born.precision)
			},
			{
				label: 'Died',
				value: artist.died && formatFullDate(artist.died.date, artist.died.precision)
			}
		].filter((row) => row.value)
	);
</script>

<header class="space-y-5">
	<div class="space-y-2">
		<!-- One line, always: a long name is cut with "…" (the whole of it is in the tooltip). -->
		<h1
			title={artist.base_name}
			class="truncate text-2xl leading-tight font-bold text-surface-content xl:text-3xl"
		>
			<!-- For now the name leads to the artist on Genius. -->
			{#if artist.genius_url}
				<ExtLink href={artist.genius_url} title="Open on Genius">{artist.base_name}</ExtLink>
			{:else}{artist.base_name}{/if}
		</h1>
		{#if subtitle}
			<p title={subtitle} class="truncate text-lg font-medium text-surface-content/90">
				{subtitle}
			</p>
		{/if}
	</div>

	<dl>
		<FactRow label="Type">
			{#if artist.artist_type}{typeName(artist.artist_type)}{:else}<span
					class="text-surface-content/40">—</span
				>{/if}
			{#if artist.import_state === 'stub'}<Chip tone="warn">Stub: not imported in full</Chip>{/if}
			{#if artist.is_meme_verified}<Chip>Meme verified</Chip>{/if}
		</FactRow>
		<FactRow label="Followers">
			{#if artist.followers_count}{formatCount(artist.followers_count)}{:else}<span
					class="text-surface-content/40">—</span
				>{/if}
		</FactRow>
		{#if works.length}<FactRow label="Works">{works.join(' · ')}</FactRow>{/if}
		{#if artist.aliases.length}
			<FactRow label="Also known as">
				<ClampList items={artist.aliases} lines={1} float>
					{#snippet item(alias)}{alias}{/snippet}
				</ClampList>
			</FactRow>
		{/if}
	</dl>
	{#if person.length}
		<dl>
			{#each person as row (row.label)}<FactRow label={row.label}>{row.value}</FactRow>{/each}
		</dl>
	{/if}
</header>

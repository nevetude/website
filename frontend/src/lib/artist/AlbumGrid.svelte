<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { api, type ArtistAlbum, type WorkRoleCount } from '#lib/api.js';
	import AlbumCategory from '#lib/album/AlbumCategory.svelte';
	import { PagedList } from '#lib/paged.svelte.js';
	import RoleFlags from '#lib/ui/RoleFlags.svelte';
	import SortMenu from '#lib/ui/SortMenu.svelte';
	import ViewToggle from '#lib/ui/ViewToggle.svelte';

	let { artistId, roles }: { artistId: number; roles: WorkRoleCount[] } = $props();

	const PAGE = 200; // the most one call gives; an artist has a few hundred albums at most
	type Sort = 'released' | 'name';
	const SORTS: { value: Sort; label: string; first: 'asc' | 'desc' }[] = [
		{ value: 'released', label: 'Released', first: 'desc' },
		{ value: 'name', label: 'Alphabet', first: 'asc' }
	];
	// The kinds of release Genius knows, in the order a discography is read.
	const CATEGORIES = [
		{ type: 'album', title: 'Albums' },
		{ type: 'mixtape', title: 'Mixtapes' },
		{ type: 'ep', title: 'EPs' },
		{ type: 'single', title: 'Singles' },
		{ type: 'compilation', title: 'Compilations' },
		{ type: 'soundtrack', title: 'Soundtracks' },
		{ type: 'live', title: 'Live' },
		{ type: 'other', title: 'Other' }
	];
	const KNOWN = new Set(CATEGORIES.map((category) => category.type));

	let sort = $state<Sort>('released');
	let order = $state<'asc' | 'desc' | null>(null);
	let selected = $state<string[]>([]);
	let unreleased = $state(false);
	let openAll = $state(false);
	let view = $state<'grid' | 'list'>('grid');

	const list = new PagedList<ArtistAlbum>(async (offset) => {
		const { data } = await api.GET('/api/v1/artists/{artist_id}/albums', {
			params: {
				path: { artist_id: artistId },
				query: {
					roles: selected,
					include_unreleased: unreleased,
					sort,
					order: order ?? undefined,
					limit: PAGE,
					offset
				}
			}
		});
		return data;
	});

	// All the albums are loaded, because the categories are made here and each one needs all of its own.
	$effect(() => {
		void [sort, order, selected, unreleased];
		void list.reload(true);
	});

	// A type Genius adds one day (or none at all) goes to "Other".
	const kindOf = (album: ArtistAlbum) =>
		album.album_type && KNOWN.has(album.album_type) ? album.album_type : 'other';

	const groups = $derived(
		CATEGORIES.map(({ type, title }) => ({
			title,
			albums: list.items.filter((album) => kindOf(album) === type)
		})).filter((group) => group.albums.length)
	);
</script>

<section class="space-y-4 rounded-xl bg-surface-200 p-5">
	<header class="flex flex-wrap items-center gap-x-4 gap-y-2">
		<!-- Like the name of a category: the title with its chevron opens or closes every list at once. -->
		<button
			type="button"
			aria-expanded={openAll}
			title="{openAll ? 'Hide' : 'Show'} all lists ({list.items.length} releases)"
			class="group/title flex items-center gap-1.5 text-surface-content hover:text-white"
			onclick={() => (openAll = !openAll)}
		>
			<h2 class="text-base font-semibold">Releases</h2>
			{#if openAll}<ChevronDown
					class="size-4 text-surface-content/60 group-hover/title:text-white"
				/>{:else}<ChevronRight
					class="size-4 text-surface-content/60 group-hover/title:text-white"
				/>{/if}
		</button>
		<div class="ml-auto flex items-center gap-2">
			<ViewToggle bind:value={view} />
			<SortMenu options={SORTS} bind:sort bind:order />
		</div>
	</header>
	<RoleFlags roles={roles.map(({ role, works }) => ({ role, count: works }))} bind:selected>
		{#snippet end()}
			<button
				type="button"
				aria-pressed={unreleased}
				class="rounded-md px-2.5 py-1 text-[13px] {unreleased
					? 'bg-surface-content/15 text-surface-content'
					: 'bg-surface-100 text-surface-content/60 hover:text-surface-content'}"
				onclick={() => (unreleased = !unreleased)}
			>
				Unreleased
			</button>
		{/snippet}
	</RoleFlags>

	{#if list.failed}
		<p class="text-xs text-danger">The albums did not load.</p>
	{:else if !list.loading && !list.items.length}
		<p class="px-4 py-6 text-center text-sm text-surface-content/40">No albums</p>
	{:else}
		<div class="space-y-5">
			{#each groups as group (group.title)}
				<AlbumCategory
					title={group.title}
					albums={group.albums}
					{view}
					{openAll}
					resetKey="{sort}|{order}|{selected.join()}"
				/>
			{/each}
		</div>
	{/if}
</section>

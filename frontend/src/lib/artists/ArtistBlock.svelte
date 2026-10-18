<script lang="ts">
	import { api, type ArtistCard as Card, type RoleCount } from '#lib/api.js';
	import { SORTS, type Block, type Order, type SortField } from '#lib/artists.js';
	import ArtistCard from '#lib/artists/ArtistCard.svelte';
	import { PagedList } from '#lib/paged.svelte.js';
	import PagedFooter from '#lib/ui/PagedFooter.svelte';
	import RoleFlags from '#lib/ui/RoleFlags.svelte';
	import SortMenu from '#lib/ui/SortMenu.svelte';

	let { block }: { block: Block } = $props();

	const PAGE = 60;

	let sort = $state<SortField>('tracks');
	let order = $state<Order | null>(null);
	let selected = $state<string[]>([]);
	let roles = $state<RoleCount[]>([]);

	const list = new PagedList<Card>(async (offset) => {
		const { data } = await api.GET('/api/v1/artists', {
			params: {
				query: {
					...block.filters,
					roles: selected,
					sort,
					order: order ?? undefined,
					limit: PAGE,
					offset
				}
			}
		});
		return data;
	});

	// A new sort or a new set of roles starts the list again from the top.
	$effect(() => {
		void [sort, order, selected];
		void list.reload();
	});

	$effect(() => {
		void (async () => {
			const { data } = await api.GET('/api/v1/artists/roles', { params: { query: block.filters } });
			roles = data ?? [];
		})();
	});
</script>

<section class="space-y-3">
	<header class="flex flex-wrap items-center gap-x-4 gap-y-2">
		<h2 class="text-base font-semibold text-surface-content">{block.title}</h2>
		<span class="tabular font-mono text-xs text-surface-content/40">{list.total}</span>
		<div class="ml-auto"><SortMenu options={SORTS} bind:sort bind:order /></div>
	</header>

	<RoleFlags roles={roles.map(({ role, artists }) => ({ role, count: artists }))} bind:selected />

	{#if list.failed}
		<p class="text-xs text-danger">The list did not load. Is the backend running?</p>
	{:else if !list.loading && !list.items.length}
		<p
			class="rounded-xl border border-dashed border-white/10 px-4 py-6 text-center text-sm text-surface-content/40"
		>
			No artists
		</p>
	{:else}
		<div class="grid grid-cols-[repeat(auto-fill,minmax(17rem,1fr))] gap-3">
			{#each list.items as artist (artist.id)}
				<ArtistCard {artist} />
			{/each}
		</div>
		<PagedFooter {list} />
	{/if}
</section>

<script lang="ts">
	import PanelTop from '@lucide/svelte/icons/panel-top';
	import { api, type ArtistSong, type WorkRoleCount } from '#lib/api.js';
	import { formatCount, formatRelease } from '#lib/format.js';
	import { PagedList } from '#lib/paged.svelte.js';
	import Chip from '#lib/ui/Chip.svelte';
	import PagedFooter from '#lib/ui/PagedFooter.svelte';
	import RoleFlags from '#lib/ui/RoleFlags.svelte';
	import SongTitle from '#lib/ui/SongTitle.svelte';
	import SortMenu from '#lib/ui/SortMenu.svelte';
	import Thumb from '#lib/ui/Thumb.svelte';

	let { artistId, roles }: { artistId: number; roles: WorkRoleCount[] } = $props();

	const PAGE = 60;
	type Sort = 'released' | 'name' | 'views';
	const SORTS: { value: Sort; label: string; first: 'asc' | 'desc' }[] = [
		{ value: 'released', label: 'Released', first: 'desc' },
		{ value: 'name', label: 'Alphabet', first: 'asc' },
		{ value: 'views', label: 'Views', first: 'desc' }
	];

	let sort = $state<Sort>('released');
	let order = $state<'asc' | 'desc' | null>(null);
	let selected = $state<string[]>([]);

	const list = new PagedList<ArtistSong>(async (offset) => {
		const { data } = await api.GET('/api/v1/artists/{artist_id}/songs', {
			params: {
				path: { artist_id: artistId },
				query: {
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

	$effect(() => {
		void [sort, order, selected];
		void list.reload();
	});
</script>

<section class="space-y-3">
	<header class="flex flex-wrap items-center gap-x-4 gap-y-2">
		<h2 class="text-base font-semibold text-surface-content">Songs</h2>
		<span class="tabular font-mono text-xs text-surface-content/40">{list.total}</span>
		<div class="ml-auto"><SortMenu options={SORTS} bind:sort bind:order /></div>
	</header>
	<RoleFlags roles={roles.map(({ role, works }) => ({ role, count: works }))} bind:selected />

	{#if list.failed}
		<p class="text-xs text-danger">The songs did not load.</p>
	{:else if !list.loading && !list.items.length}
		<p
			class="rounded-xl border border-dashed border-white/10 px-4 py-6 text-center text-sm text-surface-content/40"
		>
			No songs
		</p>
	{:else}
		<ul
			class="divide-y divide-white/6 overflow-hidden rounded-xl border border-white/8 bg-surface-200"
		>
			{#each list.items as song (song.id)}
				<li class="flex items-center gap-3 px-3 py-2">
					<Thumb src={song.cover_thumbnail_url} name="" class="size-9 rounded-md" />
					<div class="min-w-0 flex-1">
						<div class="flex items-center gap-2">
							<SongTitle {song} />
							{#if song.variant}
								<!-- The icon marks the addition at the end of the line; hovering it names the addition. -->
								<span title={song.variant} class="ml-auto shrink-0 text-surface-content/50">
									<PanelTop class="size-4" aria-label={song.variant} />
								</span>
							{/if}
							{#if song.import_state === 'stub'}<Chip>Stub</Chip>{/if}
						</div>
						{#if song.album}
							<div class="truncate text-xs text-surface-content/50">{song.album}</div>
						{/if}
					</div>
					<div class="hidden max-w-64 flex-wrap justify-end gap-1 md:flex">
						{#each [...song.roles].sort() as role (role)}<Chip>{role}</Chip>{/each}
					</div>
					{#if song.genre}<span class="hidden text-xs text-surface-content/60 lg:block"
							>{song.genre}</span
						>{/if}
					<span
						class="tabular w-[5.5rem] shrink-0 text-right font-mono text-xs whitespace-nowrap text-surface-content/60"
					>
						{formatRelease(song.release_date, song.release_date_precision) ?? ''}
					</span>
					<span class="tabular w-14 shrink-0 text-right font-mono text-xs text-surface-content/60">
						{song.view_count ? formatCount(song.view_count) : ''}
					</span>
				</li>
			{/each}
		</ul>
		<PagedFooter {list} />
	{/if}
</section>

<script lang="ts">
	import Play from '@lucide/svelte/icons/play';
	import X from '@lucide/svelte/icons/x';
	import { Button } from 'svelte-ux';
	import { api, type ArtistVideo } from '#lib/api.js';
	import { formatCount } from '#lib/format.js';
	import { youtubeEmbedUrl, youtubeLink } from '#lib/dom.js';
	import { PagedList } from '#lib/paged.svelte.js';
	import SortMenu from '#lib/ui/SortMenu.svelte';

	let { artistId }: { artistId: number } = $props();

	const PAGE = 12;
	const SORTS = [
		{ value: 'released', label: 'Released', first: 'desc' as const },
		{ value: 'name', label: 'Alphabet', first: 'asc' as const },
		{ value: 'views', label: 'Views', first: 'desc' as const }
	];

	let sort = $state('released');
	let order = $state<'asc' | 'desc' | null>(null);
	let playing = $state<string | null>(null);

	const list = new PagedList<ArtistVideo>(async (offset) => {
		const { data } = await api.GET('/api/v1/artists/{artist_id}/videos', {
			params: {
				path: { artist_id: artistId },
				query: {
					sort: sort as 'name' | 'released' | 'views',
					order: order ?? undefined,
					limit: PAGE,
					offset
				}
			}
		});
		return data;
	});

	$effect(() => {
		void [sort, order];
		void list.reload();
	});

	// Only YouTube is embedded; a clip on another site has nothing to show here.
	const clips = $derived(
		list.items.flatMap((video) => {
			const link = youtubeLink(video.url);
			return link
				? [
						{
							...video,
							src: youtubeEmbedUrl(link.id, link.start || video.start_seconds || 0),
							picture: `https://i.ytimg.com/vi/${link.id}/mqdefault.jpg`
						}
					]
				: [];
		})
	);
	const current = $derived(clips.find((clip) => clip.url === playing));
	const playerSrc = $derived(
		current && `${current.src}${current.src.includes('?') ? '&' : '?'}autoplay=1`
	);
</script>

<!-- Empty (no clips at all, or none loaded yet): the block is not on the page. -->
{#if list.total > 0}
	<section class="space-y-3">
		<header class="flex flex-wrap items-center gap-x-4 gap-y-2">
			<h2 class="text-base font-semibold text-surface-content">Videos</h2>
			<span class="tabular font-mono text-xs text-surface-content/40">{list.total}</span>
			<div class="ml-auto"><SortMenu options={SORTS} bind:sort bind:order /></div>
		</header>

		{#if current && playerSrc}
			<div class="relative aspect-video max-w-3xl overflow-hidden rounded-lg bg-black">
				<iframe
					src={playerSrc}
					title={current.song_name}
					allow="autoplay; fullscreen"
					referrerpolicy="strict-origin-when-cross-origin"
					class="absolute inset-0 size-full"
				></iframe>
				<button
					type="button"
					aria-label="Close the clip"
					title="Close the clip"
					class="absolute top-2 right-2 flex size-6 items-center justify-center rounded-full bg-black/40 text-surface-content/70 transition-colors duration-200 ease-out hover:bg-black/70 hover:text-white"
					onclick={() => (playing = null)}
				>
					<X class="size-3.5" aria-hidden="true" />
				</button>
			</div>
		{/if}

		{#if list.failed}
			<p class="text-xs text-danger">The videos did not load.</p>
		{:else}
			<ul class="grid grid-cols-[repeat(auto-fill,minmax(14rem,1fr))] gap-3">
				{#each clips as clip (clip.url)}
					<li>
						<button
							type="button"
							aria-label="Play {clip.song_name}"
							aria-current={clip.url === playing}
							class="group relative block aspect-video w-full overflow-hidden rounded-t-lg bg-black"
							onclick={() => (playing = clip.url)}
						>
							<img
								src={clip.picture}
								alt=""
								loading="lazy"
								referrerpolicy="no-referrer"
								class="size-full object-cover {clip.url === playing ? 'opacity-40' : ''}"
							/>
							<span
								class="absolute inset-0 bg-black/0 transition-colors duration-200 ease-out {clip.url ===
								playing
									? ''
									: 'group-hover:bg-black/40'}"
								aria-hidden="true"
							></span>
							<span
								class="absolute top-1/2 left-1/2 flex size-9 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-black/60 transition-colors duration-200 ease-out group-hover:bg-black"
							>
								<Play class="size-4 fill-current text-white" aria-hidden="true" />
							</span>
						</button>
						<div class="rounded-b-xl bg-surface-200 px-3 py-2">
							<div class="truncate text-xs text-surface-content" title={clip.song_name}>
								{clip.song_name}{#if clip.variant}<span class="text-surface-content/50">
										{clip.variant}</span
									>{/if}
							</div>
							<div
								class="mt-0.5 flex h-4 items-baseline gap-2 text-[11px] leading-4 text-surface-content/60"
							>
								<span class="min-w-0 flex-1 truncate">{clip.artists.join(', ')}</span>
								{#if clip.view_count}
									<span class="tabular shrink-0">{formatCount(clip.view_count)}</span>
								{/if}
								{#if clip.release_date}
									<span class="tabular shrink-0">{clip.release_date.slice(0, 4)}</span>
								{/if}
							</div>
						</div>
					</li>
				{/each}
			</ul>
			{#if list.items.length < list.total}
				<div class="flex justify-center pt-1">
					<Button variant="fill-light" size="sm" loading={list.loading} onclick={() => list.more()}>
						Show more ({list.total - list.items.length})
					</Button>
				</div>
			{/if}
		{/if}
	</section>
{/if}

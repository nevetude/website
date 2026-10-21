<script lang="ts">
	import { resolve } from '$app/paths';
	import { api } from '#lib/api.js';
	import AlbumInfo from '#lib/album/AlbumInfo.svelte';
	import AlbumScore from '#lib/album/AlbumScore.svelte';
	import DebugData from '#lib/album/DebugData.svelte';
	import Descriptors from '#lib/album/Descriptors.svelte';
	import Gallery from '#lib/album/Gallery.svelte';
	import Credits from '#lib/album/Credits.svelte';
	import Facts from '#lib/album/Facts.svelte';
	import Lists from '#lib/album/Lists.svelte';
	import Reviews from '#lib/album/Reviews.svelte';
	import Description from '#lib/entity/Description.svelte';
	import OtherVersions from '#lib/album/OtherVersions.svelte';
	import ReleaseCard from '#lib/album/ReleaseCard.svelte';
	import TracklistCard from '#lib/album/TracklistCard.svelte';
	import Videos from '#lib/album/Videos.svelte';
	import { artistTint, coverHint, coverList, coverTint } from '#lib/albums.js';
	import ImportInfo from '#lib/entity/ImportInfo.svelte';
	import RawResponse from '#lib/entity/RawResponse.svelte';
	import Technical from '#lib/entity/Technical.svelte';
	import Breadcrumbs from '#lib/ui/Breadcrumbs.svelte';
	import Collapse from '#lib/ui/Collapse.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const album = $derived(data.album);
	const owner = $derived(album.artists[0]);
	const trail = $derived([
		...(owner
			? [{ label: owner.base_name, href: resolve('/artists/[id]', { id: String(owner.id) }) }]
			: []),
		{ label: album.base_name }
	]);
	const covers = $derived(coverList(album));
	// The ground of the smaller cards (the tracklist, the clips): the colour of the cover, darker than the big card.
	const tint = $derived(coverTint(album, true));
	// The tracklist and the signs of the clips: the plain grey of a panel with some of the colour of the cover in it.
	const hint = $derived(coverHint(album));
	// The names of the artists of the album, wherever they are on the page (`.artist` in `app.css`).
	const artistColor = $derived(artistTint(album));

	// The credits and the description are this high while they are closed: almost to the bottom of the screen.
	const COLLAPSED = 470;

	// The tiles of the descriptors open over the lower edge of the header (which is 380px high whatever is in it).
	// The column of the description moves down by as much as they stick out, nothing else moves.
	let playing = $state<string | null>(null); // the clip in the main place, see `Videos`
	let blocks = $state<Record<string, HTMLElement | undefined>>({}); // the blocks that move with the clips
	let tagsOpen = $state(false);
	let tagsFull = $state(0);
	let tagsBox = $state<HTMLElement | null>(null);
	let lowerRow = $state<HTMLElement | null>(null);
	const GAP = 12;
	const push = $derived.by(() => {
		if (!tagsOpen || !tagsBox || !lowerRow) return 0;
		const out =
			tagsBox.getBoundingClientRect().top + tagsFull - lowerRow.getBoundingClientRect().top;
		return Math.max(0, out + GAP);
	});
</script>

<svelte:head><title>{album.base_name} · Music</title></svelte:head>

<div style:--artist-color={artistColor}>
	<Breadcrumbs {trail} />

	{#key album.id}
		{@const albumId = album.id}
		<div class="space-y-10">
			<!-- Two rows. First: the coloured square of the release and the header with the main facts. Second: the
		     tracklist with what goes under it, and the credits with the description. The first row is 380px
		     high whatever is in it, so the line under the header never moves; every cell of the second row
		     starts right under it, and the tracklist lies over the lower edge of the coloured square.
		     On a narrow screen the header comes first. -->
			<div
				class="grid grid-cols-[minmax(0,1fr)] items-start gap-x-8 gap-y-6 min-[1000px]:grid-cols-[380px_minmax(0,1fr)] min-[1000px]:grid-rows-[380px_auto] min-[1000px]:gap-y-0"
			>
				<div class="order-2 min-[1000px]:order-none min-[1000px]:-mb-12 min-[1000px]:self-stretch">
					<ReleaseCard {album} {covers} />
				</div>
				<div class="order-1 min-[1000px]:order-none min-[1000px]:self-stretch">
					<!-- Three rows. The first: the title with the facts of the release, and the rating. The second: Country and
				     Language. The third: Scenes and Genres, and the tiles. The rating is as high as the first two rows, so the
				     tiles under it always stand beside Scenes. The last row takes what is left, so the grey panel of the facts ends
				     exactly where the tracklist begins, whatever it holds. Under 1200px everything is one column. -->
					<div
						class="grid grid-cols-[minmax(0,1fr)] gap-y-3 pb-6 min-[1000px]:h-full min-[1200px]:grid-cols-[minmax(0,1fr)_400px] min-[1200px]:grid-rows-[auto_auto_1fr] min-[1200px]:gap-x-8 min-[1200px]:gap-y-0 min-[1200px]:pb-0"
					>
						<AlbumInfo {album} />
						<AlbumScore />
						<Descriptors bind:open={tagsOpen} bind:full={tagsFull} bind:box={tagsBox} />
					</div>
				</div>
				<div class="relative z-10 order-3 space-y-6 min-[1000px]:order-none">
					<TracklistCard {album} tracks={data.tracks} tint={hint} />
					{#if album.related.length}<OtherVersions related={album.related} />{/if}
					<Lists />
					{#if playing}<Reviews />{/if}
				</div>
				<!-- The lower part: two columns. On the left the credits and the reviews. On the right the description, the
			     clips under it and the gallery. With a clip in the main place the clips take both columns in the first
			     row (see `Videos`) and everything else goes down: the left column beside the description. Under 1200px
			     it is one column in the order of the page. The rows are the same in both cases: the third one takes what
			     is left, so a tall left column does not push the right one apart. -->
				<div
					bind:this={lowerRow}
					class="order-4 grid grid-cols-[minmax(0,1fr)] items-start gap-y-8 min-[1000px]:order-none min-[1200px]:grid-cols-[minmax(0,1fr)_400px] min-[1200px]:grid-rows-[auto_auto_1fr] min-[1200px]:gap-x-8 min-[1200px]:gap-y-0"
				>
					<div
						bind:this={blocks.left}
						class="space-y-8 min-[1200px]:col-start-1 {playing
							? 'min-[1200px]:row-span-2 min-[1200px]:row-start-2 min-[1200px]:mt-8'
							: 'min-[1000px]:mt-10 min-[1200px]:row-span-3 min-[1200px]:row-start-1'}"
					>
						{#if album.credits.length}
							<Collapse height={COLLAPSED} fade="var(--color-surface-300)">
								<Credits groups={album.credits} main={album.artists} />
							</Collapse>
						{/if}
						{#if !playing}
							<Reviews />
							<Facts />
						{/if}
					</div>
					{#if album.description}
						<div
							bind:this={blocks.description}
							class="transition-[margin] duration-200 ease-out min-[1200px]:col-start-2 {playing
								? 'min-[1200px]:row-start-2 min-[1200px]:mt-8'
								: 'min-[1200px]:row-start-1'}"
							style:margin-top={playing || !push ? undefined : `${push}px`}
						>
							<Collapse height={COLLAPSED} fade="var(--color-surface-200)" class="rounded-xl">
								<Description
									dom={album.description_dom}
									text={album.description}
									refs={album.description_refs}
								/>
							</Collapse>
						</div>
					{/if}
					<Videos
						videos={data.videos}
						tracks={data.tracks}
						tint={hint}
						main={album.artists}
						bind:playing
						others={() => Object.values(blocks)}
						push={playing ? push : 0}
						class={playing
							? 'min-[1200px]:col-span-2 min-[1200px]:col-start-1 min-[1200px]:row-start-1 min-[1200px]:mt-8'
							: album.description
								? 'min-[1200px]:col-start-2 min-[1200px]:row-start-2 min-[1200px]:mt-8'
								: 'min-[1200px]:col-start-2 min-[1200px]:row-start-1'}
					/>
					<div
						bind:this={blocks.gallery}
						class="space-y-8 min-[1200px]:col-start-2 min-[1200px]:row-start-3 min-[1200px]:mt-8"
					>
						<Gallery {tint} />
						{#if playing}<Facts />{/if}
					</div>
				</div>
			</div>
			<Technical>
				<ImportInfo
					subject="album"
					createdAt={album.created_at}
					updatedAt={album.updated_at}
					imports={album.imports}
					history={album.history}
				/>
				<RawResponse
					stub="No raw response: the album is a stub."
					fetchRaw={async () =>
						(
							await api.GET('/api/v1/albums/{album_id}/raw', {
								params: { path: { album_id: albumId } }
							})
						).data}
				/>
				<DebugData {album} />
			</Technical>
		</div>
	{/key}
</div>

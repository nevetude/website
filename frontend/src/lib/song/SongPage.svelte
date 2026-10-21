<script lang="ts">
	import { untrack } from 'svelte';
	import { resolve } from '$app/paths';
	import { api } from '#lib/api.js';
	import type { Lyrics, SongDetail } from '#lib/api.js';
	import AlbumScore from '#lib/album/AlbumScore.svelte';
	import Credits from '#lib/album/Credits.svelte';
	import DebugData from '#lib/album/DebugData.svelte';
	import Descriptors from '#lib/album/Descriptors.svelte';
	import Facts from '#lib/album/Facts.svelte';
	import Gallery from '#lib/album/Gallery.svelte';
	import Lists from '#lib/album/Lists.svelte';
	import ReleaseCard from '#lib/album/ReleaseCard.svelte';
	import Reviews from '#lib/album/Reviews.svelte';
	import Videos from '#lib/album/Videos.svelte';
	import { artistTint, coverHint, coverTint } from '#lib/albums.js';
	import Description from '#lib/entity/Description.svelte';
	import ImportInfo from '#lib/entity/ImportInfo.svelte';
	import RawResponse from '#lib/entity/RawResponse.svelte';
	import Technical from '#lib/entity/Technical.svelte';
	import AppearsOn from '#lib/song/AppearsOn.svelte';
	import LyricsCard from '#lib/song/LyricsCard.svelte';
	import RelatedSongs from '#lib/song/RelatedSongs.svelte';
	import SongInfo from '#lib/song/SongInfo.svelte';
	import { songCredits, songTrack, songVideos } from '#lib/song.js';
	import Breadcrumbs from '#lib/ui/Breadcrumbs.svelte';
	import Collapse from '#lib/ui/Collapse.svelte';

	// Laid out like the page of an album (`routes/albums/[id]`), with the lyrics where the album has its credits: the
	// card of the lyrics (the title and the artists are its top) stands beside the cover, the facts and the credits are
	// under the cover, and the rating, the tiles, the description, the clips and the gallery are a column on the right.
	// `albumId`: the album the visitor came through, if any: it stands in the breadcrumbs between the artist and the song.
	type Props = { song: SongDetail; lyrics: Lyrics | null; albumId: number | null };

	let { song, lyrics, albumId }: Props = $props();

	const owner = $derived(song.artists[0]);
	const via = $derived(song.albums.find((placement) => placement.album.id === albumId)?.album);
	const trail = $derived([
		...(owner
			? [{ label: owner.base_name, href: resolve('/artists/[id]', { id: String(owner.id) }) }]
			: []),
		...(via
			? [{ label: via.base_name, href: resolve('/albums/[id]', { id: String(via.id) }) }]
			: []),
		{ label: song.base_name }
	]);
	const covers = $derived(song.cover_url ? [song.cover_url] : []);
	const tint = $derived(coverTint(song, true));
	const hint = $derived(coverHint(song));
	const artistColor = $derived(artistTint(song));
	const credits = $derived(songCredits(song));
	// The clips are made for the tracks of an album: the song is the one track they find.
	const tracks = $derived([songTrack(song)]);
	const videos = $derived(songVideos(song));

	// The credits and the description are this high while they are closed: almost to the bottom of the screen.
	const COLLAPSED = 470;

	let playing = $state<string | null>(null); // the clip in the main place, see `Videos`
	let blocks = $state<Record<string, HTMLElement | undefined>>({}); // the blocks that move with the clips

	// The top of the description (under the clip, on the right) stands on the line of the top of the facts (under the
	// cover, on the left). The gaps in the right column are all the same, so the rating, the one block there that holds
	// nothing, takes the difference in its height (`scoreHeight`, px; at least `MIN_SCORE`). Only while the columns are
	// side by side and no clip is in the main place; the measuring starts from the height the rating has now.
	const MIN_SCORE = 96;
	let leftColumn = $state<HTMLElement | null>(null);
	let region = $state<HTMLElement | null>(null);
	let factsBox = $state<HTMLElement | null>(null);
	let scoreHeight = $state<number | null>(null);

	function align() {
		const { score, description } = blocks;
		if (
			!matchMedia('(min-width: 1200px)').matches ||
			playing ||
			!factsBox ||
			!score ||
			!description
		) {
			scoreHeight = null;
			return;
		}
		const shift = factsBox.getBoundingClientRect().top - description.getBoundingClientRect().top;
		scoreHeight = Math.max(MIN_SCORE, Math.round(score.getBoundingClientRect().height + shift));
	}

	$effect(() => {
		void [song.id, playing, lyrics, factsBox];
		// One frame later, so that the room just given does not trigger the observer in the same frame.
		const observer = new ResizeObserver(() => requestAnimationFrame(() => untrack(align)));
		for (const element of [leftColumn, region]) if (element) observer.observe(element);
		untrack(align);
		return () => observer.disconnect();
	});
</script>

<svelte:head><title>{song.base_name} · Music</title></svelte:head>

<div style:--artist-color={artistColor}>
	<Breadcrumbs {trail} />

	{#key song.id}
		<div class="space-y-10">
			<div
				class="grid grid-cols-[minmax(0,1fr)] items-start gap-x-8 gap-y-6 min-[1000px]:grid-cols-[380px_minmax(0,1fr)]"
			>
				<!-- The left column: the cover (380px high, its last 3rem are under the facts, which lie over its lower edge as
				     the tracklist does on an album), the facts, the credits and what goes with them. -->
				<div bind:this={leftColumn} class="order-2 min-[1000px]:order-none">
					<div class="min-[1000px]:h-[380px]">
						<ReleaseCard album={song} {covers} />
					</div>
					<div class="relative z-10 mt-6 space-y-6 min-[1000px]:mt-0">
						<div bind:this={factsBox}><SongInfo {song} /></div>
						{#if credits.length}
							<Collapse height={COLLAPSED} fade="var(--color-surface-300)">
								<Credits groups={credits} main={song.artists} />
							</Collapse>
						{/if}
						{#if song.albums.length}<AppearsOn albums={song.albums} />{/if}
						{#if song.related.length}<RelatedSongs related={song.related} />{/if}
						<Lists />
						{#if playing}<Reviews />{/if}
					</div>
				</div>
				<!-- The right region is the lower part of an album page: two columns, and with a clip in the main place the
				     clips take both of them in the first row (see `Videos`). On the left the lyrics; on the right the rating,
				     the clips (one to a row, as wide as the column), the description, the gallery and, last, the tiles of the tags. The lyrics are as wide as their longest line (the text is
				     16px; the page is not wider for it), and the column on the right takes what is left, 14rem at the least: the
				     two gaps and that minimum are the 16rem the lyrics leave. Under 1200px it is one column. -->
				<div
					bind:this={region}
					class="order-1 grid grid-cols-[minmax(0,1fr)] items-start gap-y-8 min-[1000px]:order-none min-[1200px]:grid-cols-[fit-content(calc(100%_-_16rem))_minmax(14rem,1fr)] min-[1200px]:grid-rows-[auto_auto_auto_auto_1fr] min-[1200px]:gap-x-8 min-[1200px]:gap-y-0"
				>
					<div
						bind:this={blocks.left}
						class="space-y-6 min-[1200px]:col-start-1 {playing
							? 'min-[1200px]:row-span-4 min-[1200px]:row-start-2 min-[1200px]:mt-8'
							: 'min-[1200px]:row-span-5 min-[1200px]:row-start-1'}"
					>
						<LyricsCard {song} {lyrics} tint={hint} />
						{#if !playing}
							<Reviews />
							<Facts />
						{/if}
					</div>
					<div
						bind:this={blocks.score}
						class="min-[1200px]:col-start-2 {playing
							? 'min-[1200px]:row-start-2 min-[1200px]:mt-8'
							: 'min-[1200px]:row-start-1'}"
					>
						<AlbumScore
							class="min-[1200px]:mb-0! {scoreHeight === null ? 'h-40' : ''}"
							style={scoreHeight === null ? undefined : `height: ${scoreHeight}px`}
						/>
					</div>
					<Videos
						{videos}
						{tracks}
						tint={hint}
						main={song.artists}
						bind:playing
						others={() => Object.values(blocks)}
						single
						class={playing
							? 'min-[1200px]:col-span-2 min-[1200px]:col-start-1 min-[1200px]:row-start-1 min-[1200px]:mt-8'
							: 'min-[1200px]:col-start-2 min-[1200px]:row-start-2 min-[1200px]:mt-3'}
					/>
					{#if song.description}
						<div
							bind:this={blocks.description}
							class="min-[1200px]:col-start-2 min-[1200px]:row-start-3 min-[1200px]:mt-3"
						>
							<Collapse height={COLLAPSED} fade="var(--color-surface-200)" class="rounded-xl">
								<Description
									dom={song.description_dom}
									text={song.description}
									refs={song.description_refs}
								/>
							</Collapse>
						</div>
					{/if}
					<div
						bind:this={blocks.gallery}
						class="space-y-8 min-[1200px]:col-start-2 min-[1200px]:row-start-4 min-[1200px]:mt-3"
					>
						<Gallery {tint} class="gap-1.5" />
						{#if playing}<Facts />{/if}
					</div>
					<div
						bind:this={blocks.tags}
						class="min-[1200px]:col-start-2 min-[1200px]:row-start-5 min-[1200px]:mt-3"
					>
						<Descriptors words={song.tags} />
					</div>
				</div>
			</div>
			<Technical>
				<ImportInfo
					subject="song"
					createdAt={song.created_at}
					updatedAt={song.updated_at}
					imports={song.imports}
					history={song.history}
				/>
				<RawResponse
					stub="No raw response: the song is a stub."
					fetchRaw={async () =>
						(
							await api.GET('/api/v1/songs/{song_id}/raw', {
								params: { path: { song_id: song.id } }
							})
						).data}
				/>
				<DebugData album={song} />
			</Technical>
		</div>
	{/key}
</div>

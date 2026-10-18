<script lang="ts">
	import Clock from '@lucide/svelte/icons/clock';
	import Music from '@lucide/svelte/icons/music';
	import type { AlbumDetail, AlbumTrack } from '#lib/api.js';
	import Tracklist from '#lib/album/Tracklist.svelte';
	import NotchedCard from '#lib/ui/NotchedCard.svelte';

	let {
		album,
		tracks,
		tint
	}: { album: AlbumDetail; tracks: AlbumTrack[]; tint: string | undefined } = $props();

	// Mock until the player and the media sources exist: the album is 52 minutes, playing the 6th track at minute 30.
	const PLAYING = { track: 6, minutes: 30, total: 52 };
</script>

<NotchedCard label="Tracklist settings" {tint}>
	{#snippet header()}
		<span
			class="flex items-center gap-1.5"
			title="{album.tracks_count} {album.tracks_count === 1 ? 'track' : 'tracks'}"
		>
			<Music class="size-3.5" aria-hidden="true" />
			<span
				>{PLAYING.track}<span class="mx-[0.12em] text-surface-content/40">/</span
				>{album.tracks_count}</span
			>
		</span>
		<!-- The progress of the album, between the songs and the time. -->
		<div
			role="progressbar"
			aria-label="Album progress"
			aria-valuemin="0"
			aria-valuemax={PLAYING.total}
			aria-valuenow={PLAYING.minutes}
			class="mx-4 h-1 flex-1 rounded-full bg-black/30"
		>
			<div
				class="h-full rounded-full bg-surface-content/70"
				style:width="{(PLAYING.minutes / PLAYING.total) * 100}%"
			></div>
		</div>
		<span class="flex items-center gap-1.5" title="Length of the release">
			<Clock class="size-3.5" aria-hidden="true" />
			<span
				>{PLAYING.minutes}<span class="mx-[0.12em] text-surface-content/40">/</span
				>{PLAYING.total}<span class="text-surface-content/40">m</span></span
			>
		</span>
	{/snippet}
	<Tracklist {tracks} artists={album.artists} />
</NotchedCard>

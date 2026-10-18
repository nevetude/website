<script lang="ts">
	import Pause from '@lucide/svelte/icons/pause';
	import Play from '@lucide/svelte/icons/play';
	import { tick } from 'svelte';
	import type { AlbumTrack, AlbumVideo } from '#lib/api.js';
	import { trackNumbers } from '#lib/albums.js';
	import { formatFullDate } from '#lib/format.js';
	import { YOUTUBE_ORIGIN, youtubeEmbedUrl, youtubeLink } from '#lib/dom.js';
	import { glide } from '#lib/glide.js';
	import VideoCredits from '#lib/album/VideoCredits.svelte';

	// `playing` is the clip in the main place (the page puts this block in another place when there is one and moves
	// its other blocks, `others`, with it); `push` is the room the page asks for above.
	type Props = {
		videos: AlbumVideo[];
		tracks: AlbumTrack[]; // what the clips are signed with: the number of the track and its artists
		tint?: string; // the ground of the signs and of the credits: the colour of the cover, darker than the big card
		playing?: string | null;
		others?: () => (HTMLElement | null | undefined)[];
		push?: number;
		class?: string;
	};

	let {
		videos,
		tracks,
		tint,
		playing = $bindable(null),
		others = () => [],
		push = 0,
		class: className = ''
	}: Props = $props();

	// The clips Genius links from the songs of the album, the way the description shows a clip. Only YouTube is
	// embedded; the other sites have nothing to show here. A clip is a picture with a button (the picture is cached
	// by the browser, and a page of many clips does not load a player for each of them). There is one player, in the
	// main place: a pressed clip is played there instead of the one that played before, so two clips never play at
	// once, and the one that played before is a picture in the row again. When a clip is over the next one of the
	// tracklist is played, like a playlist; after the last one the player stays.
	const numbers = $derived(trackNumbers(tracks));
	const players = $derived(
		videos.flatMap((video) => {
			const link = youtubeLink(video.url);
			if (!link) return [];
			const start = link.start || video.start_seconds || 0;
			const src = new URL(youtubeEmbedUrl(link.id, start));
			src.searchParams.set('autoplay', '1');
			src.searchParams.set('enablejsapi', '1'); // the player tells the page when a clip is over
			src.searchParams.set('origin', location.origin);
			// Every clip is of a song of the tracklist: the server joins them.
			const track = tracks.find((one) => one.song_id === video.song_id)!;
			const names = (list: { base_name: string }[]) => list.map((one) => one.base_name).join(', ');
			return [
				{
					...video,
					number: numbers[track.id],
					year: video.release_date?.slice(0, 4),
					date: formatFullDate(video.release_date, video.release_date_precision),
					producers: names(track.producers),
					artists:
						names(track.artists) + (track.featured.length ? ` feat. ${names(track.featured)}` : ''),
					id: link.id,
					start,
					src: src.toString(),
					picture: `https://i.ytimg.com/vi/${link.id}/mqdefault.jpg`
				}
			];
		})
	);
	const current = $derived(players.find((video) => video.url === playing));

	let figures = $state<Record<string, HTMLElement | null>>({});
	let box = $state<HTMLElement | null>(null); // the main player
	let frame = $state<HTMLIFrameElement | null>(null);
	// The address the player was opened with. The next clips are loaded into the same player by a command (it is
	// not made again, so it stays on the whole screen and there is no new entry in the history of the page).
	let embed = $state<string | null>(null);
	let ready = false; // the player has answered, so it takes commands
	let sounding = $state(true); // the clip in the player is not paused and not over (it starts by itself)
	// The picture of the player is hidden (a black screen) while a clip is changed and shown again, smoothly, when
	// the new clip has begun; a clip that does not begin in time is shown anyway.
	let hidden = $state(false);
	let showTimer: ReturnType<typeof setTimeout> | undefined;
	const FADE_MS = 250;

	function hide() {
		hidden = true;
		clearTimeout(showTimer);
		showTimer = setTimeout(() => (hidden = false), 3000);
	}

	const tell = (message: object) =>
		frame?.contentWindow?.postMessage(JSON.stringify(message), YOUTUBE_ORIGIN);

	// The player reports its state once it has been told that somebody listens. 0 is "ended".
	const listen = () => tell({ event: 'listening', channel: 'widget' });

	// Every clip and every block of the page glides from the place it was in to the place it is in now.
	const moving = () => [...Object.values(figures), ...others()];

	async function play(url: string) {
		const video = players.find((one) => one.url === url);
		// The clip that plays now fades out to black before the next one is loaded.
		hide();
		if (playing !== null) await new Promise((done) => setTimeout(done, FADE_MS));
		await glide(moving(), async () => {
			if (video && playing !== null && ready) {
				tell({
					event: 'command',
					func: 'loadVideoById',
					args: [{ videoId: video.id, startSeconds: video.start }]
				});
			} else {
				ready = false;
				embed = video?.src ?? null;
			}
			sounding = true;
			playing = url;
			await tick();
			// The page follows the player, so that it does not leave the screen.
			box?.scrollIntoView({ block: 'nearest' });
		});
	}

	function onmessage(event: MessageEvent) {
		if (event.origin !== YOUTUBE_ORIGIN || event.source !== frame?.contentWindow) return;
		ready = true;
		const data = JSON.parse(event.data);
		const state = data.event === 'onStateChange' ? data.info : data.info?.playerState;
		if (typeof state === 'number') sounding = state !== 0 && state !== 2; // 0: over, 2: paused
		if (state === 1) {
			clearTimeout(showTimer);
			hidden = false; // the new clip has begun: it fades in
		}
		if (state !== 0) return;
		const next = players[players.findIndex((video) => video.url === playing) + 1];
		if (next) void play(next.url);
	}

	// The button of the clip that is in the player pauses and resumes it, the same button that started it; the
	// state comes back from the player (`sounding`), so the button also follows the controls of the big player.
	const toggle = () =>
		tell({ event: 'command', func: sounding ? 'pauseVideo' : 'playVideo', args: [] });

	const close = () =>
		glide(moving(), async () => {
			playing = null;
			embed = null;
			ready = false;
			await tick();
		});
</script>

<svelte:window {onmessage} />

{#if players.length}
	<!-- Closed, the block stands in the second column under the description: two clips in a row. With a clip in the
	     main place the page makes the block as wide as both columns and puts it first: the player (all the room that
	     the credits leave) with the credits beside it, and the other clips four in a row under them. Under 1200px
	     it is one column, the player over the whole width. -->
	<section
		class="space-y-3 transition-[margin] duration-200 ease-out {className}"
		style:margin-top={push ? `${push}px` : undefined}
		aria-label="Videos"
	>
		{#if current}
			<!-- The player and the credits of the clip are one piece: no gap, the rounding only on the outer corners. -->
			<div class="grid min-[1200px]:grid-cols-[minmax(0,1fr)_240px]">
				<div
					bind:this={box}
					class="relative aspect-video scroll-mt-16 overflow-hidden rounded-lg bg-black min-[1200px]:rounded-r-none"
				>
					<!-- The buttons of the YouTube player have one size whatever the size of the frame. The player is laid out
					     in a frame 1/s times the box and shown at s times, so that its interface is s times as big as it
					     is: now s = 0.864 (frame 115.741%, scale-[0.864]); it was 0.6 (frame 166.667%, scale-60). On the whole
					     screen it is drawn as it is. The next clip is loaded into it. -->
					<iframe
						bind:this={frame}
						onload={listen}
						src={embed}
						title={current.song_name}
						allow="autoplay; fullscreen"
						referrerpolicy="strict-origin-when-cross-origin"
						class="absolute top-0 left-0 size-[115.741%] origin-top-left scale-[0.864] transition-opacity duration-300 ease-out [&:fullscreen]:size-full [&:fullscreen]:scale-100 {hidden
							? 'opacity-0'
							: ''}"
					></iframe>
				</div>
				<VideoCredits
					info={{
						title: current.song_name,
						date: current.date,
						artists: current.artists,
						producers: current.producers
					}}
					{tint}
					onclose={close}
					class="hidden min-[1200px]:block min-[1200px]:rounded-l-none"
				/>
			</div>
		{/if}
		<div class="grid grid-cols-2 gap-3 {current ? 'min-[1200px]:grid-cols-4' : ''}">
			{#each players as video (video.url)}
				<figure bind:this={figures[video.url]}>
					<!-- The clip that is in the player stays in its place in the row: its picture is dimmed, bars dance on it
					     while it sounds and the button pauses it; paused, the button is a play button again. -->
					<button
						type="button"
						aria-label={video.url !== playing
							? `Play ${video.song_name}`
							: sounding
								? `Pause ${video.song_name}`
								: `Resume ${video.song_name}`}
						aria-current={video.url === playing}
						class="group relative block aspect-video w-full overflow-hidden rounded-t-lg bg-black"
						onclick={() => (video.url === playing ? toggle() : play(video.url))}
					>
						<img
							src={video.picture}
							alt=""
							loading="lazy"
							referrerpolicy="no-referrer"
							class="size-full object-cover {video.url === playing ? 'opacity-40' : ''}"
						/>
						<!-- The picture darkens smoothly under the pointer; the clip in the player is dimmed already, so only its button darkens. -->
						<span
							class="absolute inset-0 bg-black/0 transition-colors duration-200 ease-out {video.url ===
							playing
								? ''
								: 'group-hover:bg-black/40'}"
							aria-hidden="true"
						></span>
						<span
							class="absolute top-1/2 left-1/2 flex size-9 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-black/60 transition-colors duration-200 ease-out group-hover:bg-black"
						>
							{#if video.url === playing && sounding}
								<!-- Under the pointer the bars give way to the pause sign: this is where it is pressed. -->
								<Pause
									class="hidden size-4 fill-current text-white group-hover:block"
									aria-hidden="true"
								/>
								<span class="flex h-4 items-end gap-0.5 group-hover:hidden" aria-hidden="true">
									{#each [0, 1, 2] as bar (bar)}
										<span
											class="equalizer-bar w-1 rounded-full bg-white"
											style:animation-delay="{bar * -0.23}s"
											style:animation-duration="{0.9 + bar * 0.17}s"
										></span>
									{/each}
								</span>
							{:else}
								<Play class="size-4 fill-current text-white" aria-hidden="true" />
							{/if}
						</span>
					</button>
					<!-- The sign under the clip, in the style of the card of the album: the title and, pressed to the right, the number of the track; under them,
					     smaller, the artists and, pressed to the right under the number, the year of the song. -->
					<figcaption class="rounded-b-xl bg-surface-200 px-3 py-2" style:background-color={tint}>
						<div class="flex items-baseline gap-2 text-xs">
							<span class="min-w-0 flex-1 truncate text-surface-content">{video.song_name}</span>
							<span class="tabular shrink-0 text-surface-content/50">{video.number}</span>
						</div>
						<div
							class="mt-0.5 flex h-4 items-baseline gap-2 text-[11px] leading-4 text-surface-content/60"
						>
							<span class="min-w-0 flex-1 truncate">{video.artists}</span>
							<span class="tabular shrink-0">{video.year}</span>
						</div>
					</figcaption>
				</figure>
			{/each}
		</div>
	</section>
{/if}

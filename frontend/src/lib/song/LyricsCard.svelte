<script lang="ts">
	import Languages from '@lucide/svelte/icons/languages';
	import type { Lyrics, SongDetail } from '#lib/api.js';
	import { languageName } from '#lib/albums.js';
	import SongHeading from '#lib/song/SongHeading.svelte';
	import NotchedCard from '#lib/ui/NotchedCard.svelte';

	type Props = { song: SongDetail; lyrics: Lyrics | null; tint: string | undefined };

	let { song, lyrics, tint }: Props = $props();

	// The shape of a text, shown while the song has none: stanzas under their names, lines of every length. Genius
	// gives no lyrics and they are never scraped; they are put by hand in `lyrics/<genius id>.txt`
	// (`lyrics/demo.txt` stands in for every song that has no file).
	const STANZAS = [
		{ name: 'Verse 1', lines: [92, 78, 86, 70, 88, 64] },
		{ name: 'Chorus', lines: [84, 90, 58, 76] },
		{ name: 'Verse 2', lines: [88, 72, 80, 94, 66, 82] },
		{ name: 'Chorus', lines: [84, 90, 58, 76] },
		{ name: 'Outro', lines: [70, 46] }
	];
</script>

<!-- The language is written out in the bite of the card, where the tracklist of an album has its gear: 4.7rem is as
     wide as "English" with its icon, so the icon stands almost at the edge. -->
{#snippet language()}
	<span
		title="Language of the song"
		class="flex w-full min-w-0 items-center justify-end gap-1.5 pr-1.5 text-xs text-surface-content/80"
	>
		<Languages class="size-3.5 shrink-0" aria-hidden="true" />
		<span class="truncate">{song.language ? languageName(song.language) : '—'}</span>
	</span>
{/snippet}

<!-- The card of the tracklist of an album (`TracklistCard`) without its top row: the title and the artists of the song
     are its top, and the text of the song is under them. -->
<NotchedCard {tint} corner={language} bite="4.7rem">
	<div class="space-y-6 px-4 pt-1 pb-3">
		<!-- Room on the right for the bite. -->
		<div class="pr-[5.2rem]"><SongHeading {song} /></div>
		<div class="space-y-5">
			{#if lyrics}
				{#each lyrics.stanzas as stanza, i (i)}
					<section class="space-y-0.5">
						{#if stanza.title}
							<h3 class="text-xs font-medium text-surface-content/50">{stanza.title}</h3>
						{/if}
						{#each stanza.lines as line, j (j)}
							<p class="text-[16px] leading-relaxed text-surface-content/90">{line}</p>
						{/each}
					</section>
				{/each}
			{:else}
				{#each STANZAS as stanza, i (i)}
					<section class="space-y-2" aria-label={stanza.name}>
						<h3 class="text-xs font-medium text-surface-content/50">{stanza.name}</h3>
						{#each stanza.lines as width, j (j)}
							<div class="h-2.5 rounded bg-white/8" style:width="{width}%"></div>
						{/each}
					</section>
				{/each}
				<p class="pt-1 text-center text-xs text-surface-content/40">Lyrics are not available yet</p>
			{/if}
		</div>
	</div>
</NotchedCard>

<script lang="ts">
	import type { SongDetail } from '#lib/api.js';
	import { languageName } from '#lib/albums.js';
	import { formatCount, formatFullDate } from '#lib/format.js';
	import FactRow from '#lib/entity/FactRow.svelte';
	import Chip from '#lib/ui/Chip.svelte';

	let { song }: { song: SongDetail } = $props();

	const dash = '—';
	const date = $derived(formatFullDate(song.release_date, song.release_date_precision));
</script>

<!-- The facts about the song in one container. The tags are the tiles of the page (`Descriptors`), so they have no row. -->
<section class="space-y-3 rounded-xl bg-surface-200 px-4 py-3" aria-label="Facts about the song">
	<dl>
		<FactRow label="Released">{date ?? 'No date'}</FactRow>
		<FactRow label="Language">{song.language ? languageName(song.language) : dash}</FactRow>
		<!-- One line: a long place is cut with "…", so the panel keeps its height. -->
		<FactRow label="Recorded">
			<span class="block truncate" title={song.recording_location ?? undefined}>
				{song.recording_location ?? dash}
			</span>
		</FactRow>
		<FactRow label="Views">
			{#if song.view_count}{formatCount(song.view_count)}{:else}{dash}{/if}
			{#if song.import_state === 'stub'}<Chip tone="warn">Stub: not imported in full</Chip>{/if}
		</FactRow>
	</dl>
	<dl>
		<FactRow label="Lyrics"><span class="capitalize">{song.lyrics_state ?? dash}</span></FactRow>
		<FactRow label="Content">
			{#if song.explicit || song.instrumental}
				{#if song.explicit}<Chip>Explicit</Chip>{/if}
				{#if song.instrumental}<Chip>Instrumental</Chip>{/if}
			{:else}{dash}{/if}
		</FactRow>
	</dl>
	<dl>
		<FactRow label="Genre">{song.genre ?? dash}</FactRow>
	</dl>
</section>

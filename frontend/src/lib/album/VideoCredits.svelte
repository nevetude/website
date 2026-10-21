<script lang="ts">
	import type { Snippet } from 'svelte';
	import X from '@lucide/svelte/icons/x';
	import { ofAlbum } from '#lib/albums.js';
	import CommaList from '#lib/ui/CommaList.svelte';

	// What the page knows about the clip: the title, the date of the song, its artists and its producers.
	type Name = { id: number; base_name: string };
	type Props = {
		info: {
			title: string;
			variant: string | null;
			date: string | null;
			artists: Name[];
			featured: Name[];
			producers: Name[];
		};
		main: { id: number }[]; // the artists of the album: only their names get the tint
		tint: string | undefined;
		onclose: () => void;
		class?: string;
	};

	let { info, main, tint, onclose, class: className = '' }: Props = $props();

	const names = (list: Name[]) => list.map((one) => one.base_name);
</script>

{#snippet row(label: string, content: Snippet)}
	<div>
		<dt class="text-surface-content/50">{label}</dt>
		<!-- The column is narrow: a name may break inside, which `CommaList` does not do by itself. -->
		<dd class="break-words text-surface-content/90 [&_span]:whitespace-normal">
			{@render content()}
		</dd>
	</div>
{/snippet}

{#snippet list(people: Name[])}
	<CommaList items={names(people)} tinted={ofAlbum(people, main)} />
{/snippet}

<!-- The credits of the clip beside the main player, a narrow column of label over value (the player takes the room), on
     the ground of the card of the album. The mock of
     what stood here before (the roles and the names of the people who made a clip) is in `docs/parked-ui.md`. -->
<section
	class="relative overflow-hidden rounded-xl bg-surface-200 px-3 py-3 {className}"
	style:background-color={tint}
	aria-label="Credits of the clip"
>
	<button
		type="button"
		aria-label="Close the clip"
		title="Close the clip"
		class="absolute top-0 right-0 flex size-7 items-center justify-center rounded-tr-xl rounded-bl-xl bg-black/30 text-surface-content/60 transition-colors duration-200 ease-out hover:bg-black/60 hover:text-white"
		onclick={onclose}
	>
		<X class="size-3.5" aria-hidden="true" />
	</button>
	<!-- Starts below the close button, which stands in the corner. -->
	<dl class="mt-6 space-y-2.5 text-xs">
		{#snippet title()}{info.title}{#if info.variant}<span class="ml-1.5 text-surface-content/65"
					>{info.variant}</span
				>{/if}{/snippet}
		{@render row('Title', title)}
		{#if info.date}
			{#snippet date()}{info.date}{/snippet}
			{@render row('Released', date)}
		{/if}
		{#if info.artists.length}
			{#snippet artists()}
				{@render list(info.artists)}
				{#if info.featured.length}
					<span class="mx-[0.3em] text-surface-content/65">feat.</span>{@render list(info.featured)}
				{/if}
			{/snippet}
			{@render row('Artists', artists)}
		{/if}
		{#if info.producers.length}
			{#snippet producers()}{@render list(info.producers)}{/snippet}
			{@render row('Producer', producers)}
		{/if}
	</dl>
</section>

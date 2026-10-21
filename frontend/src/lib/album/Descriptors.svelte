<script lang="ts">
	import ClampList from '#lib/ui/ClampList.svelte';

	// A mockup: made up, of every length, as real descriptors are.
	const DESCRIPTORS = [
		'Tag',
		'Tag two',
		'A longer tag name',
		'T',
		'Tag 5',
		'Another tag',
		'Quite a long descriptor tag',
		'Mid tag',
		'Tag',
		'Tag with some words',
		'Short',
		'Tag 12',
		'A rather long tag of many words',
		'Tag name',
		'Tiny',
		'Another longer tag',
		'Tag 17',
		'Medium length',
		'Tag',
		'One more tag with words',
		'Tag 21',
		'Last',
		'Final long tag name here'
	];

	// A page that has the real ones (the tags of a song) gives them instead of the made up ones.
	let {
		words = DESCRIPTORS,
		open = $bindable(false),
		full = $bindable(0),
		box = $bindable(null)
	}: { words?: string[]; open?: boolean; full?: number; box?: HTMLElement | null } = $props();
</script>

<!-- A cloud of tiles with hashtags, without a title: the tiles are enough to tell what they are. Three rows, then
     "…" and "Show more": the rest opens right on the page and the page makes room for it (`open` and `full` are bound). -->
<div
	bind:this={box}
	class="min-[1200px]:col-start-2 min-[1200px]:row-start-3 min-[1200px]:mt-[3.8px]"
>
	<ClampList items={words} lines={3} tiles bind:open bind:full>
		{#snippet item(word)}<span
				class="inline-flex items-center gap-1 rounded-md bg-surface-100 px-1.5 py-0.5 text-xs whitespace-nowrap text-surface-content/80"
				><span class="text-surface-content/40">#</span>{word}</span
			>{/snippet}
	</ClampList>
</div>

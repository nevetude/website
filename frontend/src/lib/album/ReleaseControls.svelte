<script lang="ts">
	import Ellipsis from '@lucide/svelte/icons/ellipsis';
	import Heart from '@lucide/svelte/icons/heart';
	import ListPlus from '@lucide/svelte/icons/list-plus';
	import Play from '@lucide/svelte/icons/play';
	import Shuffle from '@lucide/svelte/icons/shuffle';

	// `label` names the panel for a screen reader: the release, the artist.
	let { label = 'Release' }: { label?: string } = $props();

	// The player and the library do not exist yet: the panel shows where they will be.
	const SOON = 'Not available yet';
	const actions = [
		{ label: 'Shuffle', icon: Shuffle },
		{ label: 'Add to queue', icon: ListPlus },
		{ label: 'Add to library', icon: Heart },
		{ label: 'More', icon: Ellipsis }
	];
</script>

{#snippet action({ label, icon: Icon }: (typeof actions)[number])}
	<button
		type="button"
		aria-disabled="true"
		aria-label={label}
		title="{label}: {SOON.toLowerCase()}"
		class="flex size-10 shrink-0 items-center justify-center rounded-full text-surface-content/80 hover:bg-white/10"
	>
		<Icon class="size-[18px]" />
	</button>
{/snippet}

<!-- A panel of buttons under the cover, close together: two actions, Play in the middle, two actions. -->
<div class="flex justify-center">
	<div
		class="flex items-center gap-2 rounded-full bg-black/25 p-1.5"
		role="toolbar"
		aria-label={label}
	>
		{#each actions.slice(0, 2) as item (item.label)}{@render action(item)}{/each}
		<button
			type="button"
			aria-disabled="true"
			aria-label="Play"
			title="Play: {SOON.toLowerCase()}"
			class="flex size-10 shrink-0 items-center justify-center rounded-full bg-surface-content text-surface-300"
		>
			<Play class="size-[18px] fill-current" />
		</button>
		{#each actions.slice(2) as item (item.label)}{@render action(item)}{/each}
	</div>
</div>

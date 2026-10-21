<script lang="ts">
	import type { Snippet } from 'svelte';
	import { watchHeight } from '#lib/ui/watchSize.js';

	// A block that is `height` pixels high while it is closed, whatever is in it: what does not fit fades out and a grey
	// "Show more" stands under it. Opened, the whole block is shown with "Show less" at its end. Opening and closing are smooth. A block that is not much higher than `height` is shown as it is. `fade` is the colour of the
	// ground the block stands on, which the text fades into; `class` (for the rounding of a block that has a ground
	// of its own) is put on the box that cuts the block.
	type Props = { height: number; fade: string; class?: string; children: Snippet };

	let { height, fade, class: className = '', children }: Props = $props();

	const SLACK = 32; // a block that sticks out by less than this is not worth hiding

	let open = $state(false);
	let animated = $state(false); // not on the first drawing: the block does not shrink on its own when the page opens
	let full = $state(0); // the height of the whole block, 0 until it is measured
	const clamped = $derived(full > height + SLACK);

	function toggle() {
		animated = true;
		open = !open;
	}
</script>

<!-- Before the block is measured it is cut at `height` already, so that the page does not jump when it is. -->
<div
	class="relative overflow-hidden {animated
		? 'transition-[height] duration-200 ease-out'
		: ''} {className}"
	style:height={clamped ? `${open ? full : height}px` : undefined}
	style:max-height={full === 0 ? `${height}px` : undefined}
>
	<div use:watchHeight={(h) => (full = h)}>
		{@render children()}
		{#if clamped && open}
			<button
				type="button"
				aria-expanded="true"
				class="mx-auto mt-2 block text-sm text-surface-content/50 hover:text-surface-content/80"
				onclick={toggle}
			>
				Show less
			</button>
		{/if}
	</div>
	{#if clamped && !open}
		<div
			class="absolute inset-x-0 bottom-0 flex h-20 items-end justify-center pb-2"
			style:background="linear-gradient(to top, {fade} 25%, transparent)"
		>
			<button
				type="button"
				aria-expanded="false"
				class="text-sm text-surface-content/50 hover:text-surface-content/80"
				onclick={toggle}
			>
				Show more
			</button>
		</div>
	{/if}
</div>

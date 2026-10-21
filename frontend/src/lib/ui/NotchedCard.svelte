<script lang="ts">
	import type { Snippet } from 'svelte';

	// A card with a bite out of the top right corner (`.notched-right`, `app.css`) and a gear in the bite (or
	// `corner`, a small mark, instead of the gear; `bite` is the width of the bite for a mark that is wider than the
	// gear, its height stays 27px). The top row of the card (`header`) holds the facts of what is in
	// it; without it the card starts with its content. `tint` is the colour of the card.
	type Props = {
		label?: string; // what the gear is for: "Tracklist settings"
		tint?: string;
		header?: Snippet;
		corner?: Snippet;
		bite?: string; // a CSS length
		children: Snippet;
	};

	let { label, tint, header, corner, bite = '27px', children }: Props = $props();

	// The gear of the Lucide `settings` icon with its centre cut out of the same path (even-odd).
	const GEAR =
		'M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915ZM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z';
</script>

<!-- The gear sits in the bite, outside of the masked container, in light grey. Its centre shows what lies behind. -->
<div class="relative" style:--card={tint ?? 'var(--color-surface-200)'} style:--bite-w={bite}>
	{#if corner}
		<div
			class="absolute top-0 right-0 z-10 flex h-[27px] items-center justify-center"
			style:width={bite}
		>
			{@render corner()}
		</div>
	{:else}
		<button
			type="button"
			aria-disabled="true"
			aria-label={label}
			title="{label}: not available yet"
			class="group/gear absolute top-0 right-0 z-10 flex size-[27px] items-center justify-center"
		>
			<svg
				viewBox="0 0 24 24"
				aria-hidden="true"
				class="size-6 overflow-visible fill-surface-content/60 stroke-surface-content/60 [transition:rotate_700ms_ease-in-out] group-hover/gear:rotate-180"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<path fill-rule="evenodd" d={GEAR} />
			</svg>
		</button>
	{/if}
	<section class="notched-right relative rounded-xl bg-(--card) pb-1 {header ? 'pt-10' : 'pt-3'}">
		{#if header}
			<div
				class="tabular absolute inset-x-0 top-0 flex h-10 items-center justify-between pr-[37px] pl-2.5 text-xs text-surface-content/80"
			>
				{@render header()}
			</div>
		{/if}
		{@render children()}
	</section>
</div>

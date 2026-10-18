<script lang="ts" generics="T">
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { tick, type Snippet } from 'svelte';
	import { watchWidth } from '#lib/ui/watchSize.js';

	// A list written in running text ("a, b, c"), cut to a few lines. It is cut between two items, never in the
	// middle of one and never after a comma: the last item that fits is followed by "…" and a grey chevron to the
	// right ("Show all") on the same line. Opened, the whole list is shown with a grey chevron to the left ("Show
	// less") after it. Opening and closing are smooth. With `float` the opened list is laid over the page instead of
	// pushing it down (for a place whose height must not change). With `tiles` the items are tiles side by side (no commas),
	// the line is as high as a row of tiles. `open` and `full` (the height of the whole list) can be bound, for a
	// page that has to make room for the opened list.
	type Props = {
		items: T[];
		lines: number;
		float?: boolean;
		tiles?: boolean;
		open?: boolean;
		full?: number;
		item: Snippet<[T]>;
	};

	let {
		items,
		lines,
		float = false,
		tiles = false,
		open = $bindable(false),
		full = $bindable(0),
		item
	}: Props = $props();

	let content = $state<HTMLElement | null>(null);
	let width = $state(0);
	let line = $state(0); // the height of one line
	let shown = $state<number | null>(null); // how many items are in the closed text; null: not measured yet
	const closed = $derived(line * lines);
	const clamped = $derived(shown !== null && shown < items.length);

	$effect(() => {
		if (content) line = parseFloat(getComputedStyle(content).lineHeight);
	});

	// A new width (or new items) means measuring again, with every item laid out.
	$effect(() => {
		void [width, items];
		shown = null;
	});

	// Measured with every item in place: the last one that fits in `lines` lines and leaves room for the
	// suffix when it stands on the last of them. Only after the page has drawn the items again (an item that is
	// still hidden has no place to measure), and once more a frame later if that has not happened yet.
	function measure(again = true) {
		if (shown !== null || !content) return;
		const spans = [...content.querySelectorAll<HTMLElement>('[data-item]')];
		if (spans.some((span) => span.getClientRects().length === 0)) {
			if (again) requestAnimationFrame(() => measure(false));
			return;
		}
		full = content.offsetHeight;
		const box = content.getBoundingClientRect();
		const suffix = content.querySelector<HTMLElement>('[data-suffix]')?.offsetWidth ?? 0;
		const ends = spans.map((span) => {
			const rects = span.getClientRects();
			const last = rects[rects.length - 1];
			return {
				bottom: last.bottom - box.top,
				top: last.top - box.top,
				right: last.right - box.left
			};
		});
		const fits = (i: number) => ends[i].bottom <= closed + 1;
		if (spans.every((_, i) => fits(i))) {
			shown = items.length;
			return;
		}
		let n = 0;
		while (n < spans.length && fits(n)) n++;
		// the last of them must leave room for the "…" and the chevron when it is on the last line
		while (
			n > 1 &&
			ends[n - 1].top >= (lines - 1) * line - 1 &&
			ends[n - 1].right + suffix > box.width
		)
			n--;
		shown = Math.max(1, n);
	}

	// Opening and closing change the height of the text: measured again once the page has drawn it.
	async function toggle(next: boolean) {
		open = next;
		await tick();
		if (content) full = content.offsetHeight;
	}

	$effect(() => {
		if (shown === null && content && line) void tick().then(() => measure());
	});

	const GREY = 'text-surface-content/50 hover:text-surface-content/80';
</script>

<!-- The outer box keeps the height of the closed text, so that a floating list does not move what is below. -->
<div class="relative" style:height={float && clamped ? `${closed}px` : undefined}>
	<div
		class="overflow-hidden rounded transition-[height] duration-200 ease-out {float && clamped
			? 'absolute inset-x-0 top-0 z-20'
			: ''} {float && open
			? 'bg-surface-100 shadow-[0_0_0_8px_var(--color-surface-100),0_8px_24px_rgba(0,0,0,0.45)]'
			: ''}"
		style:height={clamped ? `${open ? full : closed}px` : undefined}
	>
		<div
			bind:this={content}
			use:watchWidth={(w) => (width = w)}
			class="relative {tiles ? 'text-xs leading-7' : 'text-sm leading-relaxed'}"
		>
			{#each items as it, i (i)}
				{#if i > 0 && !(!open && shown !== null && i >= shown)}{#if !tiles}<span
							class="mr-[0.3em] text-surface-content/40">,</span
						>{/if}<wbr />{/if}<span
					data-item
					class="whitespace-nowrap {tiles ? 'mr-1.5' : ''}"
					class:hidden={!open && shown !== null && i >= shown}>{@render item(it)}</span
				>{#if clamped && !open && i === (shown ?? 0) - 1}<span class={GREY}>
						…<button
							type="button"
							aria-label="Show all"
							title="Show all"
							class="inline-block align-middle"
							onclick={() => toggle(true)}
							><ChevronRight class="size-5" aria-hidden="true" /></button
						></span
					>{/if}
			{/each}
			{#if clamped && open}
				<button
					type="button"
					aria-label="Show less"
					title="Show less"
					class="{GREY} inline-block align-middle"
					onclick={() => toggle(false)}><ChevronLeft class="size-5" aria-hidden="true" /></button
				>
			{/if}
			{#if shown === null}
				<span data-suffix class="invisible absolute whitespace-nowrap"
					>…<ChevronRight class="inline size-5 align-middle" /></span
				>
			{/if}
		</div>
	</div>
</div>

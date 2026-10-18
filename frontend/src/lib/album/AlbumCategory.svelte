<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import type { ArtistAlbum } from '#lib/api.js';
	import AlbumCard from '#lib/album/AlbumCard.svelte';
	import { watchWidth } from '#lib/ui/watchSize.js';
	import { cardSpan, cardHeight, cellsPerRow, coverSize, perRow } from '#lib/albums.js';

	type Props = {
		title?: string; // none: only the controls of the strip
		albums: ArtistAlbum[];
		view: 'grid' | 'list';
		openAll: boolean; // every category follows this; a click on the title still opens just one
		resetKey: string; // a new key (another order or role) starts the strip from its beginning
		columns?: number; // cards per row of the grid view, when the place decides it and not the width
	};

	let { title, albums, view, openAll, resetKey, columns }: Props = $props();

	let expanded = $derived(openAll);
	let scroller = $state<HTMLElement | null>(null);
	let track = $state<HTMLElement | null>(null);
	let width = $state(0); // the width of the strip, which is the same open or closed
	let offset = $state(0); // how far the strip is scrolled, in percent of its length

	// Closed, the strip is one row that scrolls sideways; open, the same cards wrap into rows. Both take
	// the number of cards per row and the gap from the same place, so opening never resizes a card.
	const cells = $derived(columns ?? cellsPerRow(width));
	const perView = $derived(perRow(width, view, cells));
	// A card is `span` cells wide; the cell is a share of the row.
	const cardWidth = $derived(`calc(${cardSpan(width, view, cells) * 100}% / ${cells})`);
	// Everything fits in one row: there is nothing to scroll and nothing more to open.
	const fits = $derived(albums.length <= perView);
	const scrolls = $derived(!expanded && !fits);

	// A new order starts the strip from its beginning. Without this the browser keeps the album that was
	// first in view in sight and carries the strip along with it. Showing or hiding the unreleased
	// albums is not a new order: the strip stays where it was.
	$effect(() => {
		void resetKey;
		if (scroller) scroller.scrollLeft = 0;
	});

	const onscroll = () => scroller && (offset = (scroller.scrollLeft / scroller.scrollWidth) * 100);
	const scrollBy = (direction: 1 | -1) =>
		scroller?.scrollBy({ left: direction * scroller.clientWidth });

	// The wheel over the strip, or over the bar above it, moves the albums sideways, and the page stays
	// where it is even at the ends.
	function wheel(node: HTMLElement) {
		const onWheel = (event: WheelEvent) => {
			if (!scrolls || !scroller) return;
			event.preventDefault();
			scroller.scrollLeft += event.deltaY + event.deltaX;
		};
		node.addEventListener('wheel', onWheel, { passive: false });
		return { destroy: () => node.removeEventListener('wheel', onWheel) };
	}

	// A click on the track, or a drag along it, puts the middle of the visible part where the pointer is.
	function seek(event: PointerEvent) {
		if (!scroller || !track) return;
		const box = track.getBoundingClientRect();
		const fraction = (event.clientX - box.left) / box.width;
		scroller.scrollLeft = fraction * scroller.scrollWidth - scroller.clientWidth / 2;
	}

	function grab(event: PointerEvent) {
		(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
		seek(event);
	}

	const ARROW =
		'flex size-6 shrink-0 items-center justify-center rounded-md text-surface-content/60 hover:bg-white/8 hover:text-surface-content';
</script>

<section class="group/category space-y-1">
	<header class="flex items-center gap-3">
		{#if fits}
			<h3
				class="flex h-6 items-center text-sm font-medium text-surface-content"
				title="{albums.length} releases"
			>
				{title}
			</h3>
		{:else}
			<!-- The name opens and closes the category; the tooltip says how many releases are in it. -->
			<button
				type="button"
				aria-expanded={expanded}
				title="{expanded ? 'Hide' : 'Show'} {albums.length}"
				class="group/title flex h-6 shrink-0 items-center gap-1.5 pr-2 text-surface-content hover:text-white"
				onclick={() => (expanded = !expanded)}
			>
				<h3 class="text-sm font-medium">{title}</h3>
				<!-- The chevron lights up with the name: the pointer on either of them is the pointer on the button. -->
				{#if expanded}<ChevronDown
						class="size-4 text-surface-content/60 group-hover/title:text-white"
					/>{:else}<ChevronRight
						class="size-4 text-surface-content/60 group-hover/title:text-white"
					/>{/if}
			</button>
		{/if}

		{#if scrolls}
			<!-- Beside the name, invisible until the pointer is over the category: the position, then the arrows.
			     The whole height of the position is a zone of its own: a click puts the strip there, the wheel moves it. -->
			<div
				class="flex min-w-0 flex-1 items-center opacity-0 group-hover/category:opacity-100 focus-within:opacity-100"
			>
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					bind:this={track}
					use:wheel
					class="flex h-6 min-w-0 flex-1 cursor-pointer items-center"
					onpointerdown={grab}
					onpointermove={(event) => event.buttons === 1 && seek(event)}
				>
					<div class="relative h-2 w-full rounded-full bg-white/8">
						<div
							class="absolute inset-y-0 rounded-full bg-surface-content/40"
							style:left="{offset}%"
							style:width="{(perView / albums.length) * 100}%"
						></div>
					</div>
				</div>
				<!-- A gap from the bar, so a click that misses the arrow does not land on the bar. -->
				<div class="ml-3 flex shrink-0 items-center">
					<button type="button" class={ARROW} aria-label="Scroll left" onclick={() => scrollBy(-1)}>
						<ChevronLeft class="size-4" />
					</button>
					<button type="button" class={ARROW} aria-label="Scroll right" onclick={() => scrollBy(1)}>
						<ChevronRight class="size-4" />
					</button>
				</div>
			</div>
		{/if}
	</header>

	<div
		bind:this={scroller}
		use:watchWidth={(w) => (width = w)}
		use:wheel
		{onscroll}
		class="grid [overflow-anchor:none] {expanded
			? ''
			: 'grid-flow-col overflow-x-auto overscroll-x-contain [scrollbar-width:none]'}"
		style:grid-template-columns={expanded ? `repeat(${perView}, ${cardWidth})` : undefined}
		style:grid-auto-columns={expanded ? undefined : cardWidth}
	>
		{#each albums as album (album.id)}
			<AlbumCard
				{album}
				layout={view}
				height={cardHeight(width, view, cells)}
				cover={coverSize(width, cells)}
			/>
		{/each}
	</div>
</section>

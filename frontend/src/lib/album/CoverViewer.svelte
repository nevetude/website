<script lang="ts">
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import X from '@lucide/svelte/icons/x';
	import { fade } from 'svelte/transition';

	type Props = { covers: string[]; index: number; onclose: () => void };

	let { covers, index = $bindable(), onclose }: Props = $props();

	let closeButton = $state<HTMLElement | null>(null);
	// The icon of the zone the pointer is in lights up, whether the pointer is on the icon or anywhere in the zone.
	let active = $state<'prev' | 'next' | 'close' | null>(null);
	const lit = (zone: 'prev' | 'next' | 'close') =>
		active === zone ? 'text-white' : 'text-white/60';
	const zone = (name: 'prev' | 'next' | 'close') => ({
		onpointerenter: () => (active = name),
		onpointerleave: () => (active = null)
	});

	const go = (step: number) => (index = Math.min(covers.length - 1, Math.max(0, index + step)));

	function onkeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') onclose();
		else if (event.key === 'ArrowLeft') go(-1);
		else if (event.key === 'ArrowRight') go(1);
	}

	// The page behind does not scroll while the covers are open.
	$effect(() => {
		const before = document.body.style.overflow;
		document.body.style.overflow = 'hidden';
		closeButton?.focus();
		return () => (document.body.style.overflow = before);
	});

	const BUTTON = 'flex size-11 items-center justify-center';
</script>

<svelte:window {onkeydown} />

<!-- Turning the cover over: the left half of the picture goes back and its right half goes forward, and so does the
     half of each side next to the picture (between it and the edge of the screen); the outer half of a side closes
     the viewer. On the first and the last cover there is nothing to turn to: no icon, no zone, and the whole side
     closes (the picture does nothing there). The picture is a box of one size (`--s`), so these zones never move. The
     buttons are bare icons: grey, white when the pointer is in their zone. -->
<div
	role="dialog"
	aria-modal="true"
	aria-label="Covers"
	class="fixed inset-0 z-50 bg-black/90"
	transition:fade={{ duration: 250 }}
	style="--s: min(calc(100svh - 10rem), calc(100vw - 9rem))"
>
	<button
		type="button"
		tabindex="-1"
		aria-label="Close"
		class="absolute inset-0 cursor-default"
		onclick={onclose}
		{...zone('close')}
	></button>
	{#if index > 0}
		<button
			type="button"
			tabindex="-1"
			aria-label="Previous cover"
			class="absolute inset-y-0 cursor-pointer"
			style="left: calc((100% - var(--s)) / 4); width: calc((100% - var(--s)) / 4)"
			onclick={() => go(-1)}
			{...zone('prev')}
		></button>
	{/if}
	{#if index < covers.length - 1}
		<button
			type="button"
			tabindex="-1"
			aria-label="Next cover"
			class="absolute inset-y-0 cursor-pointer"
			style="right: calc((100% - var(--s)) / 4); width: calc((100% - var(--s)) / 4)"
			onclick={() => go(1)}
			{...zone('next')}
		></button>
	{/if}

	<!-- The picture, and right under it the covers to choose from, as far from it as they are from each other. -->
	<div class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-2">
		<div class="pointer-events-auto relative size-[var(--s)]">
			<img
				src={covers[index]}
				alt=""
				referrerpolicy="no-referrer"
				class="size-full rounded-lg object-cover shadow-2xl"
			/>
			{#if index > 0}
				<button
					type="button"
					tabindex="-1"
					aria-label="Previous cover"
					class="absolute inset-y-0 left-0 w-1/2 cursor-pointer"
					onclick={() => go(-1)}
					{...zone('prev')}
				></button>
			{/if}
			{#if index < covers.length - 1}
				<button
					type="button"
					tabindex="-1"
					aria-label="Next cover"
					class="absolute inset-y-0 right-0 w-1/2 cursor-pointer"
					onclick={() => go(1)}
					{...zone('next')}
				></button>
			{/if}
			{#if covers.length > 1}
				<p
					class="tabular pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-black/90 px-3 py-1 text-xs text-white/90"
				>
					{index + 1} / {covers.length}
				</p>
			{/if}
			{#if index > 0}
				<button
					type="button"
					aria-label="Previous cover"
					class="absolute top-1/2 right-full mr-3 -translate-y-1/2 {BUTTON} {lit('prev')}"
					onclick={() => go(-1)}
					{...zone('prev')}
				>
					<ChevronLeft class="size-6" />
				</button>
			{/if}
			{#if index < covers.length - 1}
				<button
					type="button"
					aria-label="Next cover"
					class="absolute top-1/2 left-full ml-3 -translate-y-1/2 {BUTTON} {lit('next')}"
					onclick={() => go(1)}
					{...zone('next')}
				>
					<ChevronRight class="size-6" />
				</button>
			{/if}
		</div>
		{#if covers.length > 1}
			<div class="pointer-events-auto flex w-[var(--s)] flex-wrap justify-center gap-2">
				{#each covers as url, i (url)}
					<button
						type="button"
						aria-label="Cover {i + 1}"
						aria-pressed={index === i}
						class="size-12 overflow-hidden rounded-md {index === i
							? ''
							: 'opacity-50 hover:opacity-100'}"
						onclick={() => (index = i)}
					>
						<img src={url} alt="" referrerpolicy="no-referrer" class="size-full object-cover" />
					</button>
				{/each}
			</div>
		{/if}
	</div>

	<button
		bind:this={closeButton}
		type="button"
		aria-label="Close"
		class="absolute top-4 right-4 {BUTTON} {lit('close')}"
		onclick={onclose}
		{...zone('close')}
	>
		<X class="size-5" />
	</button>
</div>

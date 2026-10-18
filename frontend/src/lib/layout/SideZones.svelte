<script lang="ts">
	import ListMusic from '@lucide/svelte/icons/list-music';
	import Library from '@lucide/svelte/icons/library';
	import Chip from '#lib/ui/Chip.svelte';

	// A mockup of the two zones of the streaming app: the library on the left, the tracklist of what plays on
	// the right, gray, lighter than the page (0.165) and darker than its containers (0.205). They stand in the free margins beside the page and only where those are wide enough
	// (the content of the page is 1240px wide, a zone ends 20px from it and 1rem from the edge of the screen, and must be at
	// least 12rem wide; `100%` is the screen without its scrollbar, like the page).
	const WIDTH = 'w-[calc((100%-1240px)/2-20px-1rem)]';
</script>

<aside
	aria-label="Library"
	class="fixed top-16 bottom-4 left-4 hidden flex-col gap-3 overflow-hidden rounded-xl bg-[oklch(0.185_0_0)] p-4 min-[1650px]:flex {WIDTH}"
>
	<h2 class="flex items-center gap-2 text-base font-semibold text-surface-content">
		<Library class="size-4" aria-hidden="true" /> Library <Chip>Mockup</Chip>
	</h2>
	<ul class="space-y-2">
		{#each [1, 2, 3, 4, 5, 6, 7, 8] as n (n)}
			<li class="flex items-center gap-3 rounded-lg p-1.5">
				<span
					class="flex size-10 shrink-0 items-center justify-center rounded-md bg-white/8 text-surface-content/30"
				>
					<ListMusic class="size-5" aria-hidden="true" />
				</span>
				<div class="min-w-0 flex-1 space-y-1.5">
					<div class="h-2.5 w-3/4 rounded bg-white/8"></div>
					<div class="h-2 w-1/2 rounded bg-white/5"></div>
				</div>
			</li>
		{/each}
	</ul>
</aside>

<aside
	aria-label="Tracklist"
	class="fixed top-16 right-4 bottom-4 hidden flex-col gap-3 overflow-hidden rounded-xl bg-[oklch(0.185_0_0)] p-4 min-[1650px]:flex {WIDTH}"
>
	<h2 class="flex items-center gap-2 text-base font-semibold text-surface-content">
		<ListMusic class="size-4" aria-hidden="true" /> Tracklist <Chip>Mockup</Chip>
	</h2>
	<ol class="space-y-2">
		{#each [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as n (n)}
			<li class="flex items-center gap-3 rounded-lg p-1.5">
				<span class="tabular w-4 shrink-0 text-center font-mono text-xs text-surface-content/30">
					{n}
				</span>
				<span class="size-8 shrink-0 rounded-md bg-white/8"></span>
				<div class="min-w-0 flex-1 space-y-1.5">
					<div class="h-2.5 w-4/5 rounded bg-white/8"></div>
					<div class="h-2 w-1/2 rounded bg-white/5"></div>
				</div>
			</li>
		{/each}
	</ol>
</aside>

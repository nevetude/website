<script lang="ts">
	import ImageIcon from '@lucide/svelte/icons/image';

	// `tint` is the ground of the signs: the colour of the cover, as under the clips.
	let { tint }: { tint: string | undefined } = $props();
</script>

<!-- A mockup: photos of the album (booklet, vinyl, the studio), apart from the alternative covers above. One row of
     photos in 16:9, each with a sign under it in the style of the signs of the clips. -->
<section class="grid grid-cols-2 gap-3" aria-label="Gallery">
	{#each [1, 2] as n (n)}
		<figure>
			<div
				class="flex aspect-video items-center justify-center rounded-t-lg bg-surface-200 text-surface-content/25"
			>
				<ImageIcon class="size-5" />
			</div>
			<figcaption class="rounded-b-xl bg-surface-200 px-3 py-2" style:background-color={tint}>
				<div class="text-xs text-surface-content">Title</div>
				<div
					class="mt-0.5 flex h-4 items-baseline gap-2 text-[11px] leading-4 text-surface-content/60"
				>
					<span class="min-w-0 flex-1 truncate">Description</span>
					<span class="tabular shrink-0">Year</span>
				</div>
			</figcaption>
		</figure>
	{/each}
</section>

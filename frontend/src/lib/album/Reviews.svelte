<script lang="ts">
</script>

<!-- A mockup: the reviews of the album, a card for a review: who, the score, the text. -->
<section class="space-y-3">
	<div class="space-y-3">
		{#each [1, 2, 3] as n (n)}
			<article class="space-y-3 rounded-lg border border-dashed border-white/10 bg-surface-200 p-4">
				<div class="flex items-center gap-3">
					<span class="size-8 shrink-0 rounded-full bg-white/8"></span>
					<div class="h-2.5 w-28 rounded bg-white/8"></div>
					<span class="ml-auto h-6 w-10 rounded-md bg-white/8"></span>
				</div>
				<div class="space-y-1.5">
					<div class="h-2 w-full rounded bg-white/6"></div>
					<div class="h-2 w-11/12 rounded bg-white/6"></div>
					<div class="h-2 w-2/3 rounded bg-white/5"></div>
				</div>
			</article>
		{/each}
	</div>
</section>

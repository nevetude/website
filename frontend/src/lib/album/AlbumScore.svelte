<script lang="ts">
	let { class: className = '', style }: { class?: string; style?: string } = $props();
</script>

<!-- The container of the rating of the album. It is empty on purpose: what it held (the scores, the ranks, the friends)
     is in `docs/parked-ui.md`. It keeps its place beside the facts and is as high as the first two rows of them.
     A page without that grid gives it a height of its own through `class` or `style`. -->
<section
	aria-label="Rating"
	{style}
	class="rounded-xl bg-surface-200 min-[1200px]:col-start-2 min-[1200px]:row-span-2 min-[1200px]:row-start-1 min-[1200px]:mb-[12.8px] {className}"
></section>

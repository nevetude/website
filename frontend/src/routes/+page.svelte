<script lang="ts">
	import { BLOCKS } from '#lib/artists.js';
	import ArtistBlock from '#lib/artists/ArtistBlock.svelte';
</script>

<div class="space-y-10">
	{#each BLOCKS as block (block.id)}
		<ArtistBlock {block} />
	{/each}
</div>

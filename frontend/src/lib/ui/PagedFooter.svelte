<script lang="ts">
	import { Button } from 'svelte-ux';
	import type { PagedList } from '#lib/paged.svelte.js';

	let { list }: { list: PagedList<unknown> } = $props();
</script>

{#if list.items.length < list.total}
	<div class="flex justify-center pt-1">
		<Button variant="fill-light" size="sm" loading={list.loading} onclick={() => list.more()}>
			Show more ({list.total - list.items.length})
		</Button>
	</div>
{/if}

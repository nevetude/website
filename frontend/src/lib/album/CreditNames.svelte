<script lang="ts">
	import { resolve } from '$app/paths';
	import type { CreditGroup } from '#lib/api.js';
	import ClampList from '#lib/ui/ClampList.svelte';

	let { artists }: { artists: CreditGroup['artists'] } = $props();
</script>

<ClampList items={artists} lines={2}>
	{#snippet item({ artist, tracks })}
		<a
			href={resolve('/artists/[id]', { id: String(artist.id) })}
			title={tracks === null ? undefined : `${tracks} ${tracks === 1 ? 'track' : 'tracks'}`}
			class="text-surface-content/90">{artist.base_name}</a
		>
	{/snippet}
</ClampList>

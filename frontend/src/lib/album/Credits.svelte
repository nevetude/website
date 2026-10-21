<script lang="ts">
	import type { CreditGroup } from '#lib/api.js';
	import { sortRoles } from '#lib/albums.js';
	import CreditNames from '#lib/album/CreditNames.svelte';
	import FactRow from '#lib/entity/FactRow.svelte';

	let { groups, main }: { groups: CreditGroup[]; main: { id: number }[] } = $props();
</script>

<dl>
	{#each sortRoles(groups) as group (group.role)}
		<FactRow label={group.role}><CreditNames artists={group.artists} {main} /></FactRow>
	{/each}
</dl>

<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = { title: string; ontoggle?: (event: Event) => void; children: Snippet };

	let { title, ontoggle, children }: Props = $props();
</script>

<details {ontoggle}>
	<summary
		class="cursor-pointer px-5 py-3 text-sm text-surface-content/70 select-none hover:text-surface-content"
	>
		{title}
	</summary>
	<div class="p-5">{@render children()}</div>
</details>

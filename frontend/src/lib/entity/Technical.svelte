<script lang="ts">
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();
</script>

<!-- What is for the developer and not for the reader: one closed list at the very bottom of a page. -->
<section class="space-y-3">
	<div class="overflow-hidden rounded-xl border border-white/8 bg-surface-200">
		{@render children()}
	</div>
</section>

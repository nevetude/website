<script lang="ts">
	import type { Snippet } from 'svelte';

	let { label, children }: { label: string; children: Snippet } = $props();
</script>

<!-- One fact of an album (released, language, producer, ...): the same row for the header and for the credits. -->
<div class="grid grid-cols-[7.25rem_1fr] gap-2 py-1.5">
	<dt class="text-[13px] leading-relaxed text-surface-content/50">{label}</dt>
	<dd class="min-w-0 text-sm leading-relaxed text-surface-content/90">{@render children()}</dd>
</div>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { Tone } from '#lib/imports.js';

	let {
		tone = 'muted',
		title,
		children
	}: { tone?: Tone; title?: string; children: Snippet } = $props();

	const styles: Record<Tone, string> = {
		muted: 'bg-surface-100 text-surface-content/80',
		good: 'bg-success/12 text-success',
		warn: 'bg-warning/12 text-warning',
		bad: 'bg-danger/12 text-danger'
	};
</script>

<span
	{title}
	class="tabular inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium whitespace-nowrap {styles[
		tone
	]}"
>
	{@render children()}
</span>

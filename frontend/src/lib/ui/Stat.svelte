<script lang="ts">
	type Props = { label: string; done: number; total: number; size?: 'lg' | 'sm' };

	let { label, done, total, size = 'lg' }: Props = $props();
	const finished = $derived(done >= total);
</script>

<div class="min-w-0">
	<div class="text-xs tracking-wider text-surface-content/50 uppercase">{label}</div>
	<div
		class="tabular font-semibold {size === 'lg' ? 'text-2xl' : 'text-base'} {finished
			? 'text-success'
			: 'text-surface-content'}"
	>
		{done}<span class="ml-1 font-normal text-surface-content/40">/ {total}</span>
	</div>
</div>

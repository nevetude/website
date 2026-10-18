<script lang="ts">
	type Props = {
		/** null: the total is not known yet, so the bar only shows that something is going on */
		value: number | null;
		max?: number;
		size?: 'sm' | 'md';
		label?: string;
	};

	let { value, max = 100, size = 'md', label }: Props = $props();

	const width = $derived(value === null || max <= 0 ? 100 : Math.min(100, (value / max) * 100));
</script>

<div
	role="progressbar"
	aria-label={label}
	aria-valuenow={value ?? undefined}
	aria-valuemax={max}
	class="overflow-hidden rounded-full bg-surface-100 {size === 'sm' ? 'h-1' : 'h-1.5'}"
>
	<div
		class="h-full rounded-full {value === null ? 'bg-primary/30' : 'bg-primary'}"
		style:width="{width}%"
	></div>
</div>

<script lang="ts">
	import LayoutGrid from '@lucide/svelte/icons/layout-grid';
	import LayoutList from '@lucide/svelte/icons/layout-list';

	let { value = $bindable() }: { value: 'grid' | 'list' } = $props();

	const modes = [
		{ value: 'grid', label: 'Grid', icon: LayoutGrid },
		{ value: 'list', label: 'Rows: the cover with its details beside it', icon: LayoutList }
	] as const;
</script>

<!-- Two icon buttons made one control, like the sort control beside it. -->
<div
	class="inline-flex h-[24px] overflow-hidden rounded-md bg-surface-100"
	role="group"
	aria-label="View"
>
	{#each modes as mode (mode.value)}
		<button
			type="button"
			title={mode.label}
			aria-label={mode.label}
			aria-pressed={value === mode.value}
			class="flex w-8 items-center justify-center {value === mode.value
				? 'bg-surface-content/15 text-surface-content'
				: 'text-surface-content/60 hover:bg-surface-content/10 hover:text-surface-content'}"
			onclick={() => (value = mode.value)}
		>
			<mode.icon class="size-4" />
		</button>
	{/each}
</div>

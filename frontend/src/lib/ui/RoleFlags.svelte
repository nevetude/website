<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = {
		roles: { role: string; count: number }[];
		selected: string[]; // all of them must match
		visible?: number;
		end?: Snippet; // pushed to the right end of the row
	};

	let { roles, selected = $bindable(), visible = 10, end }: Props = $props();

	let all = $state(false);
	const shown = $derived(all ? roles : roles.slice(0, visible));

	const toggle = (role: string) =>
		(selected = selected.includes(role) ? selected.filter((r) => r !== role) : [...selected, role]);
</script>

{#if roles.length || end}
	<div class="flex flex-wrap items-center gap-1.5">
		{#each shown as { role, count } (role)}
			{@const on = selected.includes(role)}
			<button
				type="button"
				aria-pressed={on}
				class="rounded-md px-2.5 py-1 text-[13px] {on
					? 'bg-surface-content/15 text-surface-content'
					: 'bg-surface-100 text-surface-content/60 hover:text-surface-content'}"
				onclick={() => toggle(role)}
			>
				{role}
				<span class="tabular font-mono text-surface-content/40">{count}</span>
			</button>
		{/each}
		{#if roles.length > visible}
			<button
				type="button"
				class="px-1 text-[13px] text-surface-content/50 hover:text-surface-content"
				onclick={() => (all = !all)}
			>
				{all ? 'less' : `+${roles.length - visible} more`}
			</button>
		{/if}
		{#if end}<div class="ml-auto">{@render end()}</div>{/if}
	</div>
{/if}

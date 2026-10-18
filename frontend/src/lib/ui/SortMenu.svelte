<script lang="ts" generics="T extends string">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';

	type Option = { value: T; label: string; first: 'asc' | 'desc' };
	type Props = {
		options: Option[];
		sort: T;
		order: 'asc' | 'desc' | null; // null: the first direction of the sort
	};

	let { options, sort = $bindable(), order = $bindable() }: Props = $props();

	let open = $state(false);
	let root: HTMLElement;

	const current = $derived(options.find((o) => o.value === sort) ?? options[0]);
	const direction = $derived(order ?? current.first);

	// Another field starts from its own side; the chevron beside the list turns the order around.
	function choose(value: T) {
		if (value !== sort) {
			sort = value;
			order = null;
		}
		open = false;
	}

	const reverse = () => (order = direction === 'asc' ? 'desc' : 'asc');
</script>

<svelte:window
	onclick={(event) => open && !root.contains(event.target as Node) && (open = false)}
	onkeydown={(event) => event.key === 'Escape' && (open = false)}
/>

<div class="relative inline-flex" bind:this={root}>
	<!-- One control of two parts: the list on the left, the direction on the right. The list part has a
	     fixed width, so the chevron stays where it is whichever field is chosen. -->
	<div
		class="inline-flex h-[24px] overflow-hidden rounded-md bg-surface-100 text-xs text-surface-content"
	>
		<button
			type="button"
			aria-haspopup="listbox"
			aria-expanded={open}
			class="w-[5.5rem] px-2.5 text-left hover:bg-surface-content/15"
			onclick={() => (open = !open)}
		>
			{current.label}
		</button>
		<button
			type="button"
			title={direction === 'asc' ? 'Ascending: click to reverse' : 'Descending: click to reverse'}
			aria-label="Reverse the order"
			class="flex w-[24px] items-center justify-center border-l border-white/10 text-surface-content/70 hover:bg-surface-content/15 hover:text-surface-content"
			onclick={reverse}
		>
			{#if direction === 'asc'}<ChevronUp class="size-4" />{:else}<ChevronDown
					class="size-4"
				/>{/if}
		</button>
	</div>

	{#if open}
		<!-- As wide as the whole control. The chosen field is only highlighted. -->
		<div
			role="listbox"
			class="absolute inset-x-0 top-full z-20 mt-1 rounded-md bg-surface-100 p-1 shadow-xl"
		>
			{#each options as option (option.value)}
				<button
					type="button"
					role="option"
					aria-selected={option.value === sort}
					class="flex h-[24px] w-full items-center rounded px-1.5 text-left text-xs whitespace-nowrap hover:bg-white/8 {option.value ===
					sort
						? 'bg-surface-content/15 text-surface-content'
						: 'text-surface-content/70'}"
					onclick={() => choose(option.value)}
				>
					{option.label}
				</button>
			{/each}
		</div>
	{/if}
</div>

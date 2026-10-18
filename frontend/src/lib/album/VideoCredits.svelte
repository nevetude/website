<script lang="ts">
	import X from '@lucide/svelte/icons/x';

	// What the page knows about the clip: the title, the date of the song, its artists and its producers.
	type Props = {
		info: { title: string; date: string | null; artists: string; producers: string };
		tint: string | undefined;
		onclose: () => void;
		class?: string;
	};

	let { info, tint, onclose, class: className = '' }: Props = $props();

	const rows = $derived([
		{ label: 'Title', value: info.title },
		{ label: 'Released', value: info.date },
		{ label: 'Artists', value: info.artists },
		{ label: 'Producer', value: info.producers }
	]);
</script>

<!-- The credits of the clip beside the main player, in a table, on the ground of the card of the album. The mock of
     what stood here before (the roles and the names of the people who made a clip) is in `docs/parked-ui.md`. -->
<section
	class="relative overflow-hidden rounded-xl bg-surface-200 px-3.5 py-3 {className}"
	style:background-color={tint}
	aria-label="Credits of the clip"
>
	<button
		type="button"
		aria-label="Close the clip"
		title="Close the clip"
		class="absolute top-2 right-2 flex size-6 items-center justify-center rounded-full bg-black/30 text-surface-content/60 transition-colors duration-200 ease-out hover:bg-black/60 hover:text-white"
		onclick={onclose}
	>
		<X class="size-3.5" aria-hidden="true" />
	</button>
	<table class="w-full table-fixed text-xs">
		<tbody>
			{#each rows as { label, value } (label)}
				{#if value}
					<tr class="align-top">
						<th scope="row" class="w-[32%] py-1 pr-2 text-left font-normal text-surface-content/50"
							>{label}</th
						>
						<td class="py-1 pr-7 text-surface-content/90">{value}</td>
					</tr>
				{/if}
			{/each}
		</tbody>
	</table>
</section>

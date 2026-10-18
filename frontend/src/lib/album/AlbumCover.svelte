<script lang="ts">
	type Props = { covers: string[]; onopen: () => void };

	let { covers, onopen }: Props = $props();

	// Up to two more covers lie behind the main one, fanned out like photos: the second peeks out on the left, the third on
	// the right, only a little; the pointer pulls them out a bit more.
	const behind = $derived(covers.slice(1, 3));
	const FAN = [
		'-translate-x-[6%] -rotate-[3deg] group-hover:-translate-x-[12%] group-hover:-rotate-[5deg] group-focus-visible:-translate-x-[12%]',
		'translate-x-[6%] rotate-[3deg] group-hover:translate-x-[12%] group-hover:rotate-[5deg] group-focus-visible:translate-x-[12%]'
	];
</script>

<div class="flex justify-center">
	<button
		type="button"
		class="group relative size-[14rem] min-[1000px]:size-[16rem] rounded-lg"
		aria-label="View all covers"
		onclick={onopen}
	>
		{#each behind as url, i (url)}
			<img
				src={url}
				alt=""
				referrerpolicy="no-referrer"
				class="absolute inset-0 size-full rounded-lg object-cover opacity-80 brightness-75 transition-transform duration-200 ease-out shadow-[0_6px_16px_rgba(0,0,0,0.4)] {FAN[
					i
				]}"
			/>
		{/each}
		{#if covers[0]}
			<img
				src={covers[0]}
				alt=""
				referrerpolicy="no-referrer"
				class="relative block size-full rounded-lg bg-black/20 object-cover shadow-[0_0_30px_6px_rgba(0,0,0,0.65)]"
			/>
		{/if}
	</button>
</div>

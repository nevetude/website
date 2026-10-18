<script lang="ts">
	import BadgeCheck from '@lucide/svelte/icons/badge-check';
	import ReleaseControls from '#lib/album/ReleaseControls.svelte';
	import Thumb from '#lib/ui/Thumb.svelte';

	type Props = { src: string | null; name: string; verified: boolean | null };

	let { src, name, verified }: Props = $props();
</script>

<!-- The same panel as the cover of an album (400px wide, 380px high and 3rem more under the popular tracks, which the
     page lays over its lower edge), with a round portrait. The portrait is blurred behind itself into a faint field, so
     the round shape stands on its own colour and not on the grey of the card; the badge of a verified artist sits on
     the rim of the circle, where a round picture has room for it. -->
<section
	class="relative aspect-square h-full overflow-hidden rounded-xl bg-surface-200 min-[1000px]:aspect-auto min-[1000px]:min-h-[calc(380px+3rem)]"
>
	{#if src}
		<img
			{src}
			alt=""
			aria-hidden="true"
			referrerpolicy="no-referrer"
			class="absolute inset-0 size-full scale-150 object-cover opacity-30 blur-3xl"
		/>
	{/if}
	<div class="absolute inset-x-0 top-0 flex h-full flex-col min-[1000px]:h-[calc(100%-3rem)]">
		<div class="flex-[57.5]"></div>
		<div class="flex justify-center">
			<div class="relative size-[14rem] min-[1000px]:size-[16rem]">
				<Thumb
					{src}
					{name}
					class="size-full rounded-full text-7xl shadow-[0_0_30px_6px_rgba(0,0,0,0.65)]"
				/>
				{#if verified}
					<span
						title="Verified"
						class="absolute right-[7%] bottom-[7%] flex size-9 items-center justify-center rounded-full bg-surface-200 text-surface-content"
					>
						<BadgeCheck class="size-6" aria-label="Verified" />
					</span>
				{/if}
			</div>
		</div>
		<div class="flex-[25]"></div>
		<ReleaseControls label="Artist" />
		<div class="flex-[16.5]"></div>
	</div>
</section>

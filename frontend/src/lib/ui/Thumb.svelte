<script lang="ts">
	// A picture, or the first letter of `name` on a plain square when there is none (an empty name: a blank square).
	// `class` carries the size, the radius and anything else of the place it is used in.
	type Props = { src: string | null; name: string; class?: string };

	let { src, name, class: className = 'size-14 rounded-lg' }: Props = $props();
</script>

{#if src}
	<img {src} alt="" loading="lazy" class="shrink-0 bg-surface-100 object-cover {className}" />
{:else}
	<div
		class="flex shrink-0 items-center justify-center bg-surface-100 text-surface-content/40 {className}"
	>
		{name.slice(0, 1).toUpperCase()}
	</div>
{/if}

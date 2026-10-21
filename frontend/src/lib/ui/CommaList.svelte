<script lang="ts">
	// Names in running text: grey commas, and a name never breaks across two lines (the line may break after a
	// comma). `wrap` false: the list stays on one line (its parent cuts it with "…"), no break after a comma.
	// `tinted[i]`: the name gets the tint of the artists of the album (`.artist` in `app.css`).
	let {
		items,
		wrap = true,
		tinted
	}: { items: string[]; wrap?: boolean; tinted?: boolean[] } = $props();
</script>

{#each items as item, i (i)}{#if i}<span class="mr-[0.3em] text-surface-content/40">,</span
		>{#if wrap}<wbr />{/if}{/if}<span class="whitespace-nowrap {tinted?.[i] ? 'artist' : ''}"
		>{item}</span
	>{/each}

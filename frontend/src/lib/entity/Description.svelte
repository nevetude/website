<script lang="ts">
	import type { DomNode, DomRef } from '#lib/dom.js';
	import RichText from '#lib/ui/RichText.svelte';

	// `dom` is null for what was imported before descriptions were kept as trees: then only the text is known.
	type Props = { dom: DomNode | null; text: string; refs: DomRef[] };

	let { dom, text, refs }: Props = $props();
</script>

<article class="rounded-xl bg-surface-200 p-5 text-sm leading-relaxed text-surface-content/80">
	{#if dom}
		<RichText node={dom} {refs} />
	{:else}
		<p class="whitespace-pre-line">{text}</p>
	{/if}
</article>

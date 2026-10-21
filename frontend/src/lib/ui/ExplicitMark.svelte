<script lang="ts">
	let { class: className = '' }: { class?: string } = $props();
</script>

<!-- The Tabler `explicit` icon, cropped to its frame, with rounder corners (radius 3 of 16). Nothing of its own in the
     flow, so its baseline is its bottom edge: set on the baseline of a line of text it is about as tall as its capitals.
     The size and the colour come with `class`. -->
<svg
	viewBox="3.5 3.5 17 17"
	role="img"
	aria-label="Explicit"
	class="shrink-0 {className}"
	fill="none"
	stroke="currentColor"
	stroke-width="1.5"
	stroke-linecap="round"
	stroke-linejoin="round"
>
	<title>Explicit</title>
	<path d="M4 7a3 3 0 0 1 3 -3h10a3 3 0 0 1 3 3v10a3 3 0 0 1 -3 3h-10a3 3 0 0 1 -3 -3z" />
	<path d="M14 8h-4v8h4" />
	<path d="M14 12h-4" />
</svg>

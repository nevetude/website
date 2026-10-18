<script lang="ts">
	import type { Snippet } from 'svelte';

	type Props = { href: string; class?: string; title?: string; children: Snippet };

	let { href, class: className = '', title, children }: Props = $props();
</script>

<!-- The one place for links to other sites (Genius), which the router rule about our own routes does not cover. -->
<!-- eslint-disable svelte/no-navigation-without-resolve -->
<a {href} {title} target="_blank" rel="noreferrer" class={className}>{@render children()}</a>

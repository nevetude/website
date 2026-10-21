<script lang="ts">
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import { resolve } from '$app/paths';

	// The way to the page, from the home page: every part but the last one leads back. `href` is already
	// resolved by the page that knows the route (the lint rule cannot see that through a prop).
	type Crumb = { label: string; href?: string };

	let { trail }: { trail: Crumb[] } = $props();

	const all = $derived<Crumb[]>([{ label: 'Home', href: resolve('/') }, ...trail]);
</script>

<!-- Out of the flow, in the 2rem between the header and the first block of the page (`main` is positioned and has that
     much room at the top): the block stands 1.5rem under the header whether the page has breadcrumbs or not. -->
<nav aria-label="Breadcrumbs" class="absolute inset-x-6 top-0 flex h-8 items-center text-[13px]">
	<ol class="flex min-w-0 items-center gap-x-1.5 overflow-hidden text-surface-content/60">
		{#each all as crumb, i (i)}
			{#if i > 0}<li aria-hidden="true"><ChevronRight class="size-3.5" /></li>{/if}
			<li class="min-w-0">
				{#if i < all.length - 1 && crumb.href}
					<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -->
					<a href={crumb.href} class="hover:text-surface-content">{crumb.label}</a>
				{:else}
					<span aria-current="page" class="block max-w-[28rem] truncate text-surface-content"
						>{crumb.label}</span
					>
				{/if}
			</li>
		{/each}
	</ol>
</nav>

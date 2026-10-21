<script lang="ts">
	import '../app.css';
	import { settings } from 'svelte-ux';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import SideZones from '#lib/layout/SideZones.svelte';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	// One dark theme. Svelte UX owns <html data-theme> and drops it unless a theme is registered and chosen.
	settings({ themes: { light: [], dark: ['music'] } }).currentTheme.setTheme('music');

	const links = [{ href: '/import', label: 'Import' }] as const;
</script>

<svelte:head>
	<title>Music</title>
</svelte:head>

<header class="sticky top-0 z-20 border-b border-white/8 bg-surface-300/85 backdrop-blur">
	<div class="mx-auto flex h-12 max-w-[calc(1240px+3rem)] items-center gap-8 px-6">
		<a href={resolve('/')} class="font-semibold tracking-tight text-surface-content">Music</a>
		<nav class="flex gap-5 text-sm">
			{#each links as link (link.href)}
				<a
					href={resolve(link.href)}
					aria-current={page.url.pathname.startsWith(link.href) ? 'page' : undefined}
					class="text-surface-content/50 hover:text-surface-content aria-[current=page]:text-surface-content"
				>
					{link.label}
				</a>
			{/each}
		</nav>
	</div>
</header>

<SideZones />

<!-- Every page starts 2rem under the header: its first block (the cover, the form), or the main element if there
     is no cover. The breadcrumbs stand in that room (`Breadcrumbs`). -->
<main class="relative mx-auto max-w-[calc(1240px+3rem)] px-6 pt-8 pb-8">
	{@render children()}
</main>

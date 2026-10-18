<script lang="ts">
	import { resolve } from '$app/paths';
	import { loneLink, ourPage, safeUrl, youtubeEmbed, type Dom, type DomRef } from '#lib/dom.js';
	import ExtLink from '#lib/ui/ExtLink.svelte';
	import RichText from '#lib/ui/RichText.svelte';

	// A description as Genius writes it (a `dom` tree). Only the tags below are drawn; any other tag shows
	// the text of what is inside it.
	let { node, refs }: { node: Dom; refs: DomRef[] } = $props();
</script>

{#snippet kids(of: Exclude<Dom, string>)}
	{#each of.children ?? [] as child, i (i)}<RichText node={child} {refs} />{/each}
{/snippet}

{#if typeof node === 'string'}
	{node}
{:else if node.tag === 'root'}
	<div class="space-y-4">{@render kids(node)}</div>
{:else if node.tag === 'p'}
	{@const video = youtubeEmbed(loneLink(node)?.attributes?.href)}
	{#if video}
		<iframe
			src={video}
			title="Video"
			loading="lazy"
			allowfullscreen
			referrerpolicy="strict-origin-when-cross-origin"
			class="aspect-video w-full rounded-lg"
		></iframe>
	{:else}
		<p>{@render kids(node)}</p>
	{/if}
{:else if node.tag === 'a'}
	{@const ours = ourPage(node, refs)}
	{@const href = safeUrl(node.attributes?.href)}
	{#if ours}
		<a
			href={resolve(ours.kind === 'artist' ? '/artists/[id]' : '/albums/[id]', {
				id: String(ours.id)
			})}
			class="text-surface-content">{@render kids(node)}</a
		>
	{:else if href}
		<ExtLink {href} class="text-surface-content">{@render kids(node)}</ExtLink>
	{:else}
		{@render kids(node)}
	{/if}
{:else if node.tag === 'em' || node.tag === 'i'}
	<em>{@render kids(node)}</em>
{:else if node.tag === 'strong' || node.tag === 'b'}
	<strong class="font-semibold">{@render kids(node)}</strong>
{:else if node.tag === 'blockquote'}
	<blockquote class="space-y-3 pl-4 text-surface-content/70">{@render kids(node)}</blockquote>
{:else if node.tag === 'hr'}
	<div class="h-2"></div>
{:else if node.tag === 'br'}
	<br />
{:else if node.tag === 'img'}
	{@const src = safeUrl(node.attributes?.src)}
	{#if src}
		<img
			{src}
			alt={String(node.attributes?.alt ?? '')}
			loading="lazy"
			referrerpolicy="no-referrer"
			class="max-w-full rounded-lg"
		/>
	{/if}
{:else}
	{@render kids(node)}
{/if}

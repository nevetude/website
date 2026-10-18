<script lang="ts">
	import BadgeCheck from '@lucide/svelte/icons/badge-check';
	import Users from '@lucide/svelte/icons/users';
	import { resolve } from '$app/paths';
	import type { ArtistCard } from '#lib/api.js';
	import { formatCount } from '#lib/format.js';
	import Thumb from '#lib/ui/Thumb.svelte';
	import CopyId from '#lib/ui/CopyId.svelte';
	import ExtLink from '#lib/ui/ExtLink.svelte';

	let { artist }: { artist: ArtistCard } = $props();
</script>

<!-- The whole card opens our page of the artist (a link stretched over it); the name and the id sit above that link and keep their own click. -->
<article class="relative flex gap-3 rounded-xl bg-surface-200 p-3 hover:bg-surface-100/60">
	<a
		href={resolve('/artists/[id]', { id: String(artist.id) })}
		aria-label="Open {artist.base_name}"
		class="absolute inset-0 rounded-xl"
	></a>

	<Thumb src={artist.cover_url} name={artist.base_name} class="size-14 rounded-lg text-lg" />

	<div class="pointer-events-none flex min-w-0 flex-1 flex-col">
		<div class="flex items-center gap-2">
			<h3 class="flex min-w-0 items-center gap-1.5 font-medium text-surface-content">
				{#if artist.genius_url}
					<ExtLink
						href={artist.genius_url}
						class="pointer-events-auto relative truncate hover:underline"
					>
						{artist.base_name}
					</ExtLink>
				{:else}
					<span class="truncate">{artist.base_name}</span>
				{/if}
				{#if artist.is_verified}
					<BadgeCheck class="size-4 shrink-0 text-surface-content/70" aria-label="Verified" />
				{/if}
			</h3>
			{#if artist.followers_count}
				<span
					class="tabular ml-auto flex shrink-0 items-center gap-1 rounded-md bg-surface-100 px-2 py-0.5 text-xs text-surface-content/70"
				>
					<Users class="size-3" aria-hidden="true" />
					<span class="sr-only">Followers</span>
					{formatCount(artist.followers_count)}
				</span>
			{/if}
		</div>

		<!-- Tracks on the left, the id on the right, one line at the bottom of the card, in line with the lower edge of the picture
		     (the card is as high as the picture and its padding, so all four spaces around the picture are equal). The line is there
		     without data too, so the cards do not differ. Only the id itself takes clicks, the rest of the line goes to the card link. -->
		<div
			class="tabular relative mt-auto flex h-4 items-center justify-between text-xs text-surface-content/50"
		>
			<span>
				{#if artist.tracks_count}
					{artist.tracks_count}
					{artist.tracks_count === 1 ? 'track' : 'tracks'}
				{/if}
			</span>
			{#if artist.genius_id !== null}
				<span class="pointer-events-auto"><CopyId value={artist.genius_id} /></span>
			{/if}
		</div>
	</div>
</article>

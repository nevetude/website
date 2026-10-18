# Parked UI (made empty on purpose, kept here to be put back)

Mockups of the album page that were emptied at the request of the user. The components are still in place and
hold their slot in the layout; the content they had is below, exactly as it was. To put one back, copy the code over
the component (`frontend/src/lib/album/<Name>.svelte`) and pass the props the old code took
(`AlbumScore` took `{ album }`; `VideoCredits` took `title`, `onclose` and `class`).

## `AlbumScore.svelte` (the rating container beside the facts of the album)

The users' score in a lime square in the top right corner (it opens the scores of other services as a pop-up),
the ranks, plays and libraries, the friends (a rating or a folder), the grades of the users. All of it is mock data.

```svelte
<script lang="ts">
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import Folder from '@lucide/svelte/icons/folder';
	import Headphones from '@lucide/svelte/icons/headphones';
	import Library from '@lucide/svelte/icons/library';
	import type { AlbumDetail } from '#lib/api.js';

	let { album }: { album: AlbumDetail } = $props();

	// A mockup, the same for every album: the ratings, the library and the friends do not exist yet. The users'
	// score is the main one; the others (the critics and other services) open under it. The votes are for every
	// grade from 1 to 10. A friend either rated the album or keeps it in a folder of their own.
	const MOCK = {
		users: { value: 87, title: '1,248 ratings' },
		others: [
			{ label: 'Album of the Year', value: 90, title: 'Critics: 24 reviews' },
			{ label: 'Rate Your Music', value: 78, title: '9,420 ratings' },
			{ label: 'Pitchfork', value: 84, title: '1 review' },
			{ label: 'Metacritic', value: 82, title: '18 reviews' },
			{ label: 'Genius', value: 88, title: '312 ratings' }
		],
		votes: [2, 1, 2, 3, 5, 9, 18, 34, 62, 100],
		plays: '1.2M',
		libraries: '5,402',
		rankOverall: 100,
		rankGenre: 12,
		friends: [
			{ name: 'Alex', rating: 85 },
			{ name: 'Maria', folder: 'Late night' },
			{ name: 'Dima', folder: 'To listen' }
		]
	};
	const MOST = Math.max(...MOCK.votes);
	const year = $derived(album.release_date?.slice(0, 4));
	const genre = $derived(album.genres[0]);

	const ranks = $derived([
		{ place: MOCK.rankOverall, where: 'on Music' },
		...(year ? [{ place: 200, where: `for ${year}` }] : []),
		...(genre ? [{ place: MOCK.rankGenre, where: `in ${genre}` }] : [])
	]);

	let open = $state(false);
	let corner = $state<HTMLElement | null>(null);

	// The score is a number in a square of lime green, like the scores of the sites about albums.
	const SQUARE = 'bg-[oklch(0.84_0.19_130)] font-semibold text-black/80';
</script>

<!-- The scores open as a pop-up under the corner and close with a click anywhere else or Escape. -->
<svelte:window
	onclick={(event) => {
		if (open && !corner?.contains(event.target as Node)) open = false;
	}}
	onkeydown={(event) => {
		if (event.key === 'Escape') open = false;
	}}
/>

<!-- The rating of the album in a container like the description's, in small text and not in rows of a table.
     The main score (the users') stands in the top right corner; it opens the other scores in a pop-up. -->
<section
	aria-label="Rating"
	class="relative flex flex-col rounded-xl bg-surface-200 p-5 text-sm min-[1200px]:col-start-2 min-[1200px]:row-span-2 min-[1200px]:row-start-1 min-[1200px]:mb-[12.8px]"
>
	<div bind:this={corner} class="absolute top-3 right-3 z-30">
		<button
			type="button"
			aria-expanded={open}
			aria-controls="other-scores"
			title="{MOCK.users.title}: show the scores of the critics and other services"
			class="group flex items-center gap-2"
			onclick={() => (open = !open)}
		>
			<span
				class="flex items-center gap-0.5 text-xs text-surface-content/50 group-hover:text-surface-content/80"
			>
				User score
				{#if open}<ChevronUp class="size-3.5" aria-hidden="true" />{:else}<ChevronDown
						class="size-3.5"
						aria-hidden="true"
					/>{/if}
			</span>
			<span class="tabular flex size-9 items-center justify-center rounded-md text-lg {SQUARE}">
				{MOCK.users.value}
			</span>
		</button>
		{#if open}
			<ul
				id="other-scores"
				class="absolute top-full right-0 mt-2 flex gap-3 rounded-xl bg-surface-100 p-3 shadow-[0_8px_24px_rgba(0,0,0,0.45)]"
			>
				{#each MOCK.others as { label, value, title } (label)}
					<li {title} class="w-[4.5rem] text-center">
						<div
							class="tabular mx-auto flex size-8 items-center justify-center rounded-md text-base {SQUARE}"
						>
							{value}
						</div>
						<div class="mt-1 text-[11px] leading-tight text-surface-content/50">
							{label}
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	</div>

	<div class="flex flex-1 flex-col gap-4">
		<ul class="min-h-[4.125em] space-y-0.5 pr-14 leading-snug">
			{#each ranks as { place, where } (where)}
				<li>
					<span class="font-medium text-surface-content">#{place}</span>
					<span class="text-surface-content/50">{where}</span>
				</li>
			{/each}
		</ul>

		<div class="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-surface-content/65">
			<span class="flex items-center gap-1.5" title="Plays">
				<Headphones class="size-3.5 text-surface-content/50" aria-hidden="true" />
				{MOCK.plays}
			</span>
			<span class="flex items-center gap-1.5" title="In libraries">
				<Library class="size-3.5 text-surface-content/50" aria-hidden="true" />
				{MOCK.libraries}
			</span>
		</div>

		<ul class="flex flex-wrap gap-1.5" aria-label="Friends">
			{#each MOCK.friends as friend (friend.name)}
				<li
					class="flex items-center gap-1.5 rounded-full bg-surface-100 py-0.5 pr-2.5 pl-0.5 text-xs text-surface-content/80"
				>
					<span
						aria-hidden="true"
						class="flex size-5 items-center justify-center rounded-full bg-surface-200 text-[10px] text-surface-content/70"
						>{friend.name[0]}</span
					>
					{friend.name}
					{#if friend.rating !== undefined}
						<span class="tabular rounded px-1 {SQUARE}">{friend.rating}</span>
					{:else}
						<span class="flex items-center gap-1 text-surface-content/50">
							<Folder class="size-3.5" aria-hidden="true" />
							{friend.folder}
						</span>
					{/if}
				</li>
			{/each}
		</ul>

		<div class="mt-auto">
			<div
				class="flex h-6 items-end gap-0.5"
				role="img"
				aria-label="Grades from 1 to 10: {MOCK.votes.join(', ')} votes"
			>
				{#each MOCK.votes as count, i (i)}
					<div
						title="{i + 1}: {count}"
						class="w-4 rounded-[2px] bg-surface-content/25"
						style:height="{Math.max(10, (count / MOST) * 100)}%"
					></div>
				{/each}
			</div>
		</div>
	</div>
</section>
```

## `VideoCredits.svelte` (the credits of the clip, beside the main player)

The title of the clip with a close button, and a table of the credits of the clip (mock data). Later the component got a
table of what the page knows about the clip (the track number, the title, the year, the artists); the mock below is
what it was before that.

```svelte
<script lang="ts">
	import X from '@lucide/svelte/icons/x';

	// A mockup, the same for every clip: who made a clip will come from another source. As many rows as fit beside the
	// player on the narrowest page that has this layout (two roles take two lines); the rows share the height of the box.
	const CREDITS = [
		{ role: 'Production Company', name: 'Object & Animal' },
		{ role: 'Director', name: 'Aidan Zamiri' },
		{ role: 'Exec Producer', name: 'Morgan Clement' },
		{ role: 'Producer', name: 'James Graley' },
		{ role: '1st AD', name: 'Carla Kaempfer' },
		{ role: 'DOP', name: 'Jake Hunter' },
		{ role: 'Gaffer', name: 'Simona Pranulyte' },
		{ role: 'Production Designer', name: 'Louis Simomon' },
		{ role: 'Drone', name: 'Barney Clarke' },
		{ role: 'Wardrobe Stylist', name: 'Matthew Josephs' },
		{ role: 'Make-Up', name: 'Lauren Reynolds' }
	];

	let {
		title,
		onclose,
		class: className = ''
	}: { title: string; onclose: () => void; class?: string } = $props();
</script>

<!-- The title of the clip and the credits under it. The box has no height of its own, it is as high as the player
     beside it, and the rows of the table share that height. -->
<section class="relative rounded-xl bg-surface-200 {className}" aria-label="Credits of the clip">
	<div class="absolute inset-0 flex flex-col">
		<header class="flex items-center justify-between gap-2 px-3.5 pt-3 pb-1">
			<h3 class="truncate text-[11px] font-medium text-surface-content/90">{title}</h3>
			<button
				type="button"
				aria-label="Close the clip"
				title="Close the clip"
				class="shrink-0 text-surface-content/50 hover:text-white"
				onclick={onclose}
			>
				<X class="size-3.5" aria-hidden="true" />
			</button>
		</header>
		<div class="min-h-0 flex-1 overflow-hidden px-3.5 pb-3">
			<table class="h-full w-full table-fixed text-[11px]">
				<tbody>
					{#each CREDITS as { role, name } (role)}
						<tr>
							<th
								scope="row"
								class="w-[54%] pr-1.5 leading-tight text-left font-normal text-surface-content/50"
								>{role}</th
							>
							<td class="truncate text-surface-content/90">{name}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>
</section>
```

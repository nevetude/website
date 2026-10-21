<script lang="ts">
	import { Button, SelectField, TextField } from 'svelte-ux';
	import CheckIcon from '@lucide/svelte/icons/check';
	import SearchIcon from '@lucide/svelte/icons/search';
	import { api, type ArtistHit } from '#lib/api.js';
	import { MODES, PREFIX, importBody, type Mode } from '#lib/imports.js';
	import Chip from '#lib/ui/Chip.svelte';
	import Thumb from '#lib/ui/Thumb.svelte';

	type Props = {
		onstart: (body: NonNullable<ReturnType<typeof importBody>>) => Promise<void>;
	};

	let { onstart }: Props = $props();

	let mode = $state<Mode>('discography');
	let query = $state('');
	let hits = $state<ArtistHit[] | null>(null);
	let searching = $state(false);
	let searchError = $state('');
	let idText = $state('');
	let limitText = $state('');
	let starting = $state(false);

	const body = $derived(importBody(mode, idText, limitText));
	// Only artists are looked up by name; an album or a song is imported by the id from its page.
	const withSearch = $derived(mode === 'discography' || mode === 'artist');

	async function search(event: SubmitEvent) {
		event.preventDefault();
		if (!query.trim()) return;
		searching = true;
		searchError = '';
		try {
			const { data } = await api.GET('/api/v1/genius/search/artists', {
				params: { query: { q: query.trim() } }
			});
			hits = data ?? null;
			if (!data) searchError = 'The search failed: Genius did not answer';
		} catch {
			searchError = 'The search failed: the backend is not running';
		} finally {
			searching = false;
		}
	}

	async function start(event: SubmitEvent) {
		event.preventDefault();
		if (!body) return;
		starting = true;
		try {
			await onstart(body);
		} finally {
			starting = false;
		}
	}

	const dbLabel = { stub: 'Stub', full: 'In library' } as const;
</script>

<section class="flex flex-col gap-5 rounded-xl border border-white/8 bg-surface-200 p-5">
	<header>
		<h2 class="text-base font-semibold text-surface-content">Import</h2>
		<p class="mt-0.5 text-xs text-surface-content/50">
			Pull an artist, an album or a song from Genius into the library.
		</p>
	</header>

	{#if withSearch}
		<div>
			<form class="flex items-end gap-2" onsubmit={search}>
				<div class="min-w-0 flex-1">
					<TextField bind:value={query} label="Find an artist" placeholder="Artist name" dense />
				</div>
				<Button
					type="submit"
					icon={SearchIcon}
					loading={searching}
					variant="fill-light"
					class="h-10 px-4"
				>
					Search
				</Button>
			</form>
			{#if searchError}<p class="mt-2 text-xs text-danger">{searchError}</p>{/if}
			{#if hits}
				<ul
					class="mt-3 max-h-64 divide-y divide-white/6 overflow-auto rounded-lg border border-white/8 bg-surface-300/60"
				>
					{#each hits as hit (hit.genius_id)}
						{@const chosen = idText === String(hit.genius_id)}
						<li>
							<button
								type="button"
								aria-pressed={chosen}
								class="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-white/5 {chosen
									? 'bg-white/8'
									: ''}"
								onclick={() => (idText = String(hit.genius_id))}
							>
								<Thumb src={hit.image_url} name="" class="size-8 rounded-md" />
								<span class="min-w-0 flex-1 truncate text-sm text-surface-content">{hit.name}</span>
								<span class="tabular text-xs text-surface-content/40">{hit.genius_id}</span>
								{#if hit.db_state}<Chip tone="good">{dbLabel[hit.db_state]}</Chip>{/if}
								<span class="flex size-4 shrink-0 items-center justify-center text-surface-content">
									{#if chosen}<CheckIcon class="size-4" aria-hidden="true" />{/if}
								</span>
							</button>
						</li>
					{:else}
						<li class="px-3 py-4 text-center text-xs text-surface-content/50">Nothing found</li>
					{/each}
				</ul>
			{/if}
		</div>
	{/if}

	<form class="flex flex-wrap items-end gap-3 border-t border-white/8 pt-5" onsubmit={start}>
		<div class="w-64">
			<SelectField label="Mode" options={MODES} bind:value={mode} clearable={false} dense />
		</div>
		{#if mode === 'discography'}
			<div class="w-36"><TextField bind:value={idText} label="Artist id" dense /></div>
			<div class="w-36">
				<TextField bind:value={limitText} label="Albums limit" placeholder="all" dense />
			</div>
		{:else}
			<div class="flex items-end gap-2">
				<span class="flex h-10 items-center font-mono text-xs text-surface-content/50"
					>{PREFIX[mode]}</span
				>
				<div class="w-36"><TextField bind:value={idText} label="Id" dense /></div>
			</div>
		{/if}
		<Button
			type="submit"
			loading={starting}
			disabled={!body}
			variant="fill"
			class="ml-auto h-10 min-w-28"
		>
			Import
		</Button>
	</form>
</section>

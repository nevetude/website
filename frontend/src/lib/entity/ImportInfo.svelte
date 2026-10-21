<script lang="ts">
	import { resolve } from '$app/paths';
	import type { ArtistDetail } from '#lib/api.js';
	import { describeChange, formatDateTime } from '#lib/format.js';
	import { KINDS, statusTone } from '#lib/imports.js';
	import Chip from '#lib/ui/Chip.svelte';
	import Disclosure from '#lib/ui/Disclosure.svelte';

	type Props = {
		subject: 'artist' | 'album' | 'song';
		createdAt: string;
		updatedAt: string;
		imports: ArtistDetail['imports'];
		history: ArtistDetail['history'];
	};

	let { subject, createdAt, updatedAt, imports, history }: Props = $props();

	const when = (iso: string | null) => (iso ? formatDateTime(iso) : '—');
	// The first import of an entity only records that it got its Genius id: not a change worth a line of its own.
	const isCreation = (changes: ArtistDetail['history'][number]['changes']) =>
		Object.keys(changes).join() === 'genius_id';
</script>

<Disclosure title="Imports and history">
	<div class="space-y-4 text-xs">
		<p class="tabular text-surface-content/60">
			Added {when(createdAt)}, last changed {when(updatedAt)}.
			<a href={resolve('/import')} class="text-surface-content/80 hover:text-white">Import page</a>
		</p>

		<div class="space-y-1.5">
			<h3 class="font-medium text-surface-content/70">Imports of this {subject}</h3>
			{#each imports as job (job.id)}
				<div class="tabular flex flex-wrap items-center gap-3 text-surface-content/70">
					<Chip tone={statusTone[job.status]}>{job.status}</Chip>
					<span>{KINDS[job.kind].one}{job.albums_limit ? `, newest ${job.albums_limit}` : ''}</span>
					<span class="text-surface-content/50">{when(job.finished_at ?? job.started_at)}</span>
					{#if job.error}<span class="min-w-0 break-words text-danger">{job.error}</span>{/if}
				</div>
			{:else}
				<p class="text-surface-content/40">None: the {subject} was found inside another import.</p>
			{/each}
		</div>

		<div class="space-y-1.5">
			<h3 class="font-medium text-surface-content/70">Changes</h3>
			{#each history as entry (entry.id)}
				<div class="space-y-0.5">
					<div class="tabular flex items-center gap-2 text-surface-content/50">
						<Chip>{entry.action}</Chip>
						{when(entry.created_at)}
					</div>
					{#if isCreation(entry.changes)}
						<p class="pl-1 text-surface-content/70">Added to the library.</p>
					{:else}
						<ul class="pl-1 font-mono text-surface-content/70">
							{#each Object.entries(entry.changes) as [field, change] (field)}
								<li class="break-words">{describeChange(field, change)}</li>
							{/each}
						</ul>
					{/if}
				</div>
			{:else}
				<p class="text-surface-content/40">No changes recorded.</p>
			{/each}
		</div>
	</div>
</Disclosure>

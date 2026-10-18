<script lang="ts">
	import ArrowDown from '@lucide/svelte/icons/arrow-down';
	import ArrowUp from '@lucide/svelte/icons/arrow-up';
	import type { RequestRow } from '#lib/api.js';
	import {
		clockTime,
		endpointOf,
		formatBytes,
		nextSort,
		requestTone,
		sortRows,
		taskName,
		tookTone,
		type Sort,
		type SortKey
	} from '#lib/imports.js';
	import Chip from '#lib/ui/Chip.svelte';
	import ExtLink from '#lib/ui/ExtLink.svelte';

	type Props = {
		rows: RequestRow[];
		/** Genius id of the job's own artist or album: its row is an entry point too */
		subjectId?: number;
		stickyHead?: boolean;
		empty?: string;
	};

	let { rows, subjectId, stickyHead = false, empty = 'No requests yet' }: Props = $props();

	// Fixed widths, the same for the header and every row, so a long name never moves a column. The
	// last, empty column only stretches the row (and its highlight) to the full width.
	const COLUMNS = 'grid-cols-[5rem_4.5rem_20rem_22rem_5.5rem_5rem_1fr]';
	const CELL = 'min-w-0 truncate px-3 py-1.5';
	const HEADINGS = ['Time', 'Status', 'Task', 'Request'];
	const SORTABLE: { key: SortKey; heading: string }[] = [
		{ key: 'took', heading: 'Took' },
		{ key: 'size', heading: 'Size' }
	];
	// Text colour only and dimmer than the status chip, so a column of them stays quiet.
	const TOOK = { good: 'text-success/60', warn: 'text-warning/75', bad: 'text-danger/80' };

	let sort = $state<Sort>(null);
	const sorted = $derived(sortRows(rows, sort));

	// The big steps of an import stand out like a hovered row: the request of an album itself, and of
	// the artist being imported. Not the lists (an artist's albums, an album's tracks) nor the other artists.
	const OWN_PAGE = /^\/(artists|albums)\/\d+$/;
	const isEntry = (row: RequestRow) =>
		OWN_PAGE.test(endpointOf(row.url)) &&
		(row.task_kind === 'album' || (row.task_kind === 'artist' && row.task_genius_id === subjectId));
</script>

<div role="table" aria-label="Requests to Genius" class="min-w-max text-xs">
	<div
		role="row"
		class="grid {COLUMNS} text-surface-content/50 {stickyHead
			? 'sticky top-0 z-10 bg-surface-200'
			: ''}"
	>
		{#each HEADINGS as heading (heading)}
			<div role="columnheader" class="{CELL} border-b border-white/8 py-2 font-medium">
				{heading}
			</div>
		{/each}
		{#each SORTABLE as { key, heading } (key)}
			<div
				role="columnheader"
				aria-sort={sort?.key !== key ? 'none' : sort.dir === 'asc' ? 'ascending' : 'descending'}
				class="{CELL} border-b border-white/8 py-2 font-medium"
			>
				<button
					type="button"
					title="Sort by {heading.toLowerCase()}"
					class="flex items-center gap-1 hover:text-surface-content {sort?.key === key
						? 'text-surface-content'
						: ''}"
					onclick={() => (sort = nextSort(sort, key))}
				>
					{heading}
					{#if sort?.key === key}
						{#if sort.dir === 'asc'}<ArrowUp class="size-3" />{:else}<ArrowDown
								class="size-3"
							/>{/if}
					{/if}
				</button>
			</div>
		{/each}
		<div role="columnheader" class="border-b border-white/8"></div>
	</div>

	{#each sorted as row (row.id)}
		{@const name = taskName(row.task_name, row.task_genius_id)}
		<div
			role="row"
			class="grid {COLUMNS} items-center {isEntry(row) ? 'bg-white/6' : 'hover:bg-white/3'}"
		>
			<div role="cell" class="{CELL} tabular text-surface-content/60">
				{clockTime(row.created_at)}
			</div>
			<div role="cell" class="{CELL} font-mono">
				<Chip
					tone={requestTone(row)}
					title={row.error ?? (row.attempt > 1 ? `Attempt ${row.attempt}` : undefined)}
				>
					{row.status_code ?? 'network'}
				</Chip>
			</div>
			<div role="cell" class="{CELL} text-surface-content" title={name}>
				{#if row.page_url}
					<ExtLink href={row.page_url} class="hover:underline">{name}</ExtLink>
				{:else}
					{name}
				{/if}
			</div>
			<div role="cell" class="{CELL} font-mono text-surface-content/70" title={endpointOf(row.url)}>
				<ExtLink href={row.url} class="hover:underline">{endpointOf(row.url)}</ExtLink>
			</div>
			<div role="cell" class="{CELL} tabular font-mono {TOOK[tookTone(row.elapsed_ms)]}">
				{row.elapsed_ms} ms
			</div>
			<div role="cell" class="{CELL} tabular font-mono text-surface-content/70">
				{formatBytes(row.size_bytes)}
			</div>
			<div role="cell"></div>
		</div>
	{:else}
		<div class="px-3 py-6 text-center text-surface-content/40">{empty}</div>
	{/each}
</div>

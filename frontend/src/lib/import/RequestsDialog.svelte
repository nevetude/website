<script lang="ts">
	import { Button, Dialog, TextField } from 'svelte-ux';
	import X from '@lucide/svelte/icons/x';
	import { RequestFeed } from '#lib/imports.svelte.js';
	import { endpointOf, isProblem, taskName } from '#lib/imports.js';
	import type { Job } from '#lib/api.js';
	import RequestTable from '#lib/import/RequestTable.svelte';

	type Props = { job: Job | null; active: boolean; onclose: () => void };

	let { job, active, onclose }: Props = $props();

	// The dialog is closed by the owner (job = null), so its own `open` only mirrors that.
	const open = $derived(job !== null);
	const SHOWN = 1500; // more rows than this make the page heavy and nobody reads them one by one

	let query = $state('');
	let problemsOnly = $state(false);
	let feed = $state<RequestFeed | null>(null);

	$effect(() => {
		if (!job) {
			feed = null;
			return;
		}
		const current = new RequestFeed(job.id);
		feed = current;
		void current.refresh();
		if (!active) return;
		const timer = setInterval(() => void current.refresh(), 1000);
		return () => clearInterval(timer);
	});

	const problems = $derived((feed?.rows ?? []).filter(isProblem).length);

	const visible = $derived.by(() => {
		const text = query.trim().toLowerCase();
		const rows = (feed?.rows ?? []).filter((row) => {
			if (problemsOnly && !isProblem(row)) return false;
			if (!text) return true;
			const haystack = `${taskName(row.task_name, row.task_genius_id)} ${endpointOf(row.url)} ${row.status_code ?? 'network'}`;
			return haystack.toLowerCase().includes(text);
		});
		return rows.slice(-SHOWN).reverse(); // newest first
	});
</script>

<Dialog {open} on:close={onclose} classes={{ dialog: 'w-[min(1100px,96vw)] bg-surface-200' }}>
	<!-- A fixed height: with a content-sized dialog the header jumps whenever the filter changes the row count -->
	<div class="flex h-[85dvh] flex-col">
		<div class="flex flex-wrap items-center gap-3 border-b border-white/8 px-5 py-4">
			<div class="mr-auto min-w-0">
				<h2 class="truncate text-base font-semibold text-surface-content">
					Requests · {job?.subject_name ?? `#${job?.genius_id}`}
				</h2>
				<p class="tabular text-xs text-surface-content/50">
					{feed?.rows.length ?? 0} requests{active ? ', updating live' : ''}
				</p>
			</div>
			<button
				type="button"
				aria-pressed={problemsOnly}
				title="Errors, retries and answers that took 3 s or more"
				class="tabular rounded-md px-2 py-1 font-mono text-xs {problemsOnly
					? 'bg-danger/12 text-danger'
					: 'bg-surface-100 text-surface-content/60 hover:text-surface-content'}"
				onclick={() => (problemsOnly = !problemsOnly)}
			>
				ERRORS {problems}
			</button>
			<div class="w-56">
				<TextField bind:value={query} placeholder="Filter: task, path, status" dense />
			</div>
			<Button icon={X} iconOnly size="sm" onclick={onclose} aria-label="Close" />
		</div>
		<div class="min-h-0 flex-1 overflow-auto">
			<RequestTable
				rows={visible}
				subjectId={job?.genius_id}
				stickyHead
				empty={problemsOnly || query ? 'Nothing matches' : 'No requests yet'}
			/>
			{#if (feed?.rows.length ?? 0) > SHOWN}
				<p class="px-5 py-3 text-center text-xs text-surface-content/40">
					Showing the newest {SHOWN}; use the filter to find older ones
				</p>
			{/if}
		</div>
	</div>
</Dialog>

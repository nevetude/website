<script lang="ts">
	import { Button } from 'svelte-ux';
	import ListIcon from '@lucide/svelte/icons/list';
	import type { Job } from '#lib/api.js';
	import {
		KINDS,
		elapsedMs,
		formatDuration,
		isActive,
		statusTone,
		sum,
		taskLabel
	} from '#lib/imports.js';
	import RequestTable from '#lib/import/RequestTable.svelte';
	import Chip from '#lib/ui/Chip.svelte';
	import Meter from '#lib/ui/Meter.svelte';
	import Stat from '#lib/ui/Stat.svelte';

	type Props = {
		job: Job;
		oncancel: (job: Job) => void;
		onlog: (job: Job) => void;
	};

	let { job, oncancel, onlog }: Props = $props();

	// A running job always shows its latest requests; a finished one only when asked, to keep the history short.
	let showRecent = $state(false);
	const active = $derived(isActive(job));
	const progress = $derived(job.progress);
	const units = $derived(progress ? sum(progress.units) : null);
	const items = $derived(progress ? sum(progress.items) : null);
	const failures = $derived(job.error ? job.error.split('; ') : []);
	const finishedWithErrors = $derived(job.status === 'succeeded' && failures.length > 0);
	const statusText = $derived(
		finishedWithErrors
			? 'Done with errors'
			: {
					queued: 'Queued',
					running: 'Running',
					succeeded: 'Done',
					failed: 'Failed',
					cancelled: 'Cancelled'
				}[job.status]
	);
	const current = $derived(progress?.unit);
</script>

<article class="rounded-xl border border-white/8 bg-surface-200">
	<header class="flex items-start justify-between gap-4 p-5">
		<div class="min-w-0">
			<div class="text-xs tracking-wider text-surface-content/50 uppercase">
				{KINDS[job.kind].one}
			</div>
			<h3 class="mt-0.5 truncate text-lg font-semibold text-surface-content">
				{job.subject_name ?? progress?.root?.name ?? `Genius #${job.genius_id}`}
			</h3>
		</div>
		<div class="flex shrink-0 items-center gap-3">
			<Chip tone={finishedWithErrors ? 'warn' : statusTone[job.status]}>{statusText}</Chip>
			{#if active}
				<Button size="sm" variant="outline" color="danger" onclick={() => oncancel(job)}>
					Cancel
				</Button>
			{/if}
		</div>
	</header>

	{#if active}
		<div class="space-y-5 border-t border-white/8 p-5">
			{#if units && progress}
				<div class="grid grid-cols-[repeat(auto-fit,minmax(7rem,1fr))] gap-4">
					{#each progress.units as count (count.kind)}
						<Stat label={KINDS[count.kind].many} done={count.done} total={count.total} />
					{/each}
				</div>
				<Meter value={units.done} max={units.total} label="All steps of the import" />

				{#if current}
					<div class="space-y-3 rounded-lg bg-surface-100/60 p-4">
						<div class="flex items-baseline justify-between gap-3">
							<div class="min-w-0">
								<div class="text-xs tracking-wider text-surface-content/50 uppercase">
									Now: {KINDS[current.kind].one.toLowerCase()}
								</div>
								<div class="truncate font-medium text-surface-content">
									{current.name ?? `#${current.genius_id}`}
								</div>
							</div>
							{#if progress.items.length}
								<div class="flex shrink-0 gap-5">
									{#each progress.items as count (count.kind)}
										<Stat
											label={KINDS[count.kind].many}
											done={count.done}
											total={count.total}
											size="sm"
										/>
									{/each}
								</div>
							{/if}
						</div>
						<Meter
							value={items && items.total ? items.done : null}
							max={items?.total ?? 1}
							size="sm"
							label="Contents of the current item"
						/>
					</div>
				{/if}
			{:else}
				<div class="space-y-2">
					<div class="text-sm text-surface-content/70">
						{job.status === 'queued' ? 'Waiting for the previous import…' : 'Reading the list…'}
					</div>
					<Meter value={null} label="Preparing" />
				</div>
			{/if}

			{#if progress?.active}
				<div class="flex items-center gap-2 text-xs text-surface-content/60">
					<span class="size-1.5 rounded-full bg-primary"></span>
					<span class="truncate">
						{taskLabel(progress.active.kind, progress.active.genius_id, progress.active.name)}
					</span>
				</div>
			{/if}
		</div>
	{:else}
		<div class="space-y-3 border-t border-white/8 px-5 py-4 text-sm">
			<p class="text-surface-content/70">
				{job.message ?? statusText}
				{#if job.started_at && job.finished_at}
					<span class="tabular ml-1 text-surface-content/50">
						· {formatDuration(elapsedMs(job, 0))}
					</span>
				{/if}
			</p>
			{#if failures.length}
				<ul class="space-y-1 text-xs text-danger">
					{#each failures as failure (failure)}<li class="break-words">{failure}</li>{/each}
				</ul>
			{/if}
		</div>
	{/if}

	{#if job.requests_total > 0}
		<footer class="border-t border-white/8">
			<div class="flex items-center justify-between px-5 py-2">
				<button
					type="button"
					class="tabular text-xs text-surface-content/50 enabled:hover:text-surface-content"
					disabled={active}
					onclick={() => (showRecent = !showRecent)}
				>
					{#if !active}{showRecent ? '▾' : '▸'}{/if}
					Last {job.recent_requests.length} of {job.requests_total} requests
				</button>
				<Button size="sm" variant="text" icon={ListIcon} onclick={() => onlog(job)}>
					All requests
				</Button>
			</div>
			{#if active || showRecent}
				<div class="overflow-x-auto pb-2">
					<RequestTable rows={[...job.recent_requests].reverse()} subjectId={job.genius_id} />
				</div>
			{/if}
		</footer>
	{/if}
</article>

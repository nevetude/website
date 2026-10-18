<script lang="ts">
	import type { Job } from '#lib/api.js';
	import { KINDS, elapsedMs, etaMs, formatDuration } from '#lib/imports.js';

	type Props = { job: Job | null; now: number };

	let { job, now }: Props = $props();

	const elapsed = $derived(job ? elapsedMs(job, now) : null);
	const eta = $derived(job ? etaMs(job, now) : null);
	const perMinute = $derived(
		job && elapsed && elapsed > 5000 ? Math.round((job.requests_total / elapsed) * 60_000) : null
	);

	const stats = $derived([
		{ label: 'Elapsed', value: elapsed === null ? '—' : formatDuration(elapsed) },
		{
			label: 'Time left',
			value: !job ? '—' : eta === null ? 'estimating…' : `${formatDuration(eta)}`
		},
		{ label: 'Requests', value: job ? String(job.requests_total) : '—' },
		{ label: 'Per minute', value: perMinute === null ? '—' : String(perMinute) }
	]);
</script>

<section class="rounded-xl border border-white/8 bg-surface-200 p-5">
	<div class="flex items-center justify-between gap-3">
		<h2 class="text-xs font-medium tracking-wider text-surface-content/50 uppercase">Monitor</h2>
		<span class="flex min-w-0 items-center gap-2 text-xs text-surface-content/60">
			<span class="size-1.5 shrink-0 rounded-full {job ? 'bg-success' : 'bg-surface-content/25'}"
			></span>
			<span class="truncate">
				{job ? `${KINDS[job.kind].one} · ${job.subject_name ?? `#${job.genius_id}`}` : 'Idle'}
			</span>
		</span>
	</div>
	<dl class="mt-4 grid grid-cols-2 gap-x-4 gap-y-4">
		{#each stats as stat (stat.label)}
			<div>
				<dt class="text-xs text-surface-content/50">{stat.label}</dt>
				<dd
					class="tabular mt-0.5 text-lg font-semibold {job
						? 'text-surface-content'
						: 'text-surface-content/30'}"
				>
					{stat.value}
				</dd>
			</div>
		{/each}
	</dl>
</section>

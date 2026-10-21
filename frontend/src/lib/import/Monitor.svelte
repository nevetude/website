<script lang="ts">
	import Clock from '@lucide/svelte/icons/clock';
	import Gauge from '@lucide/svelte/icons/gauge';
	import Hourglass from '@lucide/svelte/icons/hourglass';
	import Send from '@lucide/svelte/icons/send';
	import type { Job, Monitor } from '#lib/api.js';
	import {
		KINDS,
		elapsedMs,
		etaMs,
		formatBytes,
		formatDuration,
		formatMs,
		tookTone
	} from '#lib/imports.js';

	type Props = { job: Job | null; now: number; monitor: Monitor | null };

	let { job, now, monitor }: Props = $props();

	const elapsed = $derived(job ? elapsedMs(job, now) : null);
	const eta = $derived(job ? etaMs(job, now) : null);
	const perMinute = $derived(
		job && elapsed && elapsed > 5000 ? Math.round((job.requests_total / elapsed) * 60_000) : null
	);

	const stats = $derived([
		{ label: 'Elapsed', icon: Clock, value: elapsed === null ? '—' : formatDuration(elapsed) },
		{
			label: 'Time left',
			icon: Hourglass,
			value: !job ? '—' : eta === null ? 'estimating…' : formatDuration(eta)
		},
		{ label: 'Requests', icon: Send, value: job ? String(job.requests_total) : '—' },
		{ label: 'Per minute', icon: Gauge, value: perMinute === null ? '—' : String(perMinute) }
	]);

	const connection = $derived(monitor?.connection);
	const latency = $derived(monitor?.latency);
	const answers = $derived(monitor?.answers);

	const server = $derived<[string, string | null | undefined][]>([
		['Host', connection?.host],
		['Address', connection?.ip],
		['Edge', connection && [connection.server, connection.edge].filter(Boolean).join(' · ')],
		['Origin', connection?.origin],
		[
			'Protocol',
			connection && [connection.http_version, connection.tls_version].filter(Boolean).join(' · ')
		]
	]);

	const latencies = $derived<[string, number | undefined][]>([
		['Last', latency?.last_ms],
		['Median', latency?.median_ms],
		['95th', latency?.p95_ms],
		['Worst', latency?.worst_ms]
	]);

	// Answers worth a look are marked, the plain zeros are not.
	const results = $derived<[string, number | undefined, 'warn' | 'bad' | null][]>([
		['OK', answers?.ok, null],
		['Not found', answers?.client_errors, 'warn'],
		['Rate limited', answers?.rate_limited, 'bad'],
		['Server errors', answers?.server_errors, 'bad'],
		['No answer', answers?.no_answer, 'bad'],
		['Retries', answers?.retries, 'warn']
	]);

	const TONE = { good: 'text-success', warn: 'text-warning', bad: 'text-danger' } as const;
	const BAR = { good: 'bg-success/50', warn: 'bg-warning/60', bad: 'bg-danger/60' } as const;
	// The bars are as tall as the slowest answer of the chart, so one slow answer does not flatten the rest.
	const chartMax = $derived(Math.max(1, ...(latency?.recent_ms ?? [])));
</script>

{#snippet title(text: string, note?: string)}
	<h3 class="flex items-baseline justify-between text-xs font-medium text-surface-content/50">
		{text}{#if note}<span class="font-normal text-surface-content/35">{note}</span>{/if}
	</h3>
{/snippet}

<section class="flex flex-col gap-5 rounded-xl border border-white/8 bg-surface-200 p-5">
	<header class="flex items-start justify-between gap-3">
		<div class="min-w-0">
			<h2 class="text-base font-semibold text-surface-content">Monitor</h2>
			<p class="mt-0.5 truncate text-xs text-surface-content/50">
				{job
					? `${KINDS[job.kind].one} · ${job.subject_name ?? `#${job.genius_id}`}`
					: 'Nothing is running'}
			</p>
		</div>
		<span
			class="flex shrink-0 items-center gap-1.5 rounded-md px-1.5 py-0.5 text-xs font-medium {job
				? 'bg-success/12 text-success'
				: 'bg-surface-100 text-surface-content/60'}"
		>
			<span class="size-1.5 rounded-full bg-current"></span>
			{job ? 'Running' : 'Idle'}
		</span>
	</header>

	<dl class="grid grid-cols-2 gap-2">
		{#each stats as stat (stat.label)}
			<div class="rounded-lg bg-surface-300/60 px-3 py-2.5">
				<dt class="flex items-center gap-1.5 text-xs text-surface-content/50">
					<stat.icon class="size-3.5" aria-hidden="true" />
					{stat.label}
				</dt>
				<dd
					class="tabular mt-1 truncate text-lg leading-tight font-semibold {job
						? 'text-surface-content'
						: 'text-surface-content/30'}"
				>
					{stat.value}
				</dd>
			</div>
		{/each}
	</dl>

	<div class="space-y-2 border-t border-white/8 pt-5">
		{@render title('Server')}
		<dl class="space-y-1.5 text-sm">
			{#each server as [label, value] (label)}
				<div class="flex items-baseline justify-between gap-3">
					<dt class="text-xs text-surface-content/50">{label}</dt>
					<dd
						class="tabular truncate text-right {value
							? 'text-surface-content/90'
							: 'text-surface-content/30'}"
						title={value || undefined}
					>
						{value || '—'}
					</dd>
				</div>
			{/each}
		</dl>
	</div>

	<div class="space-y-3 border-t border-white/8 pt-5">
		{@render title('Response time', latency ? `last ${latency.samples} requests` : undefined)}
		<dl class="grid grid-cols-4 gap-2">
			{#each latencies as [label, ms] (label)}
				<div class="min-w-0">
					<dt class="text-xs text-surface-content/50">{label}</dt>
					<dd
						class="tabular mt-0.5 truncate text-sm font-semibold {ms === undefined
							? 'text-surface-content/30'
							: TONE[tookTone(ms)]}"
					>
						{ms === undefined ? '—' : formatMs(ms)}
					</dd>
				</div>
			{/each}
		</dl>
		<div class="flex h-10 items-end gap-px" aria-hidden="true">
			{#each latency?.recent_ms ?? [] as ms, i (i)}
				<span
					class="min-w-px flex-1 rounded-t-[1px] {BAR[tookTone(ms)]}"
					style:height="{Math.max(6, (ms / chartMax) * 100)}%"
					title={formatMs(ms)}
				></span>
			{:else}
				<span class="h-px w-full self-center bg-white/8"></span>
			{/each}
		</div>
	</div>

	<div class="space-y-2 border-t border-white/8 pt-5">
		{@render title('Answers', answers?.requests ? `last ${answers.requests} requests` : undefined)}
		<dl class="grid grid-cols-3 gap-x-3 gap-y-2.5">
			{#each results as [label, count, tone] (label)}
				<div class="min-w-0">
					<dt class="truncate text-xs text-surface-content/50">{label}</dt>
					<dd
						class="tabular mt-0.5 text-sm font-semibold {!count
							? 'text-surface-content/30'
							: tone
								? TONE[tone]
								: 'text-surface-content'}"
					>
						{count ?? '—'}
					</dd>
				</div>
			{/each}
		</dl>
		<div class="flex items-baseline justify-between gap-3 pt-1 text-xs text-surface-content/50">
			<span>Downloaded</span>
			<span class="tabular text-surface-content/90">
				{answers?.requests ? formatBytes(answers.bytes) : '—'}
			</span>
		</div>
		<div class="flex items-baseline justify-between gap-3 text-xs text-surface-content/50">
			<span>Pace</span>
			<span class="tabular text-surface-content/90">
				{monitor
					? `at most one request per ${formatMs(Math.round(monitor.min_interval_s * 1000))}`
					: '—'}
			</span>
		</div>
	</div>
</section>

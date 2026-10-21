<script lang="ts">
	import { onMount } from 'svelte';
	import { ImportJobs } from '#lib/imports.svelte.js';
	import { isActive } from '#lib/imports.js';
	import type { Job } from '#lib/api.js';
	import JobCard from '#lib/import/JobCard.svelte';
	import Monitor from '#lib/import/Monitor.svelte';
	import NewImport from '#lib/import/NewImport.svelte';
	import RequestsDialog from '#lib/import/RequestsDialog.svelte';
	import Breadcrumbs from '#lib/ui/Breadcrumbs.svelte';

	const imports = new ImportJobs();

	let now = $state(Date.now());
	let logJob = $state<Job | null>(null);
	// The one that runs now (jobs go one at a time); the list is newest first.
	const running = $derived(imports.jobs.find((j) => j.status === 'running') ?? null);
	// The dialog follows the live copy of the job, so it knows when the job has finished.
	const logActive = $derived(imports.jobs.some((j) => j.id === logJob?.id && isActive(j)));

	// A second while something runs (counters, clock), five seconds otherwise.
	onMount(() => {
		let timer: ReturnType<typeof setTimeout>;
		const tick = async () => {
			await imports.refresh();
			now = Date.now();
			timer = setTimeout(tick, imports.active ? 1000 : 5000);
		};
		void tick();
		return () => clearTimeout(timer);
	});
</script>

<Breadcrumbs trail={[{ label: 'Import' }]} />

<!-- The monitor is a column of its own, beside the form and the jobs, and stays in view while the jobs scroll. -->
<div class="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
	<div class="space-y-6 lg:col-start-1 lg:row-start-1">
		<NewImport onstart={imports.start.bind(imports)} />

		<section class="space-y-4">
			{#if imports.offline}
				<p class="text-xs text-danger">The backend does not answer</p>
			{/if}

			{#each imports.jobs as job (job.id)}
				<JobCard {job} oncancel={imports.cancel.bind(imports)} onlog={(j) => (logJob = j)} />
			{:else}
				<div
					class="rounded-xl border border-dashed border-white/10 px-6 py-12 text-center text-sm text-surface-content/40"
				>
					No imports yet
				</div>
			{/each}
		</section>
	</div>
	<div class="lg:sticky lg:top-4 lg:col-start-2 lg:row-start-1">
		<Monitor job={running} {now} monitor={imports.monitor} />
	</div>
</div>

<RequestsDialog job={logJob} active={logActive} onclose={() => (logJob = null)} />

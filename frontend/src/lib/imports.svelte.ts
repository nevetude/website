import { api, type Job, type Monitor, type RequestRow } from '#lib/api.js';
import { isActive } from '#lib/imports.js';

/** The import jobs shown on the page. The page polls `refresh`: once a second while a job is active. */
export class ImportJobs {
	jobs = $state<Job[]>([]);
	monitor = $state<Monitor | null>(null);
	offline = $state(false);
	active = $derived(this.jobs.some(isActive));

	async refresh() {
		try {
			const [{ data }, { data: monitor }] = await Promise.all([
				api.GET('/api/v1/imports', { params: { query: { limit: 10 } } }),
				api.GET('/api/v1/imports/monitor')
			]);
			if (data) this.jobs = data;
			if (monitor) this.monitor = monitor;
			this.offline = !data;
		} catch {
			this.offline = true; // the backend is not running
		}
	}

	async start(body: { kind: Job['kind']; genius_id: number; albums_limit: number | null }) {
		await api.POST('/api/v1/imports', { body });
		await this.refresh();
	}

	async cancel(job: Job) {
		await api.POST('/api/v1/imports/{job_id}/cancel', { params: { path: { job_id: job.id } } });
		await this.refresh();
	}
}

const PAGE = 500;

/** The whole request log of one job, kept up to date by asking only for what is newer. */
export class RequestFeed {
	// Replaced and not pushed to: the log of a long job has thousands of rows.
	rows = $state.raw<RequestRow[]>([]);
	loading = $state(false);
	private busy = false;

	constructor(readonly jobId: number) {}

	async refresh() {
		if (this.busy) return;
		this.busy = true;
		this.loading = this.rows.length === 0;
		try {
			for (;;) {
				const afterId = this.rows.at(-1)?.id ?? 0;
				const { data } = await api.GET('/api/v1/imports/{job_id}/requests', {
					params: { path: { job_id: this.jobId }, query: { after_id: afterId, limit: PAGE } }
				});
				if (!data || data.items.length === 0) break;
				this.rows = [...this.rows, ...data.items];
				if (data.items.length < PAGE) break;
			}
		} finally {
			this.busy = false;
			this.loading = false;
		}
	}
}

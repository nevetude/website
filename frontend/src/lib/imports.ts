import type { Count, ImportKind, Job, RequestRow } from '#lib/api.js';

export type Mode = ImportKind;

// The first mode is a pipeline of ours, not one Genius endpoint, so it has no URL.
export const MODES: { value: Mode; label: string }[] = [
	{ value: 'discography', label: 'Discography of an artist' },
	{ value: 'artist', label: 'artists/{id}' },
	{ value: 'album', label: 'albums/{id}' },
	{ value: 'song', label: 'songs/{id}' }
];

export const PREFIX: Record<Exclude<Mode, 'discography'>, string> = {
	artist: 'genius.com/api/artists/',
	album: 'genius.com/api/albums/',
	song: 'genius.com/api/songs/'
};

export const KINDS: Record<ImportKind, { one: string; many: string }> = {
	discography: { one: 'Discography', many: 'Discographies' },
	artist: { one: 'Artist', many: 'Artists' },
	album: { one: 'Album', many: 'Albums' },
	song: { one: 'Song', many: 'Songs' }
};

/** The request for the form, or null while the id is not a positive whole number. */
export function importBody(mode: Mode, idText: string, limitText: string) {
	const id = Number(idText);
	if (!idText.trim() || !Number.isInteger(id) || id < 1) return null;
	const limit = limitText.trim() === '' ? null : Number(limitText);
	return { kind: mode, genius_id: id, albums_limit: mode === 'discography' ? limit : null };
}

export const isActive = (job: Job) => job.status === 'queued' || job.status === 'running';

/** The unit counts of the job as `done / total` sums, for the overall bar. */
export const sum = (counts: Count[]) => ({
	done: counts.reduce((n, c) => n + c.done, 0),
	total: counts.reduce((n, c) => n + c.total, 0)
});

/** "3 s", "2 min 5 s", "1 h 4 min": the two biggest units are enough to read a duration. */
export function formatDuration(ms: number) {
	const seconds = Math.max(0, Math.round(ms / 1000));
	if (seconds < 60) return `${seconds} s`;
	const minutes = Math.floor(seconds / 60);
	if (minutes < 60) return `${minutes} min ${seconds % 60} s`;
	return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

export function elapsedMs(job: Job, now: number) {
	if (!job.started_at) return 0;
	const end = job.finished_at ? Date.parse(job.finished_at) : now;
	return end - Date.parse(job.started_at);
}

/** Remaining time by the pace of the finished units. Only a guess, so it needs a few units first. */
export function etaMs(job: Job, now: number) {
	const counts = job.progress?.units;
	if (!counts) return null;
	const { done, total } = sum(counts);
	if (done < 3 || done >= total) return null;
	return (elapsedMs(job, now) / done) * (total - done);
}

/** The path and query of a Genius API url: the host is the same for every request. */
export function endpointOf(url: string) {
	const { pathname, search } = new URL(url, 'https://genius.com');
	// Rows of the log written before the importer stopped asking for `text_format=plain` still have it.
	return pathname.replace(/^\/api/, '') + search.replace('?text_format=plain', '');
}

export type Tone = 'good' | 'warn' | 'bad' | 'muted';

/** 2xx is fine; a network error, 429 and 5xx are retried, so they only warn; other 4xx are final. */
export function requestTone(row: Pick<RequestRow, 'status_code'>): Tone {
	const code = row.status_code;
	if (code === null) return 'warn';
	if (code < 300) return 'good';
	return code === 429 || code >= 500 ? 'warn' : 'bad';
}

export const statusTone: Record<Job['status'], Tone> = {
	queued: 'muted',
	running: 'muted',
	succeeded: 'good',
	failed: 'bad',
	cancelled: 'warn'
};

/** The name of the task for the log: the path column already says what kind it is. */
export const taskName = (name: string | null, id: number | null) => name ?? (id ? `#${id}` : '');

// A Genius answer takes 0.2-1.7 s as a rule; the thresholds only mark what stands out.
const SLOW_MS = 1000;
const VERY_SLOW_MS = 3000;

export function tookTone(ms: number): Exclude<Tone, 'muted'> {
	return ms >= VERY_SLOW_MS ? 'bad' : ms >= SLOW_MS ? 'warn' : 'good';
}

/** What "Problems" shows: an error, a retry, or an answer that took very long. */
export const isProblem = (row: Pick<RequestRow, 'status_code' | 'attempt' | 'elapsed_ms'>) =>
	requestTone(row) !== 'good' || row.attempt > 1 || tookTone(row.elapsed_ms) === 'bad';

export const formatMs = (ms: number) => (ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`);

export function formatBytes(bytes: number | null) {
	if (bytes === null) return '—';
	return bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(bytes < 10240 ? 1 : 0)} KB`;
}

export const clockTime = (iso: string) =>
	new Date(iso).toLocaleTimeString('en-GB', { hour12: false });

/** A task as one phrase, for places that have no path column next to it: "Song Creep". */
export const taskLabel = (kind: ImportKind, id: number, name: string | null) =>
	`${KINDS[kind].one} ${name ?? `#${id}`}`;

export type SortKey = 'took' | 'size';
export type Sort = { key: SortKey; dir: 'asc' | 'desc' } | null;

/** A click on a header: biggest first, then smallest first, then back to the order of arrival. */
export function nextSort(current: Sort, key: SortKey): Sort {
	if (current?.key !== key) return { key, dir: 'desc' };
	return current.dir === 'desc' ? { key, dir: 'asc' } : null;
}

/** Rows by took or size. A request without a size (no answer) goes last whichever way it is sorted. */
export function sortRows(rows: RequestRow[], sort: Sort) {
	if (!sort) return rows;
	const value = (row: RequestRow) => (sort.key === 'took' ? row.elapsed_ms : row.size_bytes);
	const sign = sort.dir === 'asc' ? 1 : -1;
	return [...rows].sort((a, b) => {
		const [x, y] = [value(a), value(b)];
		if (x === y) return 0;
		if (x === null) return 1;
		if (y === null) return -1;
		return (x - y) * sign;
	});
}

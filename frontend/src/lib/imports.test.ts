import { describe, expect, it } from 'vitest';
import type { Job, RequestRow } from '#lib/api.js';
import {
	elapsedMs,
	endpointOf,
	etaMs,
	formatBytes,
	formatDuration,
	importBody,
	isActive,
	isProblem,
	nextSort,
	requestTone,
	sortRows,
	sum,
	taskLabel,
	taskName,
	tookTone,
	type Sort
} from '#lib/imports.js';

const job = (patch: Partial<Job> = {}) => ({ status: 'running', ...patch }) as Job;

describe('importBody', () => {
	it('is null until the id is a positive whole number', () => {
		for (const text of ['', ' ', 'abc', '0', '-1', '1.5']) {
			expect(importBody('artist', text, '')).toBeNull();
		}
	});

	it('keeps the albums limit for a discography only', () => {
		expect(importBody('discography', '604', '3')).toEqual({
			kind: 'discography',
			genius_id: 604,
			albums_limit: 3
		});
		expect(importBody('discography', '604', ' ')?.albums_limit).toBeNull();
		expect(importBody('album', '604', '3')?.albums_limit).toBeNull();
	});
});

describe('progress numbers', () => {
	it('sums counts and never goes over 100%', () => {
		const counts = [
			{ kind: 'artist', done: 1, total: 1 },
			{ kind: 'album', done: 2, total: 54 }
		] as const;
		expect(sum([...counts])).toEqual({ done: 3, total: 55 });
	});

	it('formats durations with the two biggest units', () => {
		expect(formatDuration(900)).toBe('1 s');
		expect(formatDuration(65_000)).toBe('1 min 5 s');
		expect(formatDuration(3_840_000)).toBe('1 h 4 min');
	});

	it('guesses the time left only after a few finished units', () => {
		const started = '2026-01-01T00:00:00Z';
		const now = Date.parse(started) + 60_000;
		const at = (done: number) =>
			job({
				started_at: started,
				progress: { units: [{ kind: 'album', done, total: 10 }] } as Job['progress']
			});
		expect(etaMs(at(2), now)).toBeNull();
		expect(etaMs(at(3), now)).toBe(140_000); // 20 s per unit, 7 units left
		expect(etaMs(at(10), now)).toBeNull();
		expect(etaMs(job({ started_at: started }), now)).toBeNull();
	});

	it('measures a finished job up to its end, not up to now', () => {
		const finished = job({
			started_at: '2026-01-01T00:00:00Z',
			finished_at: '2026-01-01T00:00:30Z'
		});
		expect(elapsedMs(finished, Date.parse('2026-02-01T00:00:00Z'))).toBe(30_000);
		expect(elapsedMs(job(), 123)).toBe(0);
	});
});

describe('request log', () => {
	it('shows the path of a request without the host and the default query', () => {
		expect(endpointOf('https://genius.com/api/albums/9/tracks?page=1')).toBe(
			'/albums/9/tracks?page=1'
		);
		expect(endpointOf('https://genius.com/api/artists/604?text_format=plain')).toBe('/artists/604');
	});

	it('tells final errors from the ones that are retried', () => {
		expect(requestTone({ status_code: 200 })).toBe('good');
		expect(requestTone({ status_code: 404 })).toBe('bad');
		expect(requestTone({ status_code: 429 })).toBe('warn');
		expect(requestTone({ status_code: 503 })).toBe('warn');
		expect(requestTone({ status_code: null })).toBe('warn');
	});

	it('writes sizes and task names for people', () => {
		expect(formatBytes(null)).toBe('—');
		expect(formatBytes(512)).toBe('512 B');
		expect(formatBytes(2048)).toBe('2.0 KB');
		expect(formatBytes(51_200)).toBe('50 KB');
		expect(taskName('KID A', 7)).toBe('KID A');
		expect(taskName(null, 7)).toBe('#7');
		expect(taskName(null, null)).toBe('');
		expect(taskLabel('song', 7, null)).toBe('Song #7');
	});

	it('marks how long an answer took', () => {
		expect(tookTone(240)).toBe('good');
		expect(tookTone(1000)).toBe('warn');
		expect(tookTone(2999)).toBe('warn');
		expect(tookTone(3000)).toBe('bad');
	});

	it('counts errors, retries and very slow answers as problems', () => {
		const row = { status_code: 200, attempt: 1, elapsed_ms: 400 };
		expect(isProblem(row)).toBe(false);
		expect(isProblem({ ...row, elapsed_ms: 1500 })).toBe(false); // orange is only a hint
		expect(isProblem({ ...row, elapsed_ms: 3500 })).toBe(true);
		expect(isProblem({ ...row, attempt: 2 })).toBe(true);
		expect(isProblem({ ...row, status_code: 404 })).toBe(true);
		expect(isProblem({ ...row, status_code: null })).toBe(true);
	});

	it('knows which jobs are still running', () => {
		expect(isActive(job({ status: 'queued' }))).toBe(true);
		expect(isActive(job({ status: 'succeeded' }))).toBe(false);
	});
});

describe('sorting the request log', () => {
	const row = (id: number, elapsed_ms: number, size_bytes: number | null) =>
		({ id, elapsed_ms, size_bytes }) as RequestRow;
	const rows = [row(1, 300, 10), row(2, 900, null), row(3, 100, 50)];

	it('cycles biggest first, smallest first, then the order of arrival', () => {
		const first = nextSort(null, 'took');
		expect(first).toEqual({ key: 'took', dir: 'desc' });
		const second = nextSort(first, 'took');
		expect(second).toEqual({ key: 'took', dir: 'asc' });
		expect(nextSort(second, 'took')).toBeNull();
		expect(nextSort(second, 'size')).toEqual({ key: 'size', dir: 'desc' }); // another header starts over
	});

	it('sorts by took and by size and keeps a missing size last both ways', () => {
		const ids = (sort: Sort) => sortRows(rows, sort).map((r) => r.id);
		expect(ids(null)).toEqual([1, 2, 3]);
		expect(ids({ key: 'took', dir: 'desc' })).toEqual([2, 1, 3]);
		expect(ids({ key: 'took', dir: 'asc' })).toEqual([3, 1, 2]);
		expect(ids({ key: 'size', dir: 'desc' })).toEqual([3, 1, 2]);
		expect(ids({ key: 'size', dir: 'asc' })).toEqual([1, 3, 2]);
	});
});

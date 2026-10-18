/** 1234 -> "1.2K", 1500000 -> "1.5M"; small numbers stay as they are. */
export function formatCount(n: number) {
	if (n < 1000) return String(n);
	const [value, unit] = n < 1_000_000 ? [n / 1000, 'K'] : [n / 1_000_000, 'M'];
	return `${value.toFixed(value < 10 ? 1 : 0).replace(/\.0$/, '')}${unit}`;
}

/** "2007", "2007-05" or "2007-05-17": as much of a date as Genius really knows. */
export function formatRelease(date: string | null, precision: 'year' | 'month' | 'day' | null) {
	if (!date) return null;
	const length = precision === 'day' ? 10 : precision === 'month' ? 7 : 4;
	return date.slice(0, length);
}

/** "5 Oct 2026", "Oct 2026" or "2026": the whole date when Genius knows it, and no more than it knows. */
export function formatFullDate(date: string | null, precision: 'year' | 'month' | 'day' | null) {
	if (!date) return null;
	if (precision !== 'day' && precision !== 'month') return date.slice(0, 4);
	return new Date(`${date}T00:00:00Z`).toLocaleDateString('en-GB', {
		...(precision === 'day' && { day: 'numeric' }),
		month: 'short',
		year: 'numeric',
		timeZone: 'UTC'
	});
}

/** "17 Oct 2026, 13:23": when something happened, written like `formatFullDate`. */
export const formatDateTime = (iso: string) =>
	new Date(iso).toLocaleString('en-GB', {
		day: 'numeric',
		month: 'short',
		year: 'numeric',
		hour: '2-digit',
		minute: '2-digit'
	});

/** One line for a history entry: `field: old → new`, long values cut. */
export function describeChange(field: string, change: unknown) {
	const cut = (value: unknown) => {
		const text = typeof value === 'string' ? value : JSON.stringify(value);
		return text.length > 60 ? `${text.slice(0, 60)}…` : text;
	};
	const [before, after] = change as [unknown, unknown];
	return `${field}: ${cut(before)} → ${cut(after)}`;
}

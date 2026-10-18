import { describe, expect, it } from 'vitest';
import { BLOCKS } from '#lib/artists.js';

describe('BLOCKS', () => {
	it('splits the artists so that nobody is in two blocks', () => {
		const ids = BLOCKS.map((b) => b.id);
		expect(new Set(ids).size).toBe(ids.length);
		const key = (b: (typeof BLOCKS)[number]) => JSON.stringify(b.filters);
		expect(new Set(BLOCKS.map(key)).size).toBe(BLOCKS.length);
	});
});

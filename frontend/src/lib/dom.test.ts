import { describe, expect, it } from 'vitest';
import { loneLink, ourPage, safeUrl, youtubeEmbed, youtubeLink, type DomNode } from '#lib/dom.js';

describe('safeUrl', () => {
	it('lets only http and https links through', () => {
		expect(safeUrl('https://genius.com/artists/x')).toBe('https://genius.com/artists/x');
		expect(safeUrl('http://imdb.com/t')).toBe('http://imdb.com/t');
		for (const bad of ['javascript:alert(1)', 'data:text/html,x', 'not a url', '', undefined, 5]) {
			expect(safeUrl(bad)).toBeNull();
		}
	});
});

describe('youtubeLink', () => {
	it('gives the id and the second a clip starts at', () => {
		expect(youtubeLink('https://youtu.be/dQw4w9WgXcQ?t=1m57s')).toEqual({
			id: 'dQw4w9WgXcQ',
			start: 117
		});
		expect(youtubeLink('https://www.youtube.com/watch?v=dQw4w9WgXcQ')).toEqual({
			id: 'dQw4w9WgXcQ',
			start: 0
		});
		expect(youtubeLink('https://example.com/watch?v=dQw4w9WgXcQ')).toBeNull();
	});
});

describe('youtubeEmbed', () => {
	it('makes the player of every form of a YouTube link, with the start time', () => {
		const id = 'J0Kt0hNwaCE';
		const base = `https://www.youtube-nocookie.com/embed/${id}`;
		expect(youtubeEmbed(`https://youtu.be/${id}?t=1m57s`)).toBe(`${base}?start=117`);
		expect(youtubeEmbed(`https://www.youtube.com/watch?v=${id}&t=90`)).toBe(`${base}?start=90`);
		expect(youtubeEmbed(`https://m.youtube.com/shorts/${id}`)).toBe(base);
		expect(youtubeEmbed(`https://youtu.be/${id}?t=1h2m3s`)).toBe(`${base}?start=3723`);
	});

	it('leaves any other link alone', () => {
		expect(youtubeEmbed('https://twitter.com/Lilpeep/status/1308113181706006528')).toBeNull();
		expect(youtubeEmbed('https://www.youtube.com/@channel')).toBeNull();
		expect(youtubeEmbed('https://youtu.be/short')).toBeNull();
		expect(youtubeEmbed(undefined)).toBeNull();
	});
});

describe('loneLink', () => {
	const link: DomNode = { tag: 'a', attributes: { href: 'https://youtu.be/x' }, children: ['x'] };

	it('is the link of a paragraph with nothing but that link', () => {
		expect(loneLink({ tag: 'p', children: [link] })).toBe(link);
		expect(loneLink({ tag: 'p', children: [' ', link, ''] })).toBe(link);
	});

	it('is nothing when there is text beside the link', () => {
		expect(loneLink({ tag: 'p', children: ['see ', link] })).toBeNull();
		expect(loneLink({ tag: 'p', children: [link, link] })).toBeNull();
		expect(loneLink({ tag: 'p' })).toBeNull();
	});
});

describe('ourPage', () => {
	it('finds the artist or album of ours that the link of Genius leads to', () => {
		const refs = [{ api_path: '/artists/976208', kind: 'artist' as const, id: 7 }];
		const link = (path: string): DomNode => ({ tag: 'a', data: { api_path: path } });
		expect(ourPage(link('/artists/976208'), refs)?.id).toBe(7);
		expect(ourPage(link('/artists/1'), refs)).toBeUndefined();
		expect(ourPage({ tag: 'a' }, refs)).toBeUndefined();
	});
});

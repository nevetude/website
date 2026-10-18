import type { AlbumDetail, CreditGroup, RelatedAlbums } from '#lib/api.js';

const OF = {
	deluxe_edition_of: 'Deluxe edition of',
	alternate_version_of: 'Alternate version of',
	reissue_of: 'Reissue of',
	remix_version_of: 'Remix of'
} as const;

const PLURAL = {
	deluxe_edition_of: 'Deluxe editions',
	alternate_version_of: 'Alternate versions',
	reissue_of: 'Reissues',
	remix_version_of: 'Remixes'
} as const;

/** "Deluxe edition of" when this album is the edition, "Deluxe editions" when the others are. */
export const relationTitle = ({ type, inverse }: Pick<RelatedAlbums, 'type' | 'inverse'>) =>
	(inverse ? PLURAL : OF)[type];

/** Tracks grouped by disc, in the order they came; a missing disc is the first one. */
export function byDisc<T extends { disc_number: number | null }>(tracks: T[]) {
	const discs = new Map<number, T[]>();
	for (const track of tracks) {
		const number = track.disc_number ?? 1;
		discs.set(number, [...(discs.get(number) ?? []), track]);
	}
	return [...discs].map(([number, items]) => ({ number, tracks: items }));
}

/** The number each track is shown with, by the id of its placement: Genius often has none, then the order of arrival is the number. */
export function trackNumbers<
	T extends { id: number; disc_number: number | null; position: number | null }
>(tracks: T[]) {
	return Object.fromEntries(
		byDisc(tracks).flatMap(({ tracks: disc }) =>
			disc.map((track, i) => [track.id, track.position ?? i + 1] as const)
		)
	);
}

/**
 * The second colour of the cover, toned down so that the text stays readable on it. `dark` is the shade for the
 * smaller cards (the tracklist, the clips): the colour is mixed in the colour of the page and not of a container.
 */
export const coverTint = (
	album: Pick<AlbumDetail, 'cover_secondary_color'>,
	dark = false,
	share = 16 // percent of the colour of the cover in the shade of the smaller cards
) =>
	album.cover_secondary_color
		? dark
			? `color-mix(in oklab, ${album.cover_secondary_color} ${share}%, var(--color-surface-300))`
			: `color-mix(in oklab, ${album.cover_secondary_color} 45%, var(--color-surface-200))`
		: undefined;

/** The plain grey of a panel with some of the colour of the cover mixed into it (`share` percent). */
export const coverHint = (album: Pick<AlbumDetail, 'cover_secondary_color'>, share = 10) =>
	album.cover_secondary_color
		? `color-mix(in oklab, ${album.cover_secondary_color} ${share}%, var(--color-surface-200))`
		: undefined;

/** Whether the artists of a track are not just the artists of the album: only then are they worth showing. */
export const differs = (track: { id: number }[], album: { id: number }[]) =>
	track.length !== album.length || track.some(({ id }) => !album.some((a) => a.id === id));

/** Every cover Genius knows, the main one first; an album with none of them listed still has its main one. */
export function coverList(album: Pick<AlbumDetail, 'cover_url' | 'covers'>) {
	// The same picture can be listed twice; the lists of covers are keyed by the address.
	const urls = [...new Set(album.covers.map((cover) => cover.image_url))];
	if (album.cover_url && !urls.includes(album.cover_url)) urls.unshift(album.cover_url);
	const main = album.cover_url ? urls.indexOf(album.cover_url) : -1;
	return main > 0 ? [urls[main], ...urls.filter((_, i) => i !== main)] : urls;
}

const ROLE_ORDER = ['Producer', 'Producers', 'Featuring', 'Writer', 'Writers', 'Distributor'];

/** The roles people look for first (producers, writers) come first; the rest keep their order. */
export const sortRoles = (groups: CreditGroup[]) =>
	groups.toSorted((a, b) => rank(a.role) - rank(b.role));

const rank = (role: string) => {
	const i = ROLE_ORDER.indexOf(role);
	return i === -1 ? ROLE_ORDER.length : i;
};

/** "en" -> "English". */
export const languageName = (code: string) =>
	new Intl.DisplayNames(['en'], { type: 'language' }).of(code) ?? code;

/** The best-viewed tracks of an album, by view count: song id -> place (1 is the best). */
export function popularity(tracks: { song_id: number; view_count: number | null }[], top = 5) {
	return new Map(
		tracks
			.filter((track) => track.view_count)
			.toSorted((a, b) => (b.view_count ?? 0) - (a.view_count ?? 0))
			.slice(0, top)
			.map((track, i) => [track.song_id, i + 1])
	);
}

// --- the size of an album card, shared by the strip of a category and its opened grid ---

/**
 * The size of an album card, in px. The row is made of cells at least `min` wide. A card of the grid
 * view is one cell wide and a cell plus `text` tall (`text` is what it has below its cover: the gap, the
 * title line and the line of artists). A card of the rows view is `span` cells wide and only a cell tall:
 * its cover is as big as the cover of a grid card and nothing is under it. The strip of a category and its
 * opened grid both take their columns from here, so opening a category never resizes a card.
 */
export const CARD = { min: 150, span: 2, text: 44, pad: 24 } as const; // pad: the padding of a card, both sides

/** How many cells fit in a row of this width. */
export const cellsPerRow = (width: number) => Math.max(1, Math.floor(width / CARD.min));

// The functions below take `cells` when a place wants its own number of cells per row (a narrow block
// that must show exactly two albums); without it the number follows from the width.

/** How many cells a card takes: never more than the row has. */
export const cardSpan = (width: number, view: 'grid' | 'list', cells = cellsPerRow(width)) =>
	view === 'list' ? Math.min(CARD.span, cells) : 1;

/** How many whole cards of a view fit in a row of this width. */
export const perRow = (width: number, view: 'grid' | 'list', cells = cellsPerRow(width)) =>
	Math.floor(cells / cardSpan(width, view, cells));

/** The height of a card, in px. Always a number, so that a change of view can be animated. */
export const cardHeight = (width: number, view: 'grid' | 'list', cells = cellsPerRow(width)) =>
	width / cells + (view === 'grid' ? CARD.text : 0);

/** The side of a cover, the same in both views: a cell without the padding of its card. */
export const coverSize = (width: number, cells = cellsPerRow(width)) => width / cells - CARD.pad;

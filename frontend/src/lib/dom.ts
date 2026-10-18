import type { components } from '#lib/api/schema.js';

export type DomNode = components['schemas']['DomNode'];
export type DomRef = components['schemas']['DomRef'];
export type Dom = DomNode | string;

const parse = (href: string) => {
	try {
		return new URL(href);
	} catch {
		return null;
	}
};

/** The link as it may be put in a page: only http and https (never `javascript:` and the like). */
export const safeUrl = (href: unknown) => {
	const url = typeof href === 'string' ? parse(href) : null;
	return url && (url.protocol === 'https:' || url.protocol === 'http:') ? url.href : null;
};

/** "1m57s", "117s" or "117" -> seconds. */
const seconds = (text: string | null) => {
	const found = text?.match(/^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s?)?$/);
	return found
		? Number(found[1] ?? 0) * 3600 + Number(found[2] ?? 0) * 60 + Number(found[3] ?? 0)
		: 0;
};

/** The site of the YouTube players (without cookies until a clip is played). */
export const YOUTUBE_ORIGIN = 'https://www.youtube-nocookie.com';

/** The id of the clip and the second it starts at in a YouTube link, or null for any other link. */
export function youtubeLink(href: unknown) {
	const url = typeof href === 'string' ? parse(href) : null;
	if (!url) return null;
	const host = url.hostname.replace(/^(www|m)\./, '');
	const id =
		host === 'youtu.be'
			? url.pathname.slice(1)
			: host === 'youtube.com'
				? (url.searchParams.get('v') ??
					url.pathname.match(/^\/(?:shorts|embed|live)\/([^/]+)/)?.[1])
				: null;
	if (!id || !/^[\w-]{11}$/.test(id)) return null;
	return { id, start: seconds(url.searchParams.get('t') ?? url.searchParams.get('start')) };
}

/** The address of the player of a clip. */
export const youtubeEmbedUrl = (id: string, start = 0) =>
	`${YOUTUBE_ORIGIN}/embed/${id}${start ? `?start=${start}` : ''}`;

/** The player of a YouTube link, or null for any other link. */
export function youtubeEmbed(href: unknown) {
	const link = youtubeLink(href);
	return link && youtubeEmbedUrl(link.id, link.start);
}

/** The only link of a paragraph that holds nothing else (Genius turns such a paragraph into an embed). */
export function loneLink(node: DomNode) {
	const parts = (node.children ?? []).filter((child) => typeof child !== 'string' || child.trim());
	const [only] = parts;
	return parts.length === 1 && typeof only !== 'string' && only.tag === 'a' ? only : null;
}

/** The page of ours that a link of Genius leads to, if we have that artist or album. */
export const ourPage = (node: DomNode, refs: DomRef[]) =>
	refs.find((ref) => ref.api_path === node.data?.api_path);

<script lang="ts">
	import Globe from '@lucide/svelte/icons/globe';
	import Music2 from '@lucide/svelte/icons/music-2';
	import {
		siApplemusic,
		siBandcamp,
		siFacebook,
		siInstagram,
		siShazam,
		siSnapchat,
		siSoundcloud,
		siSpotify,
		siTidal,
		siTelegram,
		siTiktok,
		siVk,
		siX,
		siYoutube
	} from 'simple-icons';
	import type { ArtistDetail } from '#lib/api.js';
	import ExtLink from '#lib/ui/ExtLink.svelte';

	let { links }: { links: ArtistDetail['links'] } = $props();

	// The brands that are in black (X, TikTok, Tidal) light up in white on this dark page; the rest in their own colour.
	const white = 'FFFFFF';
	type Brand = { label: string; path?: string; hex: string };
	const BRANDS: Record<string, Brand> = {
		spotify: { label: 'Spotify', ...siSpotify },
		apple_music: { label: 'Apple Music', ...siApplemusic },
		youtube: { label: 'YouTube', ...siYoutube },
		soundcloud: { label: 'SoundCloud', ...siSoundcloud },
		bandcamp: { label: 'Bandcamp', ...siBandcamp },
		tidal: { label: 'Tidal', path: siTidal.path, hex: white },
		shazam: { label: 'Shazam', ...siShazam },
		instagram: { label: 'Instagram', ...siInstagram },
		twitter: { label: 'X', path: siX.path, hex: white },
		facebook: { label: 'Facebook', ...siFacebook },
		tiktok: { label: 'TikTok', path: siTiktok.path, hex: white },
		snapchat: { label: 'Snapchat', ...siSnapchat },
		vk: { label: 'VK', ...siVk },
		telegram: { label: 'Telegram', ...siTelegram },
		// No brand mark of these two in the set: a plain icon in a colour of its own.
		amazon_music: { label: 'Amazon Music', hex: '25D1DA' },
		website: { label: 'Website', hex: white }
	};

	// The site has no name of its own: its address is the name (without "www.").
	const label = (kind: string, url: string) =>
		kind === 'website' ? new URL(url).host.replace(/^www\./, '') : BRANDS[kind].label;

	// Two groups: the pages of the artist on social networks (and its own site; VK and X are the last ones), and the places
	// where its music is heard or seen (YouTube is one of them).
	const SOCIAL = [
		'website',
		'instagram',
		'facebook',
		'tiktok',
		'snapchat',
		'telegram',
		'vk',
		'twitter'
	];

	// A mockup: these four are always in the social group, to see it with more rows than Genius gives.
	const MOCKED = [
		{ kind: 'vk', url: 'https://vk.ru/' },
		{ kind: 'telegram', url: 'https://telegram.org/' },
		{ kind: 'facebook', url: 'https://facebook.com/' },
		{ kind: 'twitter', url: 'https://x.com/' }
	];

	const all = $derived([
		...links,
		...MOCKED.filter((mock) => !links.some((link) => link.kind === mock.kind))
	]);
	const groups = $derived(
		[
			{
				title: 'Social',
				items: SOCIAL.flatMap((kind) => all.filter((link) => link.kind === kind))
			},
			{ title: 'Streaming', items: all.filter((link) => !SOCIAL.includes(link.kind)) }
		].filter((group) => group.items.length)
	);
</script>

<!-- The links of the artist in a plain list, no container, one column, small, the two groups a little apart and without titles: a mark and a name in grey; under the pointer
     the mark takes the colour of the brand and the name turns white. -->
{#if groups.length}
	<div aria-label="Links" class="self-start space-y-5">
		{#each groups as group (group.title)}
			<section aria-label={group.title}>
				<ul>
					{#each group.items as link (link.kind)}
						{@const brand = BRANDS[link.kind]}
						<li style:--brand="#{brand.hex}">
							<ExtLink
								href={link.url}
								class="group flex items-center gap-2 py-1 text-[11px] font-semibold text-surface-content/60 hover:text-surface-content"
							>
								{#if brand.path}
									<svg
										viewBox="0 0 24 24"
										aria-hidden="true"
										class="size-3.5 shrink-0 fill-current text-surface-content/50 group-hover:text-(--brand)"
									>
										<path d={brand.path} />
									</svg>
								{:else if link.kind === 'website'}
									<Globe
										class="size-3.5 shrink-0 text-surface-content/50 group-hover:text-(--brand)"
										aria-hidden="true"
									/>
								{:else}
									<Music2
										class="size-3.5 shrink-0 text-surface-content/50 group-hover:text-(--brand)"
										aria-hidden="true"
									/>
								{/if}
								<span class="min-w-0 truncate">{label(link.kind, link.url)}</span>
							</ExtLink>
						</li>
					{/each}
				</ul>
			</section>
		{/each}
	</div>
{/if}

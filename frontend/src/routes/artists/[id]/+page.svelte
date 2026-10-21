<script lang="ts">
	import { api } from '#lib/api.js';
	import AlbumGrid from '#lib/artist/AlbumGrid.svelte';
	import ArtistGenres from '#lib/artist/ArtistGenres.svelte';
	import ArtistInfo from '#lib/artist/ArtistInfo.svelte';
	import ArtistPortrait from '#lib/artist/ArtistPortrait.svelte';
	import ArtistVideos from '#lib/artist/ArtistVideos.svelte';
	import Description from '#lib/entity/Description.svelte';
	import ImportInfo from '#lib/entity/ImportInfo.svelte';
	import RawResponse from '#lib/entity/RawResponse.svelte';
	import Technical from '#lib/entity/Technical.svelte';
	import RelatedArtists from '#lib/artist/RelatedArtists.svelte';
	import ProfileLinks from '#lib/artist/ProfileLinks.svelte';
	import SongList from '#lib/artist/SongList.svelte';
	import TopTracks from '#lib/artist/TopTracks.svelte';
	import Breadcrumbs from '#lib/ui/Breadcrumbs.svelte';
	import Collapse from '#lib/ui/Collapse.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const artist = $derived(data.artist);

	// The description is this high while it is closed, the same as on the page of an album.
	const COLLAPSED = 470;
</script>

<svelte:head><title>{artist.base_name} · Music</title></svelte:head>

<Breadcrumbs trail={[{ label: artist.base_name }]} />

{#key artist.id}
	{@const artistId = artist.id}
	<div class="space-y-10">
		<!-- The top of the page is laid out like the top of the page of an album. Two rows. First: the portrait in its
		     panel and the header with the facts. Second: the popular tracks with what goes under them, and the
		     description with the links and the members beside it. The header is 380px high at least; the popular tracks lie over the lower
		     edge of the panel of the portrait. On a narrow screen the header comes first. -->
		<div
			class="grid grid-cols-[minmax(0,1fr)] items-start gap-x-8 gap-y-6 min-[1000px]:grid-cols-[380px_minmax(0,1fr)] min-[1000px]:grid-rows-[minmax(380px,auto)_auto] min-[1000px]:gap-y-0"
		>
			<div class="order-2 min-[1000px]:order-none min-[1000px]:-mb-12 min-[1000px]:self-stretch">
				<ArtistPortrait
					src={artist.cover_url}
					name={artist.base_name}
					verified={artist.is_verified}
				/>
			</div>
			<div class="order-1 min-[1000px]:order-none min-[1000px]:self-stretch">
				<!-- The same panel as on the page of an album, as wide as there: the right column stays for the genres. It is as
				     high as the row, so its lower edge is where the popular tracks begin. -->
				<div
					class="grid grid-cols-[minmax(0,1fr)] gap-y-3 min-[1000px]:h-full min-[1200px]:grid-cols-[minmax(0,1fr)_400px] min-[1200px]:gap-x-8"
				>
					<div class="min-w-0 rounded-xl bg-surface-200 px-4 pt-4">
						<ArtistInfo {artist} />
					</div>
					<div class="min-w-0 min-[1200px]:self-start">
						<ArtistGenres genres={artist.genres} />
					</div>
				</div>
			</div>
			<div class="relative z-10 order-3 min-[1000px]:order-none">
				<TopTracks
					artistId={artist.id}
					ownSongs={artist.song_roles.some(({ role }) => role === 'Artist')}
				/>
			</div>
			<div
				class="order-4 grid grid-cols-[minmax(0,1fr)] items-start gap-y-8 min-[1000px]:order-none min-[1200px]:grid-cols-[minmax(0,1fr)_400px] min-[1200px]:gap-x-8"
			>
				<div class="min-w-0">
					{#if artist.description}
						<Collapse height={COLLAPSED} fade="var(--color-surface-200)" class="rounded-xl">
							<Description
								dom={artist.description_dom}
								text={artist.description}
								refs={artist.description_refs}
							/>
						</Collapse>
					{/if}
				</div>
				<div class="min-w-0 space-y-8">
					<ProfileLinks links={artist.links} />
					<RelatedArtists title="Members" artists={artist.members} />
					<RelatedArtists title="Member of" artists={artist.groups} />
				</div>
			</div>
		</div>

		<AlbumGrid artistId={artist.id} roles={artist.album_roles} />
		<ArtistVideos artistId={artist.id} />
		<SongList artistId={artist.id} roles={artist.song_roles} />
		<Technical>
			<ImportInfo
				subject="artist"
				createdAt={artist.created_at}
				updatedAt={artist.updated_at}
				imports={artist.imports}
				history={artist.history}
			/>
			<RawResponse
				stub="No raw response: the artist is a stub."
				fetchRaw={async () =>
					(
						await api.GET('/api/v1/artists/{artist_id}/raw', {
							params: { path: { artist_id: artistId } }
						})
					).data}
			/>
		</Technical>
	</div>
{/key}

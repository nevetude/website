import createClient from 'openapi-fetch';
import type { components, paths } from '#lib/api/schema.js';

// Relative URLs: the dev server proxies /api to the backend, so the site and the API share one origin.
export const api = createClient<paths>();

export type Job = components['schemas']['ImportJobOut'];
export type Count = components['schemas']['CountOut'];
export type RequestRow = components['schemas']['ImportRequestOut'];
export type ImportKind = components['schemas']['ImportKind'];
export type ArtistHit = components['schemas']['ArtistSearchHit'];

export type ArtistCard = components['schemas']['ArtistCard'];
export type RoleCount = components['schemas']['RoleCount'];
export type WorkRoleCount = components['schemas']['WorkRoleCount'];

export type ArtistDetail = components['schemas']['ArtistDetail'];
export type ArtistRef = components['schemas']['ArtistRef'];
export type ArtistSong = components['schemas']['ArtistSong'];
export type ArtistAlbum = components['schemas']['ArtistAlbum'];

export type AlbumDetail = components['schemas']['AlbumDetail'];
export type AlbumTrack = components['schemas']['AlbumTrackOut'];
export type AlbumVideo = components['schemas']['AlbumVideoOut'];
export type CreditGroup = components['schemas']['CreditGroup'];
export type RelatedAlbums = components['schemas']['RelatedAlbums'];
export type ArtistVideo = components['schemas']['ArtistVideo'];

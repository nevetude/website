export type SortField = 'name' | 'followers' | 'tracks';
export type Order = 'asc' | 'desc';

export const SORTS: { value: SortField; label: string; first: Order }[] = [
	{ value: 'name', label: 'Alphabet', first: 'asc' },
	{ value: 'followers', label: 'Popularity', first: 'desc' },
	{ value: 'tracks', label: 'Tracks', first: 'desc' }
];

type Filters = {
	import_state?: 'full' | 'stub';
	is_group?: boolean;
	discography_imported?: boolean;
};

/** The blocks of the home page. A full artist is in one block only: the first one that fits. */
export const BLOCKS: { id: string; title: string; filters: Filters }[] = [
	{
		id: 'imported',
		title: 'Imported by hand',
		filters: { import_state: 'full', discography_imported: true }
	},
	{
		id: 'groups',
		title: 'Groups',
		filters: { import_state: 'full', discography_imported: false, is_group: true }
	},
	{
		id: 'artists',
		title: 'Artists',
		filters: { import_state: 'full', discography_imported: false, is_group: false }
	},
	{ id: 'stub-groups', title: 'Stub groups', filters: { import_state: 'stub', is_group: true } },
	{ id: 'stub-artists', title: 'Stub artists', filters: { import_state: 'stub', is_group: false } }
];

export type Block = (typeof BLOCKS)[number];

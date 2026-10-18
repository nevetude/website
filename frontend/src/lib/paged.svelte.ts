type Page<T> = { items: T[]; total: number };

/**
 * A list read from a paged endpoint: from the first page again (`reload`), page by page (`more`) or
 * whole (`reload(true)`). An answer to an older request never replaces the answer to a newer one.
 *
 * `fetchPage` gets the number of items already held and returns the next page, or nothing when the
 * call failed.
 */
export class PagedList<T> {
	items = $state.raw<T[]>([]);
	total = $state(0);
	loading = $state(true);
	failed = $state(false);
	private version = 0;

	constructor(private fetchPage: (offset: number) => Promise<Page<T> | undefined>) {}

	reload(all = false) {
		return this.load(false, all);
	}

	more() {
		return this.load(true, false);
	}

	private async load(append: boolean, all: boolean) {
		const mine = ++this.version;
		this.loading = true;
		this.failed = false;
		try {
			const items = append ? [...this.items] : [];
			let total = this.total;
			for (;;) {
				const page = await this.fetchPage(items.length);
				if (mine !== this.version) return;
				if (!page) {
					this.failed = true;
					return;
				}
				items.push(...page.items);
				total = page.total;
				if (!all || !page.items.length || items.length >= total) break;
			}
			this.items = items;
			this.total = total;
		} catch {
			if (mine === this.version) this.failed = true;
		} finally {
			if (mine === this.version) this.loading = false;
		}
	}
}

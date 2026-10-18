import { expect, test } from '@playwright/test';

const form = (page: import('@playwright/test').Page) =>
	page.locator('section', { has: page.getByRole('heading', { name: 'Import', exact: true }) });

test('the import page opens with the discography mode and its search', async ({ page }) => {
	await page.goto('/import');
	await expect(page.getByLabel('Find an artist')).toBeVisible();
	await expect(page.getByLabel('Artist id')).toBeVisible();
	await expect(page.getByLabel('Albums limit')).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Monitor' })).toBeVisible();
});

test('one entity is imported by its id from the mode menu', async ({ page }) => {
	await page.goto('/import');
	await page.waitForLoadState('networkidle'); // clicks before hydration do nothing
	await page.getByLabel('Mode').click();
	await page.getByRole('option', { name: 'albums/{id}' }).click();
	await expect(page.getByLabel('Find an artist')).toBeHidden();
	await expect(page.getByLabel('Albums limit')).toBeHidden();
	const start = form(page).getByRole('button', { name: 'Import' });
	await expect(start).toBeDisabled();
	await page.getByLabel('Id', { exact: true }).fill('1460125');
	await expect(start).toBeEnabled();
});

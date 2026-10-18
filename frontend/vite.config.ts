import { defineConfig } from 'vitest/config';
import { playwright } from '@vitest/browser-playwright';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			// The site is client-only (`ssr = false`): a build is static files, and every address is answered by the
			// one page that starts the app.
			adapter: adapter({ fallback: 'index.html' })
		})
	],
	// The icons are Svelte components, one file for each: they are compiled with the app. Pre-bundled, every new
	// icon makes the dev server optimize again and reload the page, and the page then breaks with "Cannot read
	// properties of undefined (reading 'call')" until it is loaded again by hand.
	optimizeDeps: { exclude: ['@lucide/svelte'] },
	// One address for the site and the API: the dev server forwards /api to the backend.
	server: { port: 8080, strictPort: true, proxy: { '/api': 'http://localhost:8000' } },
	preview: { port: 8080, proxy: { '/api': 'http://localhost:8000' } },
	test: {
		expect: { requireAssertions: true },
		projects: [
			{
				extends: './vite.config.ts',
				test: {
					name: 'client',
					browser: {
						enabled: true,
						provider: playwright(),
						instances: [{ browser: 'chromium', headless: true }]
					},
					include: ['src/**/*.svelte.{test,spec}.{js,ts}']
				}
			},

			{
				extends: './vite.config.ts',
				test: {
					name: 'server',
					environment: 'node',
					include: ['src/**/*.{test,spec}.{js,ts}'],
					exclude: ['src/**/*.svelte.{test,spec}.{js,ts}']
				}
			}
		]
	}
});

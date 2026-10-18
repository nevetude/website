import { defineConfig } from '@playwright/test';

export default defineConfig({
	webServer: { command: 'pnpm build && pnpm preview', port: 8080 },
	use: { baseURL: 'http://localhost:8080' },
	testMatch: '**/*.e2e.{ts,js}'
});

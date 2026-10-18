---
paths:
  - "frontend/**"
---

# Frontend rules (TypeScript / SvelteKit / Svelte 5)

- TypeScript `strict`; no `any`, no non-null `!` without a reason.
- Svelte 5 runes only: `$state`, `$derived`, `$effect` (sparingly), `$props`, snippets instead of slots. No `export let`, no `$:`.
- Shared reactive state goes in `.svelte.ts` modules, not legacy stores.
- Prefer SvelteKit `load` functions and form actions for data and mutations. Keep components small and presentational.
- API types are generated from the backend OpenAPI schema, never hand-written.
- Audio playback state lives in a single module that survives navigation (the player must not restart on route change).
- Accessibility is required: semantic elements, keyboard control for the player.
- Check with `svelte-check`; unit tests with `vitest`, e2e with `playwright`.
- Add dependencies with `pnpm add`.

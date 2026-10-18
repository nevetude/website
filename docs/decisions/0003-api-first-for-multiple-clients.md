# ADR 0003: The API serves any client (web now, Android later)

Status: accepted (user requirement). The SvelteKit site is just one client of the API.

## Rules
1. **All logic and data go through `/api/v1`.** No server-only paths in SvelteKit (no form actions or load functions that read the database or private endpoints directly). SvelteKit may call the API during SSR, but only through the same public endpoints.
2. **The OpenAPI schema is the contract.** Explicit response models (never ORM objects), stable `operationId`s, so clients (TypeScript now, Kotlin later) can be generated. Pydantic models are the only shape the API exposes.
3. **No presentation logic on the server.** Names are returned as separate parts (`name`, `base_name`, `variant`, `disambiguator`); what to show is the client's setting. `notes` and descriptions are returned as raw text (links are rendered by the client). Dates are returned as value plus precision. Permissions are returned (`/me`: role, `can_edit`) and enforced on the server.
4. **Auth works for browsers and native apps.** One server-side session (the existing `user_session` table, opaque random token, stored hashed). Clients send it as `Authorization: Bearer <token>` (apps, scripts). The browser gets the same token in an HttpOnly cookie. Cookie requests need CSRF protection; Bearer requests do not. This replaces the earlier "cookie only" idea; it is still a session, not a JWT.
5. **Media streaming** is a plain HTTP endpoint with `Range` support. Native players can send headers; the web `<audio>` tag cannot, so media URLs need either the cookie or short-lived signed URLs (decide when building the player).
6. **Consistent conventions:** `/api/v1` prefix, one error format (RFC 9457 problem details), one pagination format for every list (`limit`/`offset` with `total` at first), ISO 8601 UTC timestamps, integer ids, absolute URLs for images, `updated_at` available for future caching and offline sync.
7. **Breaking changes** get a new version prefix (`/api/v2`); `/api/v1` stays stable once the Android app exists.

## Consequences
- The frontend API client is generated from OpenAPI (`openapi-typescript`), as already planned.
- Endpoints are written and tested at the HTTP level (httpx against the app), so a second client can rely on them.

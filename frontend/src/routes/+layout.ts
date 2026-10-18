// A client-only site: the API is reached through the same origin as the page (the dev server proxies /api),
// and the pages must not have a data path of their own on the server (docs/decisions/0003).
export const ssr = false;

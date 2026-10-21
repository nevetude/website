import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from music_backend.enums import ImportKind

USER_AGENT = "music-research/0.1 (personal project, low volume)"
RETRY_STATUSES = frozenset({500, 502, 503, 504})


@dataclass(slots=True, frozen=True)
class RequestLog:
    url: str
    status_code: int | None
    elapsed_ms: int
    size_bytes: int | None
    attempt: int  # 1 for the first try, then the retries
    error: str | None = None
    # Which task the request was made for; filled in by the importer, not by the client.
    task_kind: ImportKind | None = None
    task_genius_id: int | None = None
    task_name: str | None = None


type Recorder = Callable[[RequestLog], Awaitable[None]]


@dataclass(slots=True, frozen=True)
class Connection:
    """What the last answer of Genius says about the server we talk to, for the monitor of the import."""

    host: str
    ip: str | None  # the address we are connected to; none when the transport is not a real socket
    http_version: str
    tls_version: str | None
    cipher: str | None
    server: str | None  # the `Server` header: Genius sits behind Cloudflare
    edge: (
        str | None
    )  # `cf-ray` ends with the code of the Cloudflare data centre that answered ("...-TLL")
    origin: str | None  # the last hop of `Via`: the app behind Cloudflare ("heroku-router")
    cache: str | None
    seen_at: datetime


class GeniusError(Exception):
    def __init__(
        self, message: str, status_code: int | None = None, *, retryable: bool = False
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class RateLimitedError(GeniusError):
    """429: not retried and not skipped like other failures. The whole import stops at the first one,
    so the request log ends exactly where the limit was hit."""


class GeniusClient:
    """Anonymous client for the public Genius web API. Requests are serialized and spaced out:
    `min_interval_s` is the pause between the starts of two requests, so the pace is the interval or
    the latency of an answer, whichever is longer."""

    def __init__(
        self, base_url: str, min_interval_s: float, retry_backoff_s: float = 2.0, retries: int = 2
    ) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"User-Agent": USER_AGENT},
            timeout=httpx.Timeout(30, connect=10),
        )
        self._min_interval_s = min_interval_s
        self._retry_backoff_s = retry_backoff_s
        self._retries = retries
        self._lock = asyncio.Lock()
        self._last_request_at = 0.0
        self.connection: Connection | None = None  # of the latest answer

    async def get(
        self, path: str, params: dict[str, Any] | None = None, record: Recorder | None = None
    ) -> dict[str, Any]:
        """Return the `response` object of a successful call; raise GeniusError otherwise.

        Network errors and 5xx are retried a couple of times (each attempt is logged); other 4xx
        answers are final, and 429 raises RateLimitedError.
        """
        for attempt in range(self._retries + 1):
            try:
                return await self._attempt(path, params, record, attempt + 1)
            except GeniusError as error:
                if not error.retryable or attempt == self._retries:
                    raise
                await asyncio.sleep(self._retry_backoff_s * (attempt + 1))
        raise AssertionError("unreachable")  # pragma: no cover

    async def _attempt(
        self, path: str, params: dict[str, Any] | None, record: Recorder | None, attempt: int
    ) -> dict[str, Any]:
        url = str(self._http.build_request("GET", path, params=params).url)
        async with self._lock:
            pause = self._min_interval_s - (time.monotonic() - self._last_request_at)
            if pause > 0:
                await asyncio.sleep(pause)
            self._last_request_at = time.monotonic()
            started = time.perf_counter()
            try:
                response = await self._http.get(path, params=params)
            except httpx.HTTPError as error:
                log = RequestLog(url, None, self._elapsed_ms(started), None, attempt, repr(error))
                if record:
                    await record(log)
                raise GeniusError(f"Genius request failed: {error!r}", retryable=True) from error

        self.connection = self._connection(response)
        limited = response.status_code == 429
        log = RequestLog(
            url,
            response.status_code,
            self._elapsed_ms(started),
            len(response.content),
            attempt,
            self._limit_note(response) if limited else None,
        )
        if record:
            await record(log)
        if limited:
            raise RateLimitedError(
                f"Genius answered 429 (too many requests) for {path}: the import was stopped. "
                f"See the request log; {log.error}",
                429,
            )
        if not response.is_success:
            raise GeniusError(
                f"Genius answered {response.status_code} for {path}",
                response.status_code,
                retryable=response.status_code in RETRY_STATUSES,
            )
        return response.json()["response"]  # type: ignore[no-any-return]

    @staticmethod
    def _connection(response: httpx.Response) -> Connection:
        stream = response.extensions.get("network_stream")  # a mocked transport has none
        address = stream.get_extra_info("server_addr") if stream else None
        tls = stream.get_extra_info("ssl_object") if stream else None
        ray = response.headers.get("cf-ray")
        via = response.headers.get("via")
        return Connection(
            host=response.url.host,
            ip=address[0] if address else None,
            http_version=response.http_version,
            tls_version=tls.version() if tls else None,
            cipher=tls.cipher()[0] if tls else None,
            server=response.headers.get("server"),
            edge=ray.rsplit("-", 1)[1] if ray else None,
            origin=via.split()[-1] if via else None,
            cache=response.headers.get("cf-cache-status"),
            seen_at=datetime.now(UTC),
        )

    @staticmethod
    def _limit_note(response: httpx.Response) -> str:
        """What may explain a 429: the body and the headers that name a limit, a wait or who answered."""
        headers = (
            f"{name}={value}"
            for name, value in response.headers.items()
            if name in ("retry-after", "date", "server", "cf-ray") or "ratelimit" in name
        )
        return f"{response.text[:300]!r} | {', '.join(headers)}"

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return round((time.perf_counter() - started) * 1000)

    async def aclose(self) -> None:
        await self._http.aclose()

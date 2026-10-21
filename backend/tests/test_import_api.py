import asyncio
from typing import Any

import httpx
import respx
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from music_backend.config import Settings
from music_backend.enums import ImportKind, ImportState, JobStatus, UserRole
from music_backend.main import create_app
from music_backend.models import AppUser, Artist, ImportJob
from tests.conftest import truncate_all_tables, wait_for_job
from tests.fakes import album_payload, artist_payload, song_payload, track

GENIUS = "https://genius.com/api"

type SessionMaker = async_sessionmaker[AsyncSession]


def answer(key: str, payload: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, json={"response": {key: payload}})


def search_response(*hits: tuple[int, str]) -> dict[str, Any]:
    results = [
        {"result": {"id": i, "name": n, "image_url": f"https://img/{i}.jpg"}} for i, n in hits
    ]
    return {"response": {"sections": [{"type": "artist", "hits": results}]}}


async def start(api: AsyncClient, kind: str, genius_id: int, **extra: Any) -> dict[str, Any]:
    created = await api.post(
        "/api/v1/imports", json={"kind": kind, "genius_id": genius_id, **extra}
    )
    assert created.status_code == 202
    return await wait_for_job(api, created.json()["id"])


# --- search --------------------------------------------------------------------------------------


async def test_search_marks_artists_already_in_the_database(
    api: AsyncClient, respx_mock: respx.MockRouter, sessionmaker: SessionMaker
) -> None:
    async with sessionmaker() as db:
        db.add(
            Artist(
                genius_id=1,
                name="Aphex Twin",
                base_name="Aphex Twin",
                import_state=ImportState.FULL,
            )
        )
        db.add(
            Artist(genius_id=2, name="Tribute", base_name="Tribute", import_state=ImportState.STUB)
        )
        await db.commit()
    respx_mock.get(f"{GENIUS}/search/artist", params={"q": "Aphex Twin"}).respond(
        json=search_response((1, "Aphex Twin"), (2, "Tribute"), (3, "Someone Else"))
    )

    response = await api.get("/api/v1/genius/search/artists", params={"q": "Aphex Twin"})

    hits = {hit["genius_id"]: hit for hit in response.json()}
    assert [hits[i]["db_state"] for i in (1, 2, 3)] == ["full", "stub", None]
    assert hits[3]["artist_id"] is None
    assert hits[1]["image_url"] == "https://img/1.jpg"


async def test_search_reports_a_genius_failure_as_bad_gateway(
    api: AsyncClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{GENIUS}/search/artist").respond(status_code=500)

    assert (await api.get("/api/v1/genius/search/artists", params={"q": "x"})).status_code == 502


# --- jobs ----------------------------------------------------------------------------------------


async def test_artist_import_job_end_to_end(
    api: AsyncClient, respx_mock: respx.MockRouter, sessionmaker: SessionMaker
) -> None:
    respx_mock.get(f"{GENIUS}/artists/21").mock(
        return_value=answer("artist", artist_payload(21, "Wu-Tang Clan"))
    )

    job = await start(api, "artist", 21)

    assert (job["status"], job["message"], job["error"]) == ("succeeded", "Done", None)
    assert (job["progress_done"], job["progress_total"]) == (1, 1)
    assert job["subject_name"] == "Wu-Tang Clan"
    assert [r["status_code"] for r in job["recent_requests"]] == [200]
    async with sessionmaker() as db:
        assert (await db.get_one(Artist, job["result_id"])).genius_id == 21
    requests = (await api.get(f"/api/v1/imports/{job['id']}/requests")).json()
    assert (requests["total"], requests["items"][0]["status_code"]) == (1, 200)
    first = requests["items"][0]
    assert (first["task_kind"], first["task_genius_id"], first["attempt"]) == ("artist", 21, 1)
    assert first["url"] == f"{GENIUS}/artists/21"
    assert (job["requests_total"], job["progress"]) == (1, None)  # progress is for running jobs
    assert first["page_url"] == "https://genius.com/artists/21"  # saved by the import itself
    newer = (await api.get(f"/api/v1/imports/{job['id']}/requests?after_id={first['id']}")).json()
    assert newer["items"] == []


async def test_monitor_is_empty_before_the_first_request(api: AsyncClient) -> None:
    monitor = (await api.get("/api/v1/imports/monitor")).json()

    assert monitor["connection"] is None
    assert monitor["latency"] is None
    assert monitor["answers"]["requests"] == 0


async def test_monitor_reports_the_server_and_how_it_answered(
    api: AsyncClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{GENIUS}/artists/21").respond(
        json={"response": {"artist": artist_payload(21)}},
        headers={
            "server": "cloudflare",
            "cf-ray": "a4db2ec76f8fabf0-TLL",
            "via": "2.0 heroku-router",
        },
    )
    respx_mock.get(f"{GENIUS}/artists/22").respond(status_code=404)

    await start(api, "artist", 21)
    await start(api, "artist", 22)
    monitor = (await api.get("/api/v1/imports/monitor")).json()

    connection = monitor["connection"]
    assert (connection["host"], connection["ip"], connection["http_version"]) == (
        "genius.com",
        None,  # respx has no socket to ask
        "HTTP/1.1",
    )
    assert connection["edge"] is None  # the latest answer was the bare 404
    assert monitor["answers"] | {"bytes": 0} == {
        "requests": 2,
        "ok": 1,
        "client_errors": 1,
        "rate_limited": 0,
        "server_errors": 0,
        "no_answer": 0,
        "retries": 0,
        "bytes": 0,
    }
    assert monitor["latency"]["samples"] == 2
    assert len(monitor["latency"]["recent_ms"]) == 2
    assert monitor["min_interval_s"] == 0.0  # the test app does not wait between requests


async def test_monitor_reads_the_cloudflare_edge_and_the_origin(
    api: AsyncClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{GENIUS}/artists/21").respond(
        json={"response": {"artist": artist_payload(21)}},
        headers={
            "server": "cloudflare",
            "cf-ray": "a4db2ec76f8fabf0-TLL",
            "via": "2.0 heroku-router",
        },
    )

    await start(api, "artist", 21)
    connection = (await api.get("/api/v1/imports/monitor")).json()["connection"]

    assert (connection["server"], connection["edge"], connection["origin"]) == (
        "cloudflare",
        "TLL",
        "heroku-router",
    )


async def test_discography_job_carries_the_albums_limit(
    api: AsyncClient, respx_mock: respx.MockRouter, sessionmaker: SessionMaker
) -> None:
    respx_mock.get(f"{GENIUS}/artists/604").mock(
        return_value=answer("artist", artist_payload(604, "Radiohead"))
    )

    job = await start(api, "discography", 604, albums_limit=0)  # 0: the artist and no albums

    assert (job["status"], job["albums_limit"], job["kind"]) == ("succeeded", 0, "discography")
    async with sessionmaker() as db:
        assert (await db.get_one(Artist, job["result_id"])).genius_id == 604


async def test_a_failing_child_does_not_fail_the_job(
    api: AsyncClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{GENIUS}/albums/100").mock(return_value=answer("album", album_payload(100)))
    respx_mock.get(f"{GENIUS}/albums/100/tracks").respond(
        json={"response": {"tracks": [track(500), track(501)], "next_page": None}}
    )
    respx_mock.get(f"{GENIUS}/songs/500").mock(return_value=answer("song", song_payload(500)))
    respx_mock.get(f"{GENIUS}/songs/501").respond(status_code=404)
    respx_mock.get(url__regex=rf"{GENIUS}/artists/\d+").mock(
        return_value=answer("artist", artist_payload(1))
    )

    job = await start(api, "album", 100)

    assert job["status"] == "succeeded"
    assert job["message"] == "Done, 1 failed"
    assert "song 501" in job["error"]


async def test_failed_root_keeps_the_request_for_analysis(
    api: AsyncClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{GENIUS}/artists/404").respond(status_code=404)

    job = await start(api, "artist", 404)

    assert job["status"] == "failed"
    assert "404" in job["error"]
    assert [r["status_code"] for r in job["recent_requests"]] == [404]


async def test_a_persistent_network_failure_is_retried_then_fails_and_every_attempt_is_logged(
    api: AsyncClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{GENIUS}/artists/21").mock(side_effect=httpx.ConnectError("no route"))

    job = await start(api, "artist", 21)

    assert job["status"] == "failed"
    attempts = (await api.get(f"/api/v1/imports/{job['id']}/requests")).json()["items"]
    assert [(r["status_code"], "no route" in r["error"]) for r in attempts] == [(None, True)] * 3
    assert [r["attempt"] for r in attempts] == [1, 2, 3]


async def test_a_transient_failure_is_retried_and_the_job_succeeds(
    api: AsyncClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{GENIUS}/artists/21").mock(
        side_effect=[
            httpx.ConnectTimeout("slow"),
            httpx.Response(503),
            answer("artist", artist_payload(21)),
        ]
    )

    job = await start(api, "artist", 21)

    assert job["status"] == "succeeded"
    attempts = (await api.get(f"/api/v1/imports/{job['id']}/requests")).json()["items"]
    assert [r["status_code"] for r in attempts] == [None, 503, 200]


async def test_client_errors_are_not_retried(
    api: AsyncClient, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(f"{GENIUS}/artists/9").respond(status_code=403)

    job = await start(api, "artist", 9)

    assert job["status"] == "failed"
    assert route.call_count == 1


async def test_a_second_request_for_the_same_target_returns_the_active_job(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    async with sessionmaker() as db:
        running = ImportJob(kind=ImportKind.ARTIST, genius_id=21, status=JobStatus.RUNNING)
        db.add(running)
        await db.commit()

    response = await api.post("/api/v1/imports", json={"kind": "artist", "genius_id": 21})

    assert (response.json()["id"], response.json()["status"]) == (running.id, "running")


async def test_cancelling_a_running_import(api: AsyncClient, respx_mock: respx.MockRouter) -> None:
    async def never_answers(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(30)
        return httpx.Response(200)

    respx_mock.get(f"{GENIUS}/artists/21").mock(side_effect=never_answers)
    job_id = (await api.post("/api/v1/imports", json={"kind": "artist", "genius_id": 21})).json()[
        "id"
    ]
    await wait_for_job(api, job_id, until=("running",))

    cancelled = await api.post(f"/api/v1/imports/{job_id}/cancel")

    assert cancelled.status_code == 200
    assert (await wait_for_job(api, job_id))["status"] == "cancelled"
    assert (await api.post(f"/api/v1/imports/{job_id}/cancel")).status_code == 409


async def test_active_jobs_are_closed_when_the_server_starts(
    migrated_url: URL, sessionmaker: SessionMaker
) -> None:
    async with sessionmaker() as db:
        stale = ImportJob(kind=ImportKind.ARTIST, genius_id=5, status=JobStatus.RUNNING)
        db.add(stale)
        await db.commit()

    app = create_app(Settings(database_url=migrated_url.render_as_string(hide_password=False)))
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        job = (await client.get(f"/api/v1/imports/{stale.id}")).json()
    await truncate_all_tables(migrated_url)

    assert job["status"] == "failed"
    assert "restart" in job["error"]


async def test_unknown_job_is_404(api: AsyncClient) -> None:
    assert (await api.get("/api/v1/imports/999")).status_code == 404


async def test_listing_jobs_can_be_limited_to_active_ones(
    api: AsyncClient, sessionmaker: SessionMaker
) -> None:
    async with sessionmaker() as db:
        db.add_all(
            [
                ImportJob(kind=ImportKind.ARTIST, genius_id=1, status=JobStatus.RUNNING),
                ImportJob(kind=ImportKind.ARTIST, genius_id=2, status=JobStatus.SUCCEEDED),
            ]
        )
        await db.commit()

    everything = (await api.get("/api/v1/imports")).json()
    active = (await api.get("/api/v1/imports", params={"active": True})).json()

    assert [job["genius_id"] for job in everything] == [2, 1]  # newest first
    assert [job["genius_id"] for job in active] == [1]


# --- access --------------------------------------------------------------------------------------


async def test_login_is_required_when_dev_auto_login_is_off(migrated_url: URL) -> None:
    app = create_app(
        Settings(
            database_url=migrated_url.render_as_string(hide_password=False), dev_auto_login=False
        )
    )
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        assert (await client.get("/api/v1/imports")).status_code == 401


async def test_a_viewer_cannot_import(api: AsyncClient, sessionmaker: SessionMaker) -> None:
    async with sessionmaker() as db:
        db.add(AppUser(login="admin", password_hash="!", role=UserRole.VIEWER))
        await db.commit()

    assert (
        await api.post("/api/v1/imports", json={"kind": "artist", "genius_id": 21})
    ).status_code == 403


async def test_operation_ids_are_the_function_names(api: AsyncClient) -> None:
    schema = (await api.get("/openapi.json")).json()
    ids = {op["operationId"] for path in schema["paths"].values() for op in path.values()}
    assert {"search_genius_artists", "create_import", "get_import", "cancel_import"} <= ids


async def test_a_429_stops_the_import_and_keeps_its_answer_for_analysis(
    api: AsyncClient, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{GENIUS}/artists/21").mock(
        return_value=httpx.Response(429, text="slow down", headers={"Retry-After": "30"})
    )

    job = await start(api, "artist", 21)

    assert job["status"] == "failed"
    assert "429" in job["error"]
    attempts = (await api.get(f"/api/v1/imports/{job['id']}/requests")).json()["items"]
    assert [r["status_code"] for r in attempts] == [429]  # not retried
    assert "slow down" in attempts[0]["error"]
    assert "retry-after=30" in attempts[0]["error"]

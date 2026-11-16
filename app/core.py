"""화면(Streamlit)에서 부르는 기능 모음.

외부 API 호출은 app/services/ 의 비동기 함수가 하고, 여기서는 그것을 일반 함수로 감싸서
화면 코드가 `search(...)`, `summary(...)` 처럼 바로 쓸 수 있게 합니다.
"""
import asyncio
import logging
from datetime import datetime

import httpx

from app.config import settings
from app.services import naver, tmap, weather

log = logging.getLogger("travel")
KST = weather.KST

# 테스트에서 가짜 API로 바꿔 끼울 수 있게 둔 자리 (평소에는 None = 진짜 인터넷)
TRANSPORT: httpx.AsyncBaseTransport | None = None


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=settings.http_timeout, transport=TRANSPORT)


def _wrap(result, name: str) -> dict:
    """성공이면 {"ok": True, "data": ...}, 실패면 {"ok": False, "error": 쉬운 안내문}."""
    if isinstance(result, Exception):
        log.warning("%s failed: %r", name, result)
        msg = str(result) if isinstance(result, (weather.KmaError, tmap.TmapError, naver.NaverError)) \
            else "정보를 가져오지 못했어요. 잠시 후 다시 시도해 주세요."
        return {"ok": False, "error": msg}
    return {"ok": True, "data": result}


def key_status() -> dict:
    """API 키가 들어 있는지 (값은 보여주지 않음)."""
    return {
        "기상청": bool(settings.kma_service_key),
        "TMAP": bool(settings.tmap_app_key),
        "네이버": bool(settings.naver_client_id and settings.naver_client_secret),
    }


def search(q: str, golf: bool = False) -> list[dict]:
    """장소 이름 → 후보 목록. 실패하면 tmap.TmapError(안내문 포함)를 냅니다."""
    q = (q or "").strip()
    if not q:
        return []

    async def run():
        async with _client() as client:
            return await tmap.search_places(client, q, golf=golf)

    try:
        return asyncio.run(run())
    except tmap.TmapError:
        raise
    except Exception as e:  # noqa: BLE001
        log.exception("search failed")
        raise tmap.TmapError("장소 검색 중 문제가 생겼어요. 잠시 후 다시 시도해 주세요.") from e


async def _summary(client, o_lat, o_lon, dest: dict, depart: datetime, golf: bool, now: datetime) -> dict:
    # 경로와 맛집은 동시에, 날씨는 도착 시각을 알아야 하므로 경로 다음에
    route, food = await asyncio.gather(
        tmap.get_route(client, o_lat, o_lon, dest["lat"], dest["lon"], depart, now),
        naver.search_food(client, dest.get("area") or dest["name"], dest["lat"], dest["lon"]),
        return_exceptions=True)
    arrive = datetime.fromisoformat(route["arrive"]) if isinstance(route, dict) else depart
    try:
        w = await weather.get_weather(client, dest["lat"], dest["lon"], arrive=arrive, golf=golf, now=now)
    except Exception as e:  # noqa: BLE001
        w = e
    return {
        "destination": {**dest, "golf": golf},
        "weather": _wrap(w, "weather"),
        "route": _wrap(route, "route"),
        "restaurants": _wrap(food, "restaurants"),
    }


def summary(o_lat: float, o_lon: float, dest: dict, depart: datetime | None = None,
            golf: bool = False) -> dict:
    """날씨·가는 길·맛집을 한 번에. dest = search() 결과 하나 (name, lat, lon, area)."""
    now = datetime.now(KST)
    depart = depart.astimezone(KST) if depart else now
    if depart < now:
        depart = now

    async def run():
        async with _client() as client:
            return await _summary(client, o_lat, o_lon, dest, depart, golf, now)

    return asyncio.run(run())

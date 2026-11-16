"""네이버 지역 검색 API로 맛집을 찾고, 목적지에서 가까운 순으로 정렬합니다.

참고: 네이버 지역 검색은 한 번에 최대 5곳만 주고 거리순 정렬이 없어서,
받은 5곳의 좌표로 목적지와의 거리를 직접 계산해 다시 정렬합니다.
"""
import html
import math
import re
from urllib.parse import quote

import httpx

from app.cache import food_cache
from app.config import settings

URL = "https://openapi.naver.com/v1/search/local.json"


class NaverError(Exception):
    pass


def _distance_m(lat1, lon1, lat2, lon2) -> float:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _fmt(m: float | None) -> str | None:
    if m is None:
        return None
    return f"{m / 1000:.1f}km" if m >= 1000 else f"{round(m / 10) * 10:.0f}m"


def _coord(item: dict) -> tuple[float, float] | None:
    """mapx/mapy: WGS84 좌표 × 10,000,000 (2023년 이후 형식)."""
    try:
        x, y = int(item["mapx"]), int(item["mapy"])
    except (KeyError, ValueError):
        return None
    if x > 10**8:
        return y / 1e7, x / 1e7
    return None  # 옛 좌표계(KATEC)면 거리 계산 생략


async def search_food(client: httpx.AsyncClient, area: str, d_lat: float, d_lon: float) -> list[dict]:
    if not (settings.naver_client_id and settings.naver_client_secret):
        raise NaverError("네이버 키(NAVER_CLIENT_ID / NAVER_CLIENT_SECRET)가 아직 설정되지 않았어요.")

    query = f"{area} 맛집".strip()
    key = (query, round(d_lat, 3), round(d_lon, 3))
    cached = food_cache.get(key)
    if cached is not None:
        return cached

    r = await client.get(URL, params={"query": query, "display": 5, "start": 1, "sort": "random"},
                         headers={"X-Naver-Client-Id": settings.naver_client_id,
                                  "X-Naver-Client-Secret": settings.naver_client_secret})
    if r.status_code in (401, 403):
        raise NaverError("네이버 키를 확인해 주세요 (검색 API 사용 설정이 되어 있는지도 확인).")
    if r.status_code >= 400:
        raise NaverError(f"네이버 검색 오류({r.status_code})")

    out = []
    for it in r.json().get("items", []):
        name = html.unescape(re.sub(r"<[^>]+>", "", it.get("title", "")))
        c = _coord(it)
        meters = _distance_m(d_lat, d_lon, c[0], c[1]) if c else None
        out.append({
            "name": name,
            "category": (it.get("category") or "").split(">")[-1].strip() or "음식점",
            "address": it.get("roadAddress") or it.get("address"),
            "phone": it.get("telephone") or None,
            "distance_m": round(meters) if meters is not None else None,
            "distance": _fmt(meters),
            "url": "https://map.naver.com/p/search/" + quote(name),
        })
    out.sort(key=lambda f: (f["distance_m"] is None, f["distance_m"] or 0))  # 가까운 순
    for i, f in enumerate(out, 1):
        f["rank"] = i
    food_cache.set(key, out)
    return out

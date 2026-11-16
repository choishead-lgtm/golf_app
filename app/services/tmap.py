"""TMAP API: 장소 검색과 자동차 경로(출발 시각 예측 포함)."""
import re
from datetime import datetime, timedelta

import httpx

from app.cache import search_cache
from app.config import settings

TMAP = "https://apis.openapi.sk.com/tmap"
GOLF_WORDS = re.compile(r"골프|컨트리|CC|C\.C|GC|G\.C", re.I)


class TmapError(Exception):
    pass


def _headers() -> dict:
    if not settings.tmap_app_key:
        raise TmapError("TMAP 키(TMAP_APP_KEY)가 아직 설정되지 않았어요.")
    return {"appKey": settings.tmap_app_key, "Accept": "application/json"}


def _is_golf(p: dict) -> bool:
    biz = " ".join(filter(None, [p.get("upperBizName"), p.get("middleBizName"),
                                 p.get("lowerBizName"), p.get("detailBizName")]))
    return bool(GOLF_WORDS.search(p.get("name", ""))) or "골프" in biz


async def search_places(client: httpx.AsyncClient, keyword: str, golf: bool = False,
                        count: int = 6) -> list[dict]:
    """장소 이름 → 후보 목록. 골프장 모드에서는 골프장만 남깁니다."""
    key = (keyword, golf, count)
    cached = search_cache.get(key)
    if cached is not None:
        return cached

    r = await client.get(f"{TMAP}/pois", headers=_headers(), params={
        "version": 1, "searchKeyword": keyword, "count": 20,
        "resCoordType": "WGS84GEO", "searchType": "all"})
    if r.status_code == 204:  # 결과 없음
        return []
    if r.status_code >= 400:
        raise TmapError(f"TMAP 장소 검색 오류({r.status_code}): 키가 맞는지 확인해 주세요.")

    pois = r.json()["searchPoiInfo"]["pois"]["poi"]
    if golf:
        pois = [p for p in pois if _is_golf(p)]
    results = []
    for p in pois[:count]:
        middle, lower = p.get("middleAddrName") or "", p.get("lowerAddrName") or ""
        results.append({
            "name": p["name"],
            "address": " ".join(filter(None, [p.get("upperAddrName"), middle, lower])),
            "area": " ".join(filter(None, [middle, lower])),  # 맛집 검색용 지역명
            "lat": float(p.get("frontLat") or p["noorLat"]),  # 입구 좌표가 경로 안내에 정확
            "lon": float(p.get("frontLon") or p["noorLon"]),
        })
    search_cache.set(key, results)
    return results


def _summary(features: list, depart: datetime) -> dict:
    props = features[0]["properties"]
    sec = int(props["totalTime"])
    return {
        "distance_m": int(props["totalDistance"]),
        "duration_s": sec,
        "toll_won": props.get("totalFare"),
        "depart": depart.isoformat(),
        "arrive": (depart + timedelta(seconds=sec)).isoformat(),
    }


async def get_route(client: httpx.AsyncClient, o_lat: float, o_lon: float,
                    d_lat: float, d_lon: float, depart: datetime, now: datetime) -> dict:
    """자동차 경로. 나중 출발이면 TMAP '타임머신(출발 시각 예측)' 경로를 먼저 시도합니다."""
    headers = _headers()

    if depart - now > timedelta(minutes=15):
        body = {"routesInfo": {
            "departure": {"name": "출발지", "lon": str(o_lon), "lat": str(o_lat)},
            "destination": {"name": "도착지", "lon": str(d_lon), "lat": str(d_lat)},
            "predictionType": "departure",
            "predictionTime": depart.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "searchOption": "00", "tollgateCarType": "car", "trafficInfo": "N"}}
        try:
            r = await client.post(f"{TMAP}/routes/prediction", headers=headers, json=body,
                                  params={"version": 1, "reqCoordType": "WGS84GEO",
                                          "resCoordType": "WGS84GEO", "sort": "index"})
            if r.status_code < 400:
                return {**_summary(r.json()["features"], depart), "predicted": True, "note": None}
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            pass
        note = "출발 시각 예측을 쓸 수 없어 지금 교통 상황으로 계산했어요."
    else:
        note = None

    r = await client.post(f"{TMAP}/routes", headers=headers, params={"version": 1}, json={
        "startX": str(o_lon), "startY": str(o_lat), "endX": str(d_lon), "endY": str(d_lat),
        "reqCoordType": "WGS84GEO", "resCoordType": "WGS84GEO",
        "searchOption": "0", "trafficInfo": "N"})
    if r.status_code >= 400:
        raise TmapError(f"TMAP 경로 오류({r.status_code}): 키가 맞는지 확인해 주세요.")
    return {**_summary(r.json()["features"], depart), "predicted": False, "note": note}

"""테스트용 가짜 외부 API (기상청·TMAP·네이버의 응답 모양을 흉내냄)."""
import json
from datetime import datetime, timedelta

import httpx

CALLS: list[str] = []          # 어떤 API가 불렸는지 기록
OPTIONS = {"prediction_ok": True}


def _kma(req: httpx.Request) -> httpx.Response:
    op = req.url.path.rsplit("/", 1)[-1]
    p = req.url.params
    if op == "getUltraSrtNcst":
        items = [{"category": c, "obsrValue": v} for c, v in
                 [("T1H", "18.4"), ("REH", "55"), ("RN1", "0"), ("WSD", "2.2"), ("PTY", "0")]]
    else:
        base = datetime.strptime(p["base_date"] + p["base_time"], "%Y%m%d%H%M")
        items = []
        for i in range(1, 73):
            t = base + timedelta(hours=i)
            d, hh = t.strftime("%Y%m%d"), t.strftime("%H%M")
            wind = "6.5" if t.hour == 9 else "2.0"       # 9시에 강풍
            vals = [("TMP", str(10 + t.hour % 12)), ("SKY", "1" if t.hour < 12 else "3"),
                    ("PTY", "0"), ("POP", "20"), ("WSD", wind)]
            items += [{"category": c, "fcstDate": d, "fcstTime": hh, "fcstValue": v} for c, v in vals]
    return httpx.Response(200, json={"response": {
        "header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
        "body": {"items": {"item": items}}}})


def _poi(name, mid, low, lat, lon, biz=""):
    return {"name": name, "upperAddrName": "경기", "middleAddrName": mid, "lowerAddrName": low,
            "noorLat": str(lat), "noorLon": str(lon), "frontLat": str(lat), "frontLon": str(lon),
            "middleBizName": biz}


def _tmap(req: httpx.Request) -> httpx.Response:
    path = req.url.path
    if path.endswith("/pois"):
        if req.url.params["searchKeyword"] == "없는곳":
            return httpx.Response(204)
        return httpx.Response(200, json={"searchPoiInfo": {"pois": {"poi": [
            _poi("솔밭컨트리클럽", "여주시", "가남읍", 37.2, 127.6, "골프장"),
            _poi("솔밭식당", "여주시", "가남읍", 37.21, 127.61, "음식점"),
            _poi("솔밭 GC 연습장", "여주시", "점동면", 37.22, 127.62),
        ]}}})
    if path.endswith("/routes/prediction"):
        CALLS.append("prediction")
        if not OPTIONS["prediction_ok"]:
            return httpx.Response(403, json={"error": "not allowed"})
        body = json.loads(req.content)
        assert body["routesInfo"]["predictionType"] == "departure"
        return httpx.Response(200, json={"features": [{"geometry": {"type": "Point"},
            "properties": {"totalDistance": 72000, "totalTime": 4200, "totalFare": 3000}}]})
    if path.endswith("/routes"):
        CALLS.append("routes")
        return httpx.Response(200, json={"features": [{"geometry": {"type": "Point"},
            "properties": {"totalDistance": 72500, "totalTime": 4800, "totalFare": 3000}}]})
    return httpx.Response(404)


def _naver(req: httpx.Request) -> httpx.Response:
    assert req.headers["X-Naver-Client-Id"] and req.headers["X-Naver-Client-Secret"]
    CALLS.append("naver:" + req.url.params["query"])

    def item(title, cat, lat, lon):
        return {"title": title, "category": cat, "roadAddress": "경기 여주시 가남읍", "address": "",
                "telephone": "", "mapx": str(int(lon * 1e7)), "mapy": str(int(lat * 1e7)), "link": ""}
    return httpx.Response(200, json={"items": [
        item("<b>먼</b> 한정식", "한식>한정식", 37.25, 127.65),
        item("가까운 &amp; 해장국", "한식>해장국", 37.2005, 127.6005),
        item("중간 매운탕", "한식>매운탕", 37.21, 127.61),
    ]})


def handler(req: httpx.Request) -> httpx.Response:
    host = req.url.host
    if host == "apis.data.go.kr":
        return _kma(req)
    if host == "apis.openapi.sk.com":
        return _tmap(req)
    if host == "openapi.naver.com":
        return _naver(req)
    return httpx.Response(404)


transport = httpx.MockTransport(handler)

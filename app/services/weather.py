"""기상청 단기예보 조회서비스 (공공데이터포털 data.go.kr).

- 초단기실황 getUltraSrtNcst : 지금 관측값 (매시 정시 기준, 약 10분 뒤 제공)
- 단기예보   getVilageFcst   : 02·05·08·11·14·17·20·23시 발표, 3일 이상 시간별 예보
도착 시각 기준 6시간 예보와, 골프장이면 라운딩 적합도까지 계산해서 돌려줍니다.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from app.cache import weather_cache
from app.config import settings
from app.services.grid import is_in_korea, latlon_to_grid

KST = ZoneInfo("Asia/Seoul")
BASE_URL = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
VILAGE_HOURS = [2, 5, 8, 11, 14, 17, 20, 23]

SKY = {"1": "맑음", "3": "구름많음", "4": "흐림"}
PTY = {"0": "", "1": "비", "2": "비/눈", "3": "눈", "4": "소나기",
       "5": "빗방울", "6": "빗방울눈날림", "7": "눈날림"}


class KmaError(Exception):
    pass


# ---------- 발표시각 ----------
def ncst_base(now: datetime) -> tuple[str, str]:
    t = now - timedelta(minutes=10)
    return t.strftime("%Y%m%d"), t.strftime("%H00")


def vilage_base(now: datetime) -> tuple[str, str]:
    t = now - timedelta(minutes=10)
    for h in reversed(VILAGE_HOURS):
        if t.hour >= h:
            return t.strftime("%Y%m%d"), f"{h:02d}00"
    prev = t - timedelta(days=1)
    return prev.strftime("%Y%m%d"), "2300"


def _shift(base: tuple[str, str], hours: int) -> tuple[str, str]:
    t = datetime.strptime(base[0] + base[1], "%Y%m%d%H%M") - timedelta(hours=hours)
    return t.strftime("%Y%m%d"), t.strftime("%H%M")


# ---------- 호출 ----------
async def _call(client, op, base, nx, ny, rows):
    params = {"serviceKey": settings.kma_service_key, "dataType": "JSON", "pageNo": 1,
              "numOfRows": rows, "base_date": base[0], "base_time": base[1], "nx": nx, "ny": ny}
    r = await client.get(f"{BASE_URL}/{op}", params=params)
    if r.status_code >= 400:
        raise KmaError(f"기상청 접속 오류({r.status_code})")
    try:
        data = r.json()
    except ValueError:  # 인증키 문제는 XML로 옴
        raise KmaError("기상청 인증키를 확인해 주세요 (Decoding 키를 넣었는지, 발급 후 1~2시간 지났는지)")
    header = data["response"]["header"]
    if header["resultCode"] == "03":  # 아직 발표 전
        return None
    if header["resultCode"] != "00":
        raise KmaError(f"기상청 오류: {header['resultMsg']}")
    return data["response"]["body"]["items"]["item"]


async def _fetch(client, op, base, step, nx, ny, rows):
    for i in range(2):  # 최신 발표분이 아직 없으면 한 단계 전 것으로
        b = _shift(base, step) if i else base
        key = (op, nx, ny) + b
        cached = weather_cache.get(key)
        if cached is not None:
            return cached
        items = await _call(client, op, b, nx, ny, rows)
        if items is not None:
            weather_cache.set(key, items)
            return items
    raise KmaError("기상청 예보가 아직 준비되지 않았어요. 잠시 후 다시 시도해 주세요.")


# ---------- 가공 ----------
def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _kind(sky: str | None, pty: str | None) -> str:
    if pty in ("3", "7"):
        return "snow"
    if pty and pty != "0":
        return "rain"
    return "sun" if sky == "1" else "cloud"


def _cond(sky, pty) -> str:
    return PTY.get(pty or "0") or SKY.get(sky or "", "-")


def build_hourly(items: list[dict]) -> list[dict]:
    slots: dict[str, dict] = {}
    for it in items:
        slots.setdefault(it["fcstDate"] + it["fcstTime"], {})[it["category"]] = it["fcstValue"]
    out = []
    for k in sorted(slots):
        s = slots[k]
        if "TMP" not in s:
            continue
        out.append({
            "key": k,  # YYYYMMDDHHMM
            "hour": int(k[8:10]),
            "temp": _num(s.get("TMP")),
            "kind": _kind(s.get("SKY"), s.get("PTY")),
            "cond": _cond(s.get("SKY"), s.get("PTY")),
            "pop": int(_num(s.get("POP")) or 0),
            "wind": _num(s.get("WSD")),
            "_tmn": _num(s.get("TMN")), "_tmx": _num(s.get("TMX")),
        })
    return out


def golf_rating(window: list[dict]) -> dict | None:
    """라운딩 시간(도착 후 5시간)의 최대 풍속·강수확률로 판정. 기준은 필요에 맞게 바꾸세요."""
    if not window:
        return None
    wind = max((h["wind"] or 0) for h in window)
    pop = max(h["pop"] for h in window)
    if wind >= 6 or pop >= 60:
        level, label = "bad", "라운딩 어려움"
        reason = f"강수확률 최대 {pop}% · 비 소식이 있어요" if pop >= 60 else f"바람 최대 {wind:g}m/s · 바람이 강해요"
    elif wind >= 4 or pop >= 30:
        level, label, reason = "soso", "라운딩 보통", f"바람 최대 {wind:g}m/s · 강수확률 최대 {pop}%"
    else:
        level, label, reason = "good", "라운딩 좋음", "바람 약하고 비 소식 없어요"
    return {"level": level, "label": label, "reason": reason, "max_wind": wind, "max_pop": pop}


async def get_weather(client: httpx.AsyncClient, lat: float, lon: float,
                      arrive: datetime | None = None, golf: bool = False,
                      now: datetime | None = None) -> dict:
    if not settings.kma_service_key:
        raise KmaError("기상청 키(KMA_SERVICE_KEY)가 아직 설정되지 않았어요.")
    if not is_in_korea(lat, lon):
        raise KmaError("기상청 예보는 한국 지역만 볼 수 있어요.")

    now = now or datetime.now(KST)
    arrive = arrive or now
    nx, ny = latlon_to_grid(lat, lon)

    ncst = await _fetch(client, "getUltraSrtNcst", ncst_base(now), 1, nx, ny, 10)
    fcst = await _fetch(client, "getVilageFcst", vilage_base(now), 3, nx, ny, 1200)

    hourly = build_hourly(fcst)
    v = {i["category"]: i["obsrValue"] for i in ncst}
    first = hourly[0] if hourly else {}
    cur_pty = str(v.get("PTY", "0"))
    current = {
        "temp": _num(v.get("T1H")),
        "humidity": _num(v.get("REH")),
        "wind": _num(v.get("WSD")),
        "rain_1h": _num(v.get("RN1")),
        "kind": _kind(None, cur_pty) if cur_pty != "0" else first.get("kind", "cloud"),
        "cond": PTY.get(cur_pty) or first.get("cond", "-"),
    }

    today = now.strftime("%Y%m%d")
    today_slots = [h for h in hourly if h["key"].startswith(today)]
    tmn = next((h["_tmn"] for h in today_slots if h["_tmn"] is not None), None)
    tmx = next((h["_tmx"] for h in today_slots if h["_tmx"] is not None), None)
    temps = [h["temp"] for h in today_slots if h["temp"] is not None]

    # 도착 시각이 속한 시간부터 6시간
    arr_key = arrive.astimezone(KST).strftime("%Y%m%d%H00")
    window = [h for h in hourly if h["key"] >= arr_key][:6]
    day_of = {now.strftime("%Y%m%d"): "", (now + timedelta(days=1)).strftime("%Y%m%d"): "내일 ",
              (now + timedelta(days=2)).strftime("%Y%m%d"): "모레 "}
    for h in window:
        h["label"] = f"{h['hour']:02d}시"
        h["day"] = day_of.get(h["key"][:8], h["key"][4:6] + "/" + h["key"][6:8] + " ")
        h["is_arrival"] = h["key"] == arr_key
    clean = lambda h: {k: val for k, val in h.items() if not k.startswith("_")}  # noqa: E731

    return {
        "current": current,
        "today_min": tmn if tmn is not None else (min(temps) if temps else None),
        "today_max": tmx if tmx is not None else (max(temps) if temps else None),
        "window": [clean(h) for h in window],
        "window_note": None if window else "도착 시각이 기상청 예보 범위(약 3일)를 넘어 예보가 없어요.",
        "golf": golf_rating(window[:5]) if golf else None,
        "source": "기상청",
    }

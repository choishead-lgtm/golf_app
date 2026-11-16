"""여행 도우미 — Streamlit 화면.

실행: streamlit run streamlit_app.py
"""
import html
import os
from datetime import datetime, timedelta

import streamlit as st

st.set_page_config(page_title="여행 도우미", page_icon="⛳", layout="centered")

# Streamlit Cloud의 'Secrets'에 넣은 키를 환경 변수로 옮겨서 app.config가 읽게 합니다.
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, (str, int, float)):
            os.environ.setdefault(_k, str(_v))
except Exception:  # secrets.toml이 없으면 .env만 사용
    pass

from app import core  # noqa: E402  (키를 먼저 옮긴 뒤에 불러옴)
from app.services.tmap import TmapError  # noqa: E402

KST = core.KST
FALLBACK = {"lat": 37.5663, "lon": 126.9779, "label": "서울시청 (위치 권한 없음)"}

MODES = {"골프장": "golf", "일반 여행지": "general"}  # 순서 = 화면 순서, 첫 번째가 기본
DEP = {  # (화면 글자, 값) — 첫 번째가 기본 선택
    "golf": [("새벽 05:30", "05:30"), ("아침 06:30", "06:30"), ("지금", "now")],
    "general": [("지금", "now"), ("1시간 뒤", "+60"), ("퇴근길 18:00", "18:00")],
}
CUSTOM = "직접 입력"
TEXT = {
    "golf": {"heading": "어느 골프장으로 갈까요?", "label": "골프장", "obj": "골프장을",
             "ph": "골프장 이름을 입력하세요 (예: 남서울)"},
    "general": {"heading": "어디로, 언제 갈까요?", "label": "목적지", "obj": "목적지를",
                "ph": "장소 이름을 입력하세요 (예: 해운대)"},
}
ICON = {"sun": "☀️", "cloud": "☁️", "rain": "🌧️", "snow": "🌨️"}


# ---------- 시간·숫자 표시 ----------
def depart_time(value: str, now: datetime) -> datetime:
    """'now' / '+60'(분 뒤) / 'HH:MM'(지난 시각이면 내일) → 출발 시각."""
    if value == "now":
        return now
    if value.startswith("+"):
        return now + timedelta(minutes=int(value[1:]))
    h, m = map(int, value.split(":"))
    t = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return t + timedelta(days=1) if t < now - timedelta(minutes=1) else t


def day_label(t: datetime, now: datetime) -> str:
    diff = (t.astimezone(KST).date() - now.date()).days
    return {0: "", 1: "내일 ", 2: "모레 "}.get(diff, f"{t.month}/{t.day} ")


def fmt_time(t: datetime, now: datetime) -> str:
    t = t.astimezone(KST)
    return f"{day_label(t, now)}{t:%H:%M}"


def fmt_dur(sec: int) -> str:
    m = round(sec / 60)
    h, m = divmod(m, 60)
    return f"{h}시간" + (f" {m}분" if m else "") if h else f"{m}분"


def fmt_km(m: int) -> str:
    if m < 1000:
        return f"{m}m"
    return f"{m / 1000:.0f}km" if m >= 100000 else f"{m / 1000:.1f}km"


def num(v, unit="") -> str:
    return "-" if v is None else f"{round(v, 1):g}{unit}"


# ---------- 검색 (같은 검색어는 다시 부르지 않음) ----------
@st.cache_data(ttl=24 * 60 * 60, show_spinner="찾는 중…")
def search_places(q: str, golf: bool) -> list[dict]:
    return core.search(q, golf=golf)


def place_picker(label: str, placeholder: str, golf: bool, key: str, empty_msg: str):
    """검색어 입력 → 후보 목록에서 고르기. 고른 장소(dict) 또는 None."""
    q = st.text_input(label, placeholder=placeholder, key=f"{key}_q").strip()
    if not q:
        return None
    try:
        results = search_places(q, golf)
    except TmapError as e:
        st.error(str(e))
        return None
    if not results:
        st.warning(empty_msg)
        return None
    i = st.selectbox(
        "검색 결과", range(len(results)), index=None, key=f"{key}_pick_{q}",
        format_func=lambda j: f"{results[j]['name']} · {results[j]['address']}",
        placeholder="목록에서 눌러 골라주세요", label_visibility="collapsed")
    return None if i is None else results[i]


# ---------- 현재 위치 ----------
def current_location():
    try:
        from streamlit_js_eval import get_geolocation
    except ImportError:
        return None
    try:
        loc = get_geolocation(component_key="geo")
    except Exception:  # noqa: BLE001  (위치 기능이 안 되는 환경)
        return None
    if isinstance(loc, dict) and "coords" in loc:
        c = loc["coords"]
        return {"lat": c["latitude"], "lon": c["longitude"], "label": "현재 위치"}
    return None


# ---------- 결과 카드 ----------
def card_error(title: str, src: str, msg: str):
    with st.container(border=True):
        st.markdown(f"**{title}**  \n:gray[출처: {src}]")
        st.error(msg)


def show_weather(w: dict, golf: bool):
    title = "골프장 날씨" if golf else "지금 날씨"
    if not w["ok"]:
        return card_error(title, "기상청", w["error"])
    d, c = w["data"], w["data"]["current"]
    with st.container(border=True):
        st.markdown(f"**{title}**  \n:gray[출처: 기상청]")
        g = d.get("golf")
        if g:
            box = {"good": st.success, "soso": st.warning, "bad": st.error}[g["level"]]
            box(f"**{g['label']}** · {g['reason']}", icon="⛳")
        st.markdown(f"### {ICON.get(c['kind'], '☁️')} {num(c['temp'], '°')} {c['cond']}")
        st.caption(f"오늘 최저 {num(d['today_min'], '°')} · 최고 {num(d['today_max'], '°')}")
        a, b, cc = st.columns(3)
        a.metric("습도", num(c["humidity"], "%"))
        b.metric("바람", num(c["wind"], "m/s"))
        cc.metric("1시간 강수", num(c["rain_1h"], "mm"))
        if d["window"]:
            st.markdown("**" + ("도착 후 라운딩 시간대 예보" if golf else "도착 무렵 시간별 예보") + "**")
            cells = []
            for h in d["window"]:
                style = "border:2px solid #2e7d32;" if h["is_arrival"] else "border:1px solid rgba(128,128,128,.3);"
                tag = "<div style='font-size:11px;color:#2e7d32;font-weight:600'>도착</div>" if h["is_arrival"] else ""
                cells.append(
                    f"<div style='{style}border-radius:10px;padding:6px 4px;min-width:58px;text-align:center'>"
                    f"<div style='font-size:11px;opacity:.7'>{html.escape(h['day'].strip()) or '&nbsp;'}</div>"
                    f"<div style='font-size:13px'>{html.escape(h['label'])}</div>"
                    f"<div style='font-size:20px'>{ICON.get(h['kind'], '☁️')}</div>"
                    f"<div><b>{num(h['temp'], '°')}</b></div>"
                    f"<div style='font-size:12px;opacity:.7'>☔ {h['pop']}%</div>"
                    f"<div style='font-size:12px;opacity:.7'>💨 {num(h['wind'])}</div>{tag}</div>")
            st.markdown("<div style='display:flex;gap:6px;overflow-x:auto;padding-bottom:4px'>"
                        + "".join(cells) + "</div>", unsafe_allow_html=True)
        elif d.get("window_note"):
            st.caption(d["window_note"])


def show_route(r: dict, now: datetime):
    if not r["ok"]:
        return card_error("가는 길 (자동차)", "TMAP", r["error"])
    d = r["data"]
    dep, arr = datetime.fromisoformat(d["depart"]), datetime.fromisoformat(d["arrive"])
    with st.container(border=True):
        st.markdown("**🚗 가는 길 (자동차)**  \n:gray[출처: TMAP]")
        st.markdown(f"### {fmt_dur(d['duration_s'])} :gray[· {fmt_km(d['distance_m'])}]")
        st.markdown(f"{fmt_time(dep, now)} 출발 → **{fmt_time(arr, now)} 도착**")
        badge = ":green-badge[출발 시각 기준 예측]" if d["predicted"] else ":gray-badge[실시간 교통 기준]"
        toll = f"통행료 약 {int(d['toll_won']):,}원" if d.get("toll_won") else "통행료 없음"
        st.markdown(f"{badge} {toll}")
        if d.get("note"):
            st.caption(d["note"])


def show_food(f: dict, golf: bool):
    title = "골프장 주변 맛집" if golf else "주변 맛집"
    if not f["ok"]:
        return card_error(title, "네이버", f["error"])
    with st.container(border=True):
        st.markdown(f"**🍽️ {title}** :green-badge[가까운 순]  \n:gray[출처: 네이버]")
        if not f["data"]:
            st.caption("근처 맛집 정보를 찾지 못했어요.")
        for it in f["data"]:
            name = it["name"].replace("[", "(").replace("]", ")")
            dist = f" · 📍 {it['distance']}" if it.get("distance") else ""
            st.markdown(f"**{it['rank']}. [{name}]({it['url']})**  \n:gray[{it['category']}{dist}]")


# ---------- 첫 화면 ----------
st.caption("여행 도우미")
mode_label = st.segmented_control("목적지 종류", list(MODES), default=list(MODES)[0],
                                  key="mode", label_visibility="collapsed")
mode = MODES.get(mode_label or list(MODES)[0])
golf = mode == "golf"
t = TEXT[mode]
st.title(t["heading"])

with st.container(border=True):
    # 출발지
    gps = current_location()
    origin_kind = st.radio("출발지", ["현재 위치", "다른 곳에서 출발"], horizontal=True, key="origin_kind")
    if origin_kind == "현재 위치":
        origin = gps or FALLBACK
        if gps is None:
            st.caption("📍 위치를 확인하지 못해 서울시청에서 출발하는 것으로 계산해요. "
                       "브라우저에서 위치 권한을 허용하거나 '다른 곳에서 출발'을 골라주세요.")
        else:
            st.caption("📍 현재 위치에서 출발")
    else:
        picked_origin = place_picker("출발지 검색", "출발할 곳 이름 (예: 강남역)", False, "origin",
                                     "장소를 찾지 못했어요. 이름을 조금 다르게 입력해 보세요.")
        origin = picked_origin or None

    # 목적지
    dest = place_picker(t["label"], t["ph"], golf, f"dest_{mode}",
                        "골프장을 찾지 못했어요. 이름을 조금 다르게 입력해 보세요." if golf
                        else "장소를 찾지 못했어요. 이름을 조금 다르게 입력해 보세요.")

    # 출발 시각
    options = [label for label, _ in DEP[mode]] + [CUSTOM]
    dep_label = st.radio("출발 시각", options, horizontal=True, key=f"dep_{mode}")
    if dep_label == CUSTOM:
        custom = st.time_input("출발 시각 직접 선택", value=None, step=300, key=f"dep_time_{mode}")
        dep_value = custom.strftime("%H:%M") if custom else "now"
    else:
        dep_value = dict(DEP[mode])[dep_label]
    now = datetime.now(KST)
    depart = depart_time(dep_value, now)
    st.caption("출발: " + ("지금 바로" if dep_value == "now" else fmt_time(depart, now)))

    go = st.button("날씨·가는 길·맛집 보기", type="primary", width="stretch")

if go:
    if origin is None:
        st.warning("출발지를 검색해서 골라주세요.")
    elif dest is None:
        st.warning(f"{t['obj']} 검색해서 목록에서 골라주세요.")
    else:
        with st.spinner("불러오는 중…"):
            st.session_state["result"] = {
                "data": core.summary(origin["lat"], origin["lon"], dest,
                                     None if dep_value == "now" else depart, golf=golf),
                "golf": golf, "dest": dest}

res = st.session_state.get("result")
if res and res["golf"] == golf:
    now = datetime.now(KST)
    data, d = res["data"], res["dest"]
    st.divider()
    st.subheader(d["name"])
    if res["data"]["route"]["ok"]:
        st.caption(f"{d['address']} · {fmt_time(datetime.fromisoformat(data['route']['data']['depart']), now)} 출발")
    else:
        st.caption(d["address"])
    show_weather(data["weather"], res["golf"])
    show_route(data["route"], now)
    show_food(data["restaurants"], res["golf"])
    st.caption("날씨: 기상청 · 길찾기: TMAP · 맛집: 네이버")

with st.expander("설정 확인 (API 키)"):
    for name, ok in core.key_status().items():
        st.write(("✅ " if ok else "❌ ") + name + (" 키가 들어 있어요" if ok else " 키가 아직 없어요"))

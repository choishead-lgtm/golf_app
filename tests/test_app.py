"""가짜 API로 전체 흐름을 확인하는 테스트. 실행: python -m pytest  (키 없이 동작)"""
import os
from datetime import datetime, timedelta

import pytest

os.environ.update(KMA_SERVICE_KEY="t", TMAP_APP_KEY="t", NAVER_CLIENT_ID="t", NAVER_CLIENT_SECRET="t")

from app import core  # noqa: E402
from app.cache import food_cache, search_cache, weather_cache  # noqa: E402
from app.services import weather  # noqa: E402
from app.services.grid import latlon_to_grid  # noqa: E402
from tests import mock_apis  # noqa: E402

KST = weather.KST
DEST = {"name": "솔밭컨트리클럽", "address": "경기 여주시 가남읍", "area": "여주시 가남읍",
        "lat": 37.2, "lon": 127.6}


@pytest.fixture(autouse=True)
def fake_apis():
    for c in (weather_cache, search_cache, food_cache):
        c.clear()
    mock_apis.CALLS.clear()
    mock_apis.OPTIONS["prediction_ok"] = True
    core.TRANSPORT = mock_apis.transport
    yield
    core.TRANSPORT = None


def test_grid():
    assert latlon_to_grid(37.5665, 126.9780) == (60, 127)
    assert latlon_to_grid(35.1796, 129.0756) == (98, 76)


def test_base_times():
    assert weather.vilage_base(datetime(2026, 10, 7, 5, 11, tzinfo=KST)) == ("20261007", "0500")
    assert weather.vilage_base(datetime(2026, 10, 7, 1, 0, tzinfo=KST)) == ("20261006", "2300")
    assert weather.ncst_base(datetime(2026, 10, 7, 0, 5, tzinfo=KST)) == ("20261006", "2300")


def test_golf_rating():
    calm = [{"wind": 2.0, "pop": 10}] * 5
    assert weather.golf_rating(calm)["level"] == "good"
    assert weather.golf_rating(calm + [{"wind": 4.5, "pop": 0}])["level"] == "soso"
    assert weather.golf_rating([{"wind": 1, "pop": 70}])["level"] == "bad"
    assert weather.golf_rating([]) is None


def test_key_status():
    assert core.key_status() == {"기상청": True, "TMAP": True, "네이버": True}


def test_search_golf_filter():
    golf = core.search("솔밭", golf=True)
    allp = core.search("솔밭", golf=False)
    assert [g["name"] for g in golf] == ["솔밭컨트리클럽", "솔밭 GC 연습장"]  # 식당은 빠짐
    assert len(allp) == 3 and core.search("없는곳") == [] and core.search("  ") == []
    assert golf[0]["area"] == "여주시 가남읍"


def _summary(depart=None, golf=True):
    return core.summary(37.5665, 126.978, DEST, depart, golf=golf)


def test_summary_future_departure_uses_prediction():
    tomorrow_6 = (datetime.now(KST) + timedelta(days=1)).replace(hour=6, minute=0, second=0, microsecond=0)
    body = _summary(tomorrow_6)
    assert body["route"]["ok"], body["route"]
    route = body["route"]["data"]
    assert route["predicted"] is True and "prediction" in mock_apis.CALLS
    assert route["arrive"].startswith((tomorrow_6 + timedelta(seconds=4200)).strftime("%Y-%m-%dT%H:%M"))

    w = body["weather"]["data"]
    assert w["window"][0]["label"] == "07시" and w["window"][0]["is_arrival"]  # 06:00+70분 → 07시대
    assert w["window"][0]["day"] == "내일 "
    assert w["golf"]["level"] == "bad"  # 9시 강풍 6.5m/s 포함

    food = body["restaurants"]["data"]
    assert [f["name"] for f in food] == ["가까운 & 해장국", "중간 매운탕", "먼 한정식"]
    assert food[0]["rank"] == 1 and food[0]["distance"].endswith("m")
    assert "naver:여주시 가남읍 맛집" in mock_apis.CALLS


def test_summary_prediction_fallback():
    mock_apis.OPTIONS["prediction_ok"] = False
    body = _summary(datetime.now(KST) + timedelta(hours=3), golf=False)
    route = body["route"]["data"]
    assert route["predicted"] is False and route["note"]
    assert mock_apis.CALLS.count("routes") == 1
    assert body["weather"]["data"]["golf"] is None


def test_summary_now_skips_prediction():
    body = _summary()
    assert body["route"]["data"]["predicted"] is False and body["route"]["data"]["note"] is None
    assert "prediction" not in mock_apis.CALLS


def test_summary_missing_keys():
    os.environ["NAVER_CLIENT_ID"] = ""
    try:
        body = _summary()
    finally:
        os.environ["NAVER_CLIENT_ID"] = "t"
    assert body["restaurants"]["ok"] is False and "네이버 키" in body["restaurants"]["error"]
    assert body["weather"]["ok"] and body["route"]["ok"]


# ---------- 화면 (Streamlit) ----------
def test_depart_time_rules():
    import streamlit_app as ui
    now = datetime(2026, 11, 16, 15, 0, tzinfo=KST)
    assert ui.depart_time("now", now) == now
    assert ui.depart_time("+60", now) == now + timedelta(hours=1)
    assert ui.depart_time("18:00", now) == now.replace(hour=18)
    assert ui.depart_time("05:30", now) == (now + timedelta(days=1)).replace(hour=5, minute=30)  # 지났으면 내일
    assert ui.fmt_dur(4200) == "1시간 10분" and ui.fmt_dur(1800) == "30분"


def test_screen_defaults():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("../streamlit_app.py", default_timeout=30).run()
    assert not at.exception
    assert at.title[0].value == "어느 골프장으로 갈까요?"  # 골프장 탭이 기본
    assert at.radio(key="dep_golf").value == "새벽 05:30"


def test_screen_full_flow():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("../streamlit_app.py", default_timeout=30).run()
    at.text_input(key="dest_golf_q").input("솔밭").run()
    at.selectbox(key="dest_golf_pick_솔밭").select(0).run()
    at.radio(key="dep_golf").set_value("지금").run()
    at.button[0].click().run()
    assert not at.exception
    assert at.subheader[0].value == "솔밭컨트리클럽"
    text = " ".join(m.value for m in at.markdown)
    assert "가는 길" in text and "가까운 & 해장국" in text

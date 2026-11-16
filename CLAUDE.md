# golf_app — 여행 도우미 웹앱 (Claude Code 작업 안내)

## 사용자
- 코딩 경험이 거의 없는 분입니다. **쉬운 한국어로, 한 번에 한 단계씩** 안내하고, 명령어는 가능하면 직접 실행해 주세요.
- 화면 문구·안내는 모두 한국어로 씁니다.

## 이 앱이 하는 일
목적지(골프장 또는 일반 여행지)와 출발 시각을 고르면 한 화면에:
1. **날씨** – 기상청 단기예보: 지금 날씨 + 도착 시각부터 6시간 예보, 골프장이면 라운딩 적합도(좋음/보통/어려움)
2. **가는 길** – TMAP 자동차 경로: 거리, 걸리는 시간, 출발→도착 시각 (나중 출발이면 TMAP 타임머신 예측 API, 실패 시 현재 교통으로 대체)
3. **맛집** – 네이버 지역 검색 5곳 → 목적지와의 거리를 계산해 **가까운 순** 정렬

## 사용자가 정한 것 (바꾸지 말 것)
- 첫 화면 탭은 **[골프장] [일반 여행지]** 순서, 앱을 열면 **골프장 탭이 기본 선택**
- 골프장 출발 시각 기본 선택지: 새벽 05:30 / 아침 06:30 / 지금 (기본 05:30)
- 일반 여행지: 지금 / 1시간 뒤 / 퇴근길 18:00, 시간 직접 입력 가능 (지난 시각이면 내일로 계산)
- 목적지 검색과 출발 시각은 **첫 화면에서 함께** 고른 뒤 버튼 하나로 결과 보기
- 맛집은 **네이버**, **가까운 순** (별점 표시 없음 – 네이버 API가 별점을 주지 않음)
- 앱은 **Streamlit**으로 동작 (2026-11-16 사용자 결정, 배포: Streamlit Community Cloud)
- 날씨는 **한국 기상청** (노르웨이·일본 기상청은 검토 후 제외), 서비스 지역은 한국 국내
- 라운딩 적합도 기준(임시): 도착 후 5시간 중 바람 ≥6m/s 또는 강수확률 ≥60% → 어려움, ≥4m/s 또는 ≥30% → 보통

## 구조
```
streamlit_app.py         Streamlit 화면 (탭·검색·출발 시각 → 날씨/경로/맛집 카드). 현재 위치는 streamlit-js-eval, 실패 시 서울시청 또는 출발지 직접 검색
app/core.py              화면용 동기 함수 search()/summary()/key_status() (내부는 asyncio.run + httpx.AsyncClient, 테스트는 core.TRANSPORT에 가짜 API)
app/config.py            환경 변수(.env) 읽기 (Streamlit Cloud Secrets는 streamlit_app.py가 환경 변수로 옮겨 줌)
app/cache.py             메모리 TTL 캐시
app/services/grid.py     위경도 → 기상청 격자(nx, ny)
app/services/weather.py  기상청 초단기실황 + 단기예보, 발표시각 계산, golf_rating()
app/services/tmap.py     TMAP 장소검색(골프장 모드는 골프장만 필터), 경로(prediction → routes 대체)
app/services/naver.py    네이버 지역검색 + 거리 계산·정렬 (mapx/mapy = WGS84 × 1e7 가정)
.streamlit/              config.toml(테마), secrets.toml.example
tests/                   가짜 API(MockTransport) 테스트 + Streamlit AppTest 화면 테스트
```
- 2026-11-16 사용자 요청으로 **Starlette+순수 JS 화면 → Streamlit**으로 변경 (app/main.py, static/ 삭제). 배포는 Streamlit Community Cloud.
- 환경 변수: `KMA_SERVICE_KEY`(공공데이터포털 **Decoding** 키), `TMAP_APP_KEY`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`

## 실행·테스트
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
python -m pytest                      # 키 없이 동작
cp .env.example .env                  # 키 입력 후
streamlit run streamlit_app.py       # http://localhost:8501 , 키 확인: 화면 맨 아래 "설정 확인"
```

## 현재 상태
- Streamlit 버전 코드 작성 완료. **아직 한 번도 실행·테스트하지 못함** (이 Mac에 개발자 도구가 없어 python/git이 동작하지 않았음). 개발자 도구 설치 후 pytest부터 돌릴 것.
- **실제 API 키로는 아직 한 번도 실행하지 않음.** 사용자가 키 3종을 아직 발급받지 않았을 수 있음.
- GitHub 저장소: https://github.com/choishead-lgtm/golf_app (2026-11-16 기준: 사용자가 웹 업로드한 옛 Starlette 버전이 golf_app/ 하위 폴더에 있음 → 이 폴더 내용으로 교체할지 사용자에게 확인 중)

## 다음 할 일 (순서대로)
1. **GitHub에 올리기**: 이 폴더를 git 저장소로 만들고 `origin` = `https://github.com/choishead-lgtm/golf_app.git` 로 연결해 push.
   원격에 이미 파일이 있으면 먼저 확인하고(웹 업로드로 같은 파일이 있을 수 있음), 덮어쓰기 전에 사용자에게 물어볼 것.
   `.env`, `.streamlit/secrets.toml`은 절대 커밋하지 않기(.gitignore에 있음).
2. **API 키 받기 안내**: README.md 1단계 참고. 받은 키는 `.env`에만 저장.
3. **실제 키로 로컬 실행해서 응답 모양 검증** – 가짜 API를 기준으로 짠 부분이라 특히 확인할 것:
   - TMAP 타임머신 예측 API(`/tmap/routes/prediction`) 요청 본문·응답 형식, 사용 신청 필요 여부
   - TMAP 장소검색 응답의 업종 필드(`middleBizName` 등)로 골프장 필터가 잘 되는지
   - 네이버 지역검색 `mapx/mapy`가 WGS84×1e7 정수인지 (아니면 거리 계산이 빠짐)
   - 기상청 단기예보 `numOfRows=1200`으로 도착 시각까지 예보가 다 오는지
   - 틀린 곳이 있으면 고치고 `tests/mock_apis.py`도 실제 모양에 맞게 고칠 것
4. **Streamlit Cloud에 배포**: README.md 3단계 (Main file `streamlit_app.py`, Python 3.11, Secrets에 키 4개).
5. 나중에: 스토어용 앱(같은 화면을 감싸는 방식), 출시 전 위치기반서비스사업 신고 검토.

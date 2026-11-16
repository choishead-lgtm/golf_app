# 여행 도우미 웹앱 — 쉬운 시작 안내

골프장·여행지까지의 **날씨(기상청) + 가는 길(TMAP) + 주변 맛집(네이버)**을 한 화면에 보여주는 웹앱입니다.
휴대폰 인터넷 창에서 열고, 홈 화면에 추가하면 앱처럼 쓸 수 있어요.

전체 순서는 3단계입니다. **한 번에 하나씩** 하시면 됩니다.

| 단계 | 하는 일 | 걸리는 시간 |
|---|---|---|
| 1 | API 키 3개 받기 | 30분~1시간 |
| 2 | 코드를 GitHub에 올리기 (Claude가 해 드림) | 5분 |
| 3 | Streamlit Cloud(무료)에 올려서 주소 받기 | 10분 |

---

## 1단계. API 키 3개 받기

받은 키는 메모장에 아래처럼 적어 두세요. 3단계에서 그대로 붙여 넣습니다.

```
KMA_SERVICE_KEY=여기에 기상청 키
TMAP_APP_KEY=여기에 TMAP 키
NAVER_CLIENT_ID=여기에 네이버 Client ID
NAVER_CLIENT_SECRET=여기에 네이버 Client Secret
```

### ① 기상청 (무료)
1. **data.go.kr** (공공데이터포털)에 회원가입·로그인
2. 검색창에 **"기상청_단기예보"** 검색 → **「기상청_단기예보 ((구)_동네예보) 조회서비스」** 클릭
3. **[활용신청]** → 활용 목적에 "개인 앱 개발" 정도로 적고 신청 (보통 바로 승인)
4. 위쪽 **마이페이지 → 개발계정 →** 방금 신청한 서비스 클릭
5. **일반 인증키 (Decoding)** 값을 복사 → `KMA_SERVICE_KEY`
   - ⚠️ **Encoding 말고 Decoding** 키입니다.
   - 발급 직후 1~2시간은 키가 동작하지 않을 수 있어요.

### ② TMAP (무료 사용량 있음)
1. **TMAP API** 홈페이지(tmapapi.tmapmobility.com)에 회원가입·로그인
   (주소가 바뀌었으면 인터넷에서 "TMAP API"를 검색하세요)
2. **새 프로젝트(앱) 만들기** → 이름은 "여행 도우미"
3. 사용할 API에서 **장소 검색(POI)**, **자동차 경로안내**를 사용 설정
   - **타임머신 자동차 길 안내**(출발 시각 예측)도 보이면 함께 신청하세요.
     신청이 안 되거나 유료여도 괜찮아요. 그때는 앱이 자동으로 "지금 교통 기준"으로 계산합니다.
4. 프로젝트의 **App Key**를 복사 → `TMAP_APP_KEY`

### ③ 네이버 (무료)
1. **developers.naver.com** (네이버 개발자센터)에 로그인
2. 위쪽 **Application → 애플리케이션 등록**
3. 애플리케이션 이름: "여행 도우미" / 사용 API: **검색** 선택
4. 비로그인 오픈 API 서비스 환경: **WEB 설정** → 웹 서비스 URL에 `http://localhost` 입력
   (3단계에서 내 앱 주소가 생기면 그 주소도 추가해 주세요)
5. 등록 후 보이는 **Client ID**, **Client Secret**을 복사 → `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`

---

## 2단계. 코드를 GitHub에 올리기

이 단계는 Claude가 대신 해 드립니다. 코드는 `https://github.com/choishead-lgtm/golf_app` 저장소에 올라갑니다.

> ⚠️ 키를 적은 메모장 파일이나 `.env`, `.streamlit/secrets.toml` 파일은 **절대 올리지 마세요.** (자동으로 빠지게 설정되어 있어요)

---

## 3단계. Streamlit Cloud에 올려서 내 앱 주소 받기

1. **share.streamlit.io** 접속 → **Continue with GitHub**로 로그인
2. 오른쪽 위 **Create app** → **Deploy a public app from GitHub** 선택
3. 칸을 이렇게 채우기

   | 항목 | 입력값 |
   |---|---|
   | Repository | `choishead-lgtm/golf_app` |
   | Branch | `main` |
   | Main file path | `streamlit_app.py` |
   | App URL | 원하는 이름 (예: `golf-helper`) |

4. **Advanced settings** → Python 버전 **3.11** 선택 → **Secrets** 칸에 1단계 키를 아래 모양으로 붙여 넣기
   (따옴표 `"` 꼭 넣기)

   ```
   KMA_SERVICE_KEY = "기상청 키"
   TMAP_APP_KEY = "TMAP 키"
   NAVER_CLIENT_ID = "네이버 Client ID"
   NAVER_CLIENT_SECRET = "네이버 Client Secret"
   ```

5. **Deploy** → 몇 분 기다리면 `https://golf-helper.streamlit.app` 같은 **내 앱 주소**가 생깁니다.

### 잘 됐는지 확인
- 앱 맨 아래 **설정 확인 (API 키)** 를 눌러 세 곳이 모두 ✅ 인지 보세요.
- 무료 요금제는 한동안 아무도 안 쓰면 잠들어요. 그러면 **"Yes, get this app back up!"** 버튼을 눌러 깨우면 됩니다 (1분 정도).

### 휴대폰 홈 화면에 추가
- **아이폰(사파리)**: 내 앱 주소 열기 → 아래 공유 버튼 → **홈 화면에 추가**
- **안드로이드(크롬)**: 내 앱 주소 열기 → 오른쪽 위 ⋮ → **홈 화면에 추가**
- 처음 열 때 **위치 권한 허용**을 눌러야 현재 위치에서 출발하는 길을 알려줍니다.
  위치가 안 잡히면 **"다른 곳에서 출발"** 을 골라 출발지를 직접 검색하세요. (그냥 두면 서울시청 출발로 계산)

---

## 문제가 생기면

| 화면에 나오는 말 | 해결 방법 |
|---|---|
| 기상청 인증키를 확인해 주세요 | Decoding 키인지 확인, 발급 후 1~2시간 기다리기 |
| TMAP … 키가 맞는지 확인 | App Key 다시 복사, 장소검색·자동차 경로안내가 사용 설정됐는지 확인 |
| 네이버 키를 확인해 주세요 | Client ID/Secret 확인, 사용 API에 **검색**이 있는지 확인 |
| 출발 시각 예측을 쓸 수 없어… | 타임머신 API가 신청 안 된 상태 (앱은 정상, 지금 교통 기준으로 계산) |

키를 바꾸려면 Streamlit Cloud 내 앱 화면 → 오른쪽 아래 **Manage app → ⋮ → Settings → Secrets** 에서 고치고 저장하세요.

---

## (참고) 개발자용 정보

```
streamlit_app.py         화면 (Streamlit): 탭·목적지 검색·출발 시각 → 날씨/가는 길/맛집 카드
app/core.py              화면이 부르는 기능: search(), summary(), key_status()
app/services/weather.py  기상청: 지금 날씨, 도착 시각부터 6시간 예보, 라운딩 적합도
app/services/tmap.py     TMAP: 장소 검색(골프장 모드는 골프장만), 경로(출발 시각 예측 → 실패 시 현재 교통)
app/services/naver.py    네이버 지역 검색: 목적지 주변 맛집 5곳 → 거리 계산 후 가까운 순
tests/                   가짜 API로 돌리는 테스트 (키 없이 실행: python -m pytest)
```

- 내 컴퓨터에서 실행: `pip install -r requirements.txt pytest` → `.env.example`을 `.env`로 복사해 키 입력 → `streamlit run streamlit_app.py` → http://localhost:8501
- 라운딩 적합도 기준: 도착 후 5시간 동안 바람 6m/s 이상 또는 강수확률 60% 이상이면 "어려움",
  4m/s 이상 또는 30% 이상이면 "보통" (`weather.py`의 `golf_rating`에서 바꿀 수 있어요)

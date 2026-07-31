# 과매도 + 수급 유입 종목 스크리너

매일 아침, 아래 3개 조건을 **모두** 만족하는 종목 상위 10개를 자동으로 찾아
아이폰에서 볼 수 있는 웹페이지에 표시합니다.

1. 일봉 RSI(14) ≤ 30
2. 최근 3거래일 연속 외국인 + 기관 모두 순매수 (네이버 증권 기준)
3. 이격도(20일선) 가 최근 3일 연속 감소(수렴) 중

가격/RSI/이격도/수급/종목목록 **전부 네이버 증권**에서 가져옵니다.
(처음에는 수급 데이터만 KRX 원천 데이터로 더 정밀하게 만들려고 했지만,
KRX 서버가 GitHub 자동실행 서버 접속을 막아서 전부 네이버 방식으로 통일했습니다.
이 때문에 '투신' 세부 구분은 제공되지 않고, 외국인+기관 합계로 판단합니다.)

> ⚠️ 이 도구는 조건에 맞는 종목을 기계적으로 찾아주는 스크리닝 도구이며,
> 매수/매도를 추천하는 것이 아닙니다. 투자 판단과 책임은 본인에게 있습니다.

---

## 1. 폴더 구조

```
stock-screener/
├── main.py                # 메인 실행 스크립트
├── indicators.py          # RSI, 이격도 계산
├── naver_price.py         # 네이버 증권 일봉 시세 크롤링
├── naver_investor.py      # 네이버 증권 외국인/기관 순매매 크롤링
├── naver_universe.py      # 네이버 증권 시가총액 순위 크롤링 (스캔 대상 목록)
├── retry_util.py          # 요청 실패 시 재시도 헬퍼
├── notify_telegram.py     # (선택) 텔레그램 알림
├── requirements.txt
├── docs/
│   ├── index.html         # 아이폰에서 볼 모바일 웹페이지
│   └── results.json       # 매일 자동 갱신되는 결과 데이터
└── .github/workflows/
    └── daily-screen.yml   # 매일 자동 실행 스케줄
```

## 2. 셋업 (한 번만 하면 됩니다)

### (1) GitHub 저장소 만들기
1. GitHub에 로그인 → 우측 상단 `+` → **New repository**
2. 이름은 자유롭게, **Public**으로 생성
   (Public이어야 GitHub Pages 무료로 사용 가능. 내용은 종목 코드/RSI 수치뿐이라 공개되어도 무방합니다)
3. 이 폴더의 파일 전체를 그 저장소에 업로드 (GitHub 웹에서 "Add file → Upload files" 로 드래그 앤 드롭 가능)
   - ⚠️ 이미 예전 버전을 올려두셨다면, 저장소의 기존 파일을 전부 지우고
     (또는 저장소를 삭제 후 새로 만들고) 이 폴더 내용으로 다시 올리는 것을 권장합니다.

### (2) GitHub Pages 켜기
1. 저장소 → **Settings → Pages**
2. Source: `Deploy from a branch` / Branch: `main`, 폴더: `/docs` 선택 → Save
3. 몇 분 후 `https://<내계정>.github.io/<저장소이름>/` 주소가 생깁니다

### (3) (선택) 텔레그램 알림 받기
알림이 없어도 위 웹페이지를 열면 항상 최신 결과가 보이지만,
"울리는 알림"을 원하시면:
1. 텔레그램에서 **@BotFather** 검색 → `/newbot` → 안내에 따라 봇 생성 → **토큰** 받기
2. 만든 봇과 대화창을 열고 아무 메시지나 전송
3. 브라우저에서 `https://api.telegram.org/bot<토큰>/getUpdates` 접속 → `"chat":{"id": ...}` 에서 **chat id** 확인
4. GitHub 저장소 → **Settings → Secrets and variables → Actions → New repository secret**
   - `TELEGRAM_BOT_TOKEN` = 봇 토큰
   - `TELEGRAM_CHAT_ID` = chat id
5. 이제 매일 아침 텔레그램 앱으로 실제 푸시 알림이 옵니다.

### (4) 아이폰에 "앱처럼" 추가하기
1. 아이폰 **Safari**에서 `https://<내계정>.github.io/<저장소이름>/` 접속
2. 하단 공유 버튼(⬆️) → **홈 화면에 추가**
3. 홈 화면에 아이콘이 생기고, 탭하면 앱처럼 전체화면으로 열립니다

## 3. 동작 확인 (수동 실행)

매일 자동으로 실행되지만, 바로 확인해보고 싶다면:
1. 저장소 → **Actions** 탭 → `Daily Stock Screening` 선택
2. **Run workflow** 버튼 클릭 → 완료까지 다소 시간이 걸릴 수 있음 (아래 참고)
3. 아이폰에서 페이지 새로고침하면 결과가 갱신되어 있습니다

## 4. 스케줄 및 실행 시간 관련 참고사항

- GitHub Actions의 cron은 **UTC 기준**이라 `.github/workflows/daily-screen.yml`에
  `30 21 * * 0-4` (UTC 일~목 21:30 = KST 월~금 06:30)로 설정해두었습니다.
- 네이버 크롤링 방식은 종목 하나당 시세+수급 데이터를 각각 여러 페이지 요청해야 해서,
  KRX API 방식보다 **시간이 더 걸립니다.** 300개 종목 기준 대략 30분~1시간 정도 걸릴 수 있어,
  8:30 표시 목표를 위해 넉넉히 2시간 전(06:30)에 시작하도록 해두었습니다.
- 그래도 시간이 부족하면 `main.py`의 `TOP_N_BY_MARKETCAP` 값을 300 → 150~200 등으로 줄이면
  더 빨리 끝납니다 (그만큼 스캔 범위는 좁아짐).

## 5. 조건 값 조정

`main.py` 상단의 설정값을 바꾸면 조건을 조정할 수 있습니다:

```python
RSI_THRESHOLD = 30          # RSI 기준값
DISPARITY_MA_PERIOD = 20    # 이격도 기준 이동평균(20일선)
TOP_N_BY_MARKETCAP = 300    # 스캔할 종목 범위
RESULT_COUNT = 10           # 최종 표시 종목 수
```

`naver_investor.py`의 `has_3day_consecutive_net_buy()` 는 현재
"외국인/기관합계 각각이 3일 모두 순매수"를 조건으로 합니다.
"둘을 합친 값이 3일 연속 순매수"로 바꾸고 싶다면 이 함수만 수정하면 됩니다.

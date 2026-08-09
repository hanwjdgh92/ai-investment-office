# 관심종목 웹 등록/삭제 기능 Design Spec

**작성일:** 2026-08-09
**배경:** `config/watchlist.yaml`에 관심종목(코인/국내주식/해외주식)이 정적으로 정의되어 있고, 지금까지
사용자가 이 파일을 직접 편집한 적이 없어 초기 시드값(BTC/ETH, 삼성전자/SK하이닉스, Apple/NVIDIA)만
계속 노출됐다. 이를 웹 화면에서 직접 추가/삭제할 수 있게 한다.

## 목표

- 라이브 오피스 화면(`http://127.0.0.1:8787`, `scripts/serve_office.py`)에서 관심종목을 추가/삭제.
- 추가한 종목은 즉시 조회되어 화면에 반영된다(다음 자동 갱신까지 기다리지 않음).
- 입력은 심볼/코드만(크립토: 심볼, 국내주식: 6자리 코드, 해외주식: 티커) — 종목명은 자동 조회.

## 범위 밖 (Non-goals)

- 정적 스냅샷(`office/index.html`, 더블클릭으로 여는 파일)에서의 편집 — 백엔드가 없어 기술적으로 불가능.
  이 화면에는 "라이브 뷰어(`launch_live_office.bat`)에서만 사용 가능" 안내만 표시한다.
- 워치리스트 편집과 시간별/전체분석 예약 작업 간의 파일 쓰기 동시성 보호 — 라이브 서버는 이미
  `price_update_loop`로 30초/2분 주기 자체 갱신을 돌리고 있어 기존에도 있던 위험이며, 개인 로컬 서버
  용도상 이번에 새로 막지 않는다.
- 삭제 확인 팝업, 종목명 수동 수정, watchlist.yaml 외 다른 설정 편집.

## 아키텍처

- `office/template.html`: 헤더에 "⚙ 관심종목 관리" 토글 버튼 + 패널. 패널 안에 크립토/국내주식/해외주식
  3개 그룹, 그룹마다 "심볼 입력창 + 추가" 한 줄과 현재 종목 칩 목록(칩마다 ✕ 삭제 버튼).
- `scripts/serve_office.py`: 새 HTTP 엔드포인트 3개 추가.
  - `GET /api/watchlist` — `config/watchlist.yaml`을 읽어 `{crypto: [...], stocks_kr: [...], stocks_us: [...]}` JSON으로 반환 (패널 초기 렌더링용).
  - `POST /api/watchlist` — body `{type: "crypto"|"stocks_kr"|"stocks_us", symbol: "..."}`.
  - `DELETE /api/watchlist` — body `{type, symbol}` (crypto/stocks_us는 symbol/ticker로, stocks_kr은 code로 식별).
- `scripts/watchlist_store.py` (신규, 작은 헬퍼 모듈): `config/watchlist.yaml` 읽기/쓰기 공용 함수.
  파일 상단 안내 주석(현재 1~2번 줄)은 고정 문자열로 다시 써주고, 그 아래 데이터만
  `yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)`로 갱신해
  기존 주석이 사라지지 않게 한다.
- 종목명 자동 조회:
  - 크립토: 별도 이름 조회 없음 — 심볼 자체가 표시명 겸함(업비트/바이빗 관례와 동일).
  - 국내주식: `fetch_stocks_kr.py`가 PER/PBR 조회 때 이미 받는 네이버 금융 페이지의 `<title>` 태그에서
    이름을 파싱(`soup.title.text.split(":")[0].strip()`). 추가 HTTP 요청 없음.
  - 해외주식: `yfinance`의 `Ticker(ticker).info.get("shortName")` (없으면 `longName`, 그마저 없으면
    티커 그대로).

## 데이터 흐름

### 추가 (예: 국내주식 코드 "000270" 입력)

```
패널에서 "000270" 입력 → 추가 클릭
  → POST /api/watchlist {type: "stocks_kr", symbol: "000270"}
  → 서버:
      1. 네이버 금융 페이지 조회해서 이름 파싱("기아") + PER/PBR 등 1건 검증 조회
      2. 성공 시: watchlist_store로 {name: "기아", code: "000270"}를 watchlist.yaml의
         stocks_kr 목록에 append 저장
      3. fetch_stocks_kr.main() 재실행 (오늘자 stocks_kr_YYYY-MM-DD.json 전체를 기존+신규 항목
         포함해 다시 씀 — 부분 병합이 아니라 전체 재조회)
      4. 202 응답 {name: "기아", status: "ok"}
      실패 시(코드 틀림 등): yaml 안 건드림, 400 응답 {error: "종목 조회 실패: ..."}
  → 프론트: 성공하면 칩 목록에 "기아" 추가하고 GET /api/live 재호출해 화면 갱신
            실패하면 입력창 옆에 에러 메시지만 표시(패널은 안 닫힘)
```

### 추가 — 크립토 (예: 심볼 "SOL")

```
POST /api/watchlist {type: "crypto", symbol: "SOL"}
  → upbit_market = "KRW-SOL", bybit_symbol = "SOLUSDT" 로 자동 유도
  → 업비트/바이빗 둘 다 시세 조회 시도
      - 하나라도 성공: watchlist.yaml에 저장 + fetch_crypto.main() 재실행 + 202 응답
        (실패한 거래소가 있으면 응답에 warning 필드로 "바이빗 미지원" 등 표시)
      - 둘 다 실패: yaml 안 건드림, 400 응답 {error: "..."}
```

### 삭제 (모든 자산군 공통)

```
칩의 ✕ 클릭 (확인 팝업 없음, 즉시 실행)
  → DELETE /api/watchlist {type, symbol}
  → 서버: watchlist_store로 yaml에서 해당 항목 제거 → 그 자산군의 fetch_*.main() 재실행
  → 204 응답 → 프론트: 칩 즉시 제거 + GET /api/live 재호출
```

## 에러 처리 / 알려진 한계

- 중복 추가: 이미 등록된 심볼/코드(크립토는 symbol, 국내주식은 code, 해외주식은 ticker 기준, 크립토·해외
  심볼은 대소문자 구분 없이 대문자로 정규화한 뒤 비교)면 저장 없이 400 "이미 등록됨" 응답.
- 크립토: 업비트/바이빗 중 하나라도 성공하면 저장, 실패한 거래소는 경고만 표시(§검증 기준 참고).
- 동시성: 새로 추가되는 fetch 호출이 `price_update_loop`나 예약 작업과 겹쳐 같은 data 파일에 쓸 수
  있음 — 기존에도 존재하던 위험이며 이번 범위에서 새로 막지 않음(§범위 밖 참고).
- 정적 스냅샷(`office/index.html`)에서는 패널이 "라이브 뷰어 전용" 안내만 표시하고 버튼은 비활성화.

## 검증 방법 (자동 테스트 프레임워크 없음 — 수동 확인)

1. `python scripts/serve_office.py` 실행 → 실존 종목(예: 코인 SOL, 국내 000270, 해외 TSLA) 각각
   패널에서 추가 → `config/watchlist.yaml`, 오늘자 `data/*.json`, 화면 칩 목록 세 곳 모두 반영되는지 확인.
2. 존재하지 않는 심볼(예: "ZZZZZZ") 추가 시도 → yaml 안 바뀌고 에러 메시지만 뜨는지 확인.
3. 업비트에만 있고 바이빗에 없는 코인 추가 → 저장은 되고 바이빗 관련 경고가 뜨는지 확인.
4. 이미 등록된 종목 재추가 시도 → "이미 등록됨" 에러 확인.
5. 삭제 클릭 → 칩/yaml/데이터 파일에서 즉시 사라지는지 확인.
6. `office/index.html`(더블클릭 버전)을 직접 열어 패널이 "라이브 뷰어 전용" 안내로만 뜨는지, 버튼이
   비활성 상태인지 확인.

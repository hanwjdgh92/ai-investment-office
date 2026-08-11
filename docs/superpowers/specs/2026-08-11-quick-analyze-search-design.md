# 종목 검색 즉시분석 기능 Design Spec

**작성일:** 2026-08-11
**배경:** 지금은 관심종목(`config/watchlist.yaml`)에 등록된 종목만 하루 3회 스케줄(`/scheduled-analysis`)로
AI 분석을 받는다. 워치리스트에 없는 임의의 종목 하나를 즉석에서 AI가 분석해주길 원하는 수요가 있다
(참고 UI: ChartPT 서비스의 검색창 — 심볼 입력 시 자동완성으로 이름+카테고리 뱃지가 뜨고 "Start Analysis"로
즉시 분석).

## 목표

- 라이브 오피스(`http://127.0.0.1:8787`, `scripts/serve_office.py`)에 검색창 추가.
- 크립토/국내주식/해외주식 중 하나를 자동완성으로 골라 "분석 시작"하면, 기존 데스크 파이프라인과 동일한
  깊이의 AI 분석(애널리스트 3명 + 데스크 리서치종합, 크립토는 매매시그널까지)을 그 종목 하나에 대해서만
  즉시 받는다.
- 결과는 저장(리포트 파일, 워치리스트 등록) 없이 1회성으로 보여주되, "최근검색" 목록에 캐싱되어 서버를
  재시작해도 다시 볼 수 있다.

## 범위 밖 (Non-goals)

- 선물/무기한계약(perpetual futures, `.P` 표기) 분석 — 레버리지·펀딩비·청산가 등 완전히 다른 리스크
  모델이 필요해 별도 설계로 분리한다.
- 검색 종목을 워치리스트에 저장하거나 정식 리포트(`reports/*.md`)로 남기는 것.
- 정적 스냅샷(`office/index.html`, 더블클릭판)에서의 실행 — 백엔드가 없어 기술적으로 불가능. 기존
  워치리스트 패널과 동일하게 "라이브 뷰어 전용" 안내만 표시.
- 자동완성 대상 해외종목은 S&P500 + 나스닥100으로 한정 (전체 상장종목 아님).
- 바이빗에만 상장된(업비트 KRW마켓에 없는) 코인 — 자동완성은 업비트 마켓 목록 기준.
- 여러 검색을 동시에 처리하는 큐/병렬 처리 — 개인 로컬 도구이므로 한 번에 하나만 처리.

## 아키텍처

```
브라우저(라이브 오피스)
  검색창(자동완성) → 종목 선택 → "분석 시작"
    → POST /api/quick-analyze {type, symbol}
    → serve_office.py가 서브프로세스로 실행:
        claude -p "/quick-analyze <type> <symbol>" --max-budget-usd <N>
      (기존 run_scheduled_analysis.ps1과 동일 방식 — 별도 API 키 불필요, Claude Code 구독 사용)
    → 완료 대기(수십초~수분) → stdout에서 최종 결과 텍스트 캡처
    → data/recent_searches.json에 캐싱 {type, symbol, name, timestamp, result_text}, 최근 N개(예: 10개)만 유지
    → 결과 텍스트를 응답으로 반환 → 브라우저가 모달/패널에 표시
```

### 자동완성 데이터 소스

| 자산군 | 소스 | 캐싱 방식 |
|---|---|---|
| 크립토 | 업비트 `GET /v1/market/all` (KRW- 마켓만) | `serve_office.py` 시작 시 1회 조회 → 메모리 |
| 국내주식 | `FinanceDataReader.StockListing('KRX')` | `serve_office.py` 시작 시 1회 조회 → 메모리 |
| 해외주식 | S&P500 + 나스닥100 심볼+이름 고정 리스트 | `config/us_universe.json` 정적 파일, 필요시 수동 갱신 |

검색창 타이핑 → 위 캐시에서 부분일치 필터링 → 심볼/이름/카테고리뱃지로 자동완성 목록 표시. 자유 텍스트
직접 실행은 막고, 반드시 자동완성 항목을 선택해야 "분석 시작"이 활성화된다 (존재하지 않는 심볼 방지).

### 신규 슬래시커맨드: `.claude/commands/quick-analyze.md`

인자: 자산군(`crypto`/`stocks_kr`/`stocks_us`) + 심볼.

1. 해당 심볼 하나만 조회하는 파이썬 fetch 실행 — 기존 `fetch_crypto.py`/`fetch_stocks_kr.py`/
   `fetch_stocks_us.py`의 조회 함수를 재사용해 결과를 `data/adhoc/<type>_<symbol>.json`에 저장한다
   (오늘자 정식 데이터 파일이나 워치리스트는 건드리지 않음). `data/adhoc/`는 `.gitignore`에 추가.
2. 데스크별 서브에이전트 호출. 기존 에이전트 정의(candle.md 등)는 수정하지 않고, 호출 시 프롬프트에서
   "오늘자 워치리스트 데이터 파일 대신 `data/adhoc/<type>_<symbol>.json`을 읽으라"고 명시적으로 지시한다.
   - 크립토: candle/proto/vibes(병렬) → node → trigger → maverick/guardian(병렬) → balance (7단계,
     매매시그널까지 포함)
   - 국내주식: chart/ledger/mood(병렬) → anchor (4단계)
   - 해외주식: trend/vault/pulse(병렬) → compass (4단계)
3. 최종 결과 텍스트를 그대로 출력한다 (`reports/`에 파일 쓰지 않음, 워치리스트에 추가하지 않음).
4. `data/adhoc/<type>_<symbol>.json` 삭제.

**비용 상한**: 크립토(7단계, 매매시그널 포함) `--max-budget-usd 2`, 국내/해외(4단계) `--max-budget-usd 1`.

### 서버 신규 엔드포인트 (`scripts/serve_office.py`)

- `GET /api/symbols?type=crypto|stocks_kr|stocks_us&q=<검색어>` — 자동완성 목록 필터링 결과 반환.
- `POST /api/quick-analyze` — body `{type, symbol}` → 위 서브프로세스 실행 → 완료까지 대기(블로킹) →
  결과 텍스트 + `recent_searches.json` 갱신 반환. 처리 중 새 요청이 오면 "이미 분석 중" 400 응답.
- `GET /api/recent-searches` — `data/recent_searches.json` 내용 반환 (페이지 최초 로딩 시 최근검색
  목록 렌더링용).

### 프론트엔드 (`office/template.html`)

- 헤더 근처(기존 "⚙ 관심종목 관리" 버튼 옆)에 검색창 추가.
- 타이핑 시 `/api/symbols` 호출 → 자동완성 드롭다운(심볼/이름/카테고리뱃지).
- 항목 선택 → "분석 시작" 버튼 활성화 → 클릭 시 `/api/quick-analyze` 호출, 버튼 비활성 + 로딩 표시(수십초
  ~분 단위 소요 안내 문구 포함).
- 결과는 기존 리포트 모달과 같은 스타일의 모달/패널로 표시.
- 검색창 아래 "최근검색" 영역: `/api/recent-searches`로 받은 최근 N개를 칩/리스트로 표시. 클릭 시 재분석
  없이 캐시된 `result_text`를 즉시 모달로 보여준다.
- 정적 스냅샷(`office/index.html`)에서는 검색창 비활성 + "라이브 뷰어 전용" 안내만 표시 (기존 워치리스트
  패널과 동일 패턴).

## 데이터 흐름 요약

```
검색어 입력 → GET /api/symbols (자동완성)
종목 선택 + 분석시작 클릭 → POST /api/quick-analyze
  → claude -p "/quick-analyze <type> <symbol>" 서브프로세스
    → 단일종목 fetch → data/adhoc/*.json
    → 애널리스트 3명 → (크립토는 +매매시그널 4단계) → 데스크 리서치종합
    → 결과 텍스트 반환, adhoc 파일 삭제
  → recent_searches.json에 캐싱(최근 N개 유지) → 응답
최근검색 칩 클릭 → GET /api/recent-searches에서 이미 받은 캐시 표시 (재실행 없음)
```

## 에러 처리 / 알려진 한계

- 존재하지 않는 심볼: 자동완성 목록에서만 선택 가능하므로 발생하지 않음.
- 단일종목 fetch 실패: 서브에이전트 호출 전에 에러 반환 (비용 발생 없음).
- 서브프로세스 타임아웃(예: 10분) 초과 시 에러 응답 + adhoc 데이터 파일 정리.
- `data/adhoc/`는 시간별 갱신·전체분석 스케줄이 쓰는 파일과 경로가 완전히 분리되어 있어 파일 경합 없음.
- 동시 요청: 분석 진행 중 새 요청은 400으로 거부 (큐 없음, 개인 로컬 도구 전제).
- 정적 스냅샷에서는 버튼 비활성 상태 유지.

## 검증 방법 (자동 테스트 프레임워크 없음 — 수동 확인)

1. 크립토/국내주식/해외주식 각 1종목씩(워치리스트에 없는 종목으로) 검색 → 자동완성 노출 확인 → 분석
   시작 → 결과에 애널리스트 3명 + 리서치종합(크립토는 +매매시그널) 포함 여부 확인.
2. 분석 후 `reports/`에 새 파일이 생기지 않는지, `config/watchlist.yaml`에 해당 종목이 추가되지
   않는지 확인.
3. `data/recent_searches.json`에 항목이 쌓이는지, `serve_office.py` 재시작 후에도 남아있는지 확인.
4. 최근검색 칩 클릭 시 재분석(서브프로세스 재실행) 없이 캐시된 결과가 즉시 표시되는지 확인.
5. 분석 진행 중 다른 종목 검색 시도 → "분석 중" 응답으로 거부되는지 확인.
6. `office/index.html`(정적 스냅샷)을 직접 열어 검색창이 "라이브 뷰어 전용" 안내로만 뜨고 비활성인지 확인.

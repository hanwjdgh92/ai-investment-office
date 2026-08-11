# 종목 검색 즉시분석 기능 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 라이브 오피스(`http://127.0.0.1:8787`)에 종목 검색창을 추가해, 워치리스트에 없는 임의의 종목 하나를
그 자리에서 기존 데스크와 동일한 깊이(애널리스트 3명 + 리서치종합, 크립토는 매매시그널까지)로 AI 분석받는다.

**Architecture:** 브라우저 검색창 → `/api/quick-analyze` POST → `serve_office.py`가 `run_quick_analyze.ps1`을
서브프로세스로 실행 → 그 안에서 `claude -p "/quick-analyze <type> <symbol>"` 헤드리스 실행(기존
`run_scheduled_analysis.ps1`과 동일 방식, API 키 불필요) → 새 슬래시커맨드가 단일종목 데이터를
`data/adhoc/`에 임시로 만들고 기존 서브에이전트(candle/proto/vibes 등)를 그 파일 하나만 보도록 호출 →
결과 텍스트를 로그 파일에 남김 → 브라우저는 `/api/quick-analyze/status`를 폴링해 완료되면 결과를 모달로
표시하고 `data/recent_searches.json`에 캐싱.

**Tech Stack:** Python 3(표준 `http.server`, `requests`, `FinanceDataReader`, `yfinance`), PowerShell 5.1,
Claude Code CLI(`claude -p`), 바닐라 JS/CSS(`office/template.html`, 빌드도구 없음).

## Global Constraints

- 워치리스트(`config/watchlist.yaml`)와 정식 데이터 파일(`data/crypto_YYYY-MM-DD.json` 등), 정식 리포트
  (`reports/*.md`)는 이 기능이 절대 건드리지 않는다 — 검색 결과는 저장하지 않고 캐싱만 한다.
- 프로젝트에 자동 테스트 프레임워크가 없다(전체 저장소에 `test_*.py` 없음) — 각 태스크는 수동 실행/확인으로
  검증한다. 새 테스트 프레임워크를 도입하지 않는다.
- 기존 에이전트 정의(`.claude/agents/*.md`)는 수정하지 않는다 — 프롬프트로 "읽을 파일 경로"만 오버라이드한다.
- Windows PowerShell 5.1 환경. 네이티브 프로세스(`claude.exe`)의 stdout을 한글 깨짐 없이 받으려면
  `run_scheduled_analysis.ps1`이 이미 쓰고 있는 패턴(`[Console]::OutputEncoding = UTF8`,
  `$ErrorActionPreference = "Continue"` 임시 전환, `Out-File -Encoding utf8`)을 그대로 재사용한다 — 이
  패턴을 벗어나면 과거에 실측된 한글 깨짐 버그가 재발한다.
- `claude.exe` 경로는 `C:\Users\user\.local\bin\claude.exe`로 고정한다(기존 스크립트와 동일).
- 신규 `.ps1` 파일은 UTF-8 BOM으로 저장해야 한다(BOM 없으면 PowerShell 5.1이 ANSI로 읽어 한글 주석이 깨짐).

---

## 파일 구조 개요

| 파일 | 종류 | 책임 |
|---|---|---|
| `.gitignore` | 수정 | `data/adhoc/` 제외 추가 |
| `scripts/fetch_adhoc.py` | 신규 | 단일 종목 시세/지표/펀더멘털 조회 → `data/adhoc/<type>_<symbol>.json` |
| `scripts/recent_searches_store.py` | 신규 | `data/recent_searches.json` 읽기/쓰기(최근 10개 유지) |
| `scripts/symbol_universe.py` | 신규 | 자동완성용 종목 유니버스(크립토/국내/해외) 메모리 캐싱 + 검색 |
| `.claude/commands/quick-analyze.md` | 신규 | 단일종목 분석 파이프라인 오케스트레이션 슬래시커맨드 |
| `scripts/run_quick_analyze.ps1` | 신규 | 위 커맨드를 헤드리스로 실행하는 래퍼(인코딩 안전 패턴 재사용) |
| `scripts/serve_office.py` | 수정 | `/api/symbols`, `/api/quick-analyze`, `/api/quick-analyze/status`, `/api/recent-searches` 엔드포인트 추가 |
| `office/template.html` | 수정 | 검색창 + 자동완성 + 최근검색 UI |

---

### Task 1: 단일 종목 조회 스크립트

**Files:**
- Modify: `.gitignore`
- Create: `scripts/fetch_adhoc.py`

**Interfaces:**
- Produces: `fetch_one(type_: str, symbol: str) -> dict` (단일 종목 데이터 dict, 기존 `data/*.json`의
  항목 1개와 동일한 필드 구조), `main()` — CLI 진입점, `sys.argv[1]`=type, `sys.argv[2]`=symbol.
- Consumes: `fetch_crypto.fetch_upbit`, `fetch_crypto.fetch_upbit_indicators`, `fetch_crypto.fetch_bybit`,
  `fetch_stocks_kr.fetch_name_and_fundamentals`, `fetch_stocks_kr.fetch_recent`,
  `fetch_stocks_us.fetch_name`, `fetch_stocks_us.fetch_recent` (모두 기존 파일에 이미 존재, 시그니처 변경 없음).

- [ ] **Step 1: `.gitignore`에 adhoc 데이터 제외 추가**

`.gitignore` 끝에 추가:

```
data/adhoc/
```

- [ ] **Step 2: `scripts/fetch_adhoc.py` 작성**

```python
"""단일 종목 즉시분석(quick-analyze)용 임시 데이터 조회 스크립트.
워치리스트/오늘자 정식 데이터 파일은 건드리지 않고 data/adhoc/<type>_<symbol>.json 하나만 만든다.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_crypto  # noqa: E402
import fetch_stocks_kr  # noqa: E402
import fetch_stocks_us  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ADHOC_DIR = ROOT / "data" / "adhoc"


def fetch_one(type_: str, symbol: str) -> dict:
    if type_ == "crypto":
        sym = symbol.upper()
        upbit_market = f"KRW-{sym}"
        bybit_symbol = f"{sym}USDT"
        entry = {"symbol": sym}
        entry["upbit"] = fetch_crypto.fetch_upbit(upbit_market)
        entry["indicators"] = fetch_crypto.fetch_upbit_indicators(upbit_market)
        try:
            entry["bybit"] = fetch_crypto.fetch_bybit(bybit_symbol)
        except Exception as exc:  # noqa: BLE001
            entry["bybit_error"] = str(exc)
        return entry

    if type_ == "stocks_kr":
        info = fetch_stocks_kr.fetch_name_and_fundamentals(symbol)
        entry = {"name": info["name"], "code": symbol}
        entry.update(fetch_stocks_kr.fetch_recent(symbol))
        entry["fundamentals"] = {"per": info["per"], "pbr": info["pbr"]}
        return entry

    if type_ == "stocks_us":
        ticker = symbol.upper()
        entry = {"name": fetch_stocks_us.fetch_name(ticker), "ticker": ticker}
        entry.update(fetch_stocks_us.fetch_recent(ticker))
        return entry

    raise ValueError(f"알 수 없는 type: {type_}")


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: python fetch_adhoc.py <type> <symbol>", file=sys.stderr)
        sys.exit(1)

    type_, symbol = sys.argv[1], sys.argv[2]
    entry = fetch_one(type_, symbol)

    ADHOC_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ADHOC_DIR / f"{type_}_{symbol.upper()}.json"
    out_path.write_text(
        json.dumps([entry], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 수동 검증 (3개 자산군 각각 워치리스트에 없는 종목으로)**

Run:
```powershell
python scripts\fetch_adhoc.py crypto SOL
python scripts\fetch_adhoc.py stocks_kr 000270
python scripts\fetch_adhoc.py stocks_us TSLA
```
Expected: 각각 `saved: ...\data\adhoc\crypto_SOL.json`, `stocks_kr_000270.json`, `stocks_us_TSLA.json` 출력.
파일을 열어 배열 안에 항목 1개, 크립토는 `upbit`/`indicators`/`bybit` 필드, 국내주식은 `name`(기아)/`code`/
`fundamentals`(per/pbr), 해외주식은 `name`(Tesla 등)/`ticker`/`fundamentals` 필드가 채워져 있는지 확인.
확인 후 `data\adhoc\` 폴더는 삭제해도 되고 남겨둬도 된다(`.gitignore`로 이미 제외됨).

- [ ] **Step 4: 커밋**

```bash
git add .gitignore scripts/fetch_adhoc.py
git commit -m "feat: 종목 검색 즉시분석용 단일종목 조회 스크립트 추가"
```

---

### Task 2: 최근검색 저장소

**Files:**
- Create: `scripts/recent_searches_store.py`

**Interfaces:**
- Produces: `load() -> list[dict]`, `add(entry: dict) -> None`, `MAX_ITEMS = 10`.
- Consumes: 없음(표준 라이브러리만 사용).

- [ ] **Step 1: `scripts/recent_searches_store.py` 작성**

```python
"""data/recent_searches.json 읽기/쓰기 공용 헬퍼. 최근 검색 결과를 최근 N개만 보관한다."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = ROOT / "data" / "recent_searches.json"
MAX_ITEMS = 10


def load() -> list[dict]:
    if not STORE_PATH.exists():
        return []
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))


def add(entry: dict) -> None:
    items = [entry] + load()
    items = items[:MAX_ITEMS]
    STORE_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
```

- [ ] **Step 2: 수동 검증**

Run:
```powershell
python -c "import sys; sys.path.insert(0, 'scripts'); import recent_searches_store as s; s.add({'symbol':'A'}); s.add({'symbol':'B'}); print(s.load())"
```
Expected: `[{'symbol': 'B'}, {'symbol': 'A'}]` (최근 항목이 앞에 옴). 11개 이상 추가했을 때 `len(s.load())`가
10을 넘지 않는지도 확인:
```powershell
python -c "import sys; sys.path.insert(0, 'scripts'); import recent_searches_store as s; [s.add({'symbol': str(i)}) for i in range(15)]; print(len(s.load()))"
```
Expected: `10`. 검증 후 `data\recent_searches.json`은 테스트 더미 데이터이므로 삭제:
```powershell
Remove-Item data\recent_searches.json
```

- [ ] **Step 3: 커밋**

```bash
git add scripts/recent_searches_store.py
git commit -m "feat: 최근검색 캐시 저장소 추가"
```

---

### Task 3: 검색 자동완성용 종목 유니버스

**Files:**
- Create: `scripts/symbol_universe.py`

**Interfaces:**
- Produces: `load_all() -> None` (서버 시작 시 1회 호출, 실패한 자산군은 빈 리스트로 남고 서버는 안 죽음),
  `search(type_: str, query: str, limit: int = 20) -> list[dict]`,
  `search_all(query: str, limit_per_type: int = 8) -> list[dict]`.
  각 항목 dict 형태: `{"symbol": str, "name": str, "type": "crypto"|"stocks_kr"|"stocks_us"}`.
- Consumes: `requests`(이미 프로젝트 의존성), `FinanceDataReader`(이미 프로젝트 의존성).

- [ ] **Step 1: `scripts/symbol_universe.py` 작성**

```python
"""검색창 자동완성용 종목 유니버스. 서버 시작 시 1회 조회해 메모리에 캐싱한다."""
import requests
import FinanceDataReader as fdr

_CACHE: dict[str, list[dict]] = {"crypto": [], "stocks_kr": [], "stocks_us": []}


def _load_crypto() -> list[dict]:
    resp = requests.get(
        "https://api.upbit.com/v1/market/all", params={"isDetails": "false"}, timeout=10
    )
    resp.raise_for_status()
    items = []
    for row in resp.json():
        market = row["market"]
        if not market.startswith("KRW-"):
            continue
        symbol = market.split("-", 1)[1]
        items.append({"symbol": symbol, "name": row.get("korean_name", symbol), "type": "crypto"})
    return items


def _load_stocks_kr() -> list[dict]:
    df = fdr.StockListing("KRX")
    return [
        {"symbol": str(row["Code"]), "name": str(row["Name"]), "type": "stocks_kr"}
        for _, row in df.iterrows()
    ]


def _load_stocks_us() -> list[dict]:
    # ponytail: 전체 상장종목이 아닌 S&P500만 소스로 씀(빠르고 안정적, 대형 나스닥 종목 대부분 포함).
    # 나스닥100 전체 구성종목이 꼭 필요해지면 별도 정적 리스트를 추가할 것.
    df = fdr.StockListing("S&P500")
    return [
        {"symbol": str(row["Symbol"]), "name": str(row["Name"]), "type": "stocks_us"}
        for _, row in df.iterrows()
    ]


def load_all() -> None:
    try:
        _CACHE["crypto"] = _load_crypto()
    except Exception as exc:  # noqa: BLE001
        print(f"[symbol_universe] 크립토 목록 조회 실패: {exc}")
    try:
        _CACHE["stocks_kr"] = _load_stocks_kr()
    except Exception as exc:  # noqa: BLE001
        print(f"[symbol_universe] 국내주식 목록 조회 실패: {exc}")
    try:
        _CACHE["stocks_us"] = _load_stocks_us()
    except Exception as exc:  # noqa: BLE001
        print(f"[symbol_universe] 해외주식 목록 조회 실패: {exc}")


def search(type_: str, query: str, limit: int = 20) -> list[dict]:
    universe = _CACHE.get(type_, [])
    q = query.strip().upper()
    if not q:
        return universe[:limit]
    matches = [
        item for item in universe
        if q in item["symbol"].upper() or q in item["name"].upper()
    ]
    return matches[:limit]


def search_all(query: str, limit_per_type: int = 8) -> list[dict]:
    results: list[dict] = []
    for type_ in ("crypto", "stocks_kr", "stocks_us"):
        results.extend(search(type_, query, limit_per_type))
    return results
```

- [ ] **Step 2: 수동 검증**

Run:
```powershell
python -c "import sys; sys.path.insert(0, 'scripts'); import symbol_universe as u; u.load_all(); print(len(u.search('crypto', ''))); print(u.search('crypto', 'BTC')); print(u.search('stocks_kr', '삼성')); print(u.search_all('AAPL'))"
```
Expected: 크립토 전체 개수(수백 개)가 0보다 큼, `search('crypto','BTC')`에 `{'symbol': 'BTC', ...}` 포함,
`search('stocks_kr','삼성')`에 삼성전자 등 포함, `search_all('AAPL')`에 `stocks_us` 타입 Apple 항목 포함.
(`fdr.StockListing('KRX')` 조회는 몇 초 걸릴 수 있음 — 정상)

- [ ] **Step 3: 커밋**

```bash
git add scripts/symbol_universe.py
git commit -m "feat: 검색 자동완성용 종목 유니버스 캐시 추가"
```

---

### Task 4: 단일종목 분석 슬래시커맨드 + 실행 래퍼

**Files:**
- Create: `.claude/commands/quick-analyze.md`
- Create: `scripts/run_quick_analyze.ps1`

**Interfaces:**
- Consumes: Task 1의 `scripts/fetch_adhoc.py` CLI(`python scripts\fetch_adhoc.py <type> <symbol>`), 기존
  서브에이전트(candle/proto/vibes/node/trigger/maverick/guardian/balance, chart/ledger/mood/anchor,
  trend/vault/pulse/compass) — 모두 수정 없이 그대로 호출.
- Produces: `run_quick_analyze.ps1 -Type <type> -Symbol <symbol> -LogFile <path> -MaxBudgetUsd <n>` —
  실행 완료 시 `<LogFile>`에 UTF-8로 최종 분석 결과 텍스트(또는 에러 메시지)가 남음, 프로세스
  종료코드 0=성공.

- [ ] **Step 1: `.claude/commands/quick-analyze.md` 작성**

```markdown
---
description: 워치리스트에 없는 종목 하나를 즉석으로 조회해 AI가 분석한다. 인자 "<type> <symbol>" (type은 crypto/stocks_kr/stocks_us). data/adhoc/에 임시 데이터만 만들고 reports/나 watchlist에는 남기지 않는다.
---

인자 `$ARGUMENTS`를 공백 기준으로 앞의 두 값만 취해 `type`과 `symbol`로 나누세요 (예: "crypto BTC" →
type=crypto, symbol=BTC). type은 반드시 crypto/stocks_kr/stocks_us 중 하나입니다.

1. PowerShell로 아래 명령을 실행해 이 종목 하나만 조회한 데이터를 `data/adhoc/<type>_<symbol 대문자>.json`에
   저장합니다.
   - `python scripts\fetch_adhoc.py <type> <symbol>`
   (python이 PATH에 없다면 `$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")` 를 먼저 실행)
   - 이 명령이 실패하면(에러 출력 또는 0이 아닌 종료코드) 즉시 중단하고 "조회 실패: <에러 메시지>"만
     출력한 뒤 종료하세요. 이후 서브에이전트 호출 단계는 진행하지 않습니다.

2. type에 따라 아래 서브에이전트들을 호출합니다. 이때 각 애널리스트에게 "오늘자 워치리스트 데이터 파일
   (`data/crypto_YYYY-MM-DD.json` 등) 대신 `data/adhoc/<type>_<symbol>.json` 파일 하나만 읽고, 그 안의
   종목 하나만 분석하라"고 명시적으로 지시하세요.

   - **crypto**: `candle`/`proto`/`vibes`를 병렬로 호출 → 세 결과를 `node`에게 전달해 리서치 종합 →
     `node` 결과를 `trigger`에게 전달해 매매 시그널 생성 → `trigger` 결과를 `maverick`/`guardian`에게
     각각 병렬로 전달해 리스크 검토 → `trigger`/`maverick`/`guardian` 결과를 모두 `balance`에게 전달해
     최종 권고로 종합.
   - **stocks_kr**: `chart`/`ledger`/`mood`를 병렬로 호출 → 세 결과를 `anchor`에게 전달해 리서치 종합.
   - **stocks_us**: `trend`/`vault`/`pulse`를 병렬로 호출 → 세 결과를 `compass`에게 전달해 리서치 종합.

3. 아래 형식으로 최종 결과를 대화창에 그대로 출력하세요. **`reports/`에 파일로 쓰지 말고,
   `config/watchlist.yaml`에도 추가하지 마세요.**

   ```
   # <symbol> 즉시분석

   ## <애널리스트1 닉네임> - <역할>
   (해당 애널리스트 출력 그대로)

   ## <애널리스트2 닉네임> - <역할>
   ...

   ## <애널리스트3 닉네임> - <역할>
   ...

   ## <리서치종합 담당 닉네임> - 리서치 종합
   ...
   ```

   crypto인 경우에만 그 아래 이어서:
   ```
   ## Trigger - 매매 시그널
   ...
   ## Maverick - 공격적 리스크 검토
   ...
   ## Guardian - 보수적 리스크 검토
   ...
   ## Balance - 최종 권고
   ...
   ```

4. 마지막으로 PowerShell에서 아래 명령으로 임시 데이터 파일을 정리하세요.
   - `Remove-Item "data\adhoc\<type>_<symbol 대문자>.json" -ErrorAction SilentlyContinue`
```

- [ ] **Step 2: `scripts/run_quick_analyze.ps1` 작성**

이 파일은 UTF-8 BOM으로 저장해야 하므로, 먼저 아래 내용으로 파일을 만든 다음 Step 3에서 인코딩을
다시 씌운다.

```powershell
# 라이브 서버(scripts/serve_office.py)가 검색창 즉시분석 요청을 받았을 때 백그라운드로 실행하는 스크립트.
# claude -p "/quick-analyze <Type> <Symbol>" 를 헤드리스로 실행하고 결과를 -LogFile 에 UTF-8로 남긴다.
# run_scheduled_analysis.ps1과 같은 이유로 이 파일 자체를 UTF-8 BOM으로 저장한다(한글 깨짐 방지).

param(
    [Parameter(Mandatory = $true)][string]$Type,
    [Parameter(Mandatory = $true)][string]$Symbol,
    [Parameter(Mandatory = $true)][string]$LogFile,
    [Parameter(Mandatory = $true)][string]$MaxBudgetUsd
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

Set-Location $ProjectRoot

$ClaudeExe = "C:\Users\user\.local\bin\claude.exe"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$PrevErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $ClaudeExe -p "/quick-analyze $Type $Symbol" --permission-mode acceptEdits --max-budget-usd $MaxBudgetUsd --output-format text 2>&1 | Out-File -FilePath $LogFile -Encoding utf8
$ErrorActionPreference = $PrevErrorActionPreference
```

- [ ] **Step 3: UTF-8 BOM으로 재저장**

Run:
```powershell
$content = Get-Content -Path scripts\run_quick_analyze.ps1 -Raw
Set-Content -Path scripts\run_quick_analyze.ps1 -Value $content -Encoding utf8
```
(Windows PowerShell 5.1의 `-Encoding utf8`은 BOM을 포함해 저장한다 — `run_scheduled_analysis.ps1`과
동일 인코딩이 되는지 `Format-Hex scripts\run_quick_analyze.ps1 -Count 3`로 첫 3바이트가
`EF BB BF`인지 확인.)

- [ ] **Step 4: 수동 검증 (실제 비용 발생 — 워치리스트에 없는 종목 1개만)**

Run:
```powershell
New-Item -ItemType Directory -Force -Path data\adhoc | Out-Null
.\scripts\run_quick_analyze.ps1 -Type stocks_kr -Symbol 000270 -LogFile data\adhoc\_test.log -MaxBudgetUsd 1
Get-Content data\adhoc\_test.log
```
Expected: 로그에 `# 000270 즉시분석`으로 시작해 Chart/Ledger/Mood/Anchor 4개 섹션이 한글 깨짐 없이
출력됨. `data\adhoc\stocks_kr_000270.json`은 커맨드 4단계에서 자동 삭제되어 없어야 함. 확인 후
`Remove-Item data\adhoc\_test.log`.

- [ ] **Step 5: 커밋**

```bash
git add .claude/commands/quick-analyze.md scripts/run_quick_analyze.ps1
git commit -m "feat: 단일종목 즉시분석 슬래시커맨드와 실행 래퍼 추가"
```

---

### Task 5: 서버 엔드포인트 연결

**Files:**
- Modify: `scripts/serve_office.py`

**Interfaces:**
- Consumes: Task 2의 `recent_searches_store.load/add`, Task 3의 `symbol_universe.load_all/search_all`,
  Task 4의 `scripts/run_quick_analyze.ps1`.
- Produces:
  - `GET /api/symbols?q=<query>` → 200 `{"items": [...]}`
  - `POST /api/quick-analyze` body `{"type", "symbol"}` → 202 `{"status": "started"}` /
    400 `{"error": "..."}` / 409 `{"error": "이미 분석이 진행 중입니다."}`
  - `GET /api/quick-analyze/status` → 200 `{"status": "idle"}` |
    `{"status": "running", "type", "symbol"}` |
    `{"status": "done", "type", "symbol", "timestamp", "result_text"}` |
    `{"status": "error", "type", "symbol", "error"}`
  - `GET /api/recent-searches` → 200 `{"items": [...]}`

- [ ] **Step 1: import 및 상수 추가**

`scripts/serve_office.py` 상단 import 블록(파일 8~19번째 줄 부근)을 아래처럼 바꾼다:

```python
import json
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
OFFICE_DIR = ROOT / "office"
RUN_SCHEDULED_ANALYSIS_PS1 = ROOT / "scripts" / "run_scheduled_analysis.ps1"
RUN_QUICK_ANALYZE_PS1 = ROOT / "scripts" / "run_quick_analyze.ps1"
QUICK_ANALYZE_LOG = ROOT / "data" / "adhoc" / "_quick_analyze_output.log"
QUICK_ANALYZE_BUDGET = {"crypto": "2", "stocks_kr": "1", "stocks_us": "1"}

_analysis_process: subprocess.Popen | None = None
_quick_analyze_process: subprocess.Popen | None = None
_quick_analyze_meta: dict | None = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_crypto  # noqa: E402
import fetch_stocks_kr  # noqa: E402
import fetch_stocks_us  # noqa: E402
import recent_searches_store  # noqa: E402
import symbol_universe  # noqa: E402
import watchlist_store  # noqa: E402
from office_data import build_office_data  # noqa: E402
```

- [ ] **Step 2: `do_GET`/`do_POST` 라우팅 변경**

기존 `do_GET`(56~68번째 줄 부근)을 아래로 교체한다:

```python
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/" or path == "/index.html":
            self._serve_index()
        elif path == "/api/live":
            self._serve_live()
        elif path == "/api/watchlist":
            self._get_watchlist()
        elif path == "/api/symbols":
            self._search_symbols(parse_qs(parsed.query))
        elif path == "/api/quick-analyze/status":
            self._quick_analyze_status()
        elif path == "/api/recent-searches":
            self._get_recent_searches()
        else:
            self.send_error(404, "Not Found")
```

기존 `do_POST`(70~76번째 줄 부근)을 아래로 교체한다:

```python
    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/run-now":
            self._run_now()
        elif self.path == "/api/watchlist":
            self._add_watchlist_item()
        elif self.path == "/api/quick-analyze":
            self._start_quick_analyze()
        else:
            self.send_error(404, "Not Found")
```

- [ ] **Step 3: 신규 핸들러 메서드 추가**

`_delete_watchlist_item` 메서드 끝(기존 240번째 줄, `class OfficeHandler` 안, `def main()` 앞) 다음에
아래 메서드들을 추가한다:

```python
    def _search_symbols(self, query: dict) -> None:
        q = (query.get("q") or [""])[0]
        self._send_json(200, {"items": symbol_universe.search_all(q)})

    def _get_recent_searches(self) -> None:
        self._send_json(200, {"items": recent_searches_store.load()})

    def _start_quick_analyze(self) -> None:
        global _quick_analyze_process, _quick_analyze_meta
        try:
            body = self._read_json_body()
        except Exception:  # noqa: BLE001
            self._send_json(400, {"error": "잘못된 요청 형식입니다."})
            return

        type_ = body.get("type")
        symbol = str(body.get("symbol", "")).strip().upper()
        if type_ not in ("crypto", "stocks_kr", "stocks_us") or not symbol:
            self._send_json(400, {"error": "type과 symbol이 필요합니다."})
            return
        if _quick_analyze_process is not None and _quick_analyze_process.poll() is None:
            self._send_json(409, {"error": "이미 분석이 진행 중입니다."})
            return

        QUICK_ANALYZE_LOG.parent.mkdir(parents=True, exist_ok=True)
        if QUICK_ANALYZE_LOG.exists():
            QUICK_ANALYZE_LOG.unlink()

        _quick_analyze_process = subprocess.Popen(
            [
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(RUN_QUICK_ANALYZE_PS1),
                "-Type", type_, "-Symbol", symbol, "-LogFile", str(QUICK_ANALYZE_LOG),
                "-MaxBudgetUsd", QUICK_ANALYZE_BUDGET[type_],
            ],
            cwd=ROOT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        _quick_analyze_meta = {"type": type_, "symbol": symbol}
        self._send_json(202, {"status": "started"})

    def _quick_analyze_status(self) -> None:
        global _quick_analyze_process, _quick_analyze_meta
        if _quick_analyze_process is None:
            self._send_json(200, {"status": "idle"})
            return

        returncode = _quick_analyze_process.poll()
        if returncode is None:
            self._send_json(200, {"status": "running", **_quick_analyze_meta})
            return

        meta = _quick_analyze_meta
        _quick_analyze_process = None
        _quick_analyze_meta = None
        text = (
            QUICK_ANALYZE_LOG.read_text(encoding="utf-8", errors="replace").strip()
            if QUICK_ANALYZE_LOG.exists() else ""
        )

        if returncode != 0 or not text:
            error = text[-2000:] if text else f"프로세스 종료 코드 {returncode}"
            self._send_json(200, {"status": "error", **meta, "error": error})
            return

        entry = {**meta, "timestamp": datetime.now(timezone.utc).isoformat(), "result_text": text}
        recent_searches_store.add(entry)
        self._send_json(200, {"status": "done", **entry})
```

- [ ] **Step 4: 서버 시작 시 유니버스 로딩**

`main()` 함수(기존 243번째 줄 부근)를 아래로 교체한다:

```python
def main() -> None:
    print("종목 검색 자동완성 목록을 불러오는 중...")
    symbol_universe.load_all()

    updater = threading.Thread(target=price_update_loop, daemon=True)
    updater.start()

    server = ThreadingHTTPServer((HOST, PORT), OfficeHandler)
    url = f"http://{HOST}:{PORT}"
    print(f"AI 오피스 라이브 서버 시작: {url}")
    print("종료하려면 Ctrl+C 를 누르세요.")
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")
        server.shutdown()
```

- [ ] **Step 5: 수동 검증**

서버 시작(포그라운드로 켜두고, 별도 PowerShell 창에서 curl 테스트):
```powershell
python scripts\serve_office.py
```
다른 PowerShell 창에서:
```powershell
Invoke-RestMethod http://127.0.0.1:8787/api/symbols?q=BTC
Invoke-RestMethod http://127.0.0.1:8787/api/recent-searches
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8787/api/quick-analyze -ContentType "application/json" -Body '{"type":"stocks_kr","symbol":"000270"}'
Invoke-RestMethod http://127.0.0.1:8787/api/quick-analyze/status
```
Expected: `/api/symbols?q=BTC`에 크립토 BTC 포함된 items 반환. `/api/recent-searches`는 처음엔 빈 items.
quick-analyze POST는 `{"status":"started"}`(202). 곧바로 status 조회하면 `{"status":"running",...}`,
1~2분 후 다시 조회하면 `{"status":"done", "result_text": "..."}` 그리고 `data/recent_searches.json`에
항목이 추가됨. 두 번째 quick-analyze POST를 첫 번째가 끝나기 전에 보내면 409 확인. 서버는 Ctrl+C로 종료.

- [ ] **Step 6: 커밋**

```bash
git add scripts/serve_office.py
git commit -m "feat: 종목 검색/즉시분석/최근검색 API 엔드포인트 추가"
```

---

### Task 6: 프론트엔드 검색 UI

**Files:**
- Modify: `office/template.html`

**Interfaces:**
- Consumes: Task 5의 `/api/symbols`, `/api/quick-analyze`, `/api/quick-analyze/status`,
  `/api/recent-searches`. 기존 전역 함수 `openModal(emp)`(`emp.emoji`, `emp.name`, `emp.fullText` 사용)를
  그대로 재사용.

- [ ] **Step 1: CSS 추가**

`.watchlist-static-note { ... }` 규칙(기존 284번째 줄) 바로 다음에 추가:

```css
  .search-suggestions { position: relative; z-index: 5; margin-top: 6px; max-height: 260px; overflow-y: auto; border: 1px solid var(--border); border-radius: 10px; background: var(--panel-bg); }
  .search-suggestions[hidden] { display: none; }
  .search-suggestion-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; cursor: pointer; font-size: 0.82rem; }
  .search-suggestion-item:hover { background: var(--bg-bottom); }
  .search-suggestion-badge { font-size: 0.68rem; padding: 2px 8px; border-radius: 999px; background: var(--accent); color: white; white-space: nowrap; }
  .search-panel { display: grid; gap: 10px; background: var(--panel-bg); border: 1px solid var(--border); border-radius: 20px; padding: 16px 20px; margin-bottom: 20px; }
  .search-panel[hidden] { display: none; }
```

- [ ] **Step 2: 헤더에 토글 버튼 추가**

기존 헤더 버튼 영역(292~297번째 줄):

```html
    <div style="display:flex; gap:8px; align-items:center;">
      <button id="watchlist-toggle-btn" class="watchlist-toggle-btn" type="button">⚙ 관심종목 관리</button>
      <button id="run-now-btn" class="run-now-btn">지금 분석 받기</button>
    </div>
```

를 아래로 교체:

```html
    <div style="display:flex; gap:8px; align-items:center;">
      <button id="search-toggle-btn" class="watchlist-toggle-btn" type="button">🔍 종목 검색</button>
      <button id="watchlist-toggle-btn" class="watchlist-toggle-btn" type="button">⚙ 관심종목 관리</button>
      <button id="run-now-btn" class="run-now-btn">지금 분석 받기</button>
    </div>
```

- [ ] **Step 3: 검색 패널 마크업 추가**

기존 `</section>`(watchlist-panel 종료, 331번째 줄) 다음, `<div class="layout">`(333번째 줄) 앞에 추가:

```html
  <section class="search-panel" id="search-panel" hidden>
    <input id="search-input" class="watchlist-input" type="text"
           placeholder="종목/코인 검색 (심볼 또는 이름) — 워치리스트에 없어도 즉시분석" autocomplete="off" disabled>
    <div id="search-suggestions" class="search-suggestions" hidden></div>
    <div id="search-status" class="watchlist-error"></div>
    <div>
      <div class="watchlist-group-title">최근검색</div>
      <div id="recent-searches-chips" class="watchlist-chips"></div>
    </div>
    <div class="watchlist-static-note" id="search-static-note">
      ⚠ 라이브 뷰어(launch_live_office.bat 실행 후 localhost:8787)에서만 사용할 수 있습니다.
    </div>
  </section>
```

- [ ] **Step 4: JS 추가**

기존 `</script>`(720번째 줄, 워치리스트 JS 블록 마지막) 바로 앞에 추가:

```javascript
  const searchToggleBtn = document.getElementById('search-toggle-btn');
  const searchPanel = document.getElementById('search-panel');
  const searchInput = document.getElementById('search-input');
  const searchSuggestions = document.getElementById('search-suggestions');
  const searchStatus = document.getElementById('search-status');
  const searchStaticNote = document.getElementById('search-static-note');
  const recentSearchesChips = document.getElementById('recent-searches-chips');
  const SEARCH_TYPE_LABELS = { crypto: '크립토', stocks_kr: '국내주식', stocks_us: '해외주식' };
  let searchLoaded = false;
  let searchDebounceTimer = null;
  let quickAnalyzePollTimer = null;

  searchToggleBtn.addEventListener('click', () => {
    const willOpen = searchPanel.hidden;
    searchPanel.hidden = !willOpen;
    if (willOpen && !searchLoaded) loadRecentSearches();
  });

  function loadRecentSearches() {
    fetch('/api/recent-searches', { cache: 'no-store' })
      .then(r => (r.ok ? r.json() : Promise.reject()))
      .then(data => {
        searchLoaded = true;
        searchStaticNote.hidden = true;
        searchInput.disabled = false;
        renderRecentSearches(data.items || []);
      })
      .catch(() => {
        searchStaticNote.hidden = false;
        searchInput.disabled = true;
      });
  }

  function renderRecentSearches(items) {
    recentSearchesChips.innerHTML = '';
    items.forEach(item => {
      const chip = document.createElement('span');
      chip.className = 'watchlist-chip';
      chip.style.cursor = 'pointer';
      chip.textContent = `${SEARCH_TYPE_LABELS[item.type] || item.type} · ${item.symbol}`;
      chip.addEventListener('click', () => {
        openModal({ emoji: '🔍', name: `${item.symbol} 즉시분석`, fullText: item.result_text });
      });
      recentSearchesChips.appendChild(chip);
    });
  }

  searchInput.addEventListener('input', () => {
    clearTimeout(searchDebounceTimer);
    const q = searchInput.value.trim();
    if (!q) { searchSuggestions.hidden = true; return; }
    searchDebounceTimer = setTimeout(() => {
      fetch(`/api/symbols?q=${encodeURIComponent(q)}`, { cache: 'no-store' })
        .then(r => (r.ok ? r.json() : { items: [] }))
        .then(data => renderSuggestions(data.items || []))
        .catch(() => { searchSuggestions.hidden = true; });
    }, 250);
  });

  function renderSuggestions(items) {
    searchSuggestions.innerHTML = '';
    if (!items.length) { searchSuggestions.hidden = true; return; }
    items.forEach(item => {
      const row = document.createElement('div');
      row.className = 'search-suggestion-item';
      row.innerHTML =
        `<span class="search-suggestion-badge">${SEARCH_TYPE_LABELS[item.type] || item.type}</span>` +
        `<span>${item.symbol}</span><span style="color:var(--text-sub);">${item.name}</span>`;
      row.addEventListener('click', () => startQuickAnalyze(item));
      searchSuggestions.appendChild(row);
    });
    searchSuggestions.hidden = false;
  }

  function startQuickAnalyze(item) {
    searchSuggestions.hidden = true;
    searchInput.value = `${item.symbol} 분석 중... (수십초~수분 소요)`;
    searchInput.disabled = true;
    searchStatus.textContent = '';
    fetch('/api/quick-analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: item.type, symbol: item.symbol }),
    })
      .then(r => r.json().then(data => ({ ok: r.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) {
          searchInput.disabled = false;
          searchInput.value = '';
          searchStatus.textContent = data.error || '분석 시작 실패';
          return;
        }
        pollQuickAnalyze();
      })
      .catch(() => {
        searchInput.disabled = false;
        searchInput.value = '';
        searchStatus.textContent = '요청 실패';
      });
  }

  function pollQuickAnalyze() {
    clearTimeout(quickAnalyzePollTimer);
    fetch('/api/quick-analyze/status', { cache: 'no-store' })
      .then(r => r.json())
      .then(data => {
        if (data.status === 'running') {
          quickAnalyzePollTimer = setTimeout(pollQuickAnalyze, 5000);
          return;
        }
        searchInput.disabled = false;
        searchInput.value = '';
        if (data.status === 'done') {
          openModal({ emoji: '🔍', name: `${data.symbol} 즉시분석`, fullText: data.result_text });
          loadRecentSearches();
        } else if (data.status === 'error') {
          searchStatus.textContent = `분석 실패: ${data.error}`;
        }
      })
      .catch(() => {
        quickAnalyzePollTimer = setTimeout(pollQuickAnalyze, 5000);
      });
  }

  document.addEventListener('click', (e) => {
    if (!searchSuggestions.contains(e.target) && e.target !== searchInput) {
      searchSuggestions.hidden = true;
    }
  });
```

- [ ] **Step 5: 수동 검증 (브라우저)**

```powershell
python scripts\serve_office.py
```
브라우저에서 `http://127.0.0.1:8787` 확인:
1. "🔍 종목 검색" 클릭 → 패널 열림, 입력창 활성화, "최근검색" 비어있음.
2. "삼성" 입력 → 자동완성에 국내주식 뱃지로 삼성전자류 후보 표시되는지 확인(1~2초 디바운스 후).
3. 후보 하나 클릭(워치리스트에 없는 종목으로) → 입력창이 "분석 중..."으로 바뀌고 비활성화됨 → 수십초~
   수분 후 모달 팝업으로 결과(헤딩/문단) 표시되는지 확인.
4. 패널을 닫았다 다시 열면 최근검색 칩에 방금 종목이 추가돼있는지, 클릭 시 재분석 없이 즉시 모달이
   뜨는지 확인.
5. `office\index.html`(정적 스냅샷, 서버 없이 더블클릭)을 열어 검색창이 비활성 + "라이브 뷰어 전용"
   안내가 보이는지 확인.

- [ ] **Step 6: 커밋**

```bash
git add office/template.html
git commit -m "feat: 종목 검색/즉시분석 UI 추가"
```

---

## Self-Review 결과

- **스펙 커버리지**: design spec의 아키텍처/자동완성 소스/파이프라인/프론트엔드/에러처리/검증 섹션 모두
  Task 1~6에 매핑됨. 해외주식 유니버스는 "S&P500만 사용"으로 스펙 대비 단순화했고, 그 이유와 업그레이드
  경로를 `symbol_universe.py`의 `ponytail:` 주석으로 명시함.
- **플레이스홀더 스캔**: TBD/TODO 없음, 모든 스텝에 실행 가능한 실제 코드/명령 포함.
- **타입/시그니처 일관성**: `fetch_one`/`load`/`add`/`load_all`/`search`/`search_all`의 이름과 반환
  타입이 Task 1→3→5→6에서 동일하게 사용됨을 확인. `/api/quick-analyze/status`의 응답 필드명
  (`type`/`symbol`/`result_text`/`error`)이 서버(Task 5)와 프론트(Task 6)에서 일치.

# 관심종목 웹 등록/삭제 기능 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 라이브 오피스(`http://127.0.0.1:8787`)의 헤더에 관심종목 관리 패널을 추가해, 코인/국내주식/해외주식을
심볼·코드만 입력해 즉시 검증·추가하거나 삭제할 수 있게 한다.

**Architecture:** `config/watchlist.yaml`을 공용 헬퍼(`scripts/watchlist_store.py`)로 읽고 쓰며,
`serve_office.py`에 `GET/POST/DELETE /api/watchlist` 3개 엔드포인트를 추가한다. 추가/삭제 시 해당
자산군의 기존 `fetch_*.main()`을 그대로 재실행해 오늘자 데이터 파일을 전체 갱신한다(부분 병합 없음).
`office/template.html`에 헤더 토글 패널 UI를 추가하고, 정적 스냅샷(`office/index.html`)에서는
"라이브 뷰어 전용" 안내만 보이게 한다.

**Tech Stack:** Python 표준 라이브러리(`http.server`), PyYAML, requests, BeautifulSoup, yfinance
(모두 기존 의존성, 신규 추가 없음), 순수 JS(프레임워크 없음).

## Global Constraints

- 스펙: `docs/superpowers/specs/2026-08-09-watchlist-editor-design.md`
- 이 저장소는 자동 테스트 프레임워크가 없다(기존 두 계획과 동일 컨벤션) — 각 태스크는 "수동 실행 확인"
  스텝으로 검증한다.
- 정적 스냅샷(`office/index.html`)에서는 패널의 입력창/버튼이 비활성 상태이고 "라이브 뷰어 전용" 안내만
  표시된다 — `/api/watchlist` fetch가 실패(정적 파일이라 서버 없음)하면 그 상태로 전환.
- 크립토 추가 검증은 업비트/바이빗 중 하나만 성공해도 통과, 실패한 거래소는 warning으로만 표시(스펙
  §데이터 흐름 참고).
- 중복 판정은 대소문자 구분 없이 정규화한 키로 비교한다(크립토: symbol, 국내주식: code, 해외주식: ticker).
- 삭제는 확인 팝업 없이 클릭 즉시 실행된다.
- 이 기능은 매수/매도 시그널이 아니다 — 관심종목 등록/삭제일 뿐이며 기존 매매 금지 제약과 무관하다.
- 워치리스트 편집과 예약 작업(시간별/전체분석) 간 파일 쓰기 동시성 보호는 이번 범위에 포함하지 않는다.

---

### Task 1: `scripts/watchlist_store.py` 신규 — watchlist.yaml 읽기/쓰기 헬퍼

**Files:**
- Create: `scripts/watchlist_store.py`

**Interfaces:**
- Consumes: `config/watchlist.yaml` (기존 파일, 스키마 변경 없음)
- Produces: `load() -> dict`, `save(data: dict) -> None`, `find(data: dict, type_: str, key: str) -> dict | None`,
  `add(data: dict, type_: str, entry: dict) -> None`, `remove(data: dict, type_: str, key: str) -> bool`.
  Task 4(`serve_office.py`)가 이 5개 함수를 그대로 가져다 쓴다.

- [ ] **Step 1: `scripts/watchlist_store.py` 작성**

```python
"""config/watchlist.yaml 읽기/쓰기 공용 헬퍼.
파일 상단 안내 주석은 고정 문자열로 유지하고, 그 아래 데이터만 다시 쓴다.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "watchlist.yaml"

HEADER = (
    "# 관심 종목/코인 목록\n"
    "# 자유롭게 추가/삭제하세요. 심볼은 아래 형식을 따릅니다.\n"
    "\n"
)

ID_FIELDS = {"crypto": "symbol", "stocks_kr": "code", "stocks_us": "ticker"}


def load() -> dict:
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    for key in ("crypto", "stocks_kr", "stocks_us"):
        data.setdefault(key, [])
    return data


def save(data: dict) -> None:
    body = yaml.safe_dump(
        data, sort_keys=False, allow_unicode=True, default_flow_style=False
    )
    CONFIG_PATH.write_text(HEADER + body, encoding="utf-8")


def find(data: dict, type_: str, key: str) -> dict | None:
    field = ID_FIELDS[type_]
    key_norm = key.strip().upper()
    for item in data[type_]:
        if str(item[field]).strip().upper() == key_norm:
            return item
    return None


def add(data: dict, type_: str, entry: dict) -> None:
    data[type_].append(entry)


def remove(data: dict, type_: str, key: str) -> bool:
    field = ID_FIELDS[type_]
    key_norm = key.strip().upper()
    before = len(data[type_])
    data[type_] = [
        item for item in data[type_] if str(item[field]).strip().upper() != key_norm
    ]
    return len(data[type_]) < before
```

- [ ] **Step 2: 수동 실행으로 검증**

Run:
```
python -c "import sys; sys.path.insert(0,'scripts'); import watchlist_store as w; d=w.load(); print(d['crypto']); print(w.find(d,'crypto','btc'))"
```
Expected: `d['crypto']`에 기존 BTC/ETH 항목이 나오고(`config/watchlist.yaml` 현재 내용과 일치), `find(d,'crypto','btc')`가 소문자 입력에도 BTC 항목을 대소문자 무시하고 찾아 반환한다(`None`이 아님).

- [ ] **Step 3: `save()` 왕복 검증 (원본 훼손 여부 확인)**

Run:
```
python -c "
import sys; sys.path.insert(0,'scripts')
import watchlist_store as w
before = w.CONFIG_PATH.read_text(encoding='utf-8')
d = w.load()
w.save(d)
after = w.CONFIG_PATH.read_text(encoding='utf-8')
print('상단 주석 유지:', after.startswith(w.HEADER))
print('데이터 동일:', w.load() == d)
"
```
Expected: `상단 주석 유지: True`, `데이터 동일: True`. 이후 `git diff config/watchlist.yaml`로 실제 종목
데이터에 변화가 없는지(주석 위치/줄바꿈 정도만 바뀔 수 있음) 확인.

- [ ] **Step 4: Commit**

```bash
git add scripts/watchlist_store.py
git commit -m "feat: watchlist.yaml 읽기/쓰기 헬퍼 추가"
```

---

### Task 2: `scripts/fetch_stocks_kr.py` — 국내주식 이름 자동조회 함수 추가

**Files:**
- Modify: `scripts/fetch_stocks_kr.py` (기존 `fetch_fundamentals` 함수 아래에 새 함수 추가, 기존 함수는
  건드리지 않음 — `main()`이 쓰는 기존 경로에 회귀 위험 없음)

**Interfaces:**
- Consumes: 없음 (네이버 금융 페이지 직접 조회)
- Produces: `fetch_name_and_fundamentals(code: str) -> dict` (키: `name`, `per`, `pbr`). 실패 시
  `ValueError` 발생. Task 4(`serve_office.py`)가 국내주식 추가 검증에 이 함수를 사용.

- [ ] **Step 1: `fetch_fundamentals` 함수 정의 바로 아래에 새 함수 추가**

`scripts/fetch_stocks_kr.py`의 `def fetch_fundamentals(code: str) -> dict:` 함수(현재 43~64줄) 바로
다음, `def main() -> None:` 정의 이전에 아래 함수를 추가한다.

```python
def fetch_name_and_fundamentals(code: str) -> dict:
    """관심종목 추가 시 사용: 종목명 + PER/PBR을 한 번의 요청으로 함께 조회한다."""
    resp = requests.get(
        f"https://finance.naver.com/item/main.naver?code={code}",
        headers=HEADERS,
        timeout=10,
    )
    resp.encoding = "euc-kr"
    soup = BeautifulSoup(resp.text, "html.parser")

    def parse_num(el):
        if not el:
            return None
        text = el.text.strip().replace(",", "")
        try:
            return float(text)
        except ValueError:
            return None

    title = soup.title.text if soup.title else ""
    name = title.split(":")[0].strip() if ":" in title else title.strip()
    if not name:
        raise ValueError("종목명을 확인할 수 없습니다 (잘못된 코드일 수 있음)")

    return {
        "name": name,
        "per": parse_num(soup.select_one("#_per")),
        "pbr": parse_num(soup.select_one("#_pbr")),
    }
```

- [ ] **Step 2: 수동 실행으로 검증 (실존 코드)**

Run:
```
python -c "import sys; sys.path.insert(0,'scripts'); from fetch_stocks_kr import fetch_name_and_fundamentals as f; print(f('005930'))"
```
Expected: `{'name': '삼성전자', 'per': ..., 'pbr': ...}` 형태로 출력(숫자는 그날 시세에 따라 다름).

- [ ] **Step 3: 잘못된 코드로 실패 케이스 검증**

Run:
```
python -c "import sys; sys.path.insert(0,'scripts'); from fetch_stocks_kr import fetch_name_and_fundamentals as f; f('999999')"
```
Expected: `ValueError: 종목명을 확인할 수 없습니다 (잘못된 코드일 수 있음)` 예외 발생 (존재하지 않는 코드라
네이버 페이지에 정상 제목이 없음).

- [ ] **Step 4: Commit**

```bash
git add scripts/fetch_stocks_kr.py
git commit -m "feat: 국내주식 종목명 자동조회 함수 추가"
```

---

### Task 3: `scripts/fetch_stocks_us.py` — 해외주식 이름 자동조회 함수 추가

**Files:**
- Modify: `scripts/fetch_stocks_us.py` (기존 `fetch_recent` 함수 위에 새 함수 추가)

**Interfaces:**
- Consumes: 없음 (yfinance 직접 조회)
- Produces: `fetch_name(ticker: str) -> str`. 실패 시 `ValueError` 발생. Task 4가 해외주식 추가 검증에 사용.

- [ ] **Step 1: `fetch_recent` 함수 정의 바로 위에 새 함수 추가**

`scripts/fetch_stocks_us.py`의 `def fetch_recent(ticker: str) -> dict:` 함수(현재 18줄) 바로 위에 추가.

```python
def fetch_name(ticker: str) -> str:
    """관심종목 추가 시 사용: 티커로 회사명을 조회한다."""
    info = yf.Ticker(ticker).info
    name = info.get("shortName") or info.get("longName")
    if not name:
        raise ValueError("종목명을 확인할 수 없습니다 (잘못된 티커일 수 있음)")
    return name
```

- [ ] **Step 2: 수동 실행으로 검증 (실존 티커)**

Run:
```
python -c "import sys; sys.path.insert(0,'scripts'); from fetch_stocks_us import fetch_name; print(fetch_name('TSLA'))"
```
Expected: `Tesla, Inc.` 또는 이와 유사한 회사명 문자열 출력.

- [ ] **Step 3: 잘못된 티커로 실패 케이스 검증**

Run:
```
python -c "import sys; sys.path.insert(0,'scripts'); from fetch_stocks_us import fetch_name; fetch_name('ZZZZZZINVALID')"
```
Expected: `ValueError: 종목명을 확인할 수 없습니다 (잘못된 티커일 수 있음)` 예외 발생.

- [ ] **Step 4: Commit**

```bash
git add scripts/fetch_stocks_us.py
git commit -m "feat: 해외주식 종목명 자동조회 함수 추가"
```

---

### Task 4: `scripts/serve_office.py` — `/api/watchlist` 엔드포인트 3개 추가

**Files:**
- Modify: `scripts/serve_office.py`

**Interfaces:**
- Consumes: Task 1의 `watchlist_store.{load,save,find,add,remove}`, Task 2의
  `fetch_stocks_kr.fetch_name_and_fundamentals`, Task 3의 `fetch_stocks_us.fetch_name`, 기존
  `fetch_crypto.fetch_upbit`/`fetch_crypto.fetch_bybit`(이미 `scripts/fetch_crypto.py`에 정의돼 있음,
  수정 불필요), 기존 `fetch_stocks_us.fetch_recent`.
- Produces: `GET /api/watchlist` → `{crypto: [...], stocks_kr: [...], stocks_us: [...]}` JSON.
  `POST /api/watchlist` (body `{type, symbol}`) → 성공 시 202 `{name, status:"ok"[, warning]}`, 실패 시
  400 `{error}`. `DELETE /api/watchlist` (body `{type, symbol}`) → 성공 시 200 `{status:"ok"}`, 실패 시
  400/404 `{error}`. Task 5(`office/template.html`)가 이 3개를 그대로 호출한다.

- [ ] **Step 1: import 구간에 `watchlist_store` 추가**

`scripts/serve_office.py` 24~27줄:
```python
import fetch_crypto  # noqa: E402
import fetch_stocks_kr  # noqa: E402
import fetch_stocks_us  # noqa: E402
from office_data import build_office_data  # noqa: E402
```
을 아래로 교체:
```python
import fetch_crypto  # noqa: E402
import fetch_stocks_kr  # noqa: E402
import fetch_stocks_us  # noqa: E402
import watchlist_store  # noqa: E402
from office_data import build_office_data  # noqa: E402
```

- [ ] **Step 2: 라우팅에 `/api/watchlist` 추가 + `do_DELETE` 메서드 신설**

`do_GET`(현재 59~65줄)을 아래로 교체:
```python
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/" or self.path == "/index.html":
            self._serve_index()
        elif self.path == "/api/live":
            self._serve_live()
        elif self.path == "/api/watchlist":
            self._get_watchlist()
        else:
            self.send_error(404, "Not Found")
```

`do_POST`(현재 67~71줄)를 아래로 교체:
```python
    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/run-now":
            self._run_now()
        elif self.path == "/api/watchlist":
            self._add_watchlist_item()
        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self) -> None:  # noqa: N802
        if self.path == "/api/watchlist":
            self._delete_watchlist_item()
        else:
            self.send_error(404, "Not Found")
```

- [ ] **Step 3: 공용 JSON 헬퍼 + 3개 핸들러 메서드 추가**

`_serve_live` 메서드(현재 104~114줄) 바로 다음에 아래 메서드들을 추가한다.

```python
    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw or b"{}")

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _get_watchlist(self) -> None:
        self._send_json(200, watchlist_store.load())

    def _add_watchlist_item(self) -> None:
        try:
            body = self._read_json_body()
        except Exception:  # noqa: BLE001
            self._send_json(400, {"error": "잘못된 요청 형식입니다."})
            return

        type_ = body.get("type")
        symbol = str(body.get("symbol", "")).strip()
        if type_ not in ("crypto", "stocks_kr", "stocks_us") or not symbol:
            self._send_json(400, {"error": "type과 symbol이 필요합니다."})
            return

        data = watchlist_store.load()
        if watchlist_store.find(data, type_, symbol):
            self._send_json(400, {"error": "이미 등록된 종목입니다."})
            return

        warning = None
        try:
            if type_ == "crypto":
                sym = symbol.upper()
                upbit_market = f"KRW-{sym}"
                bybit_symbol = f"{sym}USDT"
                upbit_ok = bybit_ok = False
                try:
                    fetch_crypto.fetch_upbit(upbit_market)
                    upbit_ok = True
                except Exception:  # noqa: BLE001
                    pass
                try:
                    fetch_crypto.fetch_bybit(bybit_symbol)
                    bybit_ok = True
                except Exception:  # noqa: BLE001
                    pass
                if not upbit_ok and not bybit_ok:
                    self._send_json(400, {"error": f"{sym}: 업비트/바이빗 모두 조회 실패"})
                    return
                if not bybit_ok:
                    warning = "바이빗 미지원 (업비트만 조회됨)"
                elif not upbit_ok:
                    warning = "업비트 미지원 (바이빗만 조회됨)"
                name = sym
                watchlist_store.add(
                    data, "crypto",
                    {"symbol": sym, "upbit_market": upbit_market, "bybit_symbol": bybit_symbol},
                )
                watchlist_store.save(data)
                fetch_crypto.main()
            elif type_ == "stocks_kr":
                info = fetch_stocks_kr.fetch_name_and_fundamentals(symbol)
                name = info["name"]
                watchlist_store.add(data, "stocks_kr", {"name": name, "code": symbol})
                watchlist_store.save(data)
                fetch_stocks_kr.main()
            else:  # stocks_us
                ticker = symbol.upper()
                name = fetch_stocks_us.fetch_name(ticker)
                fetch_stocks_us.fetch_recent(ticker)
                watchlist_store.add(data, "stocks_us", {"name": name, "ticker": ticker})
                watchlist_store.save(data)
                fetch_stocks_us.main()
        except Exception as exc:  # noqa: BLE001
            self._send_json(400, {"error": f"종목 조회 실패: {exc}"})
            return

        payload = {"name": name, "status": "ok"}
        if warning:
            payload["warning"] = warning
        self._send_json(202, payload)

    def _delete_watchlist_item(self) -> None:
        try:
            body = self._read_json_body()
        except Exception:  # noqa: BLE001
            self._send_json(400, {"error": "잘못된 요청 형식입니다."})
            return

        type_ = body.get("type")
        symbol = str(body.get("symbol", "")).strip()
        if type_ not in ("crypto", "stocks_kr", "stocks_us") or not symbol:
            self._send_json(400, {"error": "type과 symbol이 필요합니다."})
            return

        data = watchlist_store.load()
        if not watchlist_store.remove(data, type_, symbol):
            self._send_json(404, {"error": "등록되지 않은 종목입니다."})
            return
        watchlist_store.save(data)

        if type_ == "crypto":
            fetch_crypto.main()
        elif type_ == "stocks_kr":
            fetch_stocks_kr.main()
        else:
            fetch_stocks_us.main()

        self._send_json(200, {"status": "ok"})
```

- [ ] **Step 4: 수동 실행으로 검증 — 조회/추가/중복/삭제**

Run: `python scripts\serve_office.py` (서버가 뜨고 브라우저가 자동으로 열림 — 창은 열어둔 채로 아래를
별도 터미널에서 실행)

```
curl http://127.0.0.1:8787/api/watchlist
curl -X POST http://127.0.0.1:8787/api/watchlist -H "Content-Type: application/json" -d "{\"type\":\"stocks_us\",\"symbol\":\"TSLA\"}"
curl -X POST http://127.0.0.1:8787/api/watchlist -H "Content-Type: application/json" -d "{\"type\":\"stocks_us\",\"symbol\":\"TSLA\"}"
curl -X DELETE http://127.0.0.1:8787/api/watchlist -H "Content-Type: application/json" -d "{\"type\":\"stocks_us\",\"symbol\":\"TSLA\"}"
curl http://127.0.0.1:8787/api/watchlist
```
Expected: 1번째 GET에 TSLA 없음 → POST 성공(202, `{"name":"Tesla, Inc.","status":"ok"}`) → 2번째 동일
POST는 400 "이미 등록된 종목입니다" → DELETE는 200 `{"status":"ok"}` → 마지막 GET에 TSLA 다시 없음.
`data\stocks_us_오늘날짜.json`도 추가 시점에 TSLA를 포함해 갱신됐다가 삭제 시점에 다시 빠지는지 확인.

- [ ] **Step 5: Commit**

```bash
git add scripts/serve_office.py
git commit -m "feat: 라이브 서버에 관심종목 추가/삭제 API 추가"
```

---

### Task 5: `office/template.html` — 헤더 관심종목 관리 패널

**Files:**
- Modify: `office/template.html`

**Interfaces:**
- Consumes: Task 4의 `GET/POST/DELETE /api/watchlist`
- Produces: 없음 (UI 전용)

- [ ] **Step 1: 헤더에 토글 버튼 추가**

`office/template.html` 261~267줄의 `<header class="topbar">` 블록을 아래로 교체:

```html
  <header class="topbar">
    <div class="brand">
      <h1 id="office-title">나의 AI 투자 오피스</h1>
      <div class="meta" id="office-meta">불러오는 중...</div>
    </div>
    <div style="display:flex; gap:8px; align-items:center;">
      <button id="watchlist-toggle-btn" class="watchlist-toggle-btn" type="button">⚙ 관심종목 관리</button>
      <button id="run-now-btn" class="run-now-btn">지금 분석 받기</button>
    </div>
  </header>

  <section class="watchlist-panel" id="watchlist-panel" hidden>
    <div class="watchlist-group" data-type="crypto">
      <div class="watchlist-group-title">크립토 (심볼, 예: SOL)</div>
      <div class="watchlist-add-row">
        <input class="watchlist-input" type="text" placeholder="심볼 (예: SOL)" disabled>
        <button class="watchlist-add-btn" type="button" disabled>추가</button>
      </div>
      <div class="watchlist-error"></div>
      <div class="watchlist-chips"></div>
    </div>
    <div class="watchlist-group" data-type="stocks_kr">
      <div class="watchlist-group-title">국내주식 (6자리 코드, 예: 005930)</div>
      <div class="watchlist-add-row">
        <input class="watchlist-input" type="text" placeholder="코드 (예: 005930)" disabled>
        <button class="watchlist-add-btn" type="button" disabled>추가</button>
      </div>
      <div class="watchlist-error"></div>
      <div class="watchlist-chips"></div>
    </div>
    <div class="watchlist-group" data-type="stocks_us">
      <div class="watchlist-group-title">해외주식 (티커, 예: TSLA)</div>
      <div class="watchlist-add-row">
        <input class="watchlist-input" type="text" placeholder="티커 (예: TSLA)" disabled>
        <button class="watchlist-add-btn" type="button" disabled>추가</button>
      </div>
      <div class="watchlist-error"></div>
      <div class="watchlist-chips"></div>
    </div>
    <div class="watchlist-static-note" id="watchlist-static-note">
      ⚠ 라이브 뷰어(launch_live_office.bat 실행 후 localhost:8787)에서만 사용할 수 있습니다.
    </div>
  </section>
```

(정적 스냅샷에서는 `#watchlist-static-note`가 기본으로 보이고, 라이브 서버 응답을 받으면 JS가 숨긴다 —
입력창/버튼도 기본 `disabled`, 라이브 응답을 받아야 활성화된다.)

- [ ] **Step 2: CSS 추가**

`office/template.html`의 `</style>` 태그(현재 257줄) 바로 앞에 추가:

```css
  .watchlist-toggle-btn {
    border: 1px solid var(--border); border-radius: 999px; padding: 10px 16px; font-size: 0.85rem; font-weight: 600;
    background: transparent; color: var(--text-main); cursor: pointer;
  }
  .watchlist-panel {
    max-width: 1180px; margin: 0 auto 20px; background: var(--panel-bg); border: 1px solid var(--border);
    border-radius: 20px; padding: 18px 24px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px;
    backdrop-filter: blur(6px); box-shadow: 0 6px 20px rgba(0,0,0,0.08);
  }
  .watchlist-panel[hidden] { display: none; }
  @media (max-width: 860px) { .watchlist-panel { grid-template-columns: 1fr; } }
  .watchlist-group-title { font-size: 0.78rem; font-weight: 700; color: var(--text-sub); margin-bottom: 8px; }
  .watchlist-add-row { display: flex; gap: 6px; margin-bottom: 6px; }
  .watchlist-input { flex: 1; min-width: 0; padding: 6px 10px; border-radius: 999px; border: 1px solid var(--border); background: var(--bg-bottom); color: var(--text-main); font-size: 0.82rem; }
  .watchlist-add-btn { border: none; border-radius: 999px; padding: 6px 12px; font-size: 0.78rem; font-weight: 600; background: var(--accent); color: white; cursor: pointer; }
  .watchlist-add-btn:disabled, .watchlist-input:disabled { opacity: 0.5; cursor: default; }
  .watchlist-error { color: #e0574f; font-size: 0.74rem; min-height: 1em; margin-bottom: 6px; }
  .watchlist-chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .watchlist-chip { display: inline-flex; align-items: center; gap: 4px; background: var(--bg-bottom); border: 1px solid var(--border); border-radius: 999px; padding: 3px 6px 3px 10px; font-size: 0.76rem; }
  .watchlist-chip button { border: none; background: none; cursor: pointer; color: var(--text-sub); font-size: 0.8rem; padding: 0 2px; }
  .watchlist-static-note { grid-column: 1 / -1; color: var(--text-sub); font-size: 0.8rem; }
```

- [ ] **Step 3: JS 추가 — 패널 토글/조회/추가/삭제**

`office/template.html`의 `runBtn.addEventListener(...)` 블록(현재 533~544줄) 바로 다음, `</script>`
태그 앞에 추가:

```javascript
  const watchlistToggleBtn = document.getElementById('watchlist-toggle-btn');
  const watchlistPanel = document.getElementById('watchlist-panel');
  const watchlistStaticNote = document.getElementById('watchlist-static-note');
  const WATCHLIST_TYPES = ['crypto', 'stocks_kr', 'stocks_us'];
  const WATCHLIST_ID_FIELD = { crypto: 'symbol', stocks_kr: 'code', stocks_us: 'ticker' };
  let watchlistLoaded = false;

  watchlistToggleBtn.addEventListener('click', () => {
    const willOpen = watchlistPanel.hidden;
    watchlistPanel.hidden = !willOpen;
    if (willOpen && !watchlistLoaded) loadWatchlist();
  });

  function setWatchlistInputsEnabled(enabled) {
    WATCHLIST_TYPES.forEach(type => {
      const group = document.querySelector(`.watchlist-group[data-type="${type}"]`);
      group.querySelector('.watchlist-input').disabled = !enabled;
      group.querySelector('.watchlist-add-btn').disabled = !enabled;
    });
  }

  function renderChips(type, items) {
    const chipsEl = document.querySelector(`.watchlist-group[data-type="${type}"] .watchlist-chips`);
    const idField = WATCHLIST_ID_FIELD[type];
    chipsEl.innerHTML = '';
    items.forEach(item => {
      const chip = document.createElement('span');
      chip.className = 'watchlist-chip';
      chip.innerHTML = `${item.name || item.symbol}<button type="button">✕</button>`;
      chip.querySelector('button').addEventListener('click', () => deleteWatchlistItem(type, item[idField]));
      chipsEl.appendChild(chip);
    });
  }

  function loadWatchlist() {
    fetch('/api/watchlist', { cache: 'no-store' })
      .then(r => (r.ok ? r.json() : Promise.reject()))
      .then(data => {
        watchlistLoaded = true;
        watchlistStaticNote.hidden = true;
        setWatchlistInputsEnabled(true);
        WATCHLIST_TYPES.forEach(type => renderChips(type, data[type] || []));
      })
      .catch(() => {
        watchlistStaticNote.hidden = false;
        setWatchlistInputsEnabled(false);
      });
  }

  function addWatchlistItem(type) {
    const group = document.querySelector(`.watchlist-group[data-type="${type}"]`);
    const input = group.querySelector('.watchlist-input');
    const btn = group.querySelector('.watchlist-add-btn');
    const errorEl = group.querySelector('.watchlist-error');
    const symbol = input.value.trim();
    errorEl.textContent = '';
    if (!symbol) return;
    btn.disabled = true;
    fetch('/api/watchlist', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type, symbol }),
    })
      .then(r => r.json().then(data => ({ ok: r.ok, data })))
      .then(({ ok, data }) => {
        btn.disabled = false;
        if (!ok) { errorEl.textContent = data.error || '추가 실패'; return; }
        input.value = '';
        errorEl.textContent = data.warning || '';
        loadWatchlist();
        pollLive();
      })
      .catch(() => { btn.disabled = false; errorEl.textContent = '요청 실패'; });
  }

  function deleteWatchlistItem(type, symbol) {
    fetch('/api/watchlist', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type, symbol }),
    })
      .then(() => { loadWatchlist(); pollLive(); })
      .catch(() => {});
  }

  WATCHLIST_TYPES.forEach(type => {
    const group = document.querySelector(`.watchlist-group[data-type="${type}"]`);
    group.querySelector('.watchlist-add-btn').addEventListener('click', () => addWatchlistItem(type));
    group.querySelector('.watchlist-input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') addWatchlistItem(type);
    });
  });
```

- [ ] **Step 4: `generate_office.py`로 정적 스냅샷 재생성 후 더블클릭 버전 확인**

Run: `python scripts\generate_office.py`, 이후 `office\index.html` 더블클릭.
Expected: 헤더에 "⚙ 관심종목 관리" 버튼이 보이고 클릭하면 패널이 펼쳐지되, 안내 문구("라이브 뷰어에서만
사용할 수 있습니다")만 보이고 입력창/추가 버튼은 비활성(회색, 클릭 안 됨) 상태다.

- [ ] **Step 5: `serve_office.py`로 라이브 버전 확인**

Run: `python scripts\serve_office.py`, 브라우저에서 "⚙ 관심종목 관리" 클릭.
Expected: 안내 문구는 숨겨지고, 기존 등록된 종목들이 칩으로 보이며 입력창이 활성 상태. 크립토 그룹에
"SOL" 입력 후 추가 → 몇 초 후 칩 목록에 "SOL" 추가되고 에러 없음. 국내주식 그룹에 "000270" 입력 후
추가 → "기아" 칩 추가. 칩의 ✕ 클릭 → 즉시 목록에서 사라짐. 잘못된 값(예: 크립토에 "ZZZZZ") 입력 시
입력창 아래 빨간 에러 메시지만 뜨고 칩은 추가되지 않음.

- [ ] **Step 6: Commit**

```bash
git add office/template.html
git commit -m "feat: 오피스 헤더에 관심종목 관리 패널 추가"
```

---

### Task 6: 엔드투엔드 수동 검증

**Files:** 없음(검증 전용)

- [ ] **Step 1: 전체 플로우 재확인**

`python scripts\serve_office.py` 실행 후, 코인/국내주식/해외주식 각 1개씩 새로 추가 → 화면·
`config/watchlist.yaml`·오늘자 `data/*.json` 세 곳 모두 반영 확인 → 추가한 3개 모두 삭제 → 세 곳
모두 원상복구 확인.

- [ ] **Step 2: 거래소 한쪽만 지원하는 코인 경고 확인 (스펙 §데이터 흐름 크립토 케이스)**

업비트에는 있지만 바이빗에는 없는(또는 그 반대) 원화마켓 전용 알트코인을 하나 골라 추가 시도한다
(예: 바이빗 상장이 안 된 국내 전용 코인 — 실제 상장 현황은 시점마다 다르므로 추가 전 두 거래소
현황을 확인하고 적절한 예시를 고른다). Expected: 추가는 성공(202)하되 응답의 `warning` 필드에
"바이빗 미지원" 또는 "업비트 미지원" 문구가 담기고, 화면에도 그 경고가 표시된다.

- [ ] **Step 3: 기존 기능 회귀 확인**

"지금 분석 받기" 버튼이 여전히 정상 동작하는지(202 응답 후 "분석 중..." 표시) 확인 — Task 4에서
`do_GET`/`do_POST`를 통째로 교체했으므로 기존 `/api/live`, `/api/run-now` 라우팅이 안 깨졌는지 함께
확인한다.

- [ ] **Step 4: `git status`로 의도한 파일만 변경됐는지 확인**

Run: `git status --short`
Expected: `scripts/watchlist_store.py`(신규), `scripts/fetch_stocks_kr.py`,
`scripts/fetch_stocks_us.py`, `scripts/serve_office.py`, `office/template.html`, `office/index.html`
(재생성된 스냅샷)만 변경 목록에 있고, `config/watchlist.yaml`은 테스트 중 추가했다가 다시 삭제했다면
원래 상태로 깨끗해야 한다.

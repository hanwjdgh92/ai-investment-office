# 매매일지(Trading Journal) 웹앱 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 크립토 실제 매매 내역을 기록하고 FIFO로 손익/승률을 자동 계산해 보여주는, 서버 없는 로컬 전용 웹앱을 만든다.

**Architecture:** `trading-journal/` 폴더에 정적 파일만 둔다. 손익 매칭 로직(`fifo.js`)은 DOM/브라우저 API에
의존하지 않는 순수 함수로 분리해 Node 내장 테스트러너로 자동 검증한다. 나머지(`db.js`, `app.js`)는
IndexedDB/DOM 글루 코드로 브라우저에서 수동 검증한다. `launch.bat`이 `python -m http.server`로
`http://127.0.0.1:8788`을 띄워 file:// IndexedDB 차단 문제를 피한다.

**Tech Stack:** 순수 HTML/CSS/JS(ES modules), 브라우저 내장 IndexedDB, Node.js 내장 테스트러너(`node --test`),
Python 표준 라이브러리 `http.server`. 신규 의존성/빌드툴/프레임워크 없음.

## Global Constraints

- 신규 npm/pip 패키지 설치 금지 — 표준 라이브러리/브라우저 내장 API만 사용.
- 빌드 스텝 없음 — 브라우저가 그대로 로드할 수 있는 HTML/CSS/JS.
- 서버 커스텀 코드 작성 금지 — 파일 서빙은 `python -m http.server` 한 줄만 사용.
- 화면 텍스트는 한국어.
- 크립토 자산군만 지원(국내/해외주식 없음) — [스펙](../specs/2026-08-18-trading-journal-design.md) §목표.
- 자동 테스트는 Node 내장 `node --test` + `node:assert/strict`만 사용, 별도 테스트 프레임워크 설치 금지.

---

### Task 1: FIFO 손익 매칭 + 입력 검증 순수 로직 (`fifo.js`)

**Files:**
- Create: `trading-journal/fifo.js`
- Test: `tests/fifo.test.mjs`

**Interfaces:**
- Produces:
  - `computeStats(trades: Array<{id, symbol, side: "buy"|"sell", price: number, quantity: number, date: string, createdAt: number}>) => {matches: Array<{symbol, buyTradeId, sellTradeId, buyPrice, sellPrice, qty, pnl}>, totalPnl: number, winRate: number, matchCount: number, holdings: Record<string, number>}`
  - `validateTradeInput(input: {symbol, side, price, quantity, date}) => {valid: boolean, errors: string[]}`
  - 이후 Task 4(`app.js`)가 두 함수를 그대로 import해서 사용한다.

- [ ] **Step 1: 실패하는 테스트부터 작성**

`tests/fifo.test.mjs` 생성:

```js
import { test } from "node:test";
import assert from "node:assert/strict";
import { computeStats, validateTradeInput } from "../trading-journal/fifo.js";

test("1:1 매수-매도 매칭 손익 계산", () => {
  const trades = [
    { id: 1, symbol: "BTC", side: "buy", price: 100, quantity: 1, date: "2026-08-01", createdAt: 1 },
    { id: 2, symbol: "BTC", side: "sell", price: 150, quantity: 1, date: "2026-08-02", createdAt: 2 },
  ];
  const stats = computeStats(trades);
  assert.equal(stats.matches.length, 1);
  assert.equal(stats.matches[0].pnl, 50);
  assert.equal(stats.totalPnl, 50);
  assert.equal(stats.winRate, 1);
  assert.deepEqual(stats.holdings, {});
});

test("매도 1건이 매수 여러 건에 걸쳐 분할 매칭됨", () => {
  const trades = [
    { id: 1, symbol: "BTC", side: "buy", price: 100, quantity: 0.5, date: "2026-08-01", createdAt: 1 },
    { id: 2, symbol: "BTC", side: "buy", price: 200, quantity: 0.5, date: "2026-08-02", createdAt: 2 },
    { id: 3, symbol: "BTC", side: "sell", price: 300, quantity: 1, date: "2026-08-03", createdAt: 3 },
  ];
  const stats = computeStats(trades);
  assert.equal(stats.matches.length, 2);
  assert.equal(stats.matches[0].pnl, (300 - 100) * 0.5);
  assert.equal(stats.matches[1].pnl, (300 - 200) * 0.5);
  assert.equal(stats.totalPnl, 100 + 50);
});

test("미매도 수량은 holdings에 남고 손익 계산에서 제외됨", () => {
  const trades = [
    { id: 1, symbol: "ETH", side: "buy", price: 100, quantity: 2, date: "2026-08-01", createdAt: 1 },
    { id: 2, symbol: "ETH", side: "sell", price: 120, quantity: 1, date: "2026-08-02", createdAt: 2 },
  ];
  const stats = computeStats(trades);
  assert.equal(stats.matches.length, 1);
  assert.equal(stats.holdings.ETH, 1);
});

test("매도 수량이 보유 매수 수량보다 많으면 초과분은 무시됨(크래시 없음)", () => {
  const trades = [
    { id: 1, symbol: "SOL", side: "buy", price: 10, quantity: 1, date: "2026-08-01", createdAt: 1 },
    { id: 2, symbol: "SOL", side: "sell", price: 20, quantity: 5, date: "2026-08-02", createdAt: 2 },
  ];
  const stats = computeStats(trades);
  assert.equal(stats.matches.length, 1);
  assert.equal(stats.matches[0].qty, 1);
  assert.deepEqual(stats.holdings, {});
});

test("승률은 익절 매칭 수 / 전체 매칭 수", () => {
  const trades = [
    { id: 1, symbol: "BTC", side: "buy", price: 100, quantity: 1, date: "2026-08-01", createdAt: 1 },
    { id: 2, symbol: "BTC", side: "sell", price: 90, quantity: 1, date: "2026-08-02", createdAt: 2 },
    { id: 3, symbol: "BTC", side: "buy", price: 100, quantity: 1, date: "2026-08-03", createdAt: 3 },
    { id: 4, symbol: "BTC", side: "sell", price: 200, quantity: 1, date: "2026-08-04", createdAt: 4 },
  ];
  const stats = computeStats(trades);
  assert.equal(stats.matchCount, 2);
  assert.equal(stats.winRate, 0.5);
});

test("validateTradeInput: 필수 필드 누락시 에러", () => {
  const result = validateTradeInput({ symbol: "", side: "buy", price: 0, quantity: 0, date: "" });
  assert.equal(result.valid, false);
  assert.ok(result.errors.length > 0);
});

test("validateTradeInput: 정상 입력은 valid", () => {
  const result = validateTradeInput({ symbol: "BTC", side: "buy", price: 100, quantity: 1, date: "2026-08-01" });
  assert.equal(result.valid, true);
  assert.deepEqual(result.errors, []);
});
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `node --test tests/fifo.test.mjs`
Expected: FAIL — `trading-journal/fifo.js` 모듈이 없어서 import 에러.

- [ ] **Step 3: 최소 구현 작성**

`trading-journal/fifo.js` 생성:

```js
export function computeStats(trades) {
  const bySymbol = new Map();
  for (const t of trades) {
    if (!bySymbol.has(t.symbol)) bySymbol.set(t.symbol, []);
    bySymbol.get(t.symbol).push(t);
  }

  const matches = [];
  const holdings = {};

  for (const [symbol, symbolTrades] of bySymbol) {
    const sorted = [...symbolTrades].sort((a, b) => {
      if (a.date !== b.date) return a.date < b.date ? -1 : 1;
      return a.createdAt - b.createdAt;
    });

    const buyQueue = [];
    for (const t of sorted) {
      if (t.side === "buy") {
        buyQueue.push({ price: t.price, remainingQty: t.quantity, tradeId: t.id });
      } else if (t.side === "sell") {
        let sellRemaining = t.quantity;
        while (sellRemaining > 0 && buyQueue.length > 0) {
          const head = buyQueue[0];
          const matchedQty = Math.min(sellRemaining, head.remainingQty);
          matches.push({
            symbol,
            buyTradeId: head.tradeId,
            sellTradeId: t.id,
            buyPrice: head.price,
            sellPrice: t.price,
            qty: matchedQty,
            pnl: (t.price - head.price) * matchedQty,
          });
          head.remainingQty -= matchedQty;
          sellRemaining -= matchedQty;
          if (head.remainingQty <= 0) buyQueue.shift();
        }
        // sellRemaining > 0으로 남으면 공매도(보유 초과 매도) — 매칭 없이 무시
      }
    }

    const remainingQty = buyQueue.reduce((sum, b) => sum + b.remainingQty, 0);
    if (remainingQty > 0) holdings[symbol] = remainingQty;
  }

  const totalPnl = matches.reduce((sum, m) => sum + m.pnl, 0);
  const matchCount = matches.length;
  const wins = matches.filter((m) => m.pnl > 0).length;
  const winRate = matchCount > 0 ? wins / matchCount : 0;

  return { matches, totalPnl, winRate, matchCount, holdings };
}

export function validateTradeInput(input) {
  const errors = [];
  if (!input.symbol || !input.symbol.trim()) errors.push("종목을 입력하세요.");
  if (input.side !== "buy" && input.side !== "sell") errors.push("매수/매도를 선택하세요.");
  if (!(Number(input.price) > 0)) errors.push("가격은 0보다 큰 숫자여야 합니다.");
  if (!(Number(input.quantity) > 0)) errors.push("수량은 0보다 큰 숫자여야 합니다.");
  if (!input.date) errors.push("날짜를 입력하세요.");
  return { valid: errors.length === 0, errors };
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `node --test tests/fifo.test.mjs`
Expected: PASS — 7개 테스트 모두 통과.

- [ ] **Step 5: 커밋**

```bash
git add trading-journal/fifo.js tests/fifo.test.mjs
git commit -m "feat: 매매일지 FIFO 손익매칭/입력검증 순수로직 추가"
```

---

### Task 2: IndexedDB 저장소 래퍼 (`db.js`)

**Files:**
- Create: `trading-journal/db.js`

**Interfaces:**
- Consumes: 없음 (브라우저 내장 `indexedDB` API만 사용).
- Produces:
  - `openDb() => Promise<IDBDatabase>`
  - `addTrade(trade: {symbol, side, price, quantity, date, memo?, chartImage?: Blob}) => Promise<number>` (신규 id 반환, createdAt은 내부에서 자동 부여)
  - `getAllTrades() => Promise<Array<trade & {id, createdAt}>>`
  - `deleteTrade(id: number) => Promise<void>`
  - `importTrades(trades: Array<object>) => Promise<void>` (각 항목의 기존 `id`는 무시하고 autoIncrement로 새로 부여)
  - Task 4(`app.js`)가 이 5개 함수를 그대로 import해서 사용한다.

브라우저 전용 API(IndexedDB)라 Node 자동 테스트 대상에서 제외 — Task 5의 수동 검증 체크리스트로 확인한다.

- [ ] **Step 1: 구현**

`trading-journal/db.js` 생성:

```js
const DB_NAME = "trading_journal";
const DB_VERSION = 1;
const STORE_NAME = "trades";

export function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      const store = db.createObjectStore(STORE_NAME, { keyPath: "id", autoIncrement: true });
      store.createIndex("symbol", "symbol", { unique: false });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function addTrade(trade) {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const req = tx.objectStore(STORE_NAME).add({ ...trade, createdAt: Date.now() });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function getAllTrades() {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const req = tx.objectStore(STORE_NAME).getAll();
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function deleteTrade(id) {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const req = tx.objectStore(STORE_NAME).delete(id);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

export async function importTrades(trades) {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    for (const t of trades) {
      const { id, ...rest } = t;
      store.add(rest);
    }
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}
```

- [ ] **Step 2: 커밋**

```bash
git add trading-journal/db.js
git commit -m "feat: 매매일지 IndexedDB 저장소 래퍼 추가"
```

---

### Task 3: 화면 골격 (`index.html`, `style.css`)

**Files:**
- Create: `trading-journal/index.html`
- Create: `trading-journal/style.css`

**Interfaces:**
- Produces: Task 4(`app.js`)가 참조할 DOM id 목록 — `trade-form`, `symbol`, `price`, `quantity`, `date`,
  `memo`, `chartImage`, `form-error`, `stat-total-pnl`, `stat-win-rate`, `stat-match-count`,
  `stat-holdings`, `symbol-filter`, `trades-tbody`, `detail-panel`, `detail-memo`, `detail-image`,
  `detail-close`, `export-btn`, `import-file`. side는 `input[name="side"]` 라디오(`value="buy"|"sell"`).

- [ ] **Step 1: `index.html` 작성**

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>매매일지</title>
<link rel="stylesheet" href="style.css" />
</head>
<body>
<div class="app">
  <h1>매매일지</h1>

  <form id="trade-form">
    <input id="symbol" type="text" placeholder="종목 (예: BTC)" required />
    <label><input type="radio" name="side" value="buy" checked /> 매수</label>
    <label><input type="radio" name="side" value="sell" /> 매도</label>
    <input id="price" type="number" step="any" placeholder="가격" required />
    <input id="quantity" type="number" step="any" placeholder="수량" required />
    <input id="date" type="date" required />
    <textarea id="memo" placeholder="메모(선택)"></textarea>
    <input id="chartImage" type="file" accept="image/*" />
    <button type="submit">추가</button>
    <div id="form-error" class="error"></div>
  </form>

  <section id="stats">
    <div>총손익: <span id="stat-total-pnl">-</span></div>
    <div>승률: <span id="stat-win-rate">-</span></div>
    <div>매칭 횟수: <span id="stat-match-count">-</span></div>
    <div>보유중: <span id="stat-holdings">-</span></div>
  </section>

  <section id="filter">
    종목 필터:
    <select id="symbol-filter">
      <option value="">전체</option>
    </select>
  </section>

  <table id="trades-table">
    <thead>
      <tr><th>날짜</th><th>종목</th><th>구분</th><th>가격</th><th>수량</th><th>메모</th><th></th></tr>
    </thead>
    <tbody id="trades-tbody"></tbody>
  </table>

  <div id="detail-panel" class="hidden">
    <button id="detail-close">닫기</button>
    <p id="detail-memo"></p>
    <img id="detail-image" alt="차트 사진" />
  </div>

  <section id="backup">
    <button id="export-btn">내보내기(JSON)</button>
    <input id="import-file" type="file" accept="application/json" />
  </section>
</div>
<script type="module" src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: `style.css` 작성**

```css
* { box-sizing: border-box; font-family: -apple-system, "Segoe UI", "Malgun Gothic", sans-serif; }
body { margin: 0; padding: 24px; background: #f5f5fa; color: #222; }
.app { max-width: 900px; margin: 0 auto; }
form { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
form input, form textarea, form button { padding: 6px 10px; }
.error { color: #c0392b; width: 100%; }
#stats { display: flex; gap: 24px; margin-bottom: 16px; padding: 12px; background: #fff; border-radius: 8px; }
table { width: 100%; border-collapse: collapse; background: #fff; }
th, td { text-align: left; padding: 8px; border-bottom: 1px solid #eee; cursor: pointer; }
.hidden { display: none; }
#detail-panel { margin-top: 16px; padding: 12px; background: #fff; border-radius: 8px; }
#detail-image { max-width: 100%; margin-top: 8px; }
#backup { margin-top: 16px; }
```

- [ ] **Step 3: 커밋**

```bash
git add trading-journal/index.html trading-journal/style.css
git commit -m "feat: 매매일지 화면 골격(index.html/style.css) 추가"
```

---

### Task 4: 화면 연결 (`app.js`)

**Files:**
- Create: `trading-journal/app.js`

**Interfaces:**
- Consumes:
  - `fifo.js`의 `computeStats(trades)`, `validateTradeInput(input)` (Task 1)
  - `db.js`의 `addTrade`, `getAllTrades`, `deleteTrade`, `importTrades` (Task 2)
  - `index.html`의 DOM id 목록 (Task 3)
- Produces: 없음 (최상위 진입점).

브라우저 전용(DOM+IndexedDB) 글루 코드라 Node 자동 테스트 대상에서 제외 — Task 5의 수동 검증으로 확인한다.

- [ ] **Step 1: 구현**

`trading-journal/app.js` 생성:

```js
import { computeStats, validateTradeInput } from "./fifo.js";
import { addTrade, getAllTrades, deleteTrade, importTrades } from "./db.js";

let currentFilter = "";
let selectedTradeId = null;

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

async function dataUrlToBlob(dataUrl) {
  const res = await fetch(dataUrl);
  return res.blob();
}

async function renderAll() {
  const allTrades = await getAllTrades();

  const filterSelect = document.getElementById("symbol-filter");
  const symbols = [...new Set(allTrades.map((t) => t.symbol))].sort();
  const prevValue = filterSelect.value;
  filterSelect.innerHTML = '<option value="">전체</option>' +
    symbols.map((s) => `<option value="${s}">${s}</option>`).join("");
  filterSelect.value = symbols.includes(prevValue) ? prevValue : "";
  currentFilter = filterSelect.value;

  const filtered = currentFilter
    ? allTrades.filter((t) => t.symbol === currentFilter)
    : allTrades;

  const stats = computeStats(filtered);
  document.getElementById("stat-total-pnl").textContent = stats.totalPnl.toFixed(2);
  document.getElementById("stat-win-rate").textContent =
    stats.matchCount > 0 ? `${(stats.winRate * 100).toFixed(1)}%` : "-";
  document.getElementById("stat-match-count").textContent = stats.matchCount;
  document.getElementById("stat-holdings").textContent =
    Object.entries(stats.holdings).map(([s, q]) => `${s}: ${q}`).join(", ") || "없음";

  const sorted = [...filtered].sort((a, b) => b.createdAt - a.createdAt);
  const tbody = document.getElementById("trades-tbody");
  tbody.innerHTML = "";
  for (const t of sorted) {
    const tr = document.createElement("tr");
    tr.dataset.id = t.id;
    const memoPreview = (t.memo || "").slice(0, 20);
    tr.innerHTML = `
      <td>${t.date}</td>
      <td>${t.symbol}</td>
      <td>${t.side === "buy" ? "매수" : "매도"}</td>
      <td>${t.price}</td>
      <td>${t.quantity}</td>
      <td>${memoPreview}</td>
      <td><button class="delete-btn" data-id="${t.id}">삭제</button></td>
    `;
    tbody.appendChild(tr);
  }
}

async function handleFormSubmit(e) {
  e.preventDefault();
  const symbol = document.getElementById("symbol").value.trim().toUpperCase();
  const side = document.querySelector('input[name="side"]:checked').value;
  const price = Number(document.getElementById("price").value);
  const quantity = Number(document.getElementById("quantity").value);
  const date = document.getElementById("date").value;
  const memo = document.getElementById("memo").value.trim();
  const fileInput = document.getElementById("chartImage");
  const errorBox = document.getElementById("form-error");

  const { valid, errors } = validateTradeInput({ symbol, side, price, quantity, date });
  if (!valid) {
    errorBox.textContent = errors.join(" ");
    return;
  }
  errorBox.textContent = "";

  const trade = { symbol, side, price, quantity, date, memo };
  if (fileInput.files[0]) {
    trade.chartImage = fileInput.files[0];
  }

  await addTrade(trade);
  e.target.reset();
  document.querySelector('input[name="side"][value="buy"]').checked = true;
  await renderAll();
}

async function handleTableClick(e) {
  if (e.target.classList.contains("delete-btn")) {
    const id = Number(e.target.dataset.id);
    if (confirm("이 거래를 삭제할까요?")) {
      await deleteTrade(id);
      await renderAll();
    }
    return;
  }
  const row = e.target.closest("tr[data-id]");
  if (!row) return;
  const id = Number(row.dataset.id);
  const allTrades = await getAllTrades();
  const trade = allTrades.find((t) => t.id === id);
  if (!trade) return;

  selectedTradeId = id;
  document.getElementById("detail-memo").textContent = trade.memo || "(메모 없음)";
  const img = document.getElementById("detail-image");
  if (trade.chartImage) {
    img.src = URL.createObjectURL(trade.chartImage);
    img.classList.remove("hidden");
  } else {
    img.removeAttribute("src");
    img.classList.add("hidden");
  }
  document.getElementById("detail-panel").classList.remove("hidden");
}

async function handleExport() {
  const allTrades = await getAllTrades();
  const exportable = await Promise.all(
    allTrades.map(async (t) => ({
      ...t,
      chartImage: t.chartImage ? await blobToDataUrl(t.chartImage) : null,
    }))
  );
  const blob = new Blob([JSON.stringify(exportable, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `trading-journal-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

async function handleImport(e) {
  const file = e.target.files[0];
  if (!file) return;
  const text = await file.text();
  const records = JSON.parse(text);
  const restored = await Promise.all(
    records.map(async (r) => ({
      ...r,
      chartImage: r.chartImage ? await dataUrlToBlob(r.chartImage) : undefined,
    }))
  );
  await importTrades(restored);
  e.target.value = "";
  await renderAll();
}

document.getElementById("trade-form").addEventListener("submit", handleFormSubmit);
document.getElementById("trades-tbody").addEventListener("click", handleTableClick);
document.getElementById("symbol-filter").addEventListener("change", renderAll);
document.getElementById("detail-close").addEventListener("click", () => {
  document.getElementById("detail-panel").classList.add("hidden");
});
document.getElementById("export-btn").addEventListener("click", handleExport);
document.getElementById("import-file").addEventListener("change", handleImport);
document.getElementById("date").valueAsDate = new Date();

renderAll();
```

- [ ] **Step 2: 커밋**

```bash
git add trading-journal/app.js
git commit -m "feat: 매매일지 화면 로직(app.js) 연결"
```

---

### Task 5: 실행 스크립트 + 수동 검증

**Files:**
- Create: `trading-journal/launch.bat`

**Interfaces:**
- Consumes: `trading-journal/index.html` (Task 3), `trading-journal/app.js` (Task 4) — 서버가 이 폴더를 그대로 서빙.
- Produces: 없음 (최종 실행 진입점).

- [ ] **Step 1: `launch.bat` 작성**

```bat
@echo off
cd /d "%~dp0"
start "" http://127.0.0.1:8788
python -m http.server 8788
```

- [ ] **Step 2: 커밋**

```bash
git add trading-journal/launch.bat
git commit -m "feat: 매매일지 launch.bat 추가"
```

- [ ] **Step 3: 수동 검증 (자동 테스트 프레임워크 없음)**

`trading-journal/launch.bat` 더블클릭 후 브라우저에서 아래 항목을 순서대로 확인한다.

1. `http://127.0.0.1:8788`에서 화면이 뜨는지.
2. BTC 매수 1건 + 같은 수량 매도 1건 입력 → 총손익이 `(매도가-매수가)*수량`과 일치.
3. BTC 매수 2건(수량 각 0.5) 후 매도 1건(수량 1) → 두 매수 건에 걸쳐 분할 매칭되고 손익 합이 맞는지.
4. 매수만 있고 매도 없는 종목이 "보유중"에 뜨고 총손익/승률에서는 빠지는지.
5. 차트사진 첨부 후 목록 행 클릭 → 상세 패널에 이미지가 원본대로 보이는지.
6. 브라우저 완전 종료 후 `launch.bat` 재실행 → 기존 데이터가 그대로 남아있는지(IndexedDB 영속성).
7. "내보내기"로 JSON 다운로드 → 데이터 삭제(개발자도구 Application 탭에서 IndexedDB 삭제) 후 "가져오기"로
   해당 JSON 선택 → 거래/이미지/메모 모두 복원되는지.
8. 필수 필드(종목/가격/수량/날짜) 비우고 저장 시도 → 에러 메시지 뜨고 저장 안 되는지.
9. 종목 필터 선택 → 목록/통계 카드 모두 선택한 종목만 반영되는지.

모두 통과하면 완료.

---

## Self-Review 결과

- **스펙 커버리지:** 데이터 모델(Task 2 keyPath/index), FIFO 로직(Task 1), 화면 구성 5개 항목(Task 3+4:
  입력폼/통계카드/목록/필터/백업), 에러 처리(Task 1 validateTradeInput, Task 4 confirm 삭제), 실행 방식
  (Task 5 launch.bat) — 스펙의 모든 섹션에 대응하는 태스크 확인됨. 공매도 초과분 무시 로직(스펙 §에러
  처리)도 Task 1 테스트 4번째 케이스로 커버.
- **플레이스홀더 스캔:** TBD/TODO 없음. 모든 스텝에 실제 코드 포함.
- **타입/시그니처 일관성:** `computeStats`/`validateTradeInput`(Task 1) ↔ `app.js`(Task 4) 사용처 이름·
  인자 일치. `addTrade`/`getAllTrades`/`deleteTrade`/`importTrades`(Task 2) ↔ `app.js`(Task 4) 사용처
  이름·인자 일치. DOM id 목록(Task 3) ↔ `app.js`의 `getElementById` 호출 전부 일치 확인됨.

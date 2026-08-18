import { computeStats, validateTradeInput } from "./fifo.js";
import { addTrade, getAllTrades, deleteTrade, importTrades } from "./db.js";

let currentFilter = "";
let selectedTradeId = null;

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

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
    symbols.map((s) => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`).join("");
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
      <td>${escapeHtml(t.date)}</td>
      <td>${escapeHtml(t.symbol)}</td>
      <td>${t.side === "buy" ? "매수" : "매도"}</td>
      <td>${escapeHtml(t.price)}</td>
      <td>${escapeHtml(t.quantity)}</td>
      <td>${escapeHtml(memoPreview)}</td>
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
      symbol: (r.symbol || "").trim().toUpperCase(),
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
document.getElementById("date").value = new Date().toLocaleDateString("sv-SE");

renderAll();

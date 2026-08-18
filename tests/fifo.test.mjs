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

test("부동소수점 잔차: 완전 청산 시 holdings에 잔여물이 남지 않음", () => {
  const trades = [
    { id: 1, symbol: "BTC", side: "buy", price: 100, quantity: 0.9, date: "2026-08-01", createdAt: 1 },
    { id: 2, symbol: "BTC", side: "sell", price: 110, quantity: 0.3, date: "2026-08-02", createdAt: 2 },
    { id: 3, symbol: "BTC", side: "sell", price: 120, quantity: 0.6, date: "2026-08-03", createdAt: 3 },
  ];
  const stats = computeStats(trades);
  assert.deepEqual(stats.holdings, {});
});

test("부동소수점 잔차: 유령 근사-제로 매칭으로 승률이 오염되지 않음", () => {
  const trades = [
    { id: 1, symbol: "BTC", side: "buy", price: 100, quantity: 0.3, date: "2026-08-01", createdAt: 1 },
    { id: 2, symbol: "BTC", side: "buy", price: 100, quantity: 0.6, date: "2026-08-02", createdAt: 2 },
    { id: 3, symbol: "BTC", side: "buy", price: 100, quantity: 1.0, date: "2026-08-03", createdAt: 3 },
    { id: 4, symbol: "BTC", side: "sell", price: 150, quantity: 0.9, date: "2026-08-04", createdAt: 4 },
  ];
  const stats = computeStats(trades);
  assert.equal(stats.matchCount, 2);
  assert.equal(stats.winRate, 1);
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

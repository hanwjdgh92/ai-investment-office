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

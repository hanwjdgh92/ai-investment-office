"""업비트 + 바이빗 공개 API로 watchlist에 있는 코인 시세를 조회해 data/crypto_YYYY-MM-DD.json 으로 저장한다."""
import json
import sys
from datetime import date
from pathlib import Path

import requests
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from indicators import moving_averages, rsi  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "watchlist.yaml"
DATA_DIR = ROOT / "data"


def fetch_upbit(market: str) -> dict:
    resp = requests.get(
        "https://api.upbit.com/v1/ticker", params={"markets": market}, timeout=10
    )
    resp.raise_for_status()
    row = resp.json()[0]
    return {
        "price": row["trade_price"],
        "change_rate_24h": round(row["signed_change_rate"] * 100, 2),
        "volume_24h": row["acc_trade_volume_24h"],
    }


def fetch_upbit_indicators(market: str) -> dict:
    resp = requests.get(
        "https://api.upbit.com/v1/candles/days",
        params={"market": market, "count": 90},
        timeout=10,
    )
    resp.raise_for_status()
    rows = resp.json()
    closes = [r["trade_price"] for r in reversed(rows)]  # 오래된 순으로 정렬
    return {**moving_averages(closes), "rsi14": rsi(closes)}


def fetch_bybit(symbol: str) -> dict:
    resp = requests.get(
        "https://api.bybit.com/v5/market/tickers",
        params={"category": "spot", "symbol": symbol},
        timeout=10,
    )
    resp.raise_for_status()
    row = resp.json()["result"]["list"][0]
    return {
        "price": float(row["lastPrice"]),
        "change_rate_24h": round(float(row["price24hPcnt"]) * 100, 2),
        "volume_24h": float(row["volume24h"]),
    }


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    result = []

    for coin in config.get("crypto", []):
        entry = {"symbol": coin["symbol"]}
        try:
            entry["upbit"] = fetch_upbit(coin["upbit_market"])
        except Exception as exc:  # noqa: BLE001
            entry["upbit_error"] = str(exc)
        try:
            entry["indicators"] = fetch_upbit_indicators(coin["upbit_market"])
        except Exception as exc:  # noqa: BLE001
            entry["indicators_error"] = str(exc)
        try:
            entry["bybit"] = fetch_bybit(coin["bybit_symbol"])
        except Exception as exc:  # noqa: BLE001
            entry["bybit_error"] = str(exc)
        result.append(entry)

    DATA_DIR.mkdir(exist_ok=True)
    out_path = DATA_DIR / f"crypto_{date.today().isoformat()}.json"
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()

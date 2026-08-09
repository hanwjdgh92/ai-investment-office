"""yfinance로 해외 종목 시세/기술적 지표/펀더멘털을 조회해 data/stocks_us_YYYY-MM-DD.json 으로 저장한다."""
import json
import sys
from datetime import date
from pathlib import Path

import yaml
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from indicators import moving_averages, rsi  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "watchlist.yaml"
DATA_DIR = ROOT / "data"


def fetch_name(ticker: str) -> str:
    """관심종목 추가 시 사용: 티커로 회사명을 조회한다."""
    info = yf.Ticker(ticker).info
    name = info.get("shortName") or info.get("longName")
    if not name:
        raise ValueError("종목명을 확인할 수 없습니다 (잘못된 티커일 수 있음)")
    return name


def fetch_recent(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    hist = t.history(period="6mo")
    if hist.empty:
        raise ValueError("no data returned")
    last = hist.iloc[-1]
    prev = hist.iloc[-2] if len(hist) > 1 else last
    change_rate = round((last["Close"] - prev["Close"]) / prev["Close"] * 100, 2)
    closes = [float(v) for v in hist["Close"]]

    info = t.info
    fundamentals = {
        "per": info.get("trailingPE"),
        "pbr": info.get("priceToBook"),
        "marketCap": info.get("marketCap"),
        "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
    }

    return {
        "date": str(hist.index[-1].date()),
        "close": float(last["Close"]),
        "change_rate": change_rate,
        "volume": int(last["Volume"]),
        "recent_closes": [float(v) for v in hist["Close"].tail(5)],
        "indicators": {**moving_averages(closes), "rsi14": rsi(closes)},
        "fundamentals": fundamentals,
    }


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    result = []

    for stock in config.get("stocks_us", []):
        entry = {"name": stock["name"], "ticker": stock["ticker"]}
        try:
            entry.update(fetch_recent(stock["ticker"]))
        except Exception as exc:  # noqa: BLE001
            entry["error"] = str(exc)
        result.append(entry)

    DATA_DIR.mkdir(exist_ok=True)
    out_path = DATA_DIR / f"stocks_us_{date.today().isoformat()}.json"
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()

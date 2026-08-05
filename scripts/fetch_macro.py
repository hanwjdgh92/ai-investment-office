"""환율/주요 지수/금리 등 매크로 지표를 조회해 data/macro_YYYY-MM-DD.json 으로 저장한다."""
import json
from datetime import date
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

MACRO_TICKERS = {
    "USDKRW": {"symbol": "KRW=X", "label": "원/달러 환율"},
    "KOSPI": {"symbol": "^KS11", "label": "코스피 지수"},
    "SP500": {"symbol": "^GSPC", "label": "S&P500 지수"},
    "US10Y": {"symbol": "^TNX", "label": "미국 10년물 국채금리"},
    "DXY": {"symbol": "DX-Y.NYB", "label": "달러 인덱스"},
}


def fetch_one(symbol: str) -> dict:
    hist = yf.Ticker(symbol).history(period="5d")
    if hist.empty:
        raise ValueError("no data returned")
    last = hist.iloc[-1]
    prev = hist.iloc[-2] if len(hist) > 1 else last
    change_rate = round((last["Close"] - prev["Close"]) / prev["Close"] * 100, 2)
    return {
        "date": str(hist.index[-1].date()),
        "value": round(float(last["Close"]), 4),
        "change_rate": change_rate,
    }


def main() -> None:
    result = {}
    for key, meta in MACRO_TICKERS.items():
        entry = {"label": meta["label"]}
        try:
            entry.update(fetch_one(meta["symbol"]))
        except Exception as exc:  # noqa: BLE001
            entry["error"] = str(exc)
        result[key] = entry

    DATA_DIR.mkdir(exist_ok=True)
    out_path = DATA_DIR / f"macro_{date.today().isoformat()}.json"
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()

"""FinanceDataReader로 국내 종목 시세/기술적 지표를, 네이버 금융에서 PER/PBR을 조회해
data/stocks_kr_YYYY-MM-DD.json 으로 저장한다.
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import FinanceDataReader as fdr
import requests
import yaml
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from indicators import moving_averages, rsi  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "watchlist.yaml"
DATA_DIR = ROOT / "data"

HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_recent(code: str, days: int = 130) -> dict:
    start = date.today() - timedelta(days=days)
    df = fdr.DataReader(code, start)
    if df.empty:
        raise ValueError("no data returned")
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    change_rate = round((last["Close"] - prev["Close"]) / prev["Close"] * 100, 2)
    closes = [float(v) for v in df["Close"]]
    return {
        "date": str(df.index[-1].date()),
        "close": float(last["Close"]),
        "change_rate": change_rate,
        "volume": int(last["Volume"]),
        "recent_closes": [float(v) for v in df["Close"].tail(5)],
        "indicators": {**moving_averages(closes), "rsi14": rsi(closes)},
    }


def fetch_fundamentals(code: str) -> dict:
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

    return {
        "per": parse_num(soup.select_one("#_per")),
        "pbr": parse_num(soup.select_one("#_pbr")),
    }


def main() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    result = []

    for stock in config.get("stocks_kr", []):
        entry = {"name": stock["name"], "code": stock["code"]}
        try:
            entry.update(fetch_recent(stock["code"]))
        except Exception as exc:  # noqa: BLE001
            entry["error"] = str(exc)
        try:
            entry["fundamentals"] = fetch_fundamentals(stock["code"])
        except Exception as exc:  # noqa: BLE001
            entry["fundamentals_error"] = str(exc)
        result.append(entry)

    DATA_DIR.mkdir(exist_ok=True)
    out_path = DATA_DIR / f"stocks_kr_{date.today().isoformat()}.json"
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()

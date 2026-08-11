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

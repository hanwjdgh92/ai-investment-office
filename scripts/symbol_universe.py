"""검색창 자동완성용 종목 유니버스. 서버 시작 시 1회 조회해 메모리에 캐싱한다."""
import requests
import FinanceDataReader as fdr

_CACHE: dict[str, list[dict]] = {"crypto": [], "stocks_kr": [], "stocks_us": []}


def _load_crypto() -> list[dict]:
    resp = requests.get(
        "https://api.upbit.com/v1/market/all", params={"isDetails": "false"}, timeout=10
    )
    resp.raise_for_status()
    items = []
    for row in resp.json():
        market = row["market"]
        if not market.startswith("KRW-"):
            continue
        symbol = market.split("-", 1)[1]
        items.append({"symbol": symbol, "name": row.get("korean_name", symbol), "type": "crypto"})
    return items


def _load_stocks_kr() -> list[dict]:
    df = fdr.StockListing("KRX")
    return [
        {"symbol": str(row["Code"]), "name": str(row["Name"]), "type": "stocks_kr"}
        for _, row in df.iterrows()
    ]


def _load_stocks_us() -> list[dict]:
    # ponytail: 전체 상장종목이 아닌 S&P500만 소스로 씀(빠르고 안정적, 대형 나스닥 종목 대부분 포함).
    # 나스닥100 전체 구성종목이 꼭 필요해지면 별도 정적 리스트를 추가할 것.
    df = fdr.StockListing("S&P500")
    return [
        {"symbol": str(row["Symbol"]), "name": str(row["Name"]), "type": "stocks_us"}
        for _, row in df.iterrows()
    ]


def load_all() -> None:
    try:
        _CACHE["crypto"] = _load_crypto()
    except Exception as exc:  # noqa: BLE001
        print(f"[symbol_universe] 크립토 목록 조회 실패: {exc}")
    try:
        _CACHE["stocks_kr"] = _load_stocks_kr()
    except Exception as exc:  # noqa: BLE001
        print(f"[symbol_universe] 국내주식 목록 조회 실패: {exc}")
    try:
        _CACHE["stocks_us"] = _load_stocks_us()
    except Exception as exc:  # noqa: BLE001
        print(f"[symbol_universe] 해외주식 목록 조회 실패: {exc}")


def search(type_: str, query: str, limit: int = 20) -> list[dict]:
    universe = _CACHE.get(type_, [])
    q = query.strip().upper()
    if not q:
        return universe[:limit]
    matches = [
        item for item in universe
        if q in item["symbol"].upper() or q in item["name"].upper()
    ]
    return matches[:limit]


def exists(type_: str, symbol: str) -> bool:
    symbol_upper = symbol.strip().upper()
    return any(item["symbol"].upper() == symbol_upper for item in _CACHE.get(type_, []))


def search_all(query: str, limit_per_type: int = 8) -> list[dict]:
    results: list[dict] = []
    for type_ in ("crypto", "stocks_kr", "stocks_us"):
        results.extend(search(type_, query, limit_per_type))
    return results

"""data/recent_searches.json 읽기/쓰기 공용 헬퍼. 최근 검색 결과를 최근 N개만 보관한다."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = ROOT / "data" / "recent_searches.json"
MAX_ITEMS = 10


def load() -> list[dict]:
    if not STORE_PATH.exists():
        return []
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))


def add(entry: dict) -> None:
    items = [entry] + load()
    items = items[:MAX_ITEMS]
    STORE_PATH.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )

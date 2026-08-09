"""config/watchlist.yaml 읽기/쓰기 공용 헬퍼.
파일 상단 안내 주석은 고정 문자열로 유지하고, 그 아래 데이터만 다시 쓴다.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "watchlist.yaml"

HEADER = (
    "# 관심 종목/코인 목록\n"
    "# 자유롭게 추가/삭제하세요. 심볼은 아래 형식을 따릅니다.\n"
    "\n"
)

ID_FIELDS = {"crypto": "symbol", "stocks_kr": "code", "stocks_us": "ticker"}


def load() -> dict:
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    for key in ("crypto", "stocks_kr", "stocks_us"):
        data.setdefault(key, [])
    return data


def save(data: dict) -> None:
    body = yaml.safe_dump(
        data, sort_keys=False, allow_unicode=True, default_flow_style=False
    )
    CONFIG_PATH.write_text(HEADER + body, encoding="utf-8")


def find(data: dict, type_: str, key: str) -> dict | None:
    field = ID_FIELDS[type_]
    key_norm = key.strip().upper()
    for item in data[type_]:
        if str(item[field]).strip().upper() == key_norm:
            return item
    return None


def add(data: dict, type_: str, entry: dict) -> None:
    data[type_].append(entry)


def remove(data: dict, type_: str, key: str) -> bool:
    field = ID_FIELDS[type_]
    key_norm = key.strip().upper()
    before = len(data[type_])
    data[type_] = [
        item for item in data[type_] if str(item[field]).strip().upper() != key_norm
    ]
    return len(data[type_]) < before

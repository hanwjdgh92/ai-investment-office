"""office_data.py의 parse_json_block()과 EMPLOYEES 구성을 점검하는 최소 self-check.
이 저장소엔 pytest 등 테스트 프레임워크가 없어 `python scripts/test_office_data.py`로 직접
실행한다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from office_data import EMPLOYEES, WATCHLIST_EXCLUDE_IDS, parse_json_block


def test_parse_json_block_valid():
    text = (
        "### 크립토 매매 시그널 (Trigger)\n"
        "- ETH: 매수...\n\n"
        "```json\n"
        '{"signals":[{"symbol":"ETH","direction":"buy","entry":2702000,'
        '"target":2727000,"stop":2699200,"position_pct":3,"rr":8.9}]}\n'
        "```\n"
    )
    result = parse_json_block(text)
    assert result is not None, "JSON 블록을 찾지 못함"
    assert result["ETH"]["direction"] == "buy"
    assert result["ETH"]["entry"] == 2702000


def test_parse_json_block_missing():
    assert parse_json_block("그냥 텍스트, JSON 블록 없음") is None


def test_parse_json_block_malformed():
    text = "```json\n{이건 JSON이 아님}\n```"
    assert parse_json_block(text) is None


def test_parse_json_block_no_signals_key():
    text = '```json\n{"foo": "bar"}\n```'
    assert parse_json_block(text) is None


def test_employees_have_bull_bear_excluded_from_watchlist():
    ids = [e["id"] for e in EMPLOYEES]
    assert "bull" in ids and "bear" in ids
    assert WATCHLIST_EXCLUDE_IDS == {"bull", "bear"}


if __name__ == "__main__":
    test_parse_json_block_valid()
    test_parse_json_block_missing()
    test_parse_json_block_malformed()
    test_parse_json_block_no_signals_key()
    test_employees_have_bull_bear_excluded_from_watchlist()
    print("OK - all office_data self-checks passed")

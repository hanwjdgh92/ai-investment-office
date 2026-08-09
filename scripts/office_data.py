"""최신 data/*.json, reports/*.md를 읽어 오피스 화면용 데이터를 조립한다.
generate_office.py(정적 스냅샷)와 serve_office.py(라이브 API) 양쪽에서 공용으로 사용한다.
"""
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"

EMPLOYEES = [
    {
        "id": "candle",
        "name": "Candle",
        "role": "암호화폐 기술적 분석",
        "emoji": "🕯️",
        "color": "#ffd9ec",
        "team": "크립토",
        "subteam": "ANALYSTS",
        "report_sections": ["Candle - 암호화폐 기술적 분석"],
        "raw_data_glob": "crypto_*.json",
    },
    {
        "id": "proto",
        "name": "Proto",
        "role": "암호화폐 펀더멘털",
        "emoji": "🧬",
        "color": "#e0f7e9",
        "team": "크립토",
        "subteam": "ANALYSTS",
        "report_sections": ["Proto - 암호화폐 펀더멘털"],
        "raw_data_glob": "crypto_*.json",
    },
    {
        "id": "vibes",
        "name": "Vibes",
        "role": "암호화폐 뉴스·심리",
        "emoji": "🌊",
        "color": "#ffe9d9",
        "team": "크립토",
        "subteam": "ANALYSTS",
        "report_sections": ["Vibes - 암호화폐 뉴스·심리"],
        "raw_data_glob": "crypto_*.json",
    },
    {
        "id": "node",
        "name": "Node",
        "role": "크립토 리서치 종합",
        "emoji": "🧑‍🔬",
        "color": "#eae1ff",
        "team": "크립토",
        "subteam": "RESEARCH",
        "report_sections": ["Node - 크립토 리서치 종합"],
        "raw_data_glob": None,
    },
    {
        "id": "chart",
        "name": "Chart",
        "role": "국내주식 기술적 분석",
        "emoji": "📈",
        "color": "#d9f2ff",
        "team": "국내주식",
        "subteam": "ANALYSTS",
        "report_sections": ["Chart - 국내주식 기술적 분석"],
        "raw_data_glob": "stocks_kr_*.json",
    },
    {
        "id": "ledger",
        "name": "Ledger",
        "role": "국내주식 펀더멘털",
        "emoji": "📒",
        "color": "#cfe8ff",
        "team": "국내주식",
        "subteam": "ANALYSTS",
        "report_sections": ["Ledger - 국내주식 펀더멘털"],
        "raw_data_glob": "stocks_kr_*.json",
    },
    {
        "id": "mood",
        "name": "Mood",
        "role": "국내주식 뉴스·심리",
        "emoji": "🌙",
        "color": "#f0e0ff",
        "team": "국내주식",
        "subteam": "ANALYSTS",
        "report_sections": ["Mood - 국내주식 뉴스·심리"],
        "raw_data_glob": "stocks_kr_*.json",
    },
    {
        "id": "anchor",
        "name": "Anchor",
        "role": "국내주식 리서치 종합",
        "emoji": "⚓",
        "color": "#eae1ff",
        "team": "국내주식",
        "subteam": "RESEARCH",
        "report_sections": ["Anchor - 국내주식 리서치 종합"],
        "raw_data_glob": None,
    },
    {
        "id": "trend",
        "name": "Trend",
        "role": "해외주식 기술적 분석",
        "emoji": "📊",
        "color": "#ffe0d0",
        "team": "해외주식",
        "subteam": "ANALYSTS",
        "report_sections": ["Trend - 해외주식 기술적 분석"],
        "raw_data_glob": "stocks_us_*.json",
    },
    {
        "id": "vault",
        "name": "Vault",
        "role": "해외주식 펀더멘털",
        "emoji": "🏦",
        "color": "#d0e0ff",
        "team": "해외주식",
        "subteam": "ANALYSTS",
        "report_sections": ["Vault - 해외주식 펀더멘털"],
        "raw_data_glob": "stocks_us_*.json",
    },
    {
        "id": "pulse",
        "name": "Pulse",
        "role": "해외주식 뉴스·심리",
        "emoji": "💓",
        "color": "#ffd0e0",
        "team": "해외주식",
        "subteam": "ANALYSTS",
        "report_sections": ["Pulse - 해외주식 뉴스·심리"],
        "raw_data_glob": "stocks_us_*.json",
    },
    {
        "id": "compass",
        "name": "Compass",
        "role": "해외주식 리서치 종합",
        "emoji": "🧭",
        "color": "#eae1ff",
        "team": "해외주식",
        "subteam": "RESEARCH",
        "report_sections": ["Compass - 해외주식 리서치 종합"],
        "raw_data_glob": None,
    },
    {
        "id": "trigger",
        "name": "Trigger",
        "role": "매매 시그널 생성 (Execution Specialist)",
        "emoji": "🎯",
        "color": "#dcdcdc",
        "team": "TRADING",
        "placeholder": True,
        "placeholder_text": "분석과 논쟁을 진입가·목표가·손절가·포지션 크기로 숫자화하는 성격. 2단계(매매 시그널 생성)에서 합류 예정",
    },
    {
        "id": "maverick",
        "name": "Maverick",
        "role": "공격적 리스크 검토 (Aggressive Risk)",
        "emoji": "🦉",
        "color": "#e6e0d4",
        "team": "RISK MGMT",
        "placeholder": True,
        "placeholder_text": "\"왜 이렇게 소심해? 더 크게 먹을 수 있는데\" — 놓친 상승 기회도 리스크라고 주장하는 성격. 3단계(자동매매·리스크 한도)에서 합류 예정",
    },
    {
        "id": "guardian",
        "name": "Guardian",
        "role": "보수적 리스크 검토 (Conservative Risk)",
        "emoji": "🛡️",
        "color": "#e6e0d4",
        "team": "RISK MGMT",
        "placeholder": True,
        "placeholder_text": "\"그러다 다 잃는다\" — 뭐든 최악의 시나리오부터 확인하는 성격. 3단계(자동매매·리스크 한도)에서 합류 예정",
    },
    {
        "id": "balance",
        "name": "Balance",
        "role": "중립 리스크 검토 (Neutral Risk)",
        "emoji": "⚖️",
        "color": "#e6e0d4",
        "team": "RISK MGMT",
        "placeholder": True,
        "placeholder_text": "Maverick과 Guardian을 저울질해 현실적인 중간 지점을 찾는 성격. 3단계(자동매매·리스크 한도)에서 합류 예정",
    },
    {
        "id": "chief-strategist",
        "name": "The Boss",
        "role": "종합 리포트 작성 (포트폴리오 매니저)",
        "emoji": "🧑‍💼",
        "color": "#e8e0ff",
        "team": "PM",
        "report_sections": ["오늘의 요약", "주목할 리스크", "참고 의견"],
        "raw_data_glob": None,
    },
]

TEAM_ORDER = ["크립토", "국내주식", "해외주식", "PM", "TRADING", "RISK MGMT"]


def latest_file(pattern: str, directory: Path) -> Path | None:
    files = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def parse_report_sections(text: str) -> dict:
    sections = {}
    parts = re.split(r"^## +(.+)$", text, flags=re.MULTILINE)
    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections[header] = body
    return sections


def fmt_num(value: float) -> str:
    if value != value:  # NaN
        return "N/A"
    if value == int(value):
        return f"{int(value):,}"
    return f"{value:,.2f}"


def fmt_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M")


def raw_data_highlights(pattern: str) -> str:
    files = sorted(DATA_DIR.glob(pattern), key=lambda p: p.stat().st_mtime)
    if not files:
        return ""
    lines = []
    for f in files:
        try:
            rows = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for row in rows:
            if "symbol" in row and "upbit" in row:
                price = row["upbit"].get("price")
                change = row["upbit"].get("change_rate_24h")
                if price is not None:
                    line = f"{row['symbol']}: {fmt_num(price)}원 ({change:+.2f}%)"
                    line += _indicator_suffix(row.get("indicators"))
                    lines.append(line)
                else:
                    lines.append(f"{row['symbol']}: 데이터 확인 필요")
            elif "name" in row and "close" in row:
                line = (
                    f"{row['name']}: {fmt_num(row['close'])} ({row.get('change_rate', 0):+.2f}%)"
                )
                line += _indicator_suffix(row.get("indicators"))
                line += _fundamentals_suffix(row.get("fundamentals"))
                lines.append(line)
            elif "name" in row and "error" in row:
                lines.append(f"{row['name']}: 데이터 조회 실패")
    return "\n".join(lines)


def _indicator_suffix(indicators: dict | None) -> str:
    if not indicators:
        return ""
    rsi14 = indicators.get("rsi14")
    if rsi14 is None:
        return ""
    return f" [RSI14 {rsi14}]"


def _fundamentals_suffix(fundamentals: dict | None) -> str:
    if not fundamentals:
        return ""
    per = fundamentals.get("per")
    if per is None:
        return ""
    return f" [PER {per:.1f}]"


def build_office_data() -> dict:
    report_file = latest_file("*.md", REPORTS_DIR)
    sections = {}
    report_time = None
    if report_file:
        sections = parse_report_sections(report_file.read_text(encoding="utf-8"))
        report_time = fmt_time(report_file.stat().st_mtime)

    employees_out = []
    feed = []

    for emp in EMPLOYEES:
        if emp.get("placeholder"):
            employees_out.append(
                {
                    "id": emp["id"],
                    "name": emp["name"],
                    "role": emp["role"],
                    "emoji": emp["emoji"],
                    "color": emp["color"],
                    "team": emp["team"],
                    "status": "locked",
                    "statusText": emp["placeholder_text"],
                    "fullText": emp["placeholder_text"],
                    "placeholder": True,
                }
            )
            continue

        section_texts = [sections[s] for s in emp["report_sections"] if s in sections]
        full_text = "\n\n".join(section_texts).strip()

        if not full_text and emp["raw_data_glob"]:
            full_text = raw_data_highlights(emp["raw_data_glob"])

        has_content = bool(full_text)
        preview = (
            full_text[:220] + ("…" if len(full_text) > 220 else "")
            if full_text
            else "아직 분석 내용이 없습니다."
        )

        if report_time and any(s in sections for s in emp["report_sections"]):
            item_time = report_time
            status = "done"
            status_text = "리포트 작성 완료"
        elif has_content:
            data_file = latest_file(emp["raw_data_glob"], DATA_DIR) if emp["raw_data_glob"] else None
            item_time = fmt_time(data_file.stat().st_mtime) if data_file else "--:--"
            status = "pending"
            status_text = "데이터 확인 완료 · 분석 대기 중"
        else:
            item_time = "--:--"
            status = "pending"
            status_text = "대기 중"

        employees_out.append(
            {
                "id": emp["id"],
                "name": emp["name"],
                "role": emp["role"],
                "emoji": emp["emoji"],
                "color": emp["color"],
                "team": emp["team"],
                "subteam": emp.get("subteam"),
                "status": status,
                "statusText": status_text,
                "fullText": full_text or "아직 작성된 분석이 없습니다.",
            }
        )

        if has_content:
            feed.append(
                {
                    "team": emp["team"],
                    "name": emp["name"],
                    "emoji": emp["emoji"],
                    "time": item_time,
                    "text": preview,
                }
            )

    feed.sort(key=lambda x: x["time"], reverse=True)

    feed_groups = []
    for team in TEAM_ORDER:
        items = [item for item in feed if item["team"] == team]
        if items:
            feed_groups.append({"category": team, "items": items})

    return {
        "title": "나의 AI 투자 오피스",
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "employees": employees_out,
        "consoleFeed": feed_groups,
    }

"""최신 데이터/리포트를 읽어 office/template.html의 데이터 토큰을 채운 office/index.html(정적 스냅샷)을 생성한다."""
import json
from pathlib import Path

from office_data import build_office_data

ROOT = Path(__file__).resolve().parent.parent
OFFICE_DIR = ROOT / "office"


def main() -> None:
    office_data = build_office_data()

    template = (OFFICE_DIR / "template.html").read_text(encoding="utf-8")
    output = template.replace(
        "/*__OFFICE_DATA_JSON__*/", json.dumps(office_data, ensure_ascii=False)
    )
    out_path = OFFICE_DIR / "index.html"
    out_path.write_text(output, encoding="utf-8")
    print(f"saved: {out_path}")


if __name__ == "__main__":
    main()

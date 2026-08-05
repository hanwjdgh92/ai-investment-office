"""로컬 웹서버로 AI 오피스를 실시간에 가깝게 보여준다.
- 백그라운드 스레드가 암호화폐는 30초, 주식은 2분 간격으로 시세를 계속 갱신한다 (LLM 호출 없음, 비용 없음).
- http://127.0.0.1:8787 (localhost 전용, 외부에 노출되지 않음) 에서 오피스를 볼 수 있다.
- AI 분석(리포트) 자체는 여기서 자동으로 만들지 않는다. `/daily-report` 또는 시간별 예약 작업이 reports/*.md를
  갱신하면, 이 서버가 다음 폴링 때 그 내용을 그대로 반영한다.
- Ctrl+C로 종료하면 된다.
"""
import json
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OFFICE_DIR = ROOT / "office"
RUN_HOURLY_PS1 = ROOT / "scripts" / "run_hourly.ps1"

_analysis_process: subprocess.Popen | None = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_crypto  # noqa: E402
import fetch_stocks_kr  # noqa: E402
import fetch_stocks_us  # noqa: E402
from office_data import build_office_data  # noqa: E402

HOST = "127.0.0.1"
PORT = 8787
CRYPTO_INTERVAL_SEC = 30
STOCK_INTERVAL_SEC = 120


def price_update_loop() -> None:
    last_stock_run = 0.0
    while True:
        try:
            fetch_crypto.main()
        except Exception as exc:  # noqa: BLE001
            print(f"[price_update_loop] crypto fetch 실패: {exc}")

        now = time.time()
        if now - last_stock_run >= STOCK_INTERVAL_SEC:
            try:
                fetch_stocks_kr.main()
                fetch_stocks_us.main()
            except Exception as exc:  # noqa: BLE001
                print(f"[price_update_loop] stocks fetch 실패: {exc}")
            last_stock_run = now

        time.sleep(CRYPTO_INTERVAL_SEC)


class OfficeHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A002
        pass  # 콘솔을 조용하게 유지

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/" or self.path == "/index.html":
            self._serve_index()
        elif self.path == "/api/live":
            self._serve_live()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/run-now":
            self._run_now()
        else:
            self.send_error(404, "Not Found")

    def _run_now(self) -> None:
        global _analysis_process
        if _analysis_process is not None and _analysis_process.poll() is None:
            status, message = 409, "이미 분석이 실행 중입니다."
        else:
            _analysis_process = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(RUN_HOURLY_PS1)],
                cwd=ROOT,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            status, message = 202, "분석을 시작했습니다. 1~2분 후 화면이 자동으로 갱신됩니다."
        body = json.dumps({"message": message}, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_index(self) -> None:
        template = (OFFICE_DIR / "template.html").read_text(encoding="utf-8")
        data = build_office_data()
        html = template.replace(
            "/*__OFFICE_DATA_JSON__*/", json.dumps(data, ensure_ascii=False)
        )
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_live(self) -> None:
        data = build_office_data()
        returncode = _analysis_process.poll() if _analysis_process is not None else None
        data["analysisRunning"] = _analysis_process is not None and returncode is None
        data["analysisFailed"] = returncode is not None and returncode != 0
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    updater = threading.Thread(target=price_update_loop, daemon=True)
    updater.start()

    server = ThreadingHTTPServer((HOST, PORT), OfficeHandler)
    url = f"http://{HOST}:{PORT}"
    print(f"AI 오피스 라이브 서버 시작: {url}")
    print("종료하려면 Ctrl+C 를 누르세요.")
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")
        server.shutdown()


if __name__ == "__main__":
    main()

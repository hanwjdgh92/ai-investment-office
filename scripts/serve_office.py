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
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
OFFICE_DIR = ROOT / "office"
RUN_SCHEDULED_ANALYSIS_PS1 = ROOT / "scripts" / "run_scheduled_analysis.ps1"
RUN_QUICK_ANALYZE_PS1 = ROOT / "scripts" / "run_quick_analyze.ps1"
QUICK_ANALYZE_LOG = ROOT / "data" / "adhoc" / "_quick_analyze_output.log"
QUICK_ANALYZE_BUDGET = {"crypto": "2", "stocks_kr": "1", "stocks_us": "1"}

_analysis_process: subprocess.Popen | None = None
_quick_analyze_process: subprocess.Popen | None = None
_quick_analyze_meta: dict | None = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_crypto  # noqa: E402
import fetch_stocks_kr  # noqa: E402
import fetch_stocks_us  # noqa: E402
import recent_searches_store  # noqa: E402
import symbol_universe  # noqa: E402
import watchlist_store  # noqa: E402
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
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/" or path == "/index.html":
            self._serve_index()
        elif path == "/api/live":
            self._serve_live()
        elif path == "/api/watchlist":
            self._get_watchlist()
        elif path == "/api/symbols":
            self._search_symbols(parse_qs(parsed.query))
        elif path == "/api/quick-analyze/status":
            self._quick_analyze_status()
        elif path == "/api/recent-searches":
            self._get_recent_searches()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/run-now":
            self._run_now()
        elif self.path == "/api/watchlist":
            self._add_watchlist_item()
        elif self.path == "/api/quick-analyze":
            self._start_quick_analyze()
        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self) -> None:  # noqa: N802
        if self.path == "/api/watchlist":
            self._delete_watchlist_item()
        else:
            self.send_error(404, "Not Found")

    def _run_now(self) -> None:
        global _analysis_process
        if _analysis_process is not None and _analysis_process.poll() is None:
            status, message = 409, "이미 분석이 실행 중입니다."
        else:
            _analysis_process = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(RUN_SCHEDULED_ANALYSIS_PS1)],
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

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw or b"{}")

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _get_watchlist(self) -> None:
        self._send_json(200, watchlist_store.load())

    def _add_watchlist_item(self) -> None:
        try:
            body = self._read_json_body()
        except Exception:  # noqa: BLE001
            self._send_json(400, {"error": "잘못된 요청 형식입니다."})
            return

        type_ = body.get("type")
        symbol = str(body.get("symbol", "")).strip()
        if type_ not in ("crypto", "stocks_kr", "stocks_us") or not symbol:
            self._send_json(400, {"error": "type과 symbol이 필요합니다."})
            return

        data = watchlist_store.load()
        if watchlist_store.find(data, type_, symbol):
            self._send_json(400, {"error": "이미 등록된 종목입니다."})
            return

        warning = None
        try:
            if type_ == "crypto":
                sym = symbol.upper()
                upbit_market = f"KRW-{sym}"
                bybit_symbol = f"{sym}USDT"
                upbit_ok = bybit_ok = False
                try:
                    fetch_crypto.fetch_upbit(upbit_market)
                    upbit_ok = True
                except Exception:  # noqa: BLE001
                    pass
                try:
                    fetch_crypto.fetch_bybit(bybit_symbol)
                    bybit_ok = True
                except Exception:  # noqa: BLE001
                    pass
                if not upbit_ok and not bybit_ok:
                    self._send_json(400, {"error": f"{sym}: 업비트/바이빗 모두 조회 실패"})
                    return
                if not bybit_ok:
                    warning = "바이빗 미지원 (업비트만 조회됨)"
                elif not upbit_ok:
                    warning = "업비트 미지원 (바이빗만 조회됨)"
                name = sym
                watchlist_store.add(
                    data, "crypto",
                    {"symbol": sym, "upbit_market": upbit_market, "bybit_symbol": bybit_symbol},
                )
                watchlist_store.save(data)
                fetch_crypto.main()
            elif type_ == "stocks_kr":
                info = fetch_stocks_kr.fetch_name_and_fundamentals(symbol)
                name = info["name"]
                watchlist_store.add(data, "stocks_kr", {"name": name, "code": symbol})
                watchlist_store.save(data)
                fetch_stocks_kr.main()
            else:  # stocks_us
                ticker = symbol.upper()
                name = fetch_stocks_us.fetch_name(ticker)
                fetch_stocks_us.fetch_recent(ticker)
                watchlist_store.add(data, "stocks_us", {"name": name, "ticker": ticker})
                watchlist_store.save(data)
                fetch_stocks_us.main()
        except Exception as exc:  # noqa: BLE001
            self._send_json(400, {"error": f"종목 조회 실패: {exc}"})
            return

        payload = {"name": name, "status": "ok"}
        if warning:
            payload["warning"] = warning
        self._send_json(202, payload)

    def _delete_watchlist_item(self) -> None:
        try:
            body = self._read_json_body()
        except Exception:  # noqa: BLE001
            self._send_json(400, {"error": "잘못된 요청 형식입니다."})
            return

        type_ = body.get("type")
        symbol = str(body.get("symbol", "")).strip()
        if type_ not in ("crypto", "stocks_kr", "stocks_us") or not symbol:
            self._send_json(400, {"error": "type과 symbol이 필요합니다."})
            return

        data = watchlist_store.load()
        if not watchlist_store.remove(data, type_, symbol):
            self._send_json(404, {"error": "등록되지 않은 종목입니다."})
            return
        watchlist_store.save(data)

        if type_ == "crypto":
            fetch_crypto.main()
        elif type_ == "stocks_kr":
            fetch_stocks_kr.main()
        else:
            fetch_stocks_us.main()

        self._send_json(200, {"status": "ok"})

    def _search_symbols(self, query: dict) -> None:
        q = (query.get("q") or [""])[0]
        self._send_json(200, {"items": symbol_universe.search_all(q)})

    def _get_recent_searches(self) -> None:
        self._send_json(200, {"items": recent_searches_store.load()})

    def _start_quick_analyze(self) -> None:
        global _quick_analyze_process, _quick_analyze_meta
        try:
            body = self._read_json_body()
        except Exception:  # noqa: BLE001
            self._send_json(400, {"error": "잘못된 요청 형식입니다."})
            return

        type_ = body.get("type")
        symbol = str(body.get("symbol", "")).strip().upper()
        if type_ not in ("crypto", "stocks_kr", "stocks_us") or not symbol:
            self._send_json(400, {"error": "type과 symbol이 필요합니다."})
            return
        if _quick_analyze_process is not None and _quick_analyze_process.poll() is None:
            self._send_json(409, {"error": "이미 분석이 진행 중입니다."})
            return

        QUICK_ANALYZE_LOG.parent.mkdir(parents=True, exist_ok=True)
        if QUICK_ANALYZE_LOG.exists():
            QUICK_ANALYZE_LOG.unlink()

        _quick_analyze_process = subprocess.Popen(
            [
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(RUN_QUICK_ANALYZE_PS1),
                "-Type", type_, "-Symbol", symbol, "-LogFile", str(QUICK_ANALYZE_LOG),
                "-MaxBudgetUsd", QUICK_ANALYZE_BUDGET[type_],
            ],
            cwd=ROOT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        _quick_analyze_meta = {"type": type_, "symbol": symbol}
        self._send_json(202, {"status": "started"})

    def _quick_analyze_status(self) -> None:
        global _quick_analyze_process, _quick_analyze_meta
        if _quick_analyze_process is None:
            self._send_json(200, {"status": "idle"})
            return

        returncode = _quick_analyze_process.poll()
        if returncode is None:
            self._send_json(200, {"status": "running", **_quick_analyze_meta})
            return

        meta = _quick_analyze_meta
        _quick_analyze_process = None
        _quick_analyze_meta = None
        text = (
            QUICK_ANALYZE_LOG.read_text(encoding="utf-8", errors="replace").strip()
            if QUICK_ANALYZE_LOG.exists() else ""
        )

        if returncode != 0 or not text:
            error = text[-2000:] if text else f"프로세스 종료 코드 {returncode}"
            self._send_json(200, {"status": "error", **meta, "error": error})
            return

        entry = {**meta, "timestamp": datetime.now(timezone.utc).isoformat(), "result_text": text}
        recent_searches_store.add(entry)
        self._send_json(200, {"status": "done", **entry})


def main() -> None:
    print("종목 검색 자동완성 목록을 불러오는 중...")
    symbol_universe.load_all()

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

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from src.ui.services import (
    BenchmarkUiRequest,
    StrategyBatchScanRequest,
    StrategyScanRequest,
    fetch_twse_for_ui,
    list_data_files,
    run_benchmark_ui,
    run_strategy_batch_scan,
    run_strategy_scan,
)

STATIC_ROOT = Path(__file__).resolve().parent / "static"


class UiRequestHandler(SimpleHTTPRequestHandler):
    server_version = "TwQuantUi/0.1"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(STATIC_ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._redirect("/strategy")
            return
        if path == "/strategy":
            self.path = "/strategy.html"
            return super().do_GET()
        if path == "/benchmark":
            self.path = "/benchmark.html"
            return super().do_GET()
        if path == "/api/data-files":
            self._send_json({"files": list_data_files()})
            return
        return super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/strategy-scan":
                result = run_strategy_scan(StrategyScanRequest(**payload))
            elif path == "/api/strategy-batch-scan":
                result = run_strategy_batch_scan(StrategyBatchScanRequest(**payload))
            elif path == "/api/benchmark-run":
                result = run_benchmark_ui(BenchmarkUiRequest(**payload))
            elif path == "/api/fetch-twse":
                result = fetch_twse_for_ui(
                    stock_ids=[str(item).strip() for item in payload.get("stock_ids", []) if str(item).strip()],
                    start=str(payload["start"]),
                    end=str(payload["end"]),
                    output=str(payload["output"]),
                )
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._send_json({"ok": True, "result": result})
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, target: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", target)
        self.end_headers()


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), UiRequestHandler)
    print(f"tw_quant_intraday UI: http://{host}:{port}/strategy")
    print(f"tw_quant_intraday benchmark: http://{host}:{port}/benchmark")
    server.serve_forever()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the local tw_quant_intraday web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    run(args.host, args.port)


if __name__ == "__main__":
    main()

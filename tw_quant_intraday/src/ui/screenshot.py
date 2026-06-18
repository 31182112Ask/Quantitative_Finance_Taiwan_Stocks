from __future__ import annotations

from pathlib import Path
from threading import Thread
from time import sleep
from datetime import datetime

from playwright.sync_api import sync_playwright

from src.config import PROJECT_ROOT
from src.ui.server import run


EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def _screenshot_path(output_dir: Path, name: str) -> Path:
    latest_dir = output_dir / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = latest_dir / name
    if path.exists():
        return latest_dir / f"{path.stem}_{stamp}{path.suffix}"
    return path


def main() -> None:
    output_dir = PROJECT_ROOT / "reports" / "ui"
    output_dir.mkdir(parents=True, exist_ok=True)
    server = Thread(target=run, kwargs={"host": "127.0.0.1", "port": 8765}, daemon=True)
    server.start()
    sleep(1)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=EDGE_PATH, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 980}, device_scale_factor=1)

        page.goto("http://127.0.0.1:8765/strategy", wait_until="networkidle")
        page.click("#runScan")
        page.wait_for_selector("#signalDetailPanel", state="visible", timeout=10000)
        page.click("#runBatchScan")
        page.wait_for_selector("#batchPanel", state="visible", timeout=10000)
        page.screenshot(path=str(_screenshot_path(output_dir, "strategy_client.png")), full_page=True)

        page.goto("http://127.0.0.1:8765/benchmark", wait_until="networkidle")
        page.fill("#initialCash", "10000")
        page.click("#runBenchmark")
        page.wait_for_selector("#tradeTableContainer", state="visible", timeout=10000)
        page.screenshot(path=str(_screenshot_path(output_dir, "benchmark_client.png")), full_page=True)

        mobile = browser.new_page(viewport={"width": 390, "height": 900}, is_mobile=True)
        mobile.goto("http://127.0.0.1:8765/strategy", wait_until="networkidle")
        mobile.screenshot(path=str(_screenshot_path(output_dir, "strategy_mobile.png")), full_page=True)

        browser.close()
    print(f"Screenshots written to {output_dir}")


if __name__ == "__main__":
    main()

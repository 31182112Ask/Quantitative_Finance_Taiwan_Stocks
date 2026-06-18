from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

from src.config import PROJECT_ROOT


EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def main() -> None:
    output_dir = PROJECT_ROOT / "reports" / "ui"
    output_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=EDGE_PATH, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 980}, device_scale_factor=1)

        page.goto("http://127.0.0.1:8765/strategy", wait_until="networkidle")
        page.click("#runScan")
        page.wait_for_selector("#metricSide:text('BUY')", timeout=10000)
        page.screenshot(path=str(output_dir / "strategy_client.png"), full_page=True)

        page.goto("http://127.0.0.1:8765/benchmark", wait_until="networkidle")
        page.click("#runBenchmark")
        page.wait_for_selector("#returnPct:text('0.0974%')", timeout=10000)
        page.screenshot(path=str(output_dir / "benchmark_client.png"), full_page=True)

        mobile = browser.new_page(viewport={"width": 390, "height": 900}, is_mobile=True)
        mobile.goto("http://127.0.0.1:8765/strategy", wait_until="networkidle")
        mobile.screenshot(path=str(output_dir / "strategy_mobile.png"), full_page=True)

        browser.close()
    print(f"Screenshots written to {output_dir}")


if __name__ == "__main__":
    main()

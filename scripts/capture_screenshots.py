"""Capture dashboard screenshots for the documentation.

Requires a running dashboard (streamlit run dashboard/app.py) and a local Chrome installation:

    python scripts/capture_screenshots.py --url http://localhost:8501
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from playwright.sync_api import sync_playwright

from metricflow_platform.logging_config import configure_logging

logger = logging.getLogger("capture_screenshots")

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "screenshots"
TABS = {
    "Overview": ("overview.png", 1250),
    "Trends": ("trends.png", 1750),
    "Products & categories": ("products.png", 1700),
    "Customers": ("customers.png", 2250),
}


def capture(url: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome")
        page = browser.new_page(
            viewport={"width": 1440, "height": 900}, device_scale_factor=1, locale="en-US"
        )
        page.goto(url)
        page.get_by_role("tab", name="Overview").wait_for(timeout=60_000)
        for tab, (file_name, height) in TABS.items():
            page.set_viewport_size({"width": 1440, "height": height})
            page.get_by_role("tab", name=tab).click()
            page.wait_for_timeout(2_500)
            path = output_dir / file_name
            page.screenshot(path=str(path))
            logger.info("screenshot_saved tab=%s path=%s", tab, path)
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8501")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    configure_logging()
    capture(args.url, args.output_dir)


if __name__ == "__main__":
    main()

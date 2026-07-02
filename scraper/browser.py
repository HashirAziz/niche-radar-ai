"""
Playwright browser/session management.
Centralized here so fiverr_scraper.py stays focused on parsing logic.
"""

from contextlib import contextmanager
from playwright.sync_api import sync_playwright
from fake_useragent import UserAgent

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import settings
from utils.logger import get_logger

logger = get_logger("browser")

ua = UserAgent()


@contextmanager
def get_browser_context():
    """
    Yields a configured Playwright browser context.
    Usage:
        with get_browser_context() as context:
            page = context.new_page()
            ...
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=settings.HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        context = browser.new_context(
            user_agent=ua.random,
            viewport={"width": 1366, "height": 768},
            locale="en-US",
        )
        context.set_default_timeout(settings.PAGE_LOAD_TIMEOUT_MS)

        # Light fingerprint masking
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        try:
            yield context
        finally:
            context.close()
            browser.close()
            logger.info("Browser context closed.")
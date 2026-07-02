"""
Core scraping logic: navigates Fiverr search pages per keyword,
grabs rendered HTML, hands off to parser.py, and saves raw results to disk.

Includes a manual-import fallback: if Fiverr blocks/CAPTCHAs the scraper,
you can instead save a search page's HTML manually (Ctrl+S) into
data/raw/manual/<keyword>.html and this module will pick it up.

DEBUG MODE: the first keyword's full page HTML + a screenshot are saved to
data/raw/debug/ so you can inspect exactly what Fiverr returned (CAPTCHA,
login wall, redesigned layout, etc.) before chasing selector fixes blind.
"""

import json
import sys
from pathlib import Path
from urllib.parse import quote_plus

sys.path.append(str(Path(__file__).resolve().parent.parent))

from tenacity import retry, stop_after_attempt, wait_exponential
from config import settings
from scraper.browser import get_browser_context
from scraper.parser import parse_search_results
from utils.helpers import human_delay
from utils.logger import get_logger

logger = get_logger("fiverr_scraper")

MANUAL_DIR = settings.RAW_DIR / "manual"
MANUAL_DIR.mkdir(exist_ok=True)

DEBUG_DIR = settings.RAW_DIR / "debug"
DEBUG_DIR.mkdir(exist_ok=True)


@retry(stop=stop_after_attempt(settings.MAX_RETRIES), wait=wait_exponential(multiplier=2, min=2, max=20))
def _fetch_page_html(page, keyword: str) -> str:
    url = settings.FIVERR_SEARCH_URL.format(query=quote_plus(keyword))
    logger.info(f"Navigating to: {url}")
    page.goto(url, wait_until="domcontentloaded")

    # Wait for gig cards to render (best-effort; falls through on timeout)
    try:
        page.wait_for_selector("div.gig-wrapper.basic-gig-card", timeout=8000)
    except Exception:
        logger.warning(f"Gig cards selector timeout for '{keyword}' — page may use a different layout.")

    # Scroll to trigger lazy-loaded cards
    for _ in range(3):
        page.mouse.wheel(0, 1500)
        human_delay(0.5, 1.2)

    html = page.content()

    # DEBUG: dump the first page's HTML + screenshot so we can see exactly
    # what Fiverr returned (CAPTCHA page, login wall, new layout, etc.)
    if not any(DEBUG_DIR.iterdir()):
        safe_name = keyword.replace(" ", "_").lower()
        debug_html_path = DEBUG_DIR / f"{safe_name}.html"
        debug_png_path = DEBUG_DIR / f"{safe_name}.png"
        debug_html_path.write_text(html, encoding="utf-8")
        try:
            page.screenshot(path=str(debug_png_path), full_page=True)
        except Exception as e:
            logger.warning(f"Could not save debug screenshot: {e}")
        logger.warning(f"DEBUG dump saved: {debug_html_path.name} and {debug_png_path.name} — inspect these before continuing.")

    return html


def _check_manual_fallback(keyword: str) -> str | None:
    """If scraping is blocked, check for a manually-saved HTML file."""
    safe_name = keyword.replace(" ", "_").lower()
    manual_file = MANUAL_DIR / f"{safe_name}.html"
    if manual_file.exists():
        logger.info(f"Using manual fallback HTML for '{keyword}'")
        return manual_file.read_text(encoding="utf-8")
    return None


def scrape_keyword(keyword: str, context) -> list[dict]:
    """Scrapes one keyword's search results. Returns list of gig dicts."""
    page = context.new_page()
    try:
        html = _fetch_page_html(page, keyword)
    except Exception as e:
        logger.error(f"Scrape failed for '{keyword}' after retries: {e}")
        manual_html = _check_manual_fallback(keyword)
        if manual_html:
            html = manual_html
        else:
            page.close()
            return []
    finally:
        if not page.is_closed():
            page.close()

    gigs = parse_search_results(html, keyword)

    # Save raw output for auditability / re-scoring without re-scraping
    out_file = settings.RAW_DIR / f"{keyword.replace(' ', '_').lower()}.json"
    out_file.write_text(json.dumps(gigs, indent=2), encoding="utf-8")

    return gigs


def scrape_all_keywords(keywords: list[str]) -> dict[str, list[dict]]:
    """Scrapes all keywords sequentially with human-like delays between requests."""
    results = {}
    with get_browser_context() as context:
        for i, kw in enumerate(keywords, 1):
            logger.info(f"[{i}/{len(keywords)}] Scraping keyword: '{kw}'")
            gigs = scrape_keyword(kw, context)
            results[kw] = gigs
            human_delay(settings.MIN_DELAY_SEC, settings.MAX_DELAY_SEC)
    return results
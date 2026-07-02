"""
Parses raw Fiverr search-page HTML into structured gig data using BeautifulSoup.

Selectors below were derived from a live debug capture (see data/raw/debug/).
Fiverr's build-hashed CSS classes (e.g. 'fn33510', 't6d0qrk') change on every
deploy and CANNOT be relied on. Instead we anchor on stable semantic classes
and data-* attributes that persist across rebuilds:
  - gig card root:    div.gig-wrapper.basic-gig-card[data-gig-id]
  - gig title:        p.gig-header (also has a 'title' attr with full text)
  - seller name:      figure[title] (the avatar figure's title = seller name)
  - seller level:      div/span/p with data-track-tag ending in '_badge'
  - rating:            strong.rating-score
  - review count:      span.rating-count-number
  - price:             a containing span with text like 'PKR 14,579'

If Fiverr redesigns again, re-capture a debug HTML dump and search for one
known seller name (Ctrl+F) to find the new card structure, same as before.
"""

from bs4 import BeautifulSoup
import re
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.helpers import parse_int, parse_float, parse_price
from utils.logger import get_logger

logger = get_logger("parser")


def parse_search_results(html: str, keyword: str) -> list[dict]:
    """
    Parses a Fiverr search results page and returns a list of gig dicts.
    Each dict matches the schema the demand validator expects.
    """
    soup = BeautifulSoup(html, "html.parser")

    cards = soup.select("div.gig-wrapper.basic-gig-card[data-gig-id]")

    if not cards:
        logger.warning(f"No gig cards found for keyword='{keyword}'. Selectors may be stale — re-capture a debug dump.")
        return []

    results = []
    for card in cards:
        # --- Title ---
        title_el = card.select_one("p.gig-header")
        title = title_el.get("title") or title_el.get_text(strip=True) if title_el else None

        # --- Seller name (from avatar figure's title attribute) ---
        seller_el = card.select_one("figure[title]")
        seller_name = seller_el.get("title") if seller_el else None

        # --- Seller level / badge (Level 1, Level 2, Top Rated, Vetted Pro, Fiverr's Choice) ---
        seller_level = "New Seller"
        badge_el = card.select_one("[data-track-tag$='_badge']")
        if badge_el:
            badge_text = badge_el.get_text(" ", strip=True)
            if badge_text:
                seller_level = badge_text

        # --- Rating ---
        rating_el = card.select_one("strong.rating-score")
        rating = parse_float(rating_el.get_text(strip=True)) if rating_el else 0.0

        # --- Review count ---
        reviews_el = card.select_one("span.rating-count-number")
        review_count = parse_int(reviews_el.get_text(strip=True)) if reviews_el else 0

        # --- Price (look for a span containing currency-like text near 'From') ---
        price = 0.0
        price_container = card.select_one("a._0ed0fc, a.tbody-5._0ed0fc")
        if price_container:
            price_text = price_container.get_text(" ", strip=True)
            match = re.search(r"[\d,]+(\.\d+)?", price_text)
            if match:
                price = parse_price(match.group(0))

        gig = {
            "keyword": keyword,
            "title": title,
            "seller_name": seller_name,
            "seller_level": seller_level,
            "rating": rating,
            "review_count": review_count,
            "price": price,
            "delivery_days": None,  # not shown on search cards; would need a gig-page visit
        }

        if gig["title"] and gig["seller_name"]:
            results.append(gig)

    logger.info(f"Parsed {len(results)} gigs for keyword='{keyword}'")
    return results
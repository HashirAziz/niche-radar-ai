"""
Central configuration for Fiverr AI Niche Finder.
Tune thresholds and weights here without touching logic code.
"""

import os
from pathlib import Path

# ---------- Paths ----------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = DATA_DIR / "reports"

for d in (RAW_DIR, PROCESSED_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------- Scraper behavior ----------
HEADLESS = False             # TEMP: set to False so you can watch the browser live while debugging
PAGE_LOAD_TIMEOUT_MS = 45000
MIN_DELAY_SEC = 2.5          # randomized delay range between requests
MAX_DELAY_SEC = 6.0
MAX_RETRIES = 3
GIGS_PER_KEYWORD = 24        # how many gig cards to pull per search page
FIVERR_SEARCH_URL = "https://www.fiverr.com/search/gigs?query={query}"

# ---------- Demand validation thresholds ----------
MIN_SELLERS_FOR_VALID_NICHE = 15        # below this = "no market" / unproven
MAX_SELLERS_LOW_COMPETITION = 200       # above this = saturated
MIN_AVG_REVIEWS_TOP10 = 20              # top gigs must show real review counts
MIN_AVG_RATING = 4.5
MIN_TOP_SELLER_RATIO_FOR_REJECT = 0.6   # >60% of top10 being Top Rated/Pro = saturated
RECENT_REVIEW_WINDOW_DAYS = 90          # "recent activity" window if timestamps available

# ---------- Scoring weights (must sum to 1.0) ----------
WEIGHTS = {
    "buyer_activity": 0.30,
    "low_competition": 0.25,
    "recent_review_activity": 0.15,
    "trend_growth": 0.15,
    "low_top_seller_saturation": 0.10,
    "pricing_opportunity": 0.05,
}

SCORE_BANDS = [
    (0, 30, "Avoid"),
    (31, 60, "Average"),
    (61, 80, "Good Opportunity"),
    (81, 100, "High Opportunity"),
]

# ---------- Pricing opportunity reference ----------
# Used to score whether average price in a niche leaves room for premium positioning
IDEAL_PRICE_RANGE = (40, 250)  # USD, gigs priced sensibly (not race-to-bottom $5 gigs)
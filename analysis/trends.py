"""
Pulls search interest trend data via pytrends (unofficial Google Trends API)
to estimate whether interest in a keyword/niche is rising, flat, or falling.

Google Trends aggressively rate-limits (HTTP 429) if requests fire too fast.
This module adds retry/backoff and longer delays between calls to stay under
that threshold. If you still see persistent 429s, the IP itself may be
temporarily flagged — slow TRENDS_MIN_DELAY/MAX_DELAY further or wait it out.
"""

import sys
import time
import random
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from pytrends.request import TrendReq
from pytrends.exceptions import TooManyRequestsError
from utils.logger import get_logger

logger = get_logger("trends")

_pytrends = TrendReq(hl="en-US", tz=360)

TRENDS_MIN_DELAY = 8.0
TRENDS_MAX_DELAY = 15.0
TRENDS_MAX_RETRIES = 3


def get_trend_growth(keyword: str) -> dict:
    """
    Returns:
        {
            "trend_score": float (0-100, normalized average interest last 12mo),
            "growth_pct": float (% change from first half to second half of period),
            "direction": "rising" | "stable" | "falling" | "unknown"
        }
    """
    for attempt in range(1, TRENDS_MAX_RETRIES + 1):
        try:
            _pytrends.build_payload([keyword], timeframe="today 12-m")
            df = _pytrends.interest_over_time()
            time.sleep(random.uniform(TRENDS_MIN_DELAY, TRENDS_MAX_DELAY))

            if df.empty or keyword not in df.columns:
                return {"trend_score": 0.0, "growth_pct": 0.0, "direction": "unknown"}

            series = df[keyword]
            avg_score = float(series.mean())

            half = len(series) // 2
            first_half_avg = series[:half].mean() if half > 0 else series.mean()
            second_half_avg = series[half:].mean()

            growth_pct = 0.0
            if first_half_avg > 0:
                growth_pct = ((second_half_avg - first_half_avg) / first_half_avg) * 100

            if growth_pct > 10:
                direction = "rising"
            elif growth_pct < -10:
                direction = "falling"
            else:
                direction = "stable"

            return {
                "trend_score": round(avg_score, 2),
                "growth_pct": round(growth_pct, 2),
                "direction": direction,
            }

        except TooManyRequestsError:
            wait = (2 ** attempt) * 10  # 20s, 40s, 80s backoff
            logger.warning(f"Trends 429 for '{keyword}' — backing off {wait}s (attempt {attempt}/{TRENDS_MAX_RETRIES})")
            time.sleep(wait)
        except Exception as e:
            logger.warning(f"Trend fetch failed for '{keyword}': {e}")
            return {"trend_score": 0.0, "growth_pct": 0.0, "direction": "unknown"}

    logger.warning(f"Trends permanently rate-limited for '{keyword}' after {TRENDS_MAX_RETRIES} attempts — defaulting to unknown.")
    return {"trend_score": 0.0, "growth_pct": 0.0, "direction": "unknown"}
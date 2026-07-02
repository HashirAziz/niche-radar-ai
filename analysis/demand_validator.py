"""
Validates whether a keyword represents a niche with REAL buyer activity,
not just sellers hoping for clients.

A keyword passes validation only if it clears every hard rule in
validate_keyword(). Anything that fails is rejected before it ever
reaches the scoring algorithm — score is meaningless for dead niches.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import settings
from utils.logger import get_logger

logger = get_logger("demand_validator")


def _top_n(gigs: list[dict], n: int = 10) -> list[dict]:
    return sorted(gigs, key=lambda g: g.get("review_count", 0), reverse=True)[:n]


def compute_signals(keyword: str, gigs: list[dict], trend_data: dict) -> dict:
    """Aggregates raw gig data into the signal set used for validation + scoring."""
    if not gigs:
        return {
            "keyword": keyword,
            "seller_count": 0,
            "avg_rating": 0.0,
            "avg_reviews_top10": 0.0,
            "top_seller_ratio": 0.0,
            "avg_price": 0.0,
            "trend_score": trend_data.get("trend_score", 0.0),
            "growth_pct": trend_data.get("growth_pct", 0.0),
            "trend_direction": trend_data.get("direction", "unknown"),
            "total_reviews": 0,
        }

    top10 = _top_n(gigs, 10)
    seller_count = len({g.get("seller_name") for g in gigs if g.get("seller_name")})
    avg_rating = sum(g.get("rating", 0) for g in gigs) / len(gigs)
    avg_reviews_top10 = sum(g.get("review_count", 0) for g in top10) / len(top10) if top10 else 0
    total_reviews = sum(g.get("review_count", 0) for g in gigs)

    top_level_sellers = sum(
        1 for g in top10
        if g.get("seller_level", "").lower() in ("top rated seller", "level 2", "pro verified")
    )
    top_seller_ratio = top_level_sellers / len(top10) if top10 else 0

    priced_gigs = [g.get("price", 0) for g in gigs if g.get("price", 0) > 0]
    avg_price = sum(priced_gigs) / len(priced_gigs) if priced_gigs else 0

    return {
        "keyword": keyword,
        "seller_count": seller_count,
        "avg_rating": round(avg_rating, 2),
        "avg_reviews_top10": round(avg_reviews_top10, 1),
        "top_seller_ratio": round(top_seller_ratio, 2),
        "avg_price": round(avg_price, 2),
        "trend_score": trend_data.get("trend_score", 0.0),
        "growth_pct": trend_data.get("growth_pct", 0.0),
        "trend_direction": trend_data.get("direction", "unknown"),
        "total_reviews": total_reviews,
    }


def validate_keyword(signals: dict) -> tuple[bool, list[str]]:
    """
    Returns (is_valid, reasons_for_rejection).
    A keyword must pass ALL checks to count as having real buyer activity.
    """
    reasons = []

    if signals["seller_count"] < settings.MIN_SELLERS_FOR_VALID_NICHE:
        reasons.append(
            f"Too few sellers ({signals['seller_count']}) — niche may be unproven, not just uncompetitive."
        )

    if signals["avg_reviews_top10"] < settings.MIN_AVG_REVIEWS_TOP10:
        reasons.append(
            f"Top gigs averaging only {signals['avg_reviews_top10']} reviews — weak buyer engagement."
        )

    if signals["avg_rating"] < settings.MIN_AVG_RATING and signals["avg_rating"] > 0:
        reasons.append(f"Average rating {signals['avg_rating']} below quality threshold.")

    if signals["trend_direction"] == "falling":
        reasons.append(f"Search trend falling ({signals['growth_pct']}% change) — declining interest.")

    if signals["total_reviews"] == 0:
        reasons.append("Zero total reviews found across all gigs — no confirmed buyer activity.")

    is_valid = len(reasons) == 0
    if not is_valid:
        logger.info(f"REJECTED '{signals['keyword']}': {'; '.join(reasons)}")
    else:
        logger.info(f"VALID '{signals['keyword']}' — passes buyer-activity checks.")

    return is_valid, reasons
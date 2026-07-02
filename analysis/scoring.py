"""
Implements the Opportunity Score formula:

Score = (BuyerActivity * 0.30) + (LowCompetition * 0.25) + (RecentReviewActivity * 0.15)
      + (TrendGrowth * 0.15) + (LowTopSellerSaturation * 0.10) + (PricingOpportunity * 0.05)

Each sub-component is normalized to 0-100 before weighting.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import settings
from utils.logger import get_logger

logger = get_logger("scoring")


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def score_buyer_activity(signals: dict) -> float:
    """Higher avg reviews on top gigs + total reviews = stronger buyer activity."""
    avg_reviews = signals["avg_reviews_top10"]
    # Scale: 20 reviews -> ~40pts, 100+ reviews -> ~100pts (diminishing returns via cap)
    score = (avg_reviews / 100) * 100
    return _clamp(score)


def score_low_competition(signals: dict) -> float:
    """Fewer sellers (but above the 'unproven niche' floor) = higher score."""
    sellers = signals["seller_count"]
    floor = settings.MIN_SELLERS_FOR_VALID_NICHE
    ceiling = settings.MAX_SELLERS_LOW_COMPETITION

    if sellers <= floor:
        return 0.0  # shouldn't reach scoring if validator did its job, but safe default
    if sellers >= ceiling:
        return 10.0  # heavily saturated, near-zero opportunity from competition angle

    # Inverse linear scale between floor and ceiling
    score = 100 - ((sellers - floor) / (ceiling - floor)) * 90
    return _clamp(score)


def score_recent_review_activity(signals: dict) -> float:
    """
    Proxy: total review volume relative to seller count suggests ongoing
    purchase activity rather than a few legacy reviews.
    """
    sellers = signals["seller_count"] or 1
    reviews_per_seller = signals["total_reviews"] / sellers
    # 5 reviews/seller average -> ~50pts, 10+ -> 100pts
    score = (reviews_per_seller / 10) * 100
    return _clamp(score)


def score_trend_growth(signals: dict) -> float:
    """Maps growth_pct (-100 to +100+) into a 0-100 score, plus base trend interest."""
    growth = signals["growth_pct"]
    base_interest = signals["trend_score"]  # 0-100 already from pytrends

    growth_component = _clamp(50 + growth)  # 0% growth = 50, +50% growth = 100, -50% = 0
    score = (growth_component * 0.6) + (base_interest * 0.4)
    return _clamp(score)


def score_low_top_seller_saturation(signals: dict) -> float:
    """Lower ratio of Top-Rated/Pro sellers in top10 = more room for new entrants."""
    ratio = signals["top_seller_ratio"]
    score = (1 - ratio) * 100
    return _clamp(score)


def score_pricing_opportunity(signals: dict) -> float:
    """Average price within the 'sensible' range scores highest; $5 race-to-bottom scores low."""
    price = signals["avg_price"]
    lo, hi = settings.IDEAL_PRICE_RANGE

    if price <= 0:
        return 0.0
    if price < lo:
        # Too cheap = commoditized/race-to-bottom niche
        return _clamp((price / lo) * 60)
    if price > hi:
        # Very high price = could mean low volume/enterprise-only; mild penalty
        return _clamp(100 - ((price - hi) / hi) * 30)

    return 100.0  # within ideal range


def compute_opportunity_score(signals: dict) -> dict:
    """Returns full scoring breakdown plus final 0-100 score and band label."""
    components = {
        "buyer_activity": score_buyer_activity(signals),
        "low_competition": score_low_competition(signals),
        "recent_review_activity": score_recent_review_activity(signals),
        "trend_growth": score_trend_growth(signals),
        "low_top_seller_saturation": score_low_top_seller_saturation(signals),
        "pricing_opportunity": score_pricing_opportunity(signals),
    }

    final_score = sum(components[k] * settings.WEIGHTS[k] for k in components)
    final_score = round(_clamp(final_score), 1)

    label = "Avoid"
    for lo, hi, band_label in settings.SCORE_BANDS:
        if lo <= final_score <= hi:
            label = band_label
            break

    recommendation_map = {
        "Avoid": "Skip — competition or weak demand outweighs opportunity.",
        "Average": "Possible, but needs strong differentiation to compete.",
        "Good Opportunity": "Solid niche — create a gig with a clear positioning angle.",
        "High Opportunity": "Create a Fiverr gig immediately — strong demand, low saturation.",
    }

    return {
        "keyword": signals["keyword"],
        "score_components": {k: round(v, 1) for k, v in components.items()},
        "opportunity_score": final_score,
        "label": label,
        "recommendation": recommendation_map[label],
        "seller_count": signals["seller_count"],
        "avg_rating": signals["avg_rating"],
        "avg_reviews_top10": signals["avg_reviews_top10"],
        "avg_price": signals["avg_price"],
        "trend_direction": signals["trend_direction"],
    }
import random
import re
import time
from datetime import datetime, timedelta


def human_delay(min_sec: float, max_sec: float):
    """Randomized delay to mimic human browsing and reduce block risk."""
    time.sleep(random.uniform(min_sec, max_sec))


def parse_int(text: str, default: int = 0) -> int:
    """Extract first integer-like number from a string, e.g. '1,204 reviews' -> 1204."""
    if not text:
        return default
    match = re.search(r"[\d,]+", text)
    if not match:
        return default
    return int(match.group(0).replace(",", ""))


def parse_float(text: str, default: float = 0.0) -> float:
    """Extract first float-like number, e.g. '4.9 (1,204)' -> 4.9."""
    if not text:
        return default
    match = re.search(r"\d+\.\d+", text)
    if match:
        return float(match.group(0))
    match = re.search(r"\d+", text)
    return float(match.group(0)) if match else default


def parse_price(text: str, default: float = 0.0) -> float:
    """Extract numeric price from strings like 'From US$ 45' or '$45'."""
    if not text:
        return default
    match = re.search(r"[\d,]+(\.\d+)?", text)
    if not match:
        return default
    return float(match.group(0).replace(",", ""))


def relative_time_to_days(text: str) -> int:
    """
    Convert Fiverr-style relative timestamps ('2 days ago', '3 months ago')
    into an approximate day count. Returns a large number if unknown/unparseable
    so it doesn't falsely count as 'recent'.
    """
    if not text:
        return 9999

    text = text.lower().strip()
    num_match = re.search(r"\d+", text)
    num = int(num_match.group(0)) if num_match else 1

    if "day" in text:
        return num
    if "week" in text:
        return num * 7
    if "month" in text:
        return num * 30
    if "year" in text:
        return num * 365
    if "hour" in text or "minute" in text or "just now" in text:
        return 0

    return 9999


def safe_div(a, b, default=0.0):
    try:
        return a / b if b else default
    except ZeroDivisionError:
        return default
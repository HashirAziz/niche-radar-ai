"""
Entry point. Run with:  python main.py

Pipeline:
1. Load seed keywords
2. Scrape Fiverr search results per keyword (Playwright + BeautifulSoup)
3. Pull Google Trends growth signal per keyword
4. Validate buyer-activity demand (reject dead/unproven niches)
5. Score remaining valid keywords with the Opportunity Score algorithm
6. Export sorted report to data/reports/opportunities.xlsx and .csv
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

import pandas as pd

from config.keywords_seed import flatten_keywords
from config import settings
from scraper.fiverr_scraper import scrape_all_keywords
from analysis.trends import get_trend_growth
from analysis.demand_validator import compute_signals, validate_keyword
from analysis.scoring import compute_opportunity_score
from utils.logger import get_logger

logger = get_logger("main")


def run_pipeline(keywords: list[str]):
    logger.info(f"Starting pipeline for {len(keywords)} keywords.")

    # Step 1: Scrape
    scraped = scrape_all_keywords(keywords)

    rejected_log = []
    scored_results = []

    for kw in keywords:
        gigs = scraped.get(kw, [])

        # Step 2: Trend data
        trend_data = get_trend_growth(kw)

        # Step 3: Signals + validation
        signals = compute_signals(kw, gigs, trend_data)
        is_valid, reasons = validate_keyword(signals)

        if not is_valid:
            rejected_log.append({"keyword": kw, "reasons": "; ".join(reasons)})
            continue

        # Step 4: Score
        result = compute_opportunity_score(signals)
        scored_results.append(result)

    # Step 5: Export
    export_reports(scored_results, rejected_log)


def export_reports(scored_results: list[dict], rejected_log: list[dict]):
    if scored_results:
        df = pd.DataFrame(scored_results)
        # Expand score_components dict into separate columns for readability
        components_df = pd.json_normalize(df.pop("score_components")).add_prefix("component_")
        df = pd.concat([df, components_df], axis=1)
        df = df.sort_values("opportunity_score", ascending=False)

        csv_path = settings.REPORTS_DIR / "opportunities.csv"
        xlsx_path = settings.REPORTS_DIR / "opportunities.xlsx"
        df.to_csv(csv_path, index=False)
        df.to_excel(xlsx_path, index=False)

        logger.info(f"Exported {len(df)} scored opportunities to {xlsx_path}")

        print("\n=== TOP OPPORTUNITIES ===")
        for _, row in df.head(10).iterrows():
            print(
                f"{row['opportunity_score']:>5.1f} | {row['label']:<18} | "
                f"{row['keyword']} ({row['seller_count']} sellers, "
                f"${row['avg_price']} avg)"
            )
    else:
        logger.warning("No keywords passed validation — nothing to score.")

    if rejected_log:
        rej_df = pd.DataFrame(rejected_log)
        rej_path = settings.REPORTS_DIR / "rejected_keywords.csv"
        rej_df.to_csv(rej_path, index=False)
        logger.info(f"Logged {len(rej_df)} rejected keywords to {rej_path}")


if __name__ == "__main__":
    all_keywords = flatten_keywords()
    run_pipeline(all_keywords)
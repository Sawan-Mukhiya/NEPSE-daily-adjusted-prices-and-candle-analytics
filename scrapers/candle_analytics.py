"""Incremental scraper for NEPSE candle-board analytics."""

from __future__ import annotations

import urllib.parse

try:
    from scrapers.common import parse_args, run_scraper
except ImportError:
    from common import parse_args, run_scraper

DEFAULT_OUTPUT_DIR = "data/candle_analytics"
FIELDNAMES = [
    "symbol",
    "date",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "shape",
    "pattern",
    "bias",
    "trust",
    "trust_key",
    "why_en",
    "why_ne",
    "as_of",
    "final",
    "scraped_at",
]


def build_url(symbol: str) -> str:
    """Build the candle-board series API URL for *symbol*."""
    inner_path = f"/candle-board/series?symbol={urllib.parse.quote(symbol, safe='')}"
    return (
        "https://nepsetrading.com/api/chart-data?path="
        + urllib.parse.quote(inner_path, safe="")
    )


def parse_payload(symbol: str, payload: dict, scraped_at: str) -> list[dict]:
    """Parse candle-board response bars into flat row dicts."""
    bars = payload.get("bars")
    if not isinstance(bars, list):
        return []

    as_of = payload.get("asOf") or ""
    final_val = payload.get("final")
    final_str = (
        str(final_val).lower()
        if isinstance(final_val, bool)
        else ("" if final_val is None else final_val)
    )

    rows: list[dict] = []
    for bar in bars:
        if not isinstance(bar, dict):
            continue
        date_str = bar.get("t") or ""
        if not date_str:
            continue
        why = bar.get("why") if isinstance(bar.get("why"), dict) else {}
        rows.append(
            {
                "symbol": symbol,
                "date": date_str,
                "timestamp": bar.get("time", ""),
                "open": bar.get("o", ""),
                "high": bar.get("h", ""),
                "low": bar.get("l", ""),
                "close": bar.get("c", ""),
                "volume": bar.get("v", ""),
                "shape": bar.get("shape") or "",
                "pattern": bar.get("pattern") or "",
                "bias": bar.get("bias") or "",
                "trust": bar.get("trust") or "",
                "trust_key": bar.get("trustKey") or "",
                "why_en": why.get("en") or "",
                "why_ne": why.get("ne") or "",
                "as_of": as_of,
                "final": final_str,
                "scraped_at": scraped_at,
            }
        )
    return rows


def main() -> int:
    """CLI entrypoint for scraping candle analytics."""
    args = parse_args(
        DEFAULT_OUTPUT_DIR,
        "Scrape NEPSE candle-board analytics.",
        default_exclude_file="removable.txt",
    )
    return run_scraper(args, FIELDNAMES, build_url, parse_payload)


if __name__ == "__main__":
    raise SystemExit(main())

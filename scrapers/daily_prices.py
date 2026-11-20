"""Incremental scraper for NEPSE adjusted daily OHLCV prices."""

from __future__ import annotations

import sys
import urllib.parse
from datetime import datetime, timezone

try:
    from scrapers.common import parse_args, run_scraper
except ImportError:
    from common import parse_args, run_scraper

DEFAULT_OUTPUT_DIR = "data/daily_prices"
FIELDNAMES = [
    "symbol",
    "date",
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "scraped_at",
]


def build_url(symbol: str) -> str:
    """Build the TradingView UDF chart-data URL for *symbol*."""
    inner_path = f"/historical-chart/daily/adjusted?code={urllib.parse.quote(symbol, safe='')}"
    return (
        "https://nepsetrading.com/api/chart-data?path="
        + urllib.parse.quote(inner_path, safe="")
    )


def parse_payload(symbol: str, payload: dict, scraped_at: str) -> list[dict]:
    """Parse TradingView UDF arrays into daily price row dicts."""
    status = payload.get("s")
    if status != "ok":
        if status != "no_data":
            print(
                f"[warn] Unexpected status {status!r} for {symbol}",
                file=sys.stderr,
            )
        return []

    timestamps = payload.get("t")
    opens = payload.get("o")
    highs = payload.get("h")
    lows = payload.get("l")
    closes = payload.get("c")
    volumes = payload.get("v")

    if not all(isinstance(arr, list) for arr in (timestamps, opens, highs, lows, closes)):
        print(f"[warn] Invalid OHLC arrays for {symbol}", file=sys.stderr)
        return []
    if len({len(timestamps), len(opens), len(highs), len(lows), len(closes)}) != 1:
        print(f"[warn] Mismatched OHLC array lengths for {symbol}", file=sys.stderr)
        return []
    if volumes is None:
        volumes = []
    elif not isinstance(volumes, list):
        print(f"[warn] Invalid volume array for {symbol}", file=sys.stderr)
        return []

    rows: list[dict] = []
    for idx, (ts, o, h, l, c) in enumerate(zip(timestamps, opens, highs, lows, closes)):
        try:
            ts_int = int(ts)
        except (TypeError, ValueError):
            continue
        v = volumes[idx] if idx < len(volumes) else ""
        v = "" if v is None else v
        date_str = datetime.fromtimestamp(ts_int, tz=timezone.utc).strftime("%Y-%m-%d")
        rows.append(
            {
                "symbol": symbol,
                "date": date_str,
                "timestamp": ts_int,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": v,
                "scraped_at": scraped_at,
            }
        )
    return rows


def main() -> int:
    """CLI entrypoint for scraping daily adjusted prices."""
    args = parse_args(DEFAULT_OUTPUT_DIR, "Scrape NEPSE daily adjusted OHLCV prices.")
    return run_scraper(args, FIELDNAMES, build_url, parse_payload)


if __name__ == "__main__":
    raise SystemExit(main())

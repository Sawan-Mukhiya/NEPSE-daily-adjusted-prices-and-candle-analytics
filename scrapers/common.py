"""Shared HTTP, CSV, and CLI helpers for NEPSE scrapers."""

from __future__ import annotations

import argparse
import csv
import http.client
import json
import os
import random
import shutil
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

USER_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) "
    "Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
)


def symbol_filename(symbol: str) -> str:
    """Return a filesystem-safe CSV stem for *symbol*."""
    return symbol.strip().replace("/", "_").replace("\\", "_")


def load_symbols(path: str | Path = "stocks.txt") -> list[str]:
    """Read non-empty stripped symbol lines from *path*."""
    with Path(path).open("r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip()]


def fetch_json(url: str, timeout: int = 20, max_retries: int = 3) -> dict | None:
    """Fetch JSON from *url* with anonymous headers and exponential backoff retries."""
    last_err: Exception | str | None = None
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://nepsetrading.com/",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if not isinstance(data, dict):
                    print(f"[warn] Unexpected JSON type for {url}", file=sys.stderr)
                    return None
                return data
        except urllib.error.HTTPError as exc:
            last_err = f"HTTP {exc.code}"
            if exc.code != 429 and not (500 <= exc.code < 600):
                print(f"[warn] {last_err} for {url}", file=sys.stderr)
                return None
        except (
            urllib.error.URLError,
            http.client.HTTPException,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ) as exc:
            last_err = exc

        if attempt < max_retries:
            backoff = (2**attempt) + random.uniform(0.2, 1.0)
            time.sleep(backoff)

    print(
        f"[warn] Failed after {max_retries + 1} attempts ({last_err}): {url}",
        file=sys.stderr,
    )
    return None


def polite_sleep(min_s: float = 0.8, max_s: float = 1.6) -> None:
    """Sleep for a randomized duration between *min_s* and *max_s* seconds."""
    low = max(0.0, min_s)
    high = max(low, max_s)
    if high > 0:
        time.sleep(random.uniform(low, high))


def load_latest_date(csv_path: Path) -> str | None:
    """Return the date of the first data row in a newest-first CSV, or None."""
    path = Path(csv_path)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        row = next(csv.DictReader(fh), None)
        return row.get("date") if row else None


def load_seen_keys(csv_path: Path) -> set[tuple[str, str]]:
    """Return existing (symbol, date) pairs from *csv_path* if it exists."""
    path = Path(csv_path)
    if not path.exists():
        return set()
    seen: set[tuple[str, str]] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            symbol = row.get("symbol")
            date = row.get("date")
            if symbol and date:
                seen.add((symbol, date))
    return seen


def prepend_csv_rows(
    csv_path: Path, fieldnames: list[str], new_rows: list[dict]
) -> int:
    """Prepend *new_rows* before existing CSV rows atomically using UTF-8-SIG."""
    if not new_rows:
        return 0

    path = Path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    with tmp_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=fieldnames,
            quoting=csv.QUOTE_ALL,
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(new_rows)

    if path.exists():
        with path.open("rb") as src, tmp_path.open("ab") as dst:
            src.readline()  # Skip BOM + existing header line
            shutil.copyfileobj(src, dst)

    os.replace(tmp_path, path)
    return len(new_rows)


def parse_args(
    default_output_dir: str,
    description: str,
    default_exclude_file: str | None = None,
) -> argparse.Namespace:
    """Parse common CLI arguments for scraper pipelines."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--symbols-file",
        default="stocks.txt",
        help="Path to newline-delimited symbols file (default: stocks.txt)",
    )
    parser.add_argument(
        "--exclude-file",
        default=default_exclude_file,
        help=f"Optional path to newline-delimited symbols to exclude (default: {default_exclude_file})",
    )
    parser.add_argument(
        "--output-dir",
        default=default_output_dir,
        help=f"Output directory for per-symbol CSVs (default: {default_output_dir})",
    )
    parser.add_argument(
        "--symbols",
        default=None,
        help="Optional comma-separated list of symbols to scrape",
    )
    parser.add_argument(
        "--exclude-symbols",
        default=None,
        help="Optional comma-separated list of symbols to exclude",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of symbols to process",
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=0.8,
        help="Minimum delay in seconds between requests (default: 0.8)",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=1.6,
        help="Maximum delay in seconds between requests (default: 1.6)",
    )
    return parser.parse_args()


def resolve_symbols(args: argparse.Namespace) -> list[str]:
    """Resolve symbol list from ``--symbols`` or ``--symbols-file`` with optional ``--exclude-file`` and ``--limit``."""
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    else:
        symbols = load_symbols(args.symbols_file)

    exclude_file = getattr(args, "exclude_file", None)
    if exclude_file and Path(exclude_file).is_file():
        excluded = set(load_symbols(exclude_file))
        symbols = [s for s in symbols if s not in excluded]

    exclude_symbols = getattr(args, "exclude_symbols", None)
    if exclude_symbols:
        excluded_cli = {s.strip() for s in exclude_symbols.split(",") if s.strip()}
        symbols = [s for s in symbols if s not in excluded_cli]

    if args.limit is not None:
        return symbols[: max(0, args.limit)]
    return symbols


def run_scraper(
    args: argparse.Namespace,
    fieldnames: list[str],
    build_url: Callable[[str], str],
    parse_payload: Callable[[str, dict, str], list[dict]],
    incremental_by_latest_date: bool = True,
) -> int:
    """Execute an incremental per-symbol scrape and prepend new rows newest-first."""
    output_dir = Path(args.output_dir)
    symbols = resolve_symbols(args)
    scraped_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total_added = 0

    for idx, symbol in enumerate(symbols):
        if idx > 0:
            polite_sleep(args.min_delay, args.max_delay)

        csv_path = output_dir / f"{symbol_filename(symbol)}.csv"
        latest_date = load_latest_date(csv_path) if incremental_by_latest_date else None
        seen = set() if incremental_by_latest_date else load_seen_keys(csv_path)

        payload = fetch_json(build_url(symbol))
        if payload is None:
            continue

        symbol_rows: list[dict] = []
        for row in parse_payload(symbol, payload, scraped_at):
            if latest_date is not None and row["date"] <= latest_date:
                continue
            key = (row["symbol"], row["date"])
            if key in seen:
                continue
            seen.add(key)
            symbol_rows.append(row)

        symbol_rows.sort(
            key=lambda r: (r["date"], int(r.get("timestamp") or 0)),
            reverse=True,
        )
        total_added += prepend_csv_rows(csv_path, fieldnames, symbol_rows)

    print(
        f"Processed {len(symbols)} symbol(s); prepended {total_added} new row(s) under {output_dir}."
    )
    return 0

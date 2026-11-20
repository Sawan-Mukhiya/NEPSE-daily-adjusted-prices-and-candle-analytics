# NEPSE Daily Adjusted & Candle Analytics

Incremental stdlib-only Python scrapers that collect daily adjusted OHLCV prices and candlestick analytics for symbols listed in `stocks.txt` and store them newest-first in `data/`.

## Datasets

### 1. Daily Adjusted Prices (`data/daily_prices/{SYMBOL}.csv`)
- **Source**: `/historical-chart/daily/adjusted?code={symbol}` via `scrapers/daily_prices.py`
- **Columns**:
  - `symbol` — Ticker symbol
  - `date` — UTC trading date (`YYYY-MM-DD`)
  - `timestamp` — Unix epoch timestamp (seconds, UTC)
  - `open`, `high`, `low`, `close`, `volume` — Adjusted daily OHLCV
  - `scraped_at` — UTC ISO-8601 scrape timestamp

### 2. Candle Analytics (`data/candle_analytics/{SYMBOL}.csv`)
- **Source**: `/candle-board/series?symbol={symbol}` via `scrapers/candle_analytics.py`
- **Columns**:
  - `symbol`, `date`, `timestamp`, `open`, `high`, `low`, `close`, `volume`
  - `shape`, `pattern`, `bias`, `trust`, `trust_key`
  - `why_en`, `why_ne` — English and Nepali explanations
  - `as_of`, `final`, `scraped_at`

Each symbol is saved to its own CSV file (`/` in debenture symbols like `NICAD85/86` is sanitized to `_`, e.g., `NICAD85_86.csv`). CSVs use UTF-8 with BOM (`utf-8-sig`), `\n` line endings, full quoting (`QUOTE_ALL`), `(symbol, date)` deduplication, and atomic newest-first prepending per symbol.

## Local Usage

No third-party packages are required (Python 3.13+ stdlib only):

```bash
python -m scrapers.daily_prices
python -m scrapers.candle_analytics
```

Optional CLI flags (supported by both scrapers):
- `--symbols-file PATH` (default: `stocks.txt`)
- `--output-dir PATH` (default: `data/daily_prices` / `data/candle_analytics`)
- `--symbols SYM1,SYM2` (override symbols file with a comma-separated list)
- `--limit N` (process at most `N` symbols)
- `--min-delay SEC` (default: `0.8`), `--max-delay SEC` (default: `1.6`)

Example smoke run for a single symbol:

```bash
python -m scrapers.daily_prices --symbols BENH --limit 1
python -m scrapers.candle_analytics --symbols BENH --limit 1
```

## GitHub Actions Schedule

[`.github/workflows/scrape.yml`](.github/workflows/scrape.yml) runs automatically every day at **16:15 UTC (22:00 NPT)** and also supports manual `workflow_dispatch` runs with optional `limit` and `symbols` inputs. Any newly appended rows under `data/` are committed and pushed automatically.

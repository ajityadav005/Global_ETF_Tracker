"""
Global ETF / Asset Performance Dashboard
=========================================
Fetches daily prices for a basket of ETFs/ETNs (and one FX pair) via
the `yfinance` library, computes performance returns (1W / 1M / 3M / YTD / 1Y)
and a normalized comparison chart, and writes a self-contained
interactive HTML dashboard (dashboard.html) that you can open in any
browser.

REQUIREMENTS
------------
    pip install yfinance pandas plotly

USAGE
-----
    python etf_dashboard.py

This writes `dashboard.html` in the same folder. Open it in a browser.
It also writes `returns_table.csv` with the raw numbers, in case you
want to pull them into Excel/Sheets.

AUTOMATING DAILY UPDATES
------------------------
This script does NOT run on its own — it needs to be triggered.
Three ways to make that automatic:

1. Cron (Mac/Linux). Edit your crontab (`crontab -e`) and add a line
   like the following to run at 6pm every weekday:
       0 18 * * 1-5 cd /path/to/folder && /usr/bin/python3 etf_dashboard.py

2. Windows Task Scheduler. Create a new Basic Task -> Daily trigger ->
   Action = "Start a program" -> Program = python.exe, Arguments =
   the full path to this script.

3. GitHub Actions (recommended if you want it to run even when your
   computer is off, and to publish the dashboard to a URL you can
   check from your phone). See the companion file
   `.github/workflows/daily_dashboard.yml` for a ready-to-use workflow
   that runs this script every day and publishes dashboard.html to
   GitHub Pages.

NOTES ON TICKERS
----------------
- All tickers below are stripped of the "-US" suffix you had, since
  that's how Yahoo Finance/yfinance expects US-listed symbols.
- NZDUSD is a currency pair, not an ETF, so it's fetched as "NZDUSD=X"
  (Yahoo's FX pair convention) rather than a ticker like the others.
- TIO-FDS (Iron Ore 62% Fe CFR China futures) is NOT available via
  Yahoo Finance / yfinance. It's a commodity futures/swap price
  normally sourced from a paid feed (e.g., Refinitiv, Bloomberg, or
  the SGX iron ore futures contract). It's left out of TICKERS below
  — if you have another source for it (a CSV export, etc.) it can be
  merged in separately.
"""

import sys
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import yfinance as yf

# ---------------------------------------------------------------------------
# Ticker -> Display name. (yfinance-compatible symbols)
# ---------------------------------------------------------------------------
TICKERS = {
    "FXE": "CurrencyShares Euro Trust",
    "FXY": "CurrencyShares Japanese Yen Trust",
    "FXB": "CurrencyShares British Pound Sterling Trust",
    "FXC": "CurrencyShares Canadian Dollar Trust",
    "FXA": "CurrencyShares Australian Dollar Trust",
    "NZDUSD=X": "NZD/USD spot rate",
    "FXF": "CurrencyShares Swiss Franc Trust",
    "GLD": "SPDR Gold Trust",
    "TLT": "iShares 20+ Year Treasury Bond ETF",
    "TIP": "iShares TIPS Bond ETF",
    "EMB": "iShares J.P. Morgan USD EM Bond ETF",
    "HYG": "iShares iBoxx $ High Yield Corporate Bond ETF",
    "LQD": "iShares iBoxx $ Investment Grade Corporate Bond ETF",
    "ACWI": "iShares MSCI ACWI ETF",
    "VTI": "Vanguard Total Stock Market ETF",
    "SPY": "SPDR S&P 500 ETF",
    "IWM": "iShares Russell 2000 ETF",
    "QQQ": "Invesco QQQ Trust",
    "EFA": "iShares MSCI EAFE ETF",
    "VWO": "Vanguard FTSE Emerging Markets ETF",
    "VEA": "Vanguard FTSE Developed Markets ETF",
    "EZU": "iShares MSCI Eurozone ETF",
    "EZA": "iShares MSCI South Africa ETF",
    "EWH": "iShares MSCI Hong Kong ETF",
    "EWA": "iShares MSCI Australia ETF",
    "EWJ": "iShares MSCI Japan ETF",
    "FXI": "iShares China Large-Cap ETF",
    "RSX": "VanEck Russia ETF",
    "EWZ": "iShares MSCI Brazil Capped ETF",
    "INDA": "iShares MSCI India ETF",
    "XLU": "Utilities Select Sector SPDR",
    "XLI": "Industrial Select Sector SPDR",
    "XLB": "Materials Select Sector SPDR",
    "XLF": "Financial Select Sector SPDR",
    "XLV": "Health Care Select Sector SPDR",
    "XLK": "Technology Select Sector SPDR",
    "XLE": "Energy Select Sector SPDR",
    "XLY": "Consumer Discretionary Select SPDR",
    "XLP": "Consumer Staples Select Sector SPDR",
    "XHB": "SPDR S&P Homebuilders ETF",
    "GDX": "VanEck Gold Miners ETF",
    "XLRE": "Real Estate Select Sector SPDR",
    "AMLP": "Alerian MLP ETF",
    "IBB": "iShares Nasdaq Biotechnology ETF",
    "IYT": "iShares Transportation Average ETF",
    "VNQ": "Vanguard Real Estate ETF",
    "VNQI": "Vanguard Global ex-U.S. Real Estate ETF",
    "RWO": "SPDR Dow Jones Global Real Estate ETF",
    "IFGL": "iShares International Developed Real Estate ETF",
    "SLV": "iShares Silver Trust",
    "USO": "United States Oil Fund",
    "UNG": "United States Natural Gas Fund",
    "DBA": "Invesco DB Agriculture Fund",
    "DBB": "Invesco DB Base Metals Fund",
    "SLX": "VanEck Steel ETF",
    "JJC": "iPath Bloomberg Copper Subindex ETN",
    "DBC": "Invesco DB Commodity Index Tracking Fund",
    # "TIO-FDS" (Iron Ore 62% Fe futures) intentionally omitted — not on yfinance.
    "DJP": "iPath Bloomberg Commodity Index Total Return ETN",
    "URA": "Global X Uranium ETF",
    "GAL": "SPDR SSGA Global Allocation ETF",
}

LOOKBACK_DAYS = 400  # a bit over a year, so a 1Y return is always computable


def fetch_prices() -> pd.DataFrame:
    """Download daily close prices for every ticker in TICKERS."""
    end = datetime.today()
    start = end - timedelta(days=LOOKBACK_DAYS)
    print(f"Fetching {len(TICKERS)} tickers from {start.date()} to {end.date()}...")
    raw = yf.download(
        list(TICKERS.keys()), start=start, end=end, progress=False, auto_adjust=True
    )
    # yf.download returns a MultiIndex column frame when >1 ticker requested.
    prices = raw["Close"] if "Close" in raw else raw
    prices = prices.dropna(how="all")
    if prices.empty:
        sys.exit("No price data returned. Check your internet connection / tickers.")
    return prices


def compute_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Build a table of 1M / 3M / YTD / 1Y % returns per ticker."""
    periods = {"1W": 5, "1M": 21, "3M": 63, "1Y": 252}  # approx trading days
    rows = []
    current_year = prices.index[-1].year

    for ticker in prices.columns:
        series = prices[ticker].dropna()
        if series.empty:
            continue
        row = {"Ticker": ticker.replace("=X", ""), "Name": TICKERS.get(ticker, "")}

        for label, days in periods.items():
            if len(series) > days:
                row[label] = round((series.iloc[-1] / series.iloc[-days - 1] - 1) * 100, 2)
            else:
                row[label] = None

        ytd_series = series[series.index.year == current_year]
        if not ytd_series.empty:
            row["YTD"] = round((series.iloc[-1] / ytd_series.iloc[0] - 1) * 100, 2)
        else:
            row["YTD"] = None

        rows.append(row)

    df = pd.DataFrame(rows)
    return df.sort_values("YTD", ascending=False, na_position="last").reset_index(drop=True)


def build_dashboard(prices: pd.DataFrame, returns: pd.DataFrame, out_path: str = "dashboard.html"):
    """Write a self-contained HTML dashboard: normalized chart + returns table."""

    # --- Normalized price chart (rebase every series to 100 at first common date) ---
    normed = prices.dropna(how="all") / prices.bfill().iloc[0] * 100

    fig = go.Figure()
    for ticker in normed.columns:
        series = normed[ticker].dropna()
        if series.empty:
            continue
        label = ticker.replace("=X", "")
        fig.add_trace(go.Scatter(x=series.index, y=series.values, mode="lines", name=label))

    fig.update_layout(
        title="Normalized Performance (rebased to 100)",
        xaxis_title="Date",
        yaxis_title="Index (start = 100)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.4),
        height=700,
        template="plotly_white",
    )

    chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

    # --- Returns table (plain HTML, sortable via simple JS) ---
    table_html = returns.to_html(index=False, classes="returns-table", na_rep="—", border=0)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>ETF Performance Dashboard</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; background: #fafafa; color: #222; }}
  h1 {{ font-size: 1.4rem; }}
  .meta {{ color: #777; font-size: 0.85rem; margin-bottom: 1.5rem; }}
  table.returns-table {{ border-collapse: collapse; width: 100%; font-size: 0.9rem; }}
  table.returns-table th, table.returns-table td {{ padding: 6px 10px; text-align: right; border-bottom: 1px solid #eee; }}
  table.returns-table th:nth-child(1), table.returns-table td:nth-child(1),
  table.returns-table th:nth-child(2), table.returns-table td:nth-child(2) {{ text-align: left; }}
  table.returns-table th {{ background: #f0f0f0; cursor: pointer; }}
</style>
</head>
<body>
  <h1>Global ETF Performance Dashboard</h1>
  <div class="meta">Generated {generated_at} — data via Yahoo Finance (yfinance)</div>
  {chart_html}
  <h2>Returns table (%)</h2>
  {table_html}
</body>
</html>"""

    with open(out_path, "w") as f:
        f.write(html)
    print(f"Wrote {out_path}")


def main():
    prices = fetch_prices()
    returns = compute_returns(prices)
    returns.to_csv("returns_table.csv", index=False)
    print("Wrote returns_table.csv")
    build_dashboard(prices, returns)


if __name__ == "__main__":
    main()

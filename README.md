# Global ETF Performance Dashboard

Tracks ~58 ETFs/ETNs (currencies, bonds, sector SPDRs, global equities,
commodities, real estate) with a normalized comparison chart and a
1M/3M/YTD/1Y returns table.

## Quick start (run once, manually)

```bash
pip install -r requirements.txt
python etf_dashboard.py
```

This writes `dashboard.html` (open it in any browser) and
`returns_table.csv`.

## Making it update automatically every day

Pick ONE of these:

### Option A — GitHub Actions (recommended)
Runs in the cloud, no computer needs to stay on, and gives you a
shareable URL.
1. Push this folder to a new GitHub repo.
2. Repo Settings → Pages → Source → "GitHub Actions".
3. That's it — `.github/workflows/daily_dashboard.yml` runs the script
   on weekdays and publishes the result to
   `https://<you>.github.io/<repo>/`.

### Option B — cron (Mac/Linux), runs locally
```bash
crontab -e
# add:
0 18 * * 1-5 cd /full/path/to/this/folder && /usr/bin/python3 etf_dashboard.py
```

### Option C — Windows Task Scheduler
Create a Daily trigger → Action: "Start a program" → Program:
`python.exe` → Arguments: full path to `etf_dashboard.py` → Start in:
this folder.

## Known data gaps
- `TIO-FDS` (Iron Ore 62% Fe CFR China futures) is not available via
  Yahoo Finance and was left out of the ticker list. If you have
  another source for it (e.g. a CSV export from your broker/terminal),
  it can be merged into the dashboard as a separate step.
- `NZDUSD` is fetched as the FX spot rate `NZDUSD=X`, not an ETF.

## Customizing
- Add/remove tickers in the `TICKERS` dict in `etf_dashboard.py`
  (must be valid Yahoo Finance symbols).
- Change `LOOKBACK_DAYS` if you want a longer/shorter history window.
- Change the cron expression in the workflow file to run at a
  different time (cron times are UTC).

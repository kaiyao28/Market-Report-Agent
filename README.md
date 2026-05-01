# Market Report Agent

Daily US market report system. Run two scripts, then ask Claude to generate the report.

## Daily Workflow

```bash
cd /Users/mpmky/Documents/VSCode/Daily/Stock/market_report_agent

python scripts/collect_market_data.py
python scripts/calculate_indicators.py
python scripts/collect_valuation.py
```

Then open Claude and say: **"generate today's market report"**

Claude reads the processed data + skills + strategies and writes:
`reports/YYYY-MM-DD_daily_market_report.md`

## Folder Structure

```
market_report_agent/
├── data/
│   ├── raw/                    # unused for now
│   └── processed/              # CSVs written by scripts
│       ├── YYYY-MM-DD_market_prices.csv
│       ├── YYYY-MM-DD_indicators.csv
│       └── valuation_snapshot.json   # update manually each week
├── reports/                    # generated markdown reports
├── skills/                     # analysis rules Claude follows
│   ├── sector_flow.md
│   ├── commodities.md
│   ├── technical_analysis.md
│   ├── valuation.md
│   └── ytd_leaders.md
├── strategies/                 # strategy overlays
│   ├── momentum_rotation.md
│   ├── defensive_risk_off.md
│   └── commodity_macro_overlay.md
├── prompts/
│   └── daily_report_prompt.md  # report structure Claude uses
└── scripts/
    ├── collect_market_data.py  # downloads 1y of OHLCV data
    ├── calculate_indicators.py # calculates returns, MAs, RSI, sector scores
    └── collect_valuation.py    # fetches PE / CAPE from multpl.com (auto, weekly)
```

## Data Coverage

| Group | Tickers |
|-------|---------|
| Indices | SPY, QQQ, DIA, IWM, ^VIX |
| Sector ETFs | XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, XLB, XLRE, XLC |
| Commodities | CL=F, BZ=F, GC=F, SI=F, HG=F, NG=F |
| Nasdaq 100 | ~80 tickers for YTD ranking |

## Valuation (Automatic, Weekly)

`collect_valuation.py` runs daily but only fetches when the snapshot is > 7 days old.

| Metric | Source | Notes |
|--------|--------|-------|
| Trailing PE | multpl.com | Auto |
| Shiller CAPE | multpl.com | Auto |
| Market Cap / GDP | FRED API | Auto if `FRED_API_KEY` set |
| Forward PE | — | Not available free — shows as "missing" |

**Optional FRED API key** (free at fred.stlouisfed.org):
```bash
export FRED_API_KEY=your_key_here
```
Without it, Market Cap/GDP is skipped but everything else still works.

## Requirements

```bash
pip install yfinance pandas numpy requests beautifulsoup4
```

## Timing

Run after US market close (after 4pm ET / 9pm UK) or next morning before generating the report. Scripts skip re-download if today's file already exists.

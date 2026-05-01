# Skill: Commodities Daily Monitor

## Goal
Track daily and weekly movement in key commodities and interpret macro implications.

## Assets
| Commodity | Ticker | Notes |
|-----------|--------|-------|
| WTI Crude Oil | CL=F | US benchmark |
| Brent Crude Oil | BZ=F | Global benchmark |
| Gold | GC=F | Risk-off / real rate proxy |
| Silver | SI=F | Industrial + safe haven hybrid |
| Copper | HG=F | Growth / industrial demand proxy |
| Natural Gas | NG=F | Energy volatility |

## Metrics (from indicators CSV)
- `last_price`: latest close
- `ret_1d`: 1-day return
- `ret_5d`: 5-day return
- `above_20ma`: boolean
- `above_50ma`: boolean

## Interpretation Rules
| Signal | Implication |
|--------|-------------|
| Oil up > 1.5% in 1D | Inflation / energy sector pressure; watch XLE |
| Gold up > 1% in 1D | Risk-off or real-rate concern; check VIX |
| Copper up > 1% in 1D | Growth / industrial demand; supports cyclicals |
| Natural gas spike > 3% | Energy volatility; sector-specific, not macro |
| Gold up + Copper down | Stagflation signal — flag as risk |
| Oil down + Copper down | Demand concern — bearish macro backdrop |

## Output Format
Table:
```
Commodity | Ticker | Price | 1D % | 5D % | vs 20MA | vs 50MA | Implication
```
Followed by 1–2 sentence macro summary.

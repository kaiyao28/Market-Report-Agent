# Skill: Market Technical Analysis

## Goal
Classify broad US market trend and momentum using index technicals.

## Indices
| Index | Ticker | Represents |
|-------|--------|------------|
| S&P 500 | SPY | Broad US market |
| Nasdaq 100 | QQQ | Large-cap tech / growth |
| Dow Jones | DIA | Blue chip / defensive |
| Russell 2000 | IWM | Small caps / risk appetite |
| Volatility | ^VIX | Fear gauge |

## Indicators Used (from indicators CSV)
- `ret_1d`, `ret_5d`, `ret_20d`
- `ma20`, `ma50`, `ma200`
- `above_20ma`, `above_50ma`, `above_200ma`
- `rsi14`

## Trend Classification Rules
| Condition | Label |
|-----------|-------|
| price > 20MA > 50MA and RSI 50–70 | Bullish |
| price > 20MA > 50MA and RSI > 70 | Extended / Overbought |
| price between 20MA and 50MA | Neutral |
| price < 50MA but > 200MA | Caution |
| price < 200MA | Bearish |
| VIX > 25 or rising sharply (>15% in 5D) | Risk-off alert |

## Momentum Rules
- RSI > 60 and rising: Strong momentum
- RSI 45–60: Neutral
- RSI < 45: Weakening
- RSI < 30: Oversold — potential reversal watch

## Support / Resistance Proxy
- Support: 20-day low of close prices
- Resistance: 20-day high of close prices
(Use `ma20` as dynamic support in uptrends)

## Output Format
Table:
```
Index | Price | 1D % | 5D % | RSI | vs 20MA | vs 50MA | Trend Signal
```
Then:
- Overall market trend: [Bullish / Neutral / Caution / Bearish]
- Momentum: [Strong / Neutral / Weakening]
- Risk level: [Low / Moderate / Elevated / High]
- VIX reading and interpretation

# Skill: News Impact Assessment

## Goal
Interpret financial news headlines and assign market impact to inform the daily strategy outlook.
Used by Claude when reading `data/processed/YYYY-MM-DD_news.json`.

## Source Hierarchy (trust weighting)
| Priority | Sources | Why |
|----------|---------|-----|
| High | Reuters, FT, WSJ, Bloomberg | Primary-source reporting, fast, factual |
| Medium | CNBC, MarketWatch, Yahoo Finance | Fast but more opinion/reaction mixed in |
| Lower | Seeking Alpha, individual blogs | Opinion-heavy, may lag |

---

## Category → Market Impact Rules

### Macro / Rates
| Headline Signal | Market Impact | Affected Assets |
|----------------|--------------|-----------------|
| Fed rate hike / hawkish tone | Bearish equities, bearish bonds | XLK, XLRE down; XLF mixed; USD up |
| Fed rate cut / dovish tone | Bullish equities, bonds rally | XLK, XLRE, XLY up; XLU up |
| CPI above expectations | Stagflation risk; bonds sell off | Gold up; tech down; XLP, XLU defensive |
| CPI below expectations | Bullish; rate cut hope rises | Broad rally; growth > value |
| GDP beat | Risk-on; cyclicals lead | XLI, XLY, XLB up |
| GDP miss / recession fear | Defensive rotation | XLP, XLU, XLV; gold up |
| Jobs report strong | Mixed: good economy but less cuts | USD up; bonds down; growth mixed |
| Jobs report weak | Rate cut expectation rises | Bonds rally; growth stocks up |
| Yield curve inversion / deepens | Recession signal | Defensives; reduce cyclicals |

### Energy
| Headline Signal | Impact |
|----------------|--------|
| OPEC production cut | Oil up → XLE up; inflation concern |
| OPEC production increase | Oil down → XLE down; inflation relief |
| US crude inventory build | Oil down; watch XLE |
| Geopolitical disruption in Middle East | Oil spike; safe haven flows |
| Natural gas supply disruption | NG=F spike; utility sector impact |

### Metals / Commodities
| Headline Signal | Impact |
|----------------|--------|
| Gold up on macro fear | Risk-off confirmed; reduce equity exposure |
| Gold up alongside equities | Inflation hedge accumulation; mixed |
| Copper rising | Growth demand signal; supports cyclicals (XLI, XLB) |
| Copper falling | Demand concern; reduce cyclicals |
| Silver + Gold both rising | Amplified safe haven; strong risk-off |

### Technology
| Headline Signal | Impact |
|----------------|--------|
| Major AI earnings beat | XLK up; semiconductors up |
| Chip supply shortage news | Semis up short term; watch NVDA, AMD, INTC |
| Regulatory action on big tech | XLK headwind; individual names |
| AI capex increase from hyperscalers | Semis bullish (NVDA, AVGO, AMAT) |

### Geopolitical / Risk
| Headline Signal | Impact |
|----------------|--------|
| New tariffs / trade war escalation | Risk-off; USD up; global growth concern |
| Sanctions on energy exporters | Oil volatile; XLE |
| Military conflict escalation | VIX spike; gold up; oil up |
| Trade deal / de-escalation | Risk-on relief rally |

---

## Impact Scoring (use in report)
Assign each significant headline one of:
- 🟢 **Bullish** — likely supports equity prices
- 🔴 **Bearish** — likely pressures equity prices
- 🟡 **Mixed** — sector-specific or offsetting effects
- ⚪ **Neutral** — informational, no clear near-term direction

## How to Apply in Report
1. Read today's news from `data/processed/YYYY-MM-DD_news.json`
2. Group by category
3. For each category, identify the 1–2 most market-relevant headlines
4. Assign impact score
5. Cross-reference with today's price action:
   - If Gold is up AND news shows risk-off headlines → confirm defensive bias
   - If Oil is down AND news shows OPEC supply increase → fundamental, not just noise
   - If tech sector weak AND no negative tech headlines → may be rotation, not fear
6. Summarise in 3–5 bullets: "what the news says vs what the market did today"

## Red Flags (always escalate in report)
- Fed surprise (unscheduled statement or significant policy shift)
- Major earnings miss from S&P 500 top-10 constituents
- VIX spike > 20% intraday with no obvious catalyst in news → hidden risk
- Oil > +5% or < -5% in one day without OPEC/geopolitical explanation

## Rules
- Do not invent impact. If the headline is ambiguous, mark as Mixed.
- One bad headline does not override a bullish price trend.
- News confirms or challenges the data — it does not replace it.
- Prioritise news from the last 24 hours; label older articles as "background".

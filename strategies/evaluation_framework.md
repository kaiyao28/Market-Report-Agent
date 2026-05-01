# Strategy Evaluation Framework

## Purpose
Provides a structured, factor-based assessment that drives the **Strategy Evaluation** section of the daily report. Converts raw signals into a single composite score and three trigger conditions.

---

## Four Factors (–2 to +2 each)

### 1. Momentum
Measures trend health across asset classes.

| Score | Condition |
|-------|-----------|
| +2 | GTAA ≥5/6 assets above 200MA **and** Dual Momentum RISK-ON |
| +1 | GTAA 3–4/6 **and** Dual Momentum RISK-ON |
|  0 | GTAA 3/6 **but** Dual Momentum RISK-OFF, or mixed |
| −1 | GTAA ≤2/6 **or** Dual Momentum RISK-OFF with partial uptrend |
| −2 | GTAA ≤1/6 **and** Dual Momentum RISK-OFF |

**Data sources:** GTAA score (Faber 200MA rule across 6 assets), SPY YTD as absolute momentum proxy (Antonacci Dual Momentum).

---

### 2. Valuation
Measures whether equities are priced for adequate future returns.

| Score | Condition |
|-------|-----------|
| +1 | CAPE < 28 (within historical fair-value range) |
|  0 | CAPE 28–35 (elevated but post-2000 normal) |
| −1 | CAPE 35–40 (stretched; compressed risk premium) |
| −2 | CAPE > 40 (historically extreme top decile) |

If Fed Model spread (Earnings Yield − 10Y yield) is negative, this reinforces the −1 or −2 reading. Valuation is a poor short-term timing tool but sets the ceiling for long-term return expectations.

**Data sources:** Shiller CAPE (multpl.com), Fed Model spread derived from PE and ^TNX.

---

### 3. Crowding
Measures how extended the market is — the higher the crowding, the higher the reversal risk.

| Score | Condition |
|-------|-----------|
| +1 | < 5% of universe with RSI > 78; index RSI < 60 |
|  0 | 5–10% overbought; index RSI 60–75 |
| −1 | > 10% overbought **or** index RSI > 75 |
| −2 | > 15% overbought **and** index RSI > 80 |

"Universe" = Nasdaq 100 stocks (excluding indices, sectors, commodities). The **% overbought** metric is unique to this section and not shown elsewhere in the report.

**Data sources:** RSI-14 across all Nasdaq 100 constituents.

---

### 4. Macro
Measures the external environment via volatility, rates, and commodity proxies.

| Score | Adjustment |
|-------|------------|
| +1 | VIX < 16 (calm) |
| +1 | Copper 5D > +1% (growth proxy positive) |
| −1 | VIX > 25 (fear elevated) |
| −1 | Gold rising 5D > +2% while Oil falling (flight-to-safety bid) |

Scores are summed and capped at ±2. Evidence uses **directional signals**, not exact metric values (those are shown in the Market State and Commodities sections).

---

## Total Score

Sum of all four factors. Range: **−8 to +8**.

| Range | Label |
|-------|-------|
| +4 to +8 | Bullish |
| +1 to +3 | Mildly Bullish |
| −1 to 0  | Neutral / Mixed |
| −3 to −2 | Cautious |
| −8 to −4 | Bearish |

---

## Trigger Conditions

Three forward-looking conditions updated daily — these express what **would change the current thesis**, not what is currently true.

- **Bullish continuation:** SPY holds 20MA · GTAA stays ≥5 · RSI normalizes to 50–70
- **Risk-off trigger:** SPY YTD flips negative · GTAA drops to ≤2 · VIX breaks 25
- **Rotation signal:** Defensive sectors outperform cyclicals 3+ sessions · Tech/semis underperform

---

## Design Rules

1. **No metric repetition** — evidence uses derived signals, not raw numbers already shown in Market State, Valuation, or Sector Flow sections.
2. **Exactly 4 factors** — one score each, summed to a single total.
3. **1–2 evidence points per factor** — brief and non-redundant.
4. **Under 25% of total report space** — evaluation card must not dominate the layout.
5. **Evaluation ≠ prediction** — it reflects current positioning relative to historical baselines, not a forecast.

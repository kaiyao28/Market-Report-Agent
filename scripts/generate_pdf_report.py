"""
Decision-optimized daily market report.
Pipeline: indicators CSV → HTML → Chrome headless → PDF
No charts — signal compression over data completeness.
"""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

BASE     = Path(__file__).parent.parent
DATA_DIR = BASE / "data" / "processed"
RPT_DIR  = BASE / "reports"
TODAY    = date.today().isoformat()
CHROME   = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

NAVY  = "#1B2A4A"
BLUE  = "#2E86AB"
GREEN = "#1DB954"
RED   = "#E63946"
AMBER = "#F4A261"
BG    = "#F4F6F9"
CARD  = "#FFFFFF"
TEXT  = "#1C2B3A"
MUTED = "#8494A9"
BORDER = "#DDE3ED"

SECTOR_MAP = {
    "XLK": "Technology",    "XLF": "Financials",    "XLE": "Energy",
    "XLV": "Health Care",   "XLI": "Industrials",   "XLY": "Cons. Discretionary",
    "XLP": "Cons. Staples", "XLU": "Utilities",     "XLB": "Materials",
    "XLRE": "Real Estate",  "XLC": "Comm. Services",
}
SECTOR_SHORT = {
    "XLK": "Technology",    "XLF": "Financials",    "XLE": "Energy",
    "XLV": "Health Care",   "XLI": "Industrials",   "XLY": "Cons. Disc.",
    "XLP": "Cons. Stpls",   "XLU": "Utilities",     "XLB": "Materials",
    "XLRE": "Real Estate",  "XLC": "Comm. Serv.",
}
SECTOR_GROUP = {
    "XLK": "Growth",    "XLC": "Growth",
    "XLY": "Cyclical",  "XLI": "Cyclical",  "XLF": "Cyclical",
    "XLB": "Cyclical",  "XLE": "Cyclical",
    "XLP": "Defensive", "XLU": "Defensive", "XLV": "Defensive", "XLRE": "Defensive",
}
COMM_MAP = {
    "CL=F": "WTI Crude", "BZ=F": "Brent Crude", "GC=F": "Gold",
    "SI=F": "Silver",    "HG=F": "Copper",       "NG=F": "Nat Gas",
}
INDICES  = ["SPY", "QQQ", "DIA", "IWM", "^VIX", "^TNX"]
VOL_TICKS = ["^VVIX", "VXX", "VXZ"]
MACRO_TICKS = ["DX-Y.NYB", "HYG", "LQD"]
SECTORS  = list(SECTOR_MAP.keys())
COMMS    = list(COMM_MAP.keys())
EXCLUDE  = set(INDICES + VOL_TICKS + MACRO_TICKS + SECTORS + COMMS)


def load_data():
    ind_path = DATA_DIR / f"{TODAY}_indicators.csv"
    if not ind_path.exists():
        sys.exit(f"Indicators not found: {ind_path}\nRun calculate_indicators.py first.")
    df = pd.read_csv(ind_path)
    valuation = json.loads((DATA_DIR / "valuation_snapshot.json").read_text()) \
                if (DATA_DIR / "valuation_snapshot.json").exists() else {}
    news_path = DATA_DIR / f"{TODAY}_news.json"
    news = json.loads(news_path.read_text()) if news_path.exists() else {}
    return df, valuation, news


def _safe(v, default=0):
    if v is None:
        return default
    try:
        f = float(v)
        return default if np.isnan(f) else f
    except (ValueError, TypeError):
        return default


def pct(v, d=1):
    v = _safe(v, None)
    if v is None:
        return "—"
    return f"{'+' if v >= 0 else ''}{v * 100:.{d}f}%"


def price(v, d=2):
    v = _safe(v, None)
    if v is None:
        return "—"
    return f"{v:,.{d}f}"


def _index_state(r):
    rsi      = _safe(r.get("rsi14"), 50)
    ret_1d   = _safe(r.get("ret_1d"), 0)
    above_50 = bool(r.get("above_50ma", False))
    above_200 = bool(r.get("above_200ma", False))
    arrow = "↑" if ret_1d >= 0 else "↓"
    if rsi > 75:
        label, color = "Overbought", AMBER
    elif above_50 and rsi > 55:
        label, color = "Strong", GREEN
    elif above_200:
        label, color = "Moderate", MUTED
    else:
        label, color = "Weak", RED
    warn = " ⚠" if rsi > 75 else (" oversold" if rsi < 30 else "")
    return f"{arrow} {label}", f"RSI {rsi:.0f}{warn}", color


def _comm_val(com_df, ticker, col):
    row = com_df[com_df["ticker"] == ticker]
    return _safe(row.iloc[0].get(col)) if len(row) > 0 else 0


def _risk_score(idx, strat_df, valuation, above_200_ct):
    if above_200_ct >= 5:   mom = 0
    elif above_200_ct >= 3: mom = 1
    elif above_200_ct >= 1: mom = 2
    else:                   mom = 3

    cape = valuation.get("sp500_shiller_cape")
    if   cape and cape > 40: val = 3
    elif cape and cape > 35: val = 2
    elif cape and cape > 28: val = 1
    else:                    val = 0 if cape else 1

    crowd = 0
    for t in ["SPY", "QQQ", "DIA", "IWM"]:
        if t in idx.index and _safe(idx.loc[t, "rsi14"], 50) > 80:
            crowd += 1
    n_ob = len(strat_df[strat_df["rsi14"] > 78]) if len(strat_df) > 0 else 0
    if n_ob / max(len(strat_df), 1) > 0.15:
        crowd += 1
    crowd = min(4, int(crowd))

    return min(10, mom + val + crowd), mom, val, crowd


def _dots(filled, total):
    return "●" * filled + "○" * (total - filled)


def _news_score(a):
    t = a.get("title", "").lower()
    score = 0
    for w in ["fed", "fomc", "rate", "cpi", "gdp", "crash", "recession", "tariff", "war"]:
        if w in t: score += 2
    for w in ["nvidia", "apple", "microsoft", "earnings", "beat", "miss", "oil", "inflation"]:
        if w in t: score += 1
    return score


def _impact_icon(title):
    t = title.lower()
    for icon, words in [
        ("🔴", ["crash", "plunge", "slump", "recession", "tariff", "war", "miss", "layoff", "downgrade"]),
        ("🟢", ["rally", "surge", "beat", "record", "growth", "upgrade", "deal", "profit", "bullish"]),
        ("🟡", ["mixed", "flat", "uncertain", "watch", "expected"]),
    ]:
        if any(w in t for w in words):
            return icon
    return "⚪"


def build_html(df, valuation, news):
    idx      = df[df["ticker"].isin(INDICES)].set_index("ticker")
    sec      = df[df["ticker"].isin(SECTORS)].copy()
    sec["name"]  = sec["ticker"].map(SECTOR_MAP)
    sec["short"] = sec["ticker"].map(SECTOR_SHORT)
    sec      = sec.sort_values("sector_score", ascending=False)
    com      = df[df["ticker"].isin(COMMS)].copy()
    strat_df = df[~df["ticker"].isin(EXCLUDE)].copy()
    strat_df["aqr_score"] = strat_df["ytd"].fillna(0) - strat_df["ret_20d"].fillna(0)

    # ── core scalars ──────────────────────────────────────────────────────────
    def _idx(t, col):
        return _safe(idx.loc[t, col]) if t in idx.index else 0

    spy_rsi  = _idx("SPY", "rsi14") or 50
    qqq_rsi  = _idx("QQQ", "rsi14") or 50
    spy_ytd  = _safe(idx.loc["SPY", "ytd"]) if "SPY" in idx.index else None
    spy_ma20 = _safe(idx.loc["SPY", "ma20"]) if "SPY" in idx.index else None
    vix_val  = _safe(idx.loc["^VIX", "last_price"]) if "^VIX" in idx.index else None
    spy_ab50 = bool(idx.loc["SPY", "above_50ma"]) if "SPY" in idx.index else False

    trailing_pe  = valuation.get("sp500_trailing_pe")
    shiller_cape = valuation.get("sp500_shiller_cape")
    val_updated  = valuation.get("updated", "—")
    earnings_yield = round(100 / trailing_pe, 2) if trailing_pe else None

    tnx_price = _safe(idx.loc["^TNX", "last_price"]) if "^TNX" in idx.index else None
    yield_10y = round(tnx_price, 3) if tnx_price else None

    fed_spread = round(earnings_yield - yield_10y, 2) if earnings_yield and yield_10y else None
    fed_signal = ("Equities cheap vs bonds" if fed_spread and fed_spread > 0
                  else "Equities expensive vs bonds") if fed_spread is not None else "—"
    fed_color  = GREEN if fed_spread and fed_spread > 0 else RED

    # commodity values
    gold_5d   = _comm_val(com, "GC=F", "ret_5d")
    oil_5d    = _comm_val(com, "CL=F", "ret_5d")
    copper_5d = _comm_val(com, "HG=F", "ret_5d")

    # ── strategy signals ──────────────────────────────────────────────────────
    dual_signal = "RISK-ON" if spy_ytd and spy_ytd > 0 else "RISK-OFF"
    dual_color  = GREEN if dual_signal == "RISK-ON" else RED

    gtaa_tickers  = ["SPY", "QQQ", "IWM", "GC=F", "XLE", "XLRE"]
    gtaa_df       = df[df["ticker"].isin(gtaa_tickers)].copy()
    above_200_ct  = int(gtaa_df["above_200ma"].sum()) if "above_200ma" in gtaa_df.columns else 0
    if above_200_ct >= 5:   gtaa_regime, gtaa_color = "Full Risk-On", GREEN
    elif above_200_ct >= 3: gtaa_regime, gtaa_color = "Selective", AMBER
    elif above_200_ct >= 1: gtaa_regime, gtaa_color = "Defensive", AMBER
    else:                   gtaa_regime, gtaa_color = "Risk-Off", RED

    if spy_rsi > 75:
        bias, bias_color = "Extended Bullish", AMBER
    elif spy_ytd and spy_ytd > 0 and spy_ab50:
        bias, bias_color = "Bullish", GREEN
    elif spy_ytd and spy_ytd < -0.03:
        bias, bias_color = "Bearish", RED
    else:
        bias, bias_color = "Neutral", MUTED

    rs, mom_risk, val_risk, crowd_risk = _risk_score(idx, strat_df, valuation, above_200_ct)
    risk_color = RED if rs >= 7 else (AMBER if rs >= 4 else GREEN)
    risk_label = "High" if rs >= 7 else ("Moderate" if rs >= 4 else "Low")

    ob_ct = sum(1 for t in ["SPY", "QQQ"] if t in idx.index and _safe(idx.loc[t, "rsi14"], 50) > 75)
    if above_200_ct >= 5 and dual_signal == "RISK-ON":
        regime_label = "Extended Risk-On (Crowded)" if ob_ct >= 2 else "Full Risk-On"
    elif above_200_ct >= 3 and dual_signal == "RISK-ON":
        regime_label = "Selective Risk-On"
    elif dual_signal == "RISK-OFF":
        regime_label = "Risk-Off — Defensive"
    else:
        regime_label = "Transitioning / Defensive"
    regime_color = AMBER if ("Crowded" in regime_label or "Selective" in regime_label) else \
                   (GREEN if "Full" in regime_label else RED)

    vix_str   = f"{vix_val:.1f}" if vix_val else "—"
    vix_label = "Low Fear" if vix_val and vix_val < 20 else ("Elevated" if vix_val and vix_val < 30 else "High Fear ⚠")
    vix_color = GREEN if vix_val and vix_val < 20 else (AMBER if vix_val and vix_val < 30 else RED)

    # ── index state block ─────────────────────────────────────────────────────
    index_lines_html = ""
    for ticker, name in [("SPY", "S&P 500"), ("QQQ", "Nasdaq 100"), ("IWM", "Russell 2K"), ("DIA", "Dow Jones")]:
        if ticker not in idx.index:
            continue
        r = idx.loc[ticker]
        state, rsi_lbl, color = _index_state(r)
        index_lines_html += f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:7px 0;border-bottom:1px solid {BG};">
          <div style="font-weight:600;color:{TEXT};font-size:12.5px;">{name}
            <span style="font-family:monospace;font-size:10.5px;color:{BLUE};margin-left:4px;">{ticker}</span>
          </div>
          <div style="display:flex;gap:10px;align-items:center;">
            <span style="color:{color};font-weight:700;font-size:12.5px;">{state}</span>
            <span style="color:{MUTED};font-size:11px;">{rsi_lbl}</span>
            <span style="color:{MUTED};font-size:11px;">{pct(_safe(r.get('ret_1d')))}</span>
          </div>
        </div>"""
    index_lines_html += f"""
    <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 0;">
      <div style="font-weight:600;color:{TEXT};font-size:12.5px;">VIX
        <span style="font-size:10.5px;color:{MUTED};margin-left:4px;">Fear</span>
      </div>
      <div style="display:flex;gap:10px;align-items:center;">
        <span style="color:{vix_color};font-weight:700;font-size:12.5px;">{vix_str}</span>
        <span style="color:{MUTED};font-size:11px;">{vix_label}</span>
      </div>
    </div>"""

    # ── sector flow ───────────────────────────────────────────────────────────
    # Strict direction: positive sector_score → strong, negative → weak
    sec_strong = sec[sec["sector_score"] > 0].sort_values("sector_score", ascending=False)
    sec_weak   = sec[sec["sector_score"] <= 0].sort_values("sector_score")

    def _sec_item(r):
        s   = _safe(r.get("sector_score"))
        r5d = _safe(r.get("ret_5d"))
        c   = GREEN if s > 0.001 else (RED if s < -0.001 else MUTED)
        arrow = "↑" if s > 0.001 else ("↓" if s < -0.001 else "→")
        return (
            f'<div style="display:flex;align-items:center;gap:5px;padding:4px 6px;border-radius:5px;">'
            f'<span style="color:{c};font-weight:700;font-size:13px;min-width:14px;text-align:center;">{arrow}</span>'
            f'<span style="font-weight:600;font-size:11.5px;color:{TEXT};flex:1;">{r["short"]}</span>'
            f'<span style="color:{c};font-size:11px;font-weight:700;font-family:monospace;">{r5d*100:+.1f}%</span>'
            f'</div>'
        )

    strong_grid = "".join(_sec_item(r) for _, r in sec_strong.iterrows())
    weak_grid   = "".join(_sec_item(r) for _, r in sec_weak.iterrows())

    # Group rotation: Cyclical / Defensive / Growth
    grp = {"Cyclical": [], "Defensive": [], "Growth": []}
    for _, r in sec.iterrows():
        g = SECTOR_GROUP.get(r["ticker"])
        if g:
            grp[g].append(_safe(r.get("sector_score")))

    grp_avg = {g: (sum(v) / len(v) if v else 0) for g, v in grp.items()}
    leader  = max(grp_avg, key=grp_avg.get)
    lagger  = min(grp_avg, key=grp_avg.get)
    spread  = grp_avg[leader] - grp_avg[lagger]

    if spread < 0.0005:
        rotation_msg, rotation_col = "No dominant rotation — sectors moving in tandem", MUTED
    elif leader == "Defensive":
        rotation_msg, rotation_col = f"Defensives leading → late-cycle signal, reduce aggression", AMBER
    elif leader == "Cyclical":
        rotation_msg, rotation_col = f"Cyclicals leading → confirms risk-on regime", GREEN
    else:
        rotation_msg, rotation_col = f"Growth leading → momentum concentrated in tech / media", BLUE

    # ── key signals ───────────────────────────────────────────────────────────
    ob_indices = [t for t in ["SPY", "QQQ", "DIA", "IWM"]
                  if t in idx.index and _safe(idx.loc[t, "rsi14"], 50) > 75]
    signals = []
    if len(ob_indices) >= 2:
        rsis = [f"{_safe(idx.loc[t,'rsi14'],50):.0f}" for t in ob_indices]
        signals.append(("⚠", f"Multiple indices overbought — {', '.join(ob_indices)} (RSI {', '.join(rsis)})", AMBER))
    elif len(ob_indices) == 1:
        t = ob_indices[0]
        signals.append(("⚠", f"{t} overbought — RSI {_safe(idx.loc[t,'rsi14'],50):.0f}", AMBER))
    else:
        signals.append(("✓", "Indices not overbought — RSI within normal range", GREEN))

    if grp_avg.get("Defensive", 0) > grp_avg.get("Cyclical", 0) + 0.001:
        signals.append(("📊", "Defensive sectors outperforming — rotation to safety underway", AMBER))
    elif grp_avg.get("Cyclical", 0) > grp_avg.get("Defensive", 0) + 0.001:
        top_name = sec.iloc[0]["short"] if len(sec) > 0 else "—"
        signals.append(("📈", f"Cyclicals leading — {top_name} strongest", GREEN))
    else:
        signals.append(("📊", "Sector rotation neutral — no dominant theme", MUTED))

    if gold_5d > 0.02 and oil_5d < 0:
        signals.append(("🥇", f"Gold +{gold_5d*100:.1f}% 5D, oil falling — flight-to-safety signal", AMBER))
    elif copper_5d > 0.01:
        signals.append(("🔮", f"Copper +{copper_5d*100:.1f}% 5D — growth support signal", GREEN))
    else:
        signals.append(("⚖", "Commodities mixed — no clear macro direction", MUTED))

    sig_html = "".join(f"""
    <div style="display:flex;gap:10px;align-items:flex-start;padding:7px 0;border-bottom:1px solid {BG};">
      <span style="font-size:14px;">{icon}</span>
      <span style="font-size:12px;color:{TEXT};line-height:1.4;">{msg}</span>
    </div>""" for icon, msg, _ in signals)

    # ── action lists ──────────────────────────────────────────────────────────
    watchlist  = strat_df[
        (strat_df["rsi14"].between(50, 75)) &
        (strat_df["above_50ma"] == True) &
        (strat_df["ret_5d"] > 0) &
        (strat_df["aqr_score"] > 0)
    ].nlargest(5, "aqr_score")

    avoid_list = strat_df[strat_df["rsi14"] > 78].nlargest(5, "rsi14")

    bounce_list = strat_df[
        (strat_df["rsi14"] < 35) &
        (strat_df["above_200ma"] == True)
    ].nsmallest(4, "rsi14")

    def action_rows(df_rows, col):
        if len(df_rows) == 0:
            return f'<div style="color:{MUTED};font-size:11px;padding:4px 0;">None today</div>'
        html = ""
        for _, r in df_rows.iterrows():
            html += f"""<div style="padding:6px 0;border-bottom:1px solid {BG};">
              <span style="font-weight:700;color:{col};font-size:13px;">{r['ticker']}</span>
              <div style="font-size:10.5px;color:{MUTED};margin-top:1px;">
                RSI {_safe(r.get('rsi14'),0):.0f} · 5D {pct(r.get('ret_5d'))} · YTD {pct(r.get('ytd'))}
              </div>
            </div>"""
        return html

    wl_html = action_rows(watchlist,  BLUE)
    av_html = action_rows(avoid_list, RED)
    bn_html = action_rows(bounce_list, AMBER)

    # ── YTD snapshot ──────────────────────────────────────────────────────────
    top_mom    = strat_df[(strat_df["rsi14"].between(45, 75)) &
                          (strat_df["above_50ma"] == True)].nlargest(5, "ytd")
    overcrowd  = strat_df[strat_df["rsi14"] > 75].nlargest(5, "ytd")
    losing_mom = strat_df[(strat_df["ytd"] > 0.15) &
                          (strat_df["ret_5d"] < -0.02)].nlargest(5, "ytd")

    def pills(df_rows, warn=False):
        if len(df_rows) == 0:
            return f'<span style="color:{MUTED};font-size:11px;">None</span>'
        bg  = f"{RED}15" if warn else f"{BLUE}12"
        col = RED if warn else BLUE
        suf = " ⚠" if warn else ""
        return "".join(
            f'<span style="display:inline-block;background:{bg};color:{col};font-weight:600;'
            f'font-size:11px;padding:2px 8px;border-radius:4px;margin:2px 2px 2px 0;">'
            f'{r["ticker"]}{suf}</span>'
            for _, r in df_rows.iterrows()
        )

    top_pills    = pills(top_mom)
    crowd_pills  = pills(overcrowd, warn=True)
    losing_pills = pills(losing_mom)

    # ── decision + evaluation ─────────────────────────────────────────────────
    if dual_signal == "RISK-ON" and above_200_ct >= 5:
        do_item   = "Hold momentum winners — trend intact across assets"
        dont_item = "Chase overbought RSI 80+ names (reversal risk)" if ob_indices else "Add leverage into a crowded market"
    elif dual_signal == "RISK-ON" and above_200_ct >= 3:
        do_item   = "Hold only assets above 200MA; raise defensive allocation"
        dont_item = "Add new longs in broken trends (below 200MA)"
    else:
        do_item   = "Raise cash — hold defensive (XLP, XLU, GC=F)"
        dont_item = "Add equity exposure while Dual Momentum is negative"

    watch_item   = f"SPY 20MA {price(spy_ma20)}" if spy_ma20 else "SPY 20MA"
    if len(sec) > 0:
        watch_item += f" · {sec.iloc[-1]['name']} reversal watch"
    active_strat = "Momentum Rotation" if dual_signal == "RISK-ON" else "Defensive / Risk-Off"

    # evaluation factors (–2 to +2 each; evidence avoids metrics already shown above)
    n_ob   = len(strat_df[strat_df["rsi14"] > 78])
    pct_ob = n_ob / max(len(strat_df), 1)
    max_idx_rsi = max((_safe(idx.loc[t, "rsi14"], 50) for t in ["SPY", "QQQ"] if t in idx.index), default=50)

    # Momentum
    if above_200_ct >= 5 and dual_signal == "RISK-ON":
        e_mom_r, e_mom_s, e_mom_ev = "Strong",  +2, f"Trend intact: {above_200_ct}/6 tracked assets · Absolute momentum positive"
    elif above_200_ct >= 3 and dual_signal == "RISK-ON":
        e_mom_r, e_mom_s, e_mom_ev = "Moderate", +1, f"Partial trend: {above_200_ct}/6 assets · Dual momentum positive"
    elif above_200_ct >= 3:
        e_mom_r, e_mom_s, e_mom_ev = "Mixed",    0, f"{above_200_ct}/6 in uptrend · Absolute momentum negative"
    elif dual_signal == "RISK-OFF":
        e_mom_r, e_mom_s, e_mom_ev = "Weak",    -2, f"Trend breakdown: {above_200_ct}/6 above 200MA · Dual momentum negative"
    else:
        e_mom_r, e_mom_s, e_mom_ev = "Weak",    -1, f"Only {above_200_ct}/6 assets in uptrend"

    # Valuation (uses CAPE magnitude without repeating the number — shown in Valuation section)
    if shiller_cape and shiller_cape > 40:
        e_val_r, e_val_s = "Expensive", -2
        e_val_ev = f"CAPE in top historical decile · {'Equities costly vs bonds' if fed_spread and fed_spread < 0 else 'Spread near zero'}"
    elif shiller_cape and shiller_cape > 35:
        e_val_r, e_val_s = "Stretched", -1
        e_val_ev = "CAPE well above long-run average · Compressed equity risk premium"
    elif shiller_cape and shiller_cape > 28:
        e_val_r, e_val_s = "Neutral",    0
        e_val_ev = "CAPE elevated but within post-2000 normal range"
    elif shiller_cape:
        e_val_r, e_val_s = "Fair",      +1
        e_val_ev = "CAPE within historical fair-value range"
    else:
        e_val_r, e_val_s = "—",          0
        e_val_ev = "Valuation data unavailable"

    # Crowding (uses % overbought — NOT shown elsewhere in this report)
    if max_idx_rsi > 80 and pct_ob > 0.15:
        e_crd_r, e_crd_s = "Crowded",  -2
        e_crd_ev = f"{pct_ob*100:.0f}% of universe overbought · Index breadth at extremes"
    elif max_idx_rsi > 75 or pct_ob > 0.10:
        e_crd_r, e_crd_s = "Elevated", -1
        e_crd_ev = f"{pct_ob*100:.0f}% of universe overbought · Gains concentrated in leaders"
    elif pct_ob < 0.05:
        e_crd_r, e_crd_s = "Normal",   +1
        e_crd_ev = f"{pct_ob*100:.0f}% overbought · Broad participation across universe"
    else:
        e_crd_r, e_crd_s = "Neutral",   0
        e_crd_ev = f"{pct_ob*100:.0f}% overbought · Within normal distribution"

    # Macro (derived signals, not raw metrics repeated from header)
    e_mac_s = 0
    e_mac_pts = []
    if vix_val and vix_val < 16:
        e_mac_s += 1; e_mac_pts.append("VIX in low range — calm environment")
    elif vix_val and vix_val > 25:
        e_mac_s -= 1; e_mac_pts.append("VIX elevated — fear rising")
    else:
        e_mac_pts.append("VIX in neutral range")
    if gold_5d > 0.02 and oil_5d < 0:
        e_mac_s -= 1; e_mac_pts.append("Gold/oil divergence — safe-haven flows active")
    elif copper_5d > 0.01:
        e_mac_s += 1; e_mac_pts.append("Copper bid — growth proxy positive")
    else:
        e_mac_pts.append("Commodities mixed — no directional macro signal")
    e_mac_s = max(-2, min(2, e_mac_s))
    e_mac_r  = "Supportive" if e_mac_s >= 1 else ("Concerning" if e_mac_s <= -1 else "Neutral")
    e_mac_ev = " · ".join(e_mac_pts[:2])

    # Total score and label
    e_total = e_mom_s + e_val_s + e_crd_s + e_mac_s
    if   e_total >= 4:  e_label, e_col = "Bullish",        GREEN
    elif e_total >= 1:  e_label, e_col = "Mildly Bullish", GREEN
    elif e_total >= -1: e_label, e_col = "Neutral / Mixed", MUTED
    elif e_total >= -3: e_label, e_col = "Cautious",        AMBER
    else:               e_label, e_col = "Bearish",         RED

    # Score interpretation
    e_interp = {
        "Bullish":        "Full deployment warranted — all factors aligned",
        "Mildly Bullish": "Selective entries OK — monitor crowding levels",
        "Neutral / Mixed":"Hold only — no new large entries until score improves",
        "Cautious":       "Reduce aggression — trim high-RSI, do not exit entirely",
        "Bearish":        "Defensive posture — raise cash, favour bonds/gold",
    }[e_label]

    # Trigger conditions (forward-looking, not current data)
    spy_ma20_str = price(spy_ma20) if spy_ma20 else "20MA"
    t_bull  = f"SPY holds {spy_ma20_str} · GTAA stays ≥5 · RSI normalizes to 50–70"
    t_risk  = f"SPY YTD flips negative · GTAA drops to ≤2 · VIX breaks 25"
    t_rot   = "Defensive outperforms cyclicals 3+ sessions · Tech / semis underperform"

    # Probability scenarios (derived from evaluation score, not forecasts)
    if e_total >= 3:
        prob_scenarios = [("Bull continuation", 60, "+3–6%", GREEN),
                          ("Sideways / consolidation", 30, "±2%", MUTED),
                          ("Correction", 10, "−5%", RED)]
    elif e_total >= 0:
        prob_scenarios = [("Bull continuation", 45, "+2–4%", GREEN),
                          ("Sideways", 35, "±2%", MUTED),
                          ("Correction", 20, "−5–8%", RED)]
    elif e_total >= -2:
        prob_scenarios = [("Bull continuation", 35, "+2–3%", GREEN),
                          ("Sideways", 35, "±2%", MUTED),
                          ("Correction", 30, "−6–10%", RED)]
    else:
        prob_scenarios = [("Bull continuation", 20, "+1–3%", GREEN),
                          ("Sideways", 30, "±3%", MUTED),
                          ("Correction", 50, "−10–15%", RED)]

    prob_html = ""
    for label_s, prob, expected, col in prob_scenarios:
        prob_html += (
            f'<div style="display:flex;align-items:center;padding:5px 0;border-bottom:1px solid {BG};">'
            f'<div style="flex:1;">'
            f'<div style="font-size:11px;color:{TEXT};font-weight:500;">{label_s}</div>'
            f'<div style="height:4px;background:{BG};border-radius:2px;margin-top:3px;overflow:hidden;">'
            f'<div style="height:100%;width:{prob}%;background:{col};border-radius:2px;"></div></div></div>'
            f'<div style="text-align:right;margin-left:10px;min-width:85px;">'
            f'<span style="font-weight:700;color:{col};">{prob}%</span>'
            f'<span style="color:{MUTED};font-size:10.5px;"> · {expected}</span></div></div>'
        )

    # ── breadth (internal market structure) ──────────────────────────────────
    pct_above_50ma  = _safe(strat_df["above_50ma"].mean())  * 100
    pct_above_200ma = _safe(strat_df["above_200ma"].mean()) * 100
    pct_advancing   = _safe((strat_df["ret_1d"] > 0).mean()) * 100

    def _breadth_col(v, hi, lo):
        return GREEN if v >= hi else (MUTED if v >= lo else RED)

    ba50_col  = _breadth_col(pct_above_50ma,  hi=65, lo=45)
    ba200_col = _breadth_col(pct_above_200ma, hi=60, lo=40)
    adv_col   = _breadth_col(pct_advancing,   hi=60, lo=45)

    spy_1d_pos = "SPY" in idx.index and _idx("SPY", "ret_1d") > 0
    if spy_1d_pos and pct_advancing < 45:
        breadth_signal, breadth_sig_col = "⚠ Narrow rally — SPY up but breadth weak", AMBER
    elif pct_advancing > 65:
        breadth_signal, breadth_sig_col = "Broad participation — healthy internals", GREEN
    else:
        breadth_signal, breadth_sig_col = "Normal breadth distribution", MUTED

    # ── vol structure (VXX short-term / VXZ mid-term ratio) ──────────────────
    vxx_price = _safe(idx.loc["VXX", "last_price"]) if "VXX" in idx.index else None
    vxz_price = _safe(idx.loc["VXZ", "last_price"]) if "VXZ" in idx.index else None
    vvix_val  = _safe(idx.loc["^VVIX", "last_price"]) if "^VVIX" in idx.index else None

    if vxx_price and vxz_price and vxz_price > 0:
        term_ratio = vxx_price / vxz_price
        if term_ratio < 0.85:
            vol_struct, vol_struct_col = "Contango — normal, vol suppressed", GREEN
        elif term_ratio < 1.0:
            vol_struct, vol_struct_col = "Mild contango — approaching neutral", MUTED
        else:
            vol_struct, vol_struct_col = "Backwardation ⚠ — fear spike / market stress", RED
        vol_struct_detail = f"VXX/VXZ {term_ratio:.2f}"
    else:
        vol_struct, vol_struct_col = None, MUTED
        vol_struct_detail = ""

    vvix_str = f"VVIX {vvix_val:.0f}" if vvix_val else ""
    if vvix_val and vvix_val > 100:
        vvix_note = " ⚠ vol-of-vol elevated"
    elif vvix_val and vvix_val < 80:
        vvix_note = " — calm"
    else:
        vvix_note = ""

    # ── cross-asset macro (DXY, credit spread) ───────────────────────────────
    dxy_1d = _safe(idx.loc["DX-Y.NYB", "ret_1d"]) if "DX-Y.NYB" in idx.index else None
    hyg_1d = _safe(idx.loc["HYG", "ret_1d"]) if "HYG" in idx.index else None
    lqd_1d = _safe(idx.loc["LQD", "ret_1d"]) if "LQD" in idx.index else None

    if hyg_1d is not None and lqd_1d is not None:
        credit_spread_chg = hyg_1d - lqd_1d
        if credit_spread_chg < -0.002:
            credit_signal, credit_col = "HY underperforming IG — credit stress", RED
        elif credit_spread_chg > 0.002:
            credit_signal, credit_col = "HY outperforming IG — risk appetite positive", GREEN
        else:
            credit_signal, credit_col = "HY/IG spread stable", MUTED
    else:
        credit_signal, credit_col = None, MUTED

    dxy_signal = None
    if dxy_1d is not None:
        if dxy_1d > 0.003:
            dxy_signal, dxy_col = f"DXY rising ({pct(dxy_1d)}) — headwind for commodities/EM", AMBER
        elif dxy_1d < -0.003:
            dxy_signal, dxy_col = f"DXY falling ({pct(dxy_1d)}) — tailwind for risk assets", GREEN
        else:
            dxy_signal, dxy_col = f"DXY stable ({pct(dxy_1d)})", MUTED

    # ── executive decision block ──────────────────────────────────────────────
    if e_total >= 4:
        exec_stance = "Deploy capital — full risk-on"
        exec_detail = "All major factors aligned. Favour high-momentum quality names."
    elif e_total >= 2:
        exec_stance = "Stay invested — favour momentum leaders"
        exec_detail = "Trend positive. Selective entries only; avoid overbought names."
    elif e_total >= 0:
        exec_stance = "Hold — no new aggressive entries"
        exec_detail = "Mixed signals. Protect gains, wait for a cleaner setup."
    elif e_total >= -2:
        exec_stance = "Stay invested, reduce aggression"
        exec_detail = "Trend intact but overbought and expensive. Trim, do not exit."
    elif e_total >= -4:
        exec_stance = "Reduce risk — trim selectively"
        exec_detail = "Multiple warning signals. Raise cash gradually."
    else:
        exec_stance = "Defensive — raise cash"
        exec_detail = "Risk-off across frameworks. Favour bonds, cash, gold."

    exec_factors = [
        (e_mom_s, f"Momentum {e_mom_r}", e_mom_ev.split(' · ')[0]),
        (e_val_s, f"Valuation {e_val_r}", e_val_ev.split(' · ')[0]),
        (e_crd_s, f"Crowding {e_crd_r}", e_crd_ev.split(' · ')[0]),
        (e_mac_s, f"Macro {e_mac_r}", e_mac_ev.split(' · ')[0]),
    ]
    exec_factors.sort(key=lambda x: (-abs(x[0]), x[0]))

    exec_why_html = "".join(
        f'<div style="font-size:11.5px;color:{TEXT};padding:3px 0;line-height:1.5;">'
        f'<span style="color:{"#2E86AB" if s > 0 else ("#E63946" if s < 0 else MUTED)};font-weight:700;margin-right:4px;">{"▲" if s > 0 else ("▼" if s < 0 else "—")}</span>'
        f'<strong>{lbl}:</strong> {det}</div>'
        for s, lbl, det in exec_factors[:2]
    )

    exec_action_items = [do_item]
    ob_idx_tickers = [t for t in ["SPY", "QQQ"] if t in idx.index and _safe(idx.loc[t, "rsi14"], 50) > 80]
    if ob_idx_tickers:
        exec_action_items.append(f"Trim / avoid: {', '.join(ob_idx_tickers)} — RSI at extremes")
    elif len(watchlist) > 0:
        exec_action_items.append(f"Watchlist: {', '.join(watchlist['ticker'].head(3).tolist())}")
    if len(bounce_list) > 0:
        exec_action_items.append(f"Bounce watch: {', '.join(bounce_list['ticker'].head(2).tolist())} (oversold + above 200MA)")
    elif e_total < 0:
        exec_action_items.append("No new entries until evaluation score improves")
    exec_action_items = exec_action_items[:3]

    exec_action_html = "".join(
        f'<div style="font-size:11.5px;color:{TEXT};padding:3px 0;line-height:1.5;">'
        f'<span style="color:{BLUE};font-weight:700;margin-right:4px;">→</span>{action}</div>'
        for action in exec_action_items
    )

    def _factor_row(label, rating, score, evidence):
        sc = GREEN if score > 0 else (RED if score < 0 else MUTED)
        sign = f"+{score}" if score > 0 else str(score)
        rating_col = GREEN if score > 0 else (RED if score < 0 else MUTED)
        return (
            f'<tr style="border-bottom:1px solid {BG};">'
            f'<td style="padding:6px 10px;font-weight:600;color:{TEXT};white-space:nowrap;">{label}</td>'
            f'<td style="padding:6px 10px;font-weight:600;color:{rating_col};white-space:nowrap;">{rating}</td>'
            f'<td style="padding:6px 10px;font-weight:700;color:{sc};white-space:nowrap;text-align:center;">{sign}</td>'
            f'<td style="padding:6px 10px;font-size:11px;color:{MUTED};">{evidence}</td>'
            f'</tr>'
        )

    # ── commodities summary ───────────────────────────────────────────────────
    comm_lines_html = ""
    for ticker, name in [("CL=F","WTI Oil"),("GC=F","Gold"),("HG=F","Copper"),("NG=F","Nat Gas")]:
        row = com[com["ticker"] == ticker]
        if len(row) == 0:
            continue
        r   = row.iloc[0]
        r1d = _safe(r.get("ret_1d"))
        r5d = _safe(r.get("ret_5d"))
        c1  = GREEN if r1d >= 0 else RED
        c5  = GREEN if r5d >= 0 else RED
        tag = ""
        if name == "Gold"   and r5d > 0.02:  tag = " — hedge signal"
        elif name == "Copper" and r5d > 0.01: tag = " — growth support"
        elif name == "WTI Oil" and r5d < -0.03: tag = " — demand concern"
        comm_lines_html += f"""
        <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid {BG};">
          <span style="font-weight:600;color:{TEXT};">{name}
            <span style="color:{MUTED};font-size:10.5px;font-weight:400;">{tag}</span>
          </span>
          <span style="font-size:11.5px;">
            <span style="color:{c1};">{'↑' if r1d>=0 else '↓'} {pct(r1d)}</span>
            <span style="color:{MUTED};"> · </span>
            <span style="color:{c5};">{'↑' if r5d>=0 else '↓'} {pct(r5d)} 5D</span>
          </span>
        </div>"""

    if gold_5d > 0.02 and oil_5d < 0:
        comm_conclusion, comm_conc_col = "Flight to safety — risk-off undertone in commodities", AMBER
    elif copper_5d > 0.01 and oil_5d > 0:
        comm_conclusion, comm_conc_col = "Growth-supportive — copper + oil both positive", GREEN
    else:
        comm_conclusion, comm_conc_col = "Mixed — no clean macro direction from commodities", MUTED

    # ── top 3 catalysts ───────────────────────────────────────────────────────
    articles  = news.get("articles", [])
    top3      = sorted(articles, key=_news_score, reverse=True)[:3]
    cats_html = ""
    for a in top3:
        icon  = _impact_icon(a.get("title", ""))
        title = a.get("title", "")[:120] + ("…" if len(a.get("title","")) > 120 else "")
        cat   = a.get("category", "Markets")
        src   = a.get("source", "")[:22]
        link  = a.get("link", "#")
        cats_html += f"""
        <div style="display:flex;gap:12px;padding:9px 0;border-bottom:1px solid {BG};align-items:flex-start;">
          <span style="font-size:15px;padding-top:1px;">{icon}</span>
          <div>
            <a href="{link}" style="color:{TEXT};text-decoration:none;font-size:12px;
                                    font-weight:500;line-height:1.4;">{title}</a>
            <div style="font-size:10px;color:{MUTED};margin-top:2px;">{cat} · {src}</div>
          </div>
        </div>"""
    if not cats_html:
        cats_html = f'<div style="color:{MUTED};font-size:11px;">No news collected today</div>'

    # ── valuation strings ─────────────────────────────────────────────────────
    def fv(v, d=2):
        return f"{v:.{d}f}" if v is not None else "—"

    pe_color   = RED if trailing_pe and trailing_pe > 25 else (AMBER if trailing_pe and trailing_pe > 20 else GREEN)
    cape_color = RED if shiller_cape and shiller_cape > 35 else (AMBER if shiller_cape and shiller_cape > 28 else GREEN)
    pe_bench   = "Expensive" if trailing_pe and trailing_pe > 25 else ("Stretched" if trailing_pe and trailing_pe > 20 else "Fair")
    cape_bench = "Expensive" if shiller_cape and shiller_cape > 35 else ("Stretched" if shiller_cape and shiller_cape > 28 else "Fair")

    # ── risk score visuals ────────────────────────────────────────────────────
    risk_pct    = rs * 10
    mom_col     = GREEN if mom_risk == 0 else (AMBER if mom_risk == 1 else RED)
    val_col_s   = GREEN if val_risk == 0 else (AMBER if val_risk == 1 else RED)
    crowd_col_s = GREEN if crowd_risk <= 1 else (AMBER if crowd_risk <= 2 else RED)
    mom_dots    = _dots(3 - mom_risk, 3)
    val_dots    = _dots(3 - val_risk, 3)
    crowd_dots  = _dots(4 - crowd_risk, 4)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Market Report — {TODAY}</title>
<style>
  * {{ margin:0;padding:0;box-sizing:border-box; }}
  body {{
    font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;
    background:{BG};color:{TEXT};font-size:13px;line-height:1.5;
  }}
  .header {{
    background:linear-gradient(135deg,{NAVY} 0%,#2A3F6F 100%);
    color:white;padding:24px 40px 20px;
  }}
  .header-meta {{ font-size:10.5px;letter-spacing:1.5px;text-transform:uppercase;opacity:0.55;margin-bottom:4px; }}
  .header h1 {{ font-size:22px;font-weight:700;letter-spacing:-0.3px; }}
  .header-sub {{ font-size:11px;opacity:0.4;margin-top:5px; }}
  .badges {{ display:flex;gap:7px;margin-top:12px;flex-wrap:wrap; }}
  .badge {{
    padding:3px 11px;border-radius:14px;font-size:11px;font-weight:600;
    background:rgba(255,255,255,0.12);color:white;border:1px solid rgba(255,255,255,0.2);
  }}
  .body {{ padding:18px 32px;max-width:1080px;margin:0 auto; }}
  .card {{
    background:{CARD};border-radius:10px;border:1px solid {BORDER};
    box-shadow:0 1px 3px rgba(0,0,0,0.05);padding:16px 18px;margin-bottom:14px;
  }}
  .card-title {{
    font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;
    color:{MUTED};margin-bottom:11px;padding-bottom:7px;border-bottom:2px solid {BG};
    display:flex;align-items:center;gap:5px;
  }}
  .card-title::before {{
    content:"";display:inline-block;width:3px;height:12px;
    background:{BLUE};border-radius:2px;
  }}
  .grid-3 {{ display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px; }}
  .grid-2 {{ display:grid;grid-template-columns:1fr 1fr;gap:12px; }}
  .regime-banner {{
    background:linear-gradient(90deg,{regime_color}18 0%,{regime_color}06 100%);
    border:1px solid {regime_color}40;border-radius:10px;
    padding:14px 20px;margin-bottom:14px;
    display:flex;justify-content:space-between;align-items:center;gap:20px;
  }}
  .action-title {{
    font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.7px;
    padding-bottom:6px;border-bottom:2px solid;margin-bottom:8px;
  }}
  .do-dont-grid {{ display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px; }}
  .do-dont-label {{ font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:6px; }}
  .do-dont-item {{ font-size:11.5px;padding:5px 0;color:{TEXT};border-bottom:1px solid {BG}; }}
  .do-item::before   {{ content:"✓ ";color:{GREEN};font-weight:700; }}
  .dont-item::before {{ content:"✗ ";color:{RED};font-weight:700; }}
  .watch-item::before {{ content:"◎ ";color:{AMBER};font-weight:700; }}
  .footer {{
    text-align:center;padding:14px;font-size:10px;color:{MUTED};
    border-top:1px solid {BORDER};margin-top:8px;
  }}
  @media print {{
    body {{ background:white; }}
    .header,.regime-banner {{ -webkit-print-color-adjust:exact;print-color-adjust:exact; }}
    .card {{ break-inside:avoid; }}
  }}
</style>
</head>
<body>

<div class="header">
  <div class="header-meta">US Equity Market · Daily Research Report</div>
  <h1>Market Report — {TODAY}</h1>
  <div class="header-sub">End-of-day data · yfinance · multpl.com · Not financial advice</div>
  <div class="badges">
    <span class="badge" style="background:{bias_color}40;border-color:{bias_color}90;">Bias: {bias}</span>
    <span class="badge">VIX {vix_str} — {vix_label}</span>
    <span class="badge">SPY {pct(spy_ytd)} YTD</span>
    <span class="badge">CAPE {fv(shiller_cape)}</span>
    <span class="badge">10Y {fv(yield_10y)}%</span>
  </div>
</div>

<div class="body">

<!-- EXECUTIVE DECISION BLOCK -->
<div style="background:linear-gradient(135deg,{e_col}16,{e_col}06);border:2px solid {e_col}45;
            border-radius:10px;padding:16px 20px;margin-bottom:14px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:20px;">
    <div style="flex:1;">
      <div style="font-size:10px;text-transform:uppercase;letter-spacing:1.2px;color:{MUTED};margin-bottom:4px;">Today's Stance</div>
      <div style="font-size:21px;font-weight:700;color:{e_col};margin-bottom:3px;">{exec_stance}</div>
      <div style="font-size:11.5px;color:{MUTED};">{exec_detail}</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:13px;">
        <div>
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:{MUTED};margin-bottom:5px;">Why</div>
          {exec_why_html}
        </div>
        <div>
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:{MUTED};margin-bottom:5px;">Action</div>
          {exec_action_html}
        </div>
      </div>
    </div>
    <div style="text-align:right;min-width:90px;border-left:1px solid {e_col}25;padding-left:20px;">
      <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.7px;color:{MUTED};margin-bottom:3px;">Eval Score</div>
      <div style="font-size:34px;font-weight:700;color:{e_col};line-height:1;">{e_total:+d}</div>
      <div style="font-size:11px;color:{MUTED};margin-top:2px;">of ±8</div>
      <div style="font-size:11px;font-weight:700;color:{e_col};margin-top:4px;">{e_label}</div>
    </div>
  </div>
</div>

<!-- REGIME BANNER -->
<div class="regime-banner">
  <div>
    <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.7px;color:{MUTED};margin-bottom:3px;">Market Regime</div>
    <div style="font-size:20px;font-weight:700;color:{regime_color};">{regime_label}</div>
  </div>
  <div style="flex:1;display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;padding:0 20px;">
    <div>
      <div style="font-size:10px;color:{MUTED};text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px;">Momentum</div>
      <div style="font-size:15px;color:{mom_col};font-weight:700;letter-spacing:2px;">{mom_dots}</div>
    </div>
    <div>
      <div style="font-size:10px;color:{MUTED};text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px;">Valuation</div>
      <div style="font-size:15px;color:{val_col_s};font-weight:700;letter-spacing:2px;">{val_dots}</div>
    </div>
    <div>
      <div style="font-size:10px;color:{MUTED};text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px;">Crowding</div>
      <div style="font-size:15px;color:{crowd_col_s};font-weight:700;letter-spacing:2px;">{crowd_dots}</div>
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.7px;color:{MUTED};margin-bottom:3px;">Risk Score</div>
    <div style="font-size:26px;font-weight:700;color:{risk_color};">{rs}<span style="font-size:14px;color:{MUTED};">/10</span></div>
    <div style="font-size:10.5px;color:{risk_color};font-weight:600;">{risk_label} Risk</div>
  </div>
</div>

<!-- ROW 1: Market State | Key Signals | Strategy Signals -->
<div class="grid-3">

  <div class="card">
    <div class="card-title">Market State</div>
    {index_lines_html}
    <div style="margin-top:8px;padding-top:8px;border-top:1px solid {BG};">
      <div style="font-size:9.5px;text-transform:uppercase;letter-spacing:0.6px;color:{MUTED};margin-bottom:5px;">Breadth — Nasdaq 100 Universe</div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:4px;margin-bottom:5px;">
        <div><span style="color:{ba50_col};font-weight:700;">{pct_above_50ma:.0f}%</span> <span style="color:{MUTED};font-size:10.5px;">above 50MA</span></div>
        <div><span style="color:{ba200_col};font-weight:700;">{pct_above_200ma:.0f}%</span> <span style="color:{MUTED};font-size:10.5px;">above 200MA</span></div>
        <div><span style="color:{adv_col};font-weight:700;">{pct_advancing:.0f}%</span> <span style="color:{MUTED};font-size:10.5px;">advancing</span></div>
      </div>
      <div style="font-size:10.5px;color:{breadth_sig_col};">{breadth_signal}</div>
    </div>
    {f'<div style="margin-top:6px;padding-top:6px;border-top:1px solid {BG};"><div style="font-size:9.5px;text-transform:uppercase;letter-spacing:0.6px;color:{MUTED};margin-bottom:4px;">Vol Structure</div><div style="font-size:10.5px;color:{vol_struct_col};">{vol_struct}</div><div style="font-size:10px;color:{MUTED};">{vol_struct_detail}{" · " if vol_struct_detail and vvix_str else ""}{vvix_str}{vvix_note}</div></div>' if vol_struct else ""}
  </div>

  <div class="card">
    <div class="card-title">Key Signals</div>
    {sig_html}
    {f'<div style="display:flex;gap:10px;align-items:flex-start;padding:7px 0;border-bottom:1px solid {BG};"><span style="font-size:14px;">💵</span><span style="font-size:12px;color:{dxy_col};line-height:1.4;">{dxy_signal}</span></div>' if dxy_signal else ""}
    {f'<div style="display:flex;gap:10px;align-items:flex-start;padding:7px 0;border-bottom:1px solid {BG};"><span style="font-size:14px;">📉</span><span style="font-size:12px;color:{credit_col};line-height:1.4;">{credit_signal}</span></div>' if credit_signal else ""}
  </div>

  <div class="card">
    <div class="card-title">Strategy Signals</div>
    <div style="display:grid;gap:8px;">
      <div style="background:{dual_color}12;border:1px solid {dual_color}30;border-radius:7px;padding:10px 12px;">
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:{MUTED};">Dual Momentum</div>
        <div style="font-size:16px;font-weight:700;color:{dual_color};">{dual_signal}</div>
        <div style="font-size:10.5px;color:{MUTED};">SPY YTD {pct(spy_ytd)} · {"absolute momentum positive" if dual_signal == "RISK-ON" else "negative — favour cash"}</div>
      </div>
      <div style="background:{gtaa_color}12;border:1px solid {gtaa_color}30;border-radius:7px;padding:10px 12px;">
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:{MUTED};">Faber GTAA</div>
        <div style="font-size:16px;font-weight:700;color:{gtaa_color};">{gtaa_regime}</div>
        <div style="font-size:10.5px;color:{MUTED};">{above_200_ct}/6 tracked assets above 200MA</div>
      </div>
    </div>
  </div>

</div>

<!-- ACTION LISTS -->
<div class="card">
  <div class="card-title">Action Lists — AQR Momentum Framework</div>
  <div class="grid-3">
    <div>
      <div class="action-title" style="color:{BLUE};border-color:{BLUE}30;">● Momentum Watchlist</div>
      {wl_html}
    </div>
    <div>
      <div class="action-title" style="color:{RED};border-color:{RED}30;">● Avoid / Overbought</div>
      {av_html}
    </div>
    <div>
      <div class="action-title" style="color:{AMBER};border-color:{AMBER}50;">● RSI-2 Bounce Watch</div>
      {bn_html}
    </div>
  </div>
</div>

<!-- YTD SNAPSHOT -->
<div class="card">
  <div class="card-title">YTD Leaders — Nasdaq 100 Snapshot</div>
  <div class="grid-3">
    <div>
      <div style="font-size:10px;font-weight:700;color:{GREEN};text-transform:uppercase;letter-spacing:0.5px;margin-bottom:7px;">Top Momentum (RSI 45–75)</div>
      <div>{top_pills}</div>
    </div>
    <div>
      <div style="font-size:10px;font-weight:700;color:{RED};text-transform:uppercase;letter-spacing:0.5px;margin-bottom:7px;">Overcrowded (RSI 75+) ⚠</div>
      <div>{crowd_pills}</div>
    </div>
    <div>
      <div style="font-size:10px;font-weight:700;color:{MUTED};text-transform:uppercase;letter-spacing:0.5px;margin-bottom:7px;">Losing Momentum (5D &lt; −2%)</div>
      <div>{losing_pills}</div>
    </div>
  </div>
</div>

<!-- STRATEGY EVALUATION -->
<div class="card" style="background:linear-gradient(135deg,{NAVY}04,{BLUE}04);border-color:{BLUE}20;">
  <div class="card-title">Strategy Evaluation</div>

  <!-- Decision: 5 lines max -->
  <div style="display:grid;grid-template-columns:1fr auto;gap:16px;align-items:start;
              padding:10px 14px;background:{e_col}0A;border-left:3px solid {e_col};
              border-radius:0 7px 7px 0;margin-bottom:12px;">
    <div>
      <div style="font-size:12.5px;font-weight:700;color:{bias_color};margin-bottom:6px;">
        {bias} &nbsp;·&nbsp; {active_strat}
      </div>
      <div style="font-size:11.5px;line-height:1.8;">
        <span style="color:{GREEN};font-weight:600;">DO &nbsp;</span>{do_item}<br>
        <span style="color:{RED};font-weight:600;">DON'T </span>{dont_item}<br>
        <span style="color:{AMBER};font-weight:600;">WATCH </span>{watch_item}
      </div>
    </div>
    <div style="text-align:right;min-width:80px;">
      <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.6px;color:{MUTED};">Score</div>
      <div style="font-size:28px;font-weight:700;color:{e_col};">{e_total:+d}</div>
      <div style="font-size:10.5px;color:{e_col};font-weight:600;">{e_label}</div>
    </div>
  </div>

  <!-- Evaluation table -->
  <table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:11px;">
    <thead>
      <tr style="background:{BG};">
        <th style="padding:6px 10px;text-align:left;font-size:10px;text-transform:uppercase;
                   letter-spacing:0.5px;color:{MUTED};font-weight:600;border-bottom:1px solid {BORDER};">Factor</th>
        <th style="padding:6px 10px;text-align:left;font-size:10px;text-transform:uppercase;
                   letter-spacing:0.5px;color:{MUTED};font-weight:600;border-bottom:1px solid {BORDER};">Rating</th>
        <th style="padding:6px 10px;text-align:center;font-size:10px;text-transform:uppercase;
                   letter-spacing:0.5px;color:{MUTED};font-weight:600;border-bottom:1px solid {BORDER};width:50px;">Score</th>
        <th style="padding:6px 10px;text-align:left;font-size:10px;text-transform:uppercase;
                   letter-spacing:0.5px;color:{MUTED};font-weight:600;border-bottom:1px solid {BORDER};">Evidence (new data only)</th>
      </tr>
    </thead>
    <tbody>
      {_factor_row("Momentum",  e_mom_r, e_mom_s, e_mom_ev)}
      {_factor_row("Valuation", e_val_r, e_val_s, e_val_ev)}
      {_factor_row("Crowding",  e_crd_r, e_crd_s, e_crd_ev)}
      {_factor_row("Macro",     e_mac_r, e_mac_s, e_mac_ev)}
    </tbody>
    <tfoot>
      <tr style="background:{e_col}08;border-top:2px solid {BORDER};">
        <td colspan="2" style="padding:6px 10px;font-weight:700;color:{TEXT};">Total &nbsp;<span style="font-size:10px;color:{MUTED};font-weight:400;">(range −8 to +8)</span></td>
        <td style="padding:6px 10px;font-weight:700;color:{e_col};text-align:center;font-size:14px;">{e_total:+d}</td>
        <td style="padding:6px 10px;">
          <span style="font-weight:700;color:{e_col};">{e_label}</span>
          <div style="font-size:10.5px;color:{MUTED};margin-top:2px;">{e_interp}</div>
        </td>
      </tr>
    </tfoot>
  </table>

  <!-- Triggers + Probability scenarios -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:11px;">
    <div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:{MUTED};margin-bottom:7px;">Change Triggers</div>
      <div style="padding:6px 10px;background:{GREEN}0A;border-radius:5px;border:1px solid {GREEN}25;margin-bottom:5px;">
        <div style="font-size:9.5px;font-weight:700;color:{GREEN};margin-bottom:2px;">● Bullish continues if</div>
        <div style="font-size:11px;color:{TEXT};">{t_bull}</div>
      </div>
      <div style="padding:6px 10px;background:{RED}0A;border-radius:5px;border:1px solid {RED}25;margin-bottom:5px;">
        <div style="font-size:9.5px;font-weight:700;color:{RED};margin-bottom:2px;">● Risk-off trigger</div>
        <div style="font-size:11px;color:{TEXT};">{t_risk}</div>
      </div>
      <div style="padding:6px 10px;background:{AMBER}0A;border-radius:5px;border:1px solid {AMBER}35;">
        <div style="font-size:9.5px;font-weight:700;color:{AMBER};margin-bottom:2px;">● Rotation signal</div>
        <div style="font-size:11px;color:{TEXT};">{t_rot}</div>
      </div>
    </div>
    <div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;color:{MUTED};margin-bottom:7px;">Forward Scenarios — 4-week</div>
      {prob_html}
      <div style="font-size:9.5px;color:{MUTED};margin-top:6px;font-style:italic;">Model-derived from evaluation score. Not forecasts.</div>
    </div>
  </div>
</div>

<!-- SECTOR FLOW | COMMODITIES -->
<div class="grid-2">
  <div class="card">
    <div class="card-title">Sector Flow — 5D Performance</div>

    {f'''<div style="margin-bottom:9px;">
      <div style="font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;
                  color:{GREEN};margin-bottom:3px;">▲ Strong (score &gt; 0)</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;">{strong_grid}</div>
    </div>''' if strong_grid else ""}

    {f'''<div style="margin-bottom:9px;">
      <div style="font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:0.6px;
                  color:{RED};margin-bottom:3px;">▼ Weak (score ≤ 0)</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1px;">{weak_grid}</div>
    </div>''' if weak_grid else ""}

    <div style="font-size:11.5px;padding:8px 12px;background:{rotation_col}0F;
                border-left:3px solid {rotation_col};border-radius:0 5px 5px 0;color:{TEXT};">
      {rotation_msg}
    </div>
  </div>

  <div class="card">
    <div class="card-title">Commodities</div>
    {comm_lines_html}
    <div style="margin-top:10px;font-size:11.5px;padding:8px 12px;
                background:{comm_conc_col}0F;border-left:3px solid {comm_conc_col};
                border-radius:0 5px 5px 0;color:{TEXT};">
      {comm_conclusion}
    </div>
  </div>
</div>

<!-- VALUATION | TOP CATALYSTS -->
<div class="grid-2">
  <div class="card">
    <div class="card-title">Valuation Snapshot</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-bottom:11px;">
      <div style="background:{BG};border-radius:7px;padding:10px 12px;">
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:{MUTED};">Trailing PE</div>
        <div style="font-size:18px;font-weight:700;color:{pe_color};">{fv(trailing_pe)}</div>
        <div style="font-size:10.5px;color:{pe_color};">{pe_bench}</div>
      </div>
      <div style="background:{BG};border-radius:7px;padding:10px 12px;">
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:{MUTED};">Shiller CAPE</div>
        <div style="font-size:18px;font-weight:700;color:{cape_color};">{fv(shiller_cape)}</div>
        <div style="font-size:10.5px;color:{cape_color};">{cape_bench}</div>
      </div>
      <div style="background:{BG};border-radius:7px;padding:10px 12px;">
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:{MUTED};">Earnings Yield</div>
        <div style="font-size:18px;font-weight:700;color:{NAVY};">{"—" if not earnings_yield else f"{earnings_yield:.2f}%"}</div>
        <div style="font-size:10.5px;color:{MUTED};">Inverse of PE</div>
      </div>
      <div style="background:{BG};border-radius:7px;padding:10px 12px;">
        <div style="font-size:10px;text-transform:uppercase;letter-spacing:0.5px;color:{MUTED};">10Y Treasury</div>
        <div style="font-size:18px;font-weight:700;color:{NAVY};">{"—" if not yield_10y else f"{yield_10y:.2f}%"}</div>
        <div style="font-size:10.5px;color:{MUTED};">Risk-free rate</div>
      </div>
    </div>
    <div style="padding:8px 12px;background:{fed_color}0F;border-left:3px solid {fed_color};
                border-radius:0 5px 5px 0;font-size:11.5px;color:{TEXT};">
      <strong>Fed Model:</strong> {"—" if fed_spread is None else f"{fed_spread:+.2f}%"} — {fed_signal}
    </div>
    <div style="font-size:10px;color:{MUTED};margin-top:8px;">multpl.com · ^TNX · Updated {val_updated}</div>
  </div>

  <div class="card">
    <div class="card-title">Top 3 Catalysts</div>
    {cats_html}
  </div>
</div>

</div>

<div class="footer">
  Market Report Agent · {TODAY} · Data delayed · For research purposes only · Not financial advice
</div>
</body>
</html>"""


def to_pdf(html_path, pdf_path):
    result = subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
         "--print-to-pdf-no-header", f"--print-to-pdf={pdf_path}", str(html_path)],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        print(f"Chrome error: {result.stderr}")
        return False
    return True


def main():
    print(f"Loading data for {TODAY}…")
    df, valuation, news = load_data()
    print("Building HTML…")
    html = build_html(df, valuation, news)

    import tempfile
    pdf_path = RPT_DIR / f"{TODAY}_daily_market_report.pdf"
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(html)
        tmp_path = Path(tmp.name)

    print("Converting to PDF via Chrome…")
    try:
        if to_pdf(tmp_path, pdf_path):
            print(f"PDF saved → {pdf_path}")
        else:
            print("PDF conversion failed — check Chrome installation")
    finally:
        tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()

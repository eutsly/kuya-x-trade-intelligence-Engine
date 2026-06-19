from __future__ import annotations

import pandas as pd


def _normalise(series: pd.Series) -> pd.Series:
    series = pd.to_numeric(series, errors="coerce").fillna(0)
    max_value = series.max()
    min_value = series.min()
    if max_value == min_value:
        return pd.Series([50] * len(series), index=series.index)
    return ((series - min_value) / (max_value - min_value)) * 100


def add_opportunity_scores(df: pd.DataFrame, annual_profit_col: str = "annual_profit_gbp") -> pd.DataFrame:
    """
    Add a 0-100 opportunity score.

    Score logic:
    - Annual profit matters most.
    - ROI matters because capital is limited.
    - Capital velocity matters because faster turnover reuses money more often.
    - Demand confidence improves score.
    - Risk score reduces score.
    """
    out = df.copy()

    profit_score = _normalise(out.get(annual_profit_col, pd.Series([0] * len(out))))
    roi_col = "budget_annual_roi_pct" if annual_profit_col == "budget_annual_profit_gbp" else "annual_roi_pct"
    cycles_col = "budget_annual_cycles" if annual_profit_col == "budget_annual_profit_gbp" else "annual_cycles"

    roi_score = _normalise(out.get(roi_col, pd.Series([0] * len(out))))
    velocity_score = _normalise(out.get(cycles_col, pd.Series([0] * len(out))))
    demand_score = (pd.to_numeric(out["demand_confidence"], errors="coerce").fillna(0).clip(0, 5) / 5) * 100
    risk_penalty = pd.to_numeric(out["risk_score"], errors="coerce").fillna(50).clip(0, 100)

    out["profit_score"] = profit_score
    out["roi_score"] = roi_score
    out["velocity_score"] = velocity_score
    out["demand_score"] = demand_score
    out["risk_penalty"] = risk_penalty

    out["opportunity_score"] = (
        (profit_score * 0.35)
        + (roi_score * 0.25)
        + (velocity_score * 0.20)
        + (demand_score * 0.15)
        - (risk_penalty * 0.15)
    ).clip(lower=0, upper=100)

    return out

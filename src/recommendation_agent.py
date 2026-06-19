from __future__ import annotations

import pandas as pd

from src.calculations import format_currency


def build_product_recommendation(row: pd.Series) -> str:
    """Generate a plain-English AI-style recommendation from calculated metrics."""
    product = row["product_name"]
    annual_roi = row["annual_roi_pct"]
    cycle = row["cycle_time_months"]
    annual_cycles = row["annual_cycles"]
    risk = row["risk_score"]
    annual_profit = row["annual_profit_gbp"]
    profit_unit = row["profit_per_unit_gbp"]

    lines = [
        f"**{product}** has an estimated annual profit of **{format_currency(annual_profit)}** "
        f"with an annual ROI of **{annual_roi:.1f}%**.",
        f"The estimated cycle time is **{cycle:.1f} months**, which means the same capital can be reused around "
        f"**{annual_cycles:.1f} times per year**.",
    ]

    if profit_unit <= 0:
        lines.append("This product should not be prioritised because the current assumptions produce negative unit profit.")
    elif annual_roi >= 100 and cycle <= 3 and risk <= 40:
        lines.append(
            "This is a strong opportunity because it combines good profit, fast capital turnover and manageable risk."
        )
    elif annual_roi >= 60 and cycle <= 4:
        lines.append(
            "This is worth testing because the yearly return is attractive, especially if demand assumptions are realistic."
        )
    elif cycle > 6:
        lines.append(
            "The main concern is capital lock-up. The shipment may be profitable, but the money takes too long to return."
        )
    elif risk > 70:
        lines.append(
            "The risk level is high. Validate the supplier, tax rate, market demand and damage/quality risk before buying."
        )
    else:
        lines.append(
            "This product should stay on the watchlist until the selling price, demand and tax assumptions are validated."
        )

    lines.append(
        "Recommended next step: collect at least three supplier quotes, confirm the HS code/tax treatment, "
        "verify current market price in Ethiopia, and test demand before committing the full budget."
    )

    return "\n\n".join(lines)


def build_portfolio_recommendation(df: pd.DataFrame, budget_gbp: float) -> str:
    if df.empty:
        return "No products match the current filters."

    best = df.iloc[0]
    second = df.iloc[1] if len(df) > 1 else None

    text = [
        f"With a budget of **{format_currency(budget_gbp)}**, the strongest current option is "
        f"**{best['product_name']}**.",
        f"It could generate around **{format_currency(best['budget_annual_profit_gbp'])}** annual profit "
        f"with an estimated annual ROI of **{best['budget_annual_roi_pct']:.1f}%**.",
        f"The key reason is capital velocity: the estimated cycle time is **{best['budget_cycle_time_months']:.1f} months**, "
        f"so the money can turn over around **{best['budget_annual_cycles']:.1f} times per year**.",
    ]

    if second is not None:
        text.append(
            f"The second-best option is **{second['product_name']}**, with estimated annual profit of "
            f"**{format_currency(second['budget_annual_profit_gbp'])}**. Compare these two carefully before buying."
        )

    text.append(
        "Do not choose only by profit per shipment. A slower container may look more profitable, "
        "but a faster product can produce more total yearly profit because the same capital is reused more often."
    )

    return "\n\n".join(text)

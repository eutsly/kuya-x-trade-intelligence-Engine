from __future__ import annotations

import pandas as pd

from src.calculations import format_currency
from src.recommendation_agent import build_product_recommendation


def build_markdown_report(df: pd.DataFrame, budget_gbp: float) -> str:
    if df.empty:
        return "# Kuya_X Trade Intelligence Report\n\nNo products match the current filters."

    ranked = df.sort_values(by="opportunity_score", ascending=False).reset_index(drop=True)
    best = ranked.iloc[0]

    lines = [
        "# Kuya_X Trade Intelligence Report",
        "",
        "## Executive summary",
        "",
        f"The highest-ranked product in the current model is **{best['product_name']}**.",
        f"It has an estimated annual profit of **{format_currency(best['annual_profit_gbp'])}**, "
        f"an annual ROI of **{best['annual_roi_pct']:.1f}%**, and an opportunity score of "
        f"**{best['opportunity_score']:.0f}/100**.",
        "",
        "The model compares products by landed cost, selling price, taxes, freight, demand, risk and capital velocity. "
        "The key principle is that profit per shipment is not enough; the tool also checks how quickly capital can be reused.",
        "",
        "## Top 5 ranked products",
        "",
        "| Rank | Product | Annual profit | Annual ROI | Cycle time | Risk | Score |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]

    for idx, row in ranked.head(5).iterrows():
        lines.append(
            f"| {idx + 1} | {row['product_name']} | {format_currency(row['annual_profit_gbp'])} | "
            f"{row['annual_roi_pct']:.1f}% | {row['cycle_time_months']:.1f} months | "
            f"{row['risk_score']:.0f}/100 | {row['opportunity_score']:.0f}/100 |"
        )

    lines.extend([
        "",
        "## Recommendation for the best product",
        "",
        build_product_recommendation(best),
        "",
        "## Notes and assumptions",
        "",
        f"- Budget scenario used in the app: **{format_currency(budget_gbp)}**.",
        "- Tax calculations are simplified and must be verified against current customs rules.",
        "- Selling prices and demand estimates must be validated using real Ethiopian market data.",
        "- Supplier reliability, product quality and clearance risk should be checked before committing capital.",
    ])

    return "\n".join(lines)

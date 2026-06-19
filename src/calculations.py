from __future__ import annotations

import math
from typing import Iterable

import pandas as pd

REQUIRED_COLUMNS = [
    "product_name",
    "category",
    "origin_country",
    "supplier",
    "buy_price_gbp",
    "units_per_shipment",
    "freight_total_gbp",
    "insurance_total_gbp",
    "clearance_total_gbp",
    "local_transport_total_gbp",
    "duty_rate",
    "vat_rate",
    "surtax_rate",
    "excise_rate",
    "selling_price_etb",
    "monthly_demand_units",
    "shipping_months",
    "clearance_months",
    "selling_months",
    "demand_confidence",
    "risk_score",
    "notes",
]


def validate_required_columns(df: pd.DataFrame) -> list[str]:
    """Return missing CSV columns."""
    return [col for col in REQUIRED_COLUMNS if col not in df.columns]


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator in (0, 0.0) or pd.isna(denominator):
        return default
    return numerator / denominator


def format_currency(value: float) -> str:
    try:
        return f"£{value:,.0f}"
    except Exception:
        return "£0"


def calculate_product_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate landed cost, profit, cycle time, annual cycles and ROI.

    This is a simplified decision-support model, not an official customs calculator.
    Confirm real tax treatment with customs, freight forwarders and accountants.
    """
    out = df.copy()

    numeric_cols = [
        "buy_price_gbp",
        "units_per_shipment",
        "freight_total_gbp",
        "insurance_total_gbp",
        "clearance_total_gbp",
        "local_transport_total_gbp",
        "duty_rate",
        "vat_rate",
        "surtax_rate",
        "excise_rate",
        "selling_price_etb",
        "monthly_demand_units",
        "shipping_months",
        "clearance_months",
        "selling_months",
        "demand_confidence",
        "risk_score",
        "fx_rate",
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)

    out["goods_cost_total_gbp"] = out["buy_price_gbp"] * out["units_per_shipment"]
    out["cif_gbp"] = (
        out["goods_cost_total_gbp"]
        + out["freight_total_gbp"]
        + out["insurance_total_gbp"]
    )

    # Simplified tax model.
    out["customs_duty_gbp"] = out["cif_gbp"] * out["duty_rate"]
    out["excise_base_gbp"] = out["cif_gbp"] + out["customs_duty_gbp"]
    out["excise_gbp"] = out["excise_base_gbp"] * out["excise_rate"]

    out["surtax_base_gbp"] = out["cif_gbp"] + out["customs_duty_gbp"] + out["excise_gbp"]
    out["surtax_gbp"] = out["surtax_base_gbp"] * out["surtax_rate"]

    out["vat_base_gbp"] = (
        out["cif_gbp"]
        + out["customs_duty_gbp"]
        + out["excise_gbp"]
        + out["surtax_gbp"]
    )
    out["vat_gbp"] = out["vat_base_gbp"] * out["vat_rate"]

    out["landed_cost_total_gbp"] = (
        out["cif_gbp"]
        + out["customs_duty_gbp"]
        + out["excise_gbp"]
        + out["surtax_gbp"]
        + out["vat_gbp"]
        + out["clearance_total_gbp"]
        + out["local_transport_total_gbp"]
    )
    out["landed_cost_per_unit_gbp"] = out.apply(
        lambda r: safe_divide(r["landed_cost_total_gbp"], r["units_per_shipment"]),
        axis=1,
    )

    out["selling_price_gbp"] = out.apply(
        lambda r: safe_divide(r["selling_price_etb"], r["fx_rate"]),
        axis=1,
    )
    out["revenue_per_shipment_gbp"] = out["selling_price_gbp"] * out["units_per_shipment"]
    out["profit_per_unit_gbp"] = out["selling_price_gbp"] - out["landed_cost_per_unit_gbp"]
    out["profit_per_shipment_gbp"] = out["profit_per_unit_gbp"] * out["units_per_shipment"]
    out["gross_margin_pct"] = out.apply(
        lambda r: safe_divide(r["profit_per_shipment_gbp"], r["revenue_per_shipment_gbp"]) * 100,
        axis=1,
    )

    # If monthly demand suggests it will take longer to sell than expected, extend sell-through time.
    out["demand_based_selling_months"] = out.apply(
        lambda r: safe_divide(r["units_per_shipment"], r["monthly_demand_units"], default=r["selling_months"]),
        axis=1,
    )
    out["adjusted_selling_months"] = out[["selling_months", "demand_based_selling_months"]].max(axis=1)

    out["cycle_time_months"] = (
        out["shipping_months"]
        + out["clearance_months"]
        + out["adjusted_selling_months"]
    )
    out["annual_cycles"] = out["cycle_time_months"].apply(
        lambda x: safe_divide(12, x) if x > 0 else 0
    )
    out["annual_profit_gbp"] = out["profit_per_shipment_gbp"] * out["annual_cycles"]
    out["annual_roi_pct"] = out.apply(
        lambda r: safe_divide(r["annual_profit_gbp"], r["landed_cost_total_gbp"]) * 100,
        axis=1,
    )

    out["risk_score"] = out["risk_score"].clip(lower=0, upper=100)
    out["risk_adjusted_annual_profit_gbp"] = out["annual_profit_gbp"] * (1 - out["risk_score"] / 100)

    out["recommendation_tag"] = out.apply(_recommendation_tag, axis=1)

    return out


def _recommendation_tag(row: pd.Series) -> str:
    if row["profit_per_unit_gbp"] <= 0:
        return "Avoid: negative unit profit"
    if row["annual_roi_pct"] >= 100 and row["cycle_time_months"] <= 3 and row["risk_score"] <= 40:
        return "Strong: fast, profitable, acceptable risk"
    if row["annual_roi_pct"] >= 60 and row["risk_score"] <= 60:
        return "Consider: good return but check assumptions"
    if row["cycle_time_months"] > 6:
        return "Slow: capital locked for too long"
    if row["risk_score"] > 70:
        return "Risky: validate before importing"
    return "Watchlist: needs more data"


def calculate_budget_scenarios(df: pd.DataFrame, budget_gbp: float) -> pd.DataFrame:
    """
    Simulate investing a fixed amount of capital into each product.

    This helps compare high-margin slow products against lower-margin fast-turnover products.
    """
    out = df.copy()

    def units_affordable(row: pd.Series) -> int:
        unit_cost = row["landed_cost_per_unit_gbp"]
        if unit_cost <= 0:
            return 0
        return int(math.floor(budget_gbp / unit_cost))

    out["budget_units_affordable"] = out.apply(units_affordable, axis=1)
    out["budget_capital_used_gbp"] = out["budget_units_affordable"] * out["landed_cost_per_unit_gbp"]
    out["budget_profit_per_cycle_gbp"] = out["budget_units_affordable"] * out["profit_per_unit_gbp"]

    out["budget_demand_based_selling_months"] = out.apply(
        lambda r: safe_divide(
            r["budget_units_affordable"],
            r["monthly_demand_units"],
            default=r["selling_months"],
        ),
        axis=1,
    )
    out["budget_adjusted_selling_months"] = out[["selling_months", "budget_demand_based_selling_months"]].max(axis=1)
    out["budget_cycle_time_months"] = (
        out["shipping_months"] + out["clearance_months"] + out["budget_adjusted_selling_months"]
    )
    out["budget_annual_cycles"] = out["budget_cycle_time_months"].apply(
        lambda x: safe_divide(12, x) if x > 0 else 0
    )
    out["budget_annual_profit_gbp"] = out["budget_profit_per_cycle_gbp"] * out["budget_annual_cycles"]
    out["budget_annual_roi_pct"] = out.apply(
        lambda r: safe_divide(r["budget_annual_profit_gbp"], budget_gbp) * 100,
        axis=1,
    )
    out["budget_risk_adjusted_annual_profit_gbp"] = out["budget_annual_profit_gbp"] * (1 - out["risk_score"] / 100)

    return out

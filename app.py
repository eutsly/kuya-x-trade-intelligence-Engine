from __future__ import annotations

import pandas as pd
import streamlit as st

from src.calculations import (
    calculate_budget_scenarios,
    calculate_product_metrics,
    format_currency,
    validate_required_columns,
)
from src.recommendation_agent import (
    build_portfolio_recommendation,
    build_product_recommendation,
)
from src.reporting import build_markdown_report
from src.scoring import add_opportunity_scores


st.set_page_config(
    page_title="Kuya_X Trade Intelligence Engine",
    page_icon="📦",
    layout="wide",
)


DISPLAY_COLUMNS = [
    "product_name",
    "category",
    "origin_country",
    "supplier",
    "landed_cost_per_unit_gbp",
    "selling_price_gbp",
    "profit_per_unit_gbp",
    "profit_per_shipment_gbp",
    "cycle_time_months",
    "annual_cycles",
    "annual_profit_gbp",
    "annual_roi_pct",
    "risk_score",
    "opportunity_score",
    "recommendation_tag",
]

BUDGET_COLUMNS = [
    "product_name",
    "category",
    "budget_units_affordable",
    "budget_capital_used_gbp",
    "budget_profit_per_cycle_gbp",
    "budget_cycle_time_months",
    "budget_annual_cycles",
    "budget_annual_profit_gbp",
    "budget_annual_roi_pct",
    "risk_score",
    "opportunity_score",
]

CURRENCY_FORMATS = {
    "landed_cost_per_unit_gbp": "£{:.2f}",
    "selling_price_gbp": "£{:.2f}",
    "profit_per_unit_gbp": "£{:.2f}",
    "profit_per_shipment_gbp": "£{:,.0f}",
    "annual_profit_gbp": "£{:,.0f}",
    "risk_adjusted_annual_profit_gbp": "£{:,.0f}",
    "budget_capital_used_gbp": "£{:,.0f}",
    "budget_profit_per_cycle_gbp": "£{:,.0f}",
    "budget_annual_profit_gbp": "£{:,.0f}",
}

PERCENT_FORMATS = {
    "annual_roi_pct": "{:.1f}%",
    "budget_annual_roi_pct": "{:.1f}%",
    "gross_margin_pct": "{:.1f}%",
}

NUMBER_FORMATS = {
    "cycle_time_months": "{:.1f}",
    "annual_cycles": "{:.1f}",
    "budget_cycle_time_months": "{:.1f}",
    "budget_annual_cycles": "{:.1f}",
    "risk_score": "{:.0f}",
    "opportunity_score": "{:.0f}",
}


@st.cache_data(show_spinner=False)
def load_sample_data() -> pd.DataFrame:
    return pd.read_csv("data/sample_products.csv")


def existing_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    return [col for col in columns if col in df.columns]


def display_dataframe(df: pd.DataFrame, columns: list[str], use_formatting: bool = True) -> None:
    cols = existing_columns(df, columns)
    if not cols:
        st.warning("No display columns were found in the current data.")
        return

    view = df[cols].copy()
    if use_formatting:
        format_map = {}
        format_map.update({k: v for k, v in CURRENCY_FORMATS.items() if k in view.columns})
        format_map.update({k: v for k, v in PERCENT_FORMATS.items() if k in view.columns})
        format_map.update({k: v for k, v in NUMBER_FORMATS.items() if k in view.columns})
        st.dataframe(view.style.format(format_map), use_container_width=True)
    else:
        st.dataframe(view, use_container_width=True)


def show_empty_state() -> None:
    st.warning(
        "No products match the current filters. Lower the minimum score or increase the maximum risk setting."
    )


st.title("Kuya_X Trade Intelligence Engine")
st.caption("Capital-velocity decision-support tool for sourcing and import opportunities")

st.info(
    "This is a working prototype. It helps compare sourcing opportunities by landed cost, "
    "profit, demand, cycle time, annual ROI and risk. Before any real purchase, use verified "
    "supplier quotes, freight quotes, market prices and customs/tax data."
)

with st.sidebar:
    st.header("Scenario settings")
    default_fx = st.number_input(
        "Exchange rate: 1 GBP = ETB",
        min_value=1.0,
        value=213.0,
        step=1.0,
        help="This overrides the FX rate in the CSV so the same scenario can be applied to all products.",
    )
    budget = st.number_input(
        "Available capital / budget (£)",
        min_value=1000.0,
        value=20000.0,
        step=1000.0,
    )
    max_risk = st.slider("Maximum risk score to include", 0, 100, 80)
    min_score = st.slider("Minimum opportunity score", 0, 100, 0)
    st.divider()
    st.write("Upload your own CSV or use the sample product data.")

uploaded_file = st.file_uploader("Upload product CSV", type=["csv"])

try:
    if uploaded_file is not None:
        raw_df = pd.read_csv(uploaded_file)
    else:
        raw_df = load_sample_data()
except Exception as exc:
    st.error(f"Could not read the CSV file: {exc}")
    st.stop()

missing = validate_required_columns(raw_df)
if missing:
    st.error("Your CSV is missing these required columns:")
    st.code(", ".join(missing), language="text")
    st.stop()

# Use one FX rate across all products for a fair scenario comparison.
df = raw_df.copy()
df["fx_rate"] = default_fx

metrics_df = calculate_product_metrics(df)
ranked_df = add_opportunity_scores(metrics_df)

filtered_df = ranked_df[
    (ranked_df["risk_score"] <= max_risk)
    & (ranked_df["opportunity_score"] >= min_score)
].copy()

filtered_df = filtered_df.sort_values(
    by=["opportunity_score", "annual_profit_gbp", "annual_roi_pct"],
    ascending=[False, False, False],
)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Executive dashboard",
        "Product data",
        "Profit ranking",
        "Budget simulator",
        "Product deep dive",
        "Decision report",
    ]
)

with tab1:
    st.subheader("Executive dashboard")

    st.markdown(
        """
        This tool is built around one business question:

        **If capital is limited, which product gives the best annual return after landed cost, demand, risk and speed of sale are considered?**

        It does not only compare profit per shipment. It also checks how quickly the same money can be reused.
        """
    )

    col1, col2, col3, col4 = st.columns(4)
    if filtered_df.empty:
        col1.metric("Best product", "No match")
        col2.metric("Opportunity score", "—")
        col3.metric("Annual profit", "—")
        col4.metric("Annual ROI", "—")
        show_empty_state()
    else:
        best = filtered_df.iloc[0]
        col1.metric("Best product", str(best["product_name"]))
        col2.metric("Opportunity score", f"{best['opportunity_score']:.0f}/100")
        col3.metric("Annual profit", format_currency(best["annual_profit_gbp"]))
        col4.metric("Annual ROI", f"{best['annual_roi_pct']:.1f}%")

        st.markdown("### Top products by opportunity score")
        display_dataframe(filtered_df, DISPLAY_COLUMNS)

        st.markdown("### Annual profit vs risk-adjusted annual profit")
        chart_cols = ["annual_profit_gbp", "risk_adjusted_annual_profit_gbp"]
        chart_df = filtered_df.head(10).set_index("product_name")[chart_cols]
        st.bar_chart(chart_df)

with tab2:
    st.subheader("Product data")
    st.write("These are the current input products. Upload a CSV to replace the sample data.")
    st.dataframe(raw_df, use_container_width=True)

    st.markdown("### Required CSV template")
    st.code(
        "product_name,category,origin_country,supplier,buy_price_gbp,units_per_shipment,"
        "freight_total_gbp,insurance_total_gbp,clearance_total_gbp,local_transport_total_gbp,"
        "duty_rate,vat_rate,surtax_rate,excise_rate,selling_price_etb,monthly_demand_units,"
        "shipping_months,clearance_months,selling_months,demand_confidence,risk_score,notes",
        language="csv",
    )

with tab3:
    st.subheader("Profit ranking")
    st.write(
        "Use this tab to see how rankings change when you prioritise profit, ROI, speed or risk-adjusted return."
    )

    if filtered_df.empty:
        show_empty_state()
    else:
        sort_option = st.selectbox(
            "Rank products by",
            [
                "opportunity_score",
                "annual_profit_gbp",
                "annual_roi_pct",
                "profit_per_unit_gbp",
                "profit_per_shipment_gbp",
                "annual_cycles",
                "risk_adjusted_annual_profit_gbp",
            ],
        )
        sorted_df = filtered_df.sort_values(by=sort_option, ascending=False)
        display_dataframe(sorted_df, DISPLAY_COLUMNS)

        csv_data = sorted_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download ranked products CSV",
            data=csv_data,
            file_name="kuya_x_ranked_products.csv",
            mime="text/csv",
        )

with tab4:
    st.subheader("Budget simulator")
    st.write(
        "This answers the practical question: with a fixed amount of capital, which product creates "
        "the highest yearly profit after considering how fast the money returns?"
    )

    if filtered_df.empty:
        show_empty_state()
    else:
        budget_df = calculate_budget_scenarios(filtered_df, budget_gbp=budget)
        budget_df = add_opportunity_scores(budget_df, annual_profit_col="budget_annual_profit_gbp")
        budget_df = budget_df.sort_values(
            by=["budget_annual_profit_gbp", "budget_annual_roi_pct", "opportunity_score"],
            ascending=[False, False, False],
        )

        st.markdown(f"### Scenario: investing approximately {format_currency(budget)} into one product at a time")
        display_dataframe(budget_df, BUDGET_COLUMNS)

        st.markdown("### Budget scenario chart")
        chart = budget_df.head(10).set_index("product_name")[["budget_annual_profit_gbp"]]
        st.bar_chart(chart)

        st.markdown("### Portfolio recommendation")
        st.write(build_portfolio_recommendation(budget_df, budget_gbp=budget))

with tab5:
    st.subheader("Product deep dive")

    if filtered_df.empty:
        show_empty_state()
    else:
        product_names = filtered_df["product_name"].tolist()
        selected = st.selectbox("Select product", product_names)
        row = filtered_df[filtered_df["product_name"] == selected].iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Landed cost / unit", format_currency(row["landed_cost_per_unit_gbp"]))
        c2.metric("Profit / unit", format_currency(row["profit_per_unit_gbp"]))
        c3.metric("Cycle time", f"{row['cycle_time_months']:.1f} months")
        c4.metric("Annual cycles", f"{row['annual_cycles']:.1f}")

        st.markdown("### Cost build-up")
        cost_breakdown = pd.DataFrame(
            {
                "Cost item": [
                    "Goods cost",
                    "Freight",
                    "Insurance",
                    "Customs duty",
                    "Excise",
                    "Surtax",
                    "VAT",
                    "Clearance",
                    "Local transport",
                ],
                "Amount GBP": [
                    row["goods_cost_total_gbp"],
                    row["freight_total_gbp"],
                    row["insurance_total_gbp"],
                    row["customs_duty_gbp"],
                    row["excise_gbp"],
                    row["surtax_gbp"],
                    row["vat_gbp"],
                    row["clearance_total_gbp"],
                    row["local_transport_total_gbp"],
                ],
            }
        )
        st.dataframe(cost_breakdown.style.format({"Amount GBP": "£{:,.2f}"}), use_container_width=True)
        st.bar_chart(cost_breakdown.set_index("Cost item"))

        st.markdown("### Plain-English recommendation")
        st.write(build_product_recommendation(row))

        st.markdown("### Product notes")
        st.write(row.get("notes", "No notes provided."))

with tab6:
    st.subheader("Decision report")
    st.write("This creates a markdown report for the current scenario and filters.")

    if filtered_df.empty:
        show_empty_state()
    else:
        report = build_markdown_report(filtered_df, budget_gbp=budget)
        st.markdown(report)

        st.download_button(
            label="Download markdown report",
            data=report.encode("utf-8"),
            file_name="kuya_x_trade_intelligence_report.md",
            mime="text/markdown",
        )

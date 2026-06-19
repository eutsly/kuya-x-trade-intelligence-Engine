import pandas as pd
import streamlit as st

from src.calculations import (
    calculate_product_metrics,
    calculate_budget_scenarios,
    format_currency,
    validate_required_columns,
)
from src.scoring import add_opportunity_scores
from src.recommendation_agent import build_product_recommendation, build_portfolio_recommendation
from src.reporting import build_markdown_report

st.set_page_config(
    page_title="Kuya_X Trade Intelligence Engine",
    page_icon="📦",
    layout="wide",
)

st.title("Kuya_X Trade Intelligence Engine")
st.caption("AI-style import profitability, landed-cost and capital-velocity decision tool")

st.info(
    "This tool is a decision-support prototype. Use real supplier quotes, freight quotes, "
    "market prices and customs/tax data before making business decisions."
)

with st.sidebar:
    st.header("Scenario settings")
    default_fx = st.number_input("Exchange rate: 1 GBP = ETB", min_value=1.0, value=213.0, step=1.0)
    budget = st.number_input("Available capital / budget (£)", min_value=1000.0, value=20000.0, step=1000.0)
    max_risk = st.slider("Maximum risk score to include", 0, 100, 80)
    min_score = st.slider("Minimum opportunity score", 0, 100, 0)
    st.divider()
    st.write("Upload your own CSV or use the sample data.")

uploaded_file = st.file_uploader("Upload product CSV", type=["csv"])

if uploaded_file is not None:
    raw_df = pd.read_csv(uploaded_file)
else:
    raw_df = pd.read_csv("data/sample_products.csv")

missing = validate_required_columns(raw_df)
if missing:
    st.error("Your CSV is missing required columns: " + ", ".join(missing))
    st.stop()

# Allow the global FX setting to override the column if user wants consistent scenario.
df = raw_df.copy()
df["fx_rate"] = default_fx

metrics_df = calculate_product_metrics(df)
ranked_df = add_opportunity_scores(metrics_df)

filtered_df = ranked_df[
    (ranked_df["risk_score"] <= max_risk) &
    (ranked_df["opportunity_score"] >= min_score)
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
        "£20k budget simulator",
        "Product deep dive",
        "AI-style report",
    ]
)

with tab1:
    st.subheader("Executive dashboard")

    col1, col2, col3, col4 = st.columns(4)
    if not filtered_df.empty:
        best = filtered_df.iloc[0]
        col1.metric("Best product", best["product_name"])
        col2.metric("Opportunity score", f'{best["opportunity_score"]:.0f}/100')
        col3.metric("Annual profit", format_currency(best["annual_profit_gbp"]))
        col4.metric("Annual ROI", f'{best["annual_roi_pct"]:.1f}%')
    else:
        col1.metric("Best product", "No match")
        col2.metric("Opportunity score", "—")
        col3.metric("Annual profit", "—")
        col4.metric("Annual ROI", "—")

    st.markdown("### Top products by opportunity score")
    display_cols = [
        "product_name",
        "category",
        "origin_country",
        "landed_cost_per_unit_gbp",
        "selling_price_gbp",
        "profit_per_unit_gbp",
        "cycle_time_months",
        "annual_cycles",
        "annual_profit_gbp",
        "annual_roi_pct",
        "risk_score",
        "opportunity_score",
    ]
    st.dataframe(
        filtered_df[display_cols].style.format({
            "landed_cost_per_unit_gbp": "£{:.2f}",
            "selling_price_gbp": "£{:.2f}",
            "profit_per_unit_gbp": "£{:.2f}",
            "cycle_time_months": "{:.1f}",
            "annual_cycles": "{:.1f}",
            "annual_profit_gbp": "£{:,.0f}",
            "annual_roi_pct": "{:.1f}%",
            "opportunity_score": "{:.0f}",
        }),
        use_container_width=True,
    )

    if not filtered_df.empty:
        chart_df = filtered_df.head(10).set_index("product_name")[["annual_profit_gbp", "risk_adjusted_annual_profit_gbp"]]
        st.markdown("### Annual profit vs risk-adjusted annual profit")
        st.bar_chart(chart_df)

with tab2:
    st.subheader("Product data")
    st.write("These are the current input products. Upload a CSV to replace the sample data.")
    st.dataframe(raw_df, use_container_width=True)

    st.markdown("### CSV template columns")
    st.code(
        "product_name,category,origin_country,supplier,buy_price_gbp,units_per_shipment,"
        "freight_total_gbp,insurance_total_gbp,clearance_total_gbp,local_transport_total_gbp,"
        "duty_rate,vat_rate,surtax_rate,excise_rate,selling_price_etb,monthly_demand_units,"
        "shipping_months,clearance_months,selling_months,demand_confidence,risk_score,notes",
        language="csv",
    )

with tab3:
    st.subheader("Profit ranking")
    sort_option = st.selectbox(
        "Rank products by",
        [
            "opportunity_score",
            "annual_profit_gbp",
            "annual_roi_pct",
            "profit_per_unit_gbp",
            "annual_cycles",
            "risk_adjusted_annual_profit_gbp",
        ],
    )
    sorted_df = filtered_df.sort_values(by=sort_option, ascending=False)
    st.dataframe(
        sorted_df[display_cols + ["recommendation_tag"]],
        use_container_width=True,
    )

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
        "This answers your key question: if you have limited capital, which product creates the "
        "highest yearly profit after considering how fast the money returns?"
    )

    budget_df = calculate_budget_scenarios(filtered_df, budget_gbp=budget)
    budget_df = add_opportunity_scores(budget_df, annual_profit_col="budget_annual_profit_gbp")
    budget_df = budget_df.sort_values(
        by=["budget_annual_profit_gbp", "budget_annual_roi_pct"],
        ascending=[False, False],
    )

    st.markdown(f"### If you invest approximately {format_currency(budget)} into one product at a time")
    budget_cols = [
        "product_name",
        "budget_units_affordable",
        "budget_cycle_time_months",
        "budget_annual_cycles",
        "budget_profit_per_cycle_gbp",
        "budget_annual_profit_gbp",
        "budget_annual_roi_pct",
        "risk_score",
    ]
    st.dataframe(
        budget_df[budget_cols].style.format({
            "budget_cycle_time_months": "{:.1f}",
            "budget_annual_cycles": "{:.1f}",
            "budget_profit_per_cycle_gbp": "£{:,.0f}",
            "budget_annual_profit_gbp": "£{:,.0f}",
            "budget_annual_roi_pct": "{:.1f}%",
        }),
        use_container_width=True,
    )

    if not budget_df.empty:
        st.markdown("### Budget scenario chart")
        chart = budget_df.head(10).set_index("product_name")[["budget_annual_profit_gbp"]]
        st.bar_chart(chart)

        st.markdown("### AI-style portfolio recommendation")
        st.write(build_portfolio_recommendation(budget_df, budget_gbp=budget))

with tab5:
    st.subheader("Product deep dive")
    product_names = filtered_df["product_name"].tolist()
    if product_names:
        selected = st.selectbox("Select product", product_names)
        row = filtered_df[filtered_df["product_name"] == selected].iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Landed cost / unit", format_currency(row["landed_cost_per_unit_gbp"]))
        c2.metric("Profit / unit", format_currency(row["profit_per_unit_gbp"]))
        c3.metric("Cycle time", f'{row["cycle_time_months"]:.1f} months')
        c4.metric("Annual cycles", f'{row["annual_cycles"]:.1f}')

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

        st.markdown("### Recommendation")
        st.write(build_product_recommendation(row))
    else:
        st.warning("No product matches the current filters.")

with tab6:
    st.subheader("AI-style report")
    st.write("Use this report in your README, application note, or business planning.")
    report = build_markdown_report(filtered_df, budget_gbp=budget)
    st.markdown(report)

    st.download_button(
        label="Download markdown report",
        data=report.encode("utf-8"),
        file_name="kuya_x_trade_intelligence_report.md",
        mime="text/markdown",
    )

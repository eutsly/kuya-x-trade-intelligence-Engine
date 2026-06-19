# Application note: short project description

One project I built is **Kuya_X Trade Intelligence Engine**, an import profitability and capital-velocity decision tool.

The project compares products by supplier price, landed cost, freight, import tax inputs, selling price, demand, risk, shipping time and sell-through time. Instead of only calculating profit per shipment, it calculates annualised return by modelling how quickly the same capital can be reused.

For example, a product with a lower profit per container may still be more attractive if it lands and sells faster, because the money can be reinvested more times during the year.

I built the prototype using Python, pandas and Streamlit. The tool allows a user to upload a product list, calculate landed cost, compare yearly profit, run a fixed-budget scenario and produce a ranked list of the strongest opportunities.

The aim was to build a practical decision-support tool, not just a technical demo. It reflects how a sourcing or investment team could move from scattered supplier quotes and market assumptions to a clearer ranked decision.

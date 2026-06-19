# CSV template

Required columns:

```csv
product_name,category,origin_country,supplier,buy_price_gbp,units_per_shipment,freight_total_gbp,insurance_total_gbp,clearance_total_gbp,local_transport_total_gbp,duty_rate,vat_rate,surtax_rate,excise_rate,selling_price_etb,monthly_demand_units,shipping_months,clearance_months,selling_months,demand_confidence,risk_score,notes
```

## Column meaning

| Column | Meaning |
|---|---|
| product_name | Product name |
| category | Product group |
| origin_country | Where it is sourced from |
| supplier | Supplier name or placeholder |
| buy_price_gbp | Supplier price per unit in GBP |
| units_per_shipment | Units in one shipment/container/batch |
| freight_total_gbp | Total freight cost for the shipment |
| insurance_total_gbp | Total insurance cost |
| clearance_total_gbp | Clearance/documentation/agent cost |
| local_transport_total_gbp | Local transport after arrival |
| duty_rate | Import duty as decimal, e.g. 0.20 for 20% |
| vat_rate | VAT as decimal |
| surtax_rate | Surtax as decimal |
| excise_rate | Excise as decimal, if applicable |
| selling_price_etb | Expected selling price per unit in Ethiopia |
| monthly_demand_units | Estimated monthly sales volume |
| shipping_months | Time to land in Ethiopia |
| clearance_months | Customs/clearance time |
| selling_months | Estimated time to sell shipment |
| demand_confidence | 1 to 5 confidence score |
| risk_score | 0 to 100 risk score |
| notes | Any useful notes |

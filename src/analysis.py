# src/analysis.py

import pandas as pd
from typing import Dict, Optional

# ... (rest of the class is correct) ...

def _generate_insights(summary_data: pd.Series, quality_metrics: Dict,
                      period_days: int, unit_cost: Optional[float] = None, sales_price: Optional[float] = None) -> str:
    insights = []
    return_rate = summary_data['return_rate']
    sku = summary_data['sku']

    insights.append(
        f"**Return Rate Analysis for SKU {sku}**: The product's return rate is **{return_rate:.2f}%** over the last {period_days} days. "
        f"This is evaluated against the medical device industry standard of 5-10%."
    )

    if return_rate > 15:
        insights.append(
            "🚨 **Critical Alert**: This rate is significantly above industry standards, suggesting serious quality issues that require immediate investigation and a formal CAPA process."
        )
    elif return_rate > 10:
        insights.append(
            "⚠️ **Warning**: The return rate is above the industry standard. An investigation is highly recommended to identify root causes and prevent the issue from escalating."
        )
    else:
        insights.append(
            "✅ **Acceptable Performance**: The return rate is within or below the industry standard. Continue to monitor for any upward trends."
        )

    if sales_price and sales_price > 0:
        lost_revenue = summary_data['total_returned'] * sales_price
        # FIX: Added a space before 'the' and after '$' for proper formatting
        insights.append(f"💰 **Financial Impact**: Based on a sales price of ${sales_price:,.2f}, the estimated lost revenue from returns for this period is **${lost_revenue:,.2f}**.")
    elif unit_cost and unit_cost > 0:
        return_cost = summary_data['total_returned'] * unit_cost
        # FIX: Added a space before 'the' and after '$' for proper formatting
        insights.append(f"💰 **Financial Impact**: Based on a unit cost of ${unit_cost:,.2f}, the cost of returned goods for this period is approximately **${return_cost:,.2f}**.")

    return "\n\n".join(insights)

# ... (rest of the file is correct) ...

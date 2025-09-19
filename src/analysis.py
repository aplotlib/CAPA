# src/analysis.py

import pandas as pd
from typing import Dict, Optional

class MetricsCalculator:
    """Calculate quality metrics from sales and returns data."""
    @staticmethod
    def calculate_return_rates(sales_df: pd.DataFrame, returns_df: pd.DataFrame) -> pd.DataFrame:
        if sales_df is None or sales_df.empty:
            return pd.DataFrame()

        sales_summary = sales_df.groupby('sku')['quantity'].sum().reset_index()
        sales_summary.rename(columns={'quantity': 'total_sold'}, inplace=True)

        if returns_df is None or returns_df.empty:
            summary_df = sales_summary.copy()
            summary_df['total_returned'] = 0
        else:
            returns_summary = returns_df.groupby('sku')['quantity'].sum().reset_index()
            returns_summary.rename(columns={'quantity': 'total_returned'}, inplace=True)
            summary_df = pd.merge(sales_summary, returns_summary, on='sku', how='left')
            summary_df['total_returned'] = summary_df['total_returned'].fillna(0)

        summary_df['return_rate'] = summary_df.apply(
            lambda row: (row['total_returned'] / row['total_sold'] * 100) if row['total_sold'] > 0 else 0,
            axis=1
        )
        summary_df['quality_status'] = summary_df['return_rate'].apply(
            lambda x: 'Critical' if x > 15 else ('Warning' if x > 10 else 'Good')
        )
        return summary_df.round(2)

    @staticmethod
    def calculate_quality_metrics(return_rate: float) -> Dict[str, any]:
        if return_rate < 5: quality_score = 90 + (5 - return_rate) * 2
        elif return_rate < 10: quality_score = 70 + (10 - return_rate) * 4
        elif return_rate < 15: quality_score = 50 + (15 - return_rate) * 4
        elif return_rate < 20: quality_score = 30 + (20 - return_rate) * 4
        else: quality_score = max(0, 30 - (return_rate - 20) * 3)

        if return_rate > 15: risk_level = 'High'
        elif return_rate > 10: risk_level = 'Medium'
        else: risk_level = 'Low'

        return {
            'quality_score': round(quality_score),
            'risk_level': risk_level,
        }

def run_full_analysis(sales_df: pd.DataFrame, returns_df: pd.DataFrame,
                     report_period_days: int = 30, unit_cost: Optional[float] = None, sales_price: Optional[float] = None) -> Dict:
    if sales_df is None or sales_df.empty:
        return {"error": "Sales data is missing or invalid."}

    calculator = MetricsCalculator()
    return_summary = calculator.calculate_return_rates(sales_df, returns_df)

    if return_summary.empty:
        return {"error": "Could not calculate return summary."}

    primary_sku_data = return_summary.iloc[0]
    quality_metrics = calculator.calculate_quality_metrics(primary_sku_data['return_rate'])

    insights = _generate_insights(primary_sku_data, quality_metrics, report_period_days, unit_cost, sales_price)

    return {
        'return_summary': return_summary,
        'quality_metrics': quality_metrics,
        'insights': insights,
    }

def _generate_insights(summary_data: pd.Series, quality_metrics: Dict,
                      period_days: int, unit_cost: Optional[float] = None, sales_price: Optional[float] = None) -> str:
    insights = []
    return_rate = summary_data['return_rate']

    insights.append(
        f"**Return Rate Analysis**: The product's return rate is **{return_rate:.2f}%** over the last {period_days} days. "
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
        insights.append(f"💰 **Financial Impact**: Based on a sales price of ${sales_price:,.2f}, the estimated lost revenue from returns for this period is **${lost_revenue:,.2f}**.")
    elif unit_cost and unit_cost > 0:
        return_cost = summary_data['total_returned'] * unit_cost
        insights.append(f"💰 **Financial Impact**: Based on a unit cost of ${unit_cost:,.2f}, the cost of returned goods for this period is approximately **${return_cost:,.2f}**.")


    return "\n\n".join(insights)

def calculate_cost_benefit(analysis_results: Dict, current_unit_cost: float, cost_change: float, expected_rr_reduction: float) -> Dict:
    """
    Calculates the cost-benefit of a proposed change.
    """
    summary_data = analysis_results['return_summary'].iloc[0]
    total_sold = summary_data['total_sold']
    current_return_rate = summary_data['return_rate']

    # Calculations
    new_return_rate = current_return_rate - expected_rr_reduction
    if new_return_rate < 0:
        new_return_rate = 0

    returns_reduced = total_sold * (expected_rr_reduction / 100)
    savings_from_returns = returns_reduced * current_unit_cost

    new_unit_cost = current_unit_cost + cost_change
    total_additional_cost = total_sold * cost_change

    net_savings = savings_from_returns - total_additional_cost

    # Scale to annual
    annual_scaling_factor = 365 / 30 # Assuming analysis is for 30 days
    annual_savings = net_savings * annual_scaling_factor

    roi = (annual_savings / (total_additional_cost * annual_scaling_factor)) * 100 if total_additional_cost > 0 else float('inf')

    breakeven_units = total_additional_cost / (savings_from_returns / total_sold) if savings_from_returns > 0 else float('inf')

    # Summary
    summary = (
        f"The proposed change is projected to result in annual savings of ${annual_savings:,.2f}. "
        f"This represents a {roi:.2f}% return on investment. "
        "This is a financially viable change." if annual_savings > 0 else "This change is not financially viable."
    )

    details = {
        "Current Return Rate": f"{current_return_rate:.2f}%",
        "Expected New Return Rate": f"{new_return_rate:.2f}%",
        "Units Sold in Period": f"{int(total_sold):,}",
        "Returns Reduced in Period": f"{int(returns_reduced):,}",
        "Savings from Reduced Returns": f"${savings_from_returns:,.2f}",
        "Additional Cost for Period": f"${total_additional_cost:,.2f}",
        "Net Savings for Period": f"${net_savings:,.2f}",
        "Projected Annual Savings": f"${annual_savings:,.2f}",
    }

    return {
        "summary": summary,
        "annual_savings": annual_savings,
        "roi": roi,
        "breakeven_units": breakeven_units,
        "details": details,
    }

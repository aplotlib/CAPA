# src/analysis.py

import pandas as pd
from typing import Dict, Optional, Any

class MetricsCalculator:
    """A collection of static methods to calculate key quality metrics."""

    @staticmethod
    def calculate_return_rates(sales_df: pd.DataFrame, returns_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates return rates by merging sales and returns data.

        Args:
            sales_df: DataFrame with 'sku' and 'quantity' of units sold.
            returns_df: DataFrame with 'sku' and 'quantity' of units returned.

        Returns:
            A DataFrame summarizing total sold, returned, return rate, and quality status per SKU.
        """
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
            summary_df['total_returned'] = summary_df['total_returned'].fillna(0).astype(int)

        summary_df['return_rate'] = summary_df.apply(
            lambda row: (row['total_returned'] / row['total_sold'] * 100) if row['total_sold'] > 0 else 0,
            axis=1
        )
        summary_df['quality_status'] = summary_df['return_rate'].apply(
            lambda x: 'Critical' if x > 15 else ('Warning' if x > 10 else 'Good')
        )
        return summary_df.round(2)

    @staticmethod
    def calculate_quality_metrics(return_rate: float) -> Dict[str, Any]:
        """
        Calculates a quality score and risk level based on the return rate.

        Args:
            return_rate: The percentage return rate for a product.

        Returns:
            A dictionary containing the calculated 'quality_score' and 'risk_level'.
        """
        if return_rate < 5:
            quality_score = 90 + (5 - return_rate) * 2
        elif return_rate < 10:
            quality_score = 70 + (10 - return_rate) * 4
        elif return_rate < 15:
            quality_score = 50 + (15 - return_rate) * 4
        elif return_rate < 20:
            quality_score = 30 + (20 - return_rate) * 4
        else:
            quality_score = max(0, 30 - (return_rate - 20) * 3)

        if return_rate > 15:
            risk_level = 'High'
        elif return_rate > 10:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'

        return {
            'quality_score': round(quality_score),
            'risk_level': risk_level,
        }


def _generate_insights(
    summary_data: pd.Series,
    quality_metrics: Dict,
    period_days: int,
    unit_cost: Optional[float] = None,
    sales_price: Optional[float] = None
) -> str:
    """
    Generates a human-readable summary of the analysis results.

    Args:
        summary_data: A pandas Series containing summary data for one SKU.
        quality_metrics: A dictionary with quality score and risk level.
        period_days: The number of days in the reporting period.
        unit_cost: The cost of a single unit.
        sales_price: The sale price of a single unit.

    Returns:
        A formatted markdown string with insights.
    """
    insights = []
    return_rate = summary_data['return_rate']
    sku = summary_data['sku']
    risk_level = quality_metrics['risk_level']

    insights.append(
        f"**Return Rate Analysis for SKU `{sku}`**: Over the last {period_days} days, "
        f"the product's return rate is **{return_rate:.2f}%**. The current risk level is assessed as **{risk_level}**."
    )

    if risk_level == 'High':
        insights.append(
            "🚨 **Critical Alert**: This rate is significantly above industry benchmarks, suggesting "
            "serious quality issues that require immediate investigation and a formal CAPA process."
        )
    elif risk_level == 'Medium':
        insights.append(
            "⚠️ **Warning**: The return rate is trending higher than desired. An investigation is "
            "highly recommended to identify root causes and prevent escalation."
        )
    else:
        insights.append(
            "✅ **Acceptable Performance**: The return rate is within or below the typical industry "
            "standard. Continue to monitor for any upward trends."
        )

    if sales_price and sales_price > 0:
        lost_revenue = summary_data['total_returned'] * sales_price
        insights.append(
            f"💰 **Financial Impact**: Based on a sales price of ${sales_price:,.2f}, the "
            f"estimated lost revenue from returns for this period is **${lost_revenue:,.2f}**."
        )
    elif unit_cost and unit_cost > 0:
        return_cost = summary_data['total_returned'] * unit_cost
        insights.append(
            f"💰 **Financial Impact**: Based on a unit cost of ${unit_cost:,.2f}, the cost of "
            f"returned goods for this period is approximately **${return_cost:,.2f}**."
        )

    return "\n\n".join(insights)


def run_full_analysis(
    sales_df: pd.DataFrame,
    returns_df: pd.DataFrame,
    report_period_days: int = 30,
    unit_cost: Optional[float] = None,
    sales_price: Optional[float] = None
) -> Dict:
    """
    Runs a comprehensive analysis on sales and returns data.

    Args:
        sales_df: The processed sales data.
        returns_df: The processed returns data.
        report_period_days: The number of days in the analysis period.
        unit_cost: The cost per unit of the product.
        sales_price: The selling price per unit of the product.

    Returns:
        A dictionary containing the return summary, quality metrics, and generated insights.
    """
    if sales_df is None or sales_df.empty:
        return {"error": "Sales data is missing or invalid."}

    calculator = MetricsCalculator()
    return_summary = calculator.calculate_return_rates(sales_df, returns_df)

    if return_summary.empty:
        return {"error": "Could not calculate return summary."}

    # Use the first SKU in the summary as the primary target for insights
    primary_sku_data = return_summary.iloc[0]
    quality_metrics = calculator.calculate_quality_metrics(primary_sku_data['return_rate'])

    insights = _generate_insights(
        summary_data=primary_sku_data,
        quality_metrics=quality_metrics,
        period_days=report_period_days,
        unit_cost=unit_cost,
        sales_price=sales_price
    )

    return {
        'return_summary': return_summary,
        'quality_metrics': quality_metrics,
        'insights': insights,
    }

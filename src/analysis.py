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

        # Aggregate total units sold per SKU
        sales_summary = sales_df.groupby('sku')['quantity'].sum().reset_index()
        sales_summary.rename(columns={'quantity': 'total_sold'}, inplace=True)

        # Merge with returns data if available
        if returns_df is None or returns_df.empty:
            summary_df = sales_summary.copy()
            summary_df['total_returned'] = 0
        else:
            returns_summary = returns_df.groupby('sku')['quantity'].sum().reset_index()
            returns_summary.rename(columns={'quantity': 'total_returned'}, inplace=True)
            summary_df = pd.merge(sales_summary, returns_summary, on='sku', how='left')
            summary_df['total_returned'] = summary_df['total_returned'].fillna(0).astype(int)

        # Calculate return rate and assign a status
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
        # ... (rest of the logic)
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
        A dictionary containing the return summary, quality metrics, and AI-generated insights.
    """
    if sales_df is None or sales_df.empty:
        return {"error": "Sales data is missing or invalid."}

    calculator = MetricsCalculator()
    return_summary = calculator.calculate_return_rates(sales_df, returns_df)

    if return_summary.empty:
        return {"error": "Could not calculate return summary."}
    
    # Assume the first SKU is the primary one for detailed analysis
    primary_sku_data = return_summary.iloc[0]
    quality_metrics = calculator.calculate_quality_metrics(primary_sku_data['return_rate'])

    insights = _generate_insights(primary_sku_data, quality_metrics, report_period_days, unit_cost, sales_price)

    return {
        'return_summary': return_summary,
        'quality_metrics': quality_metrics,
        'insights': insights,
    }


def _generate_insights(
    summary_data: pd.Series, 
    quality_metrics: Dict,
    period_days: int, 
    unit_cost: Optional[float] = None, 
    sales_price: Optional[float] = None
) -> str:
    """Generates a human-readable summary of the analysis results."""
    # ... (insight generation logic remains the same)
    return ""

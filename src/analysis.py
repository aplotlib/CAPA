# src/analysis.py
import pandas as pd
from typing import Dict
from datetime import datetime, timedelta

class MetricsCalculator:
    @staticmethod
    def calculate_return_rates(sales_df: pd.DataFrame, returns_df: pd.DataFrame) -> pd.DataFrame:
        if sales_df.empty: return pd.DataFrame()
        sales_summary = sales_df.groupby('sku')['quantity'].sum().reset_index().rename(columns={'quantity': 'total_sold'})
        returns_summary = returns_df.groupby('sku')['quantity'].sum().reset_index().rename(columns={'quantity': 'total_returned'})
        summary_df = pd.merge(sales_summary, returns_summary, on='sku', how='left')
        summary_df['total_returned'].fillna(0, inplace=True)
        summary_df['return_rate'] = summary_df.apply(lambda row: (row['total_returned'] / row['total_sold'] * 100) if row['total_sold'] > 0 else 0, axis=1)
        return summary_df.round(2)

def run_full_analysis(sales_df: pd.DataFrame, returns_df: pd.DataFrame, report_period_days: int) -> Dict:
    if sales_df.empty: return {"error": "Sales data is empty."}
    return_summary = MetricsCalculator.calculate_return_rates(sales_df, returns_df)
    if return_summary.empty: return {"error": "Could not calculate return rates."}
    total_sales = sales_df['quantity'].sum()
    total_returns = returns_df['quantity'].sum()
    return {
        'total_sales': total_sales,
        'total_returns': total_returns,
        'return_summary': return_summary
    }

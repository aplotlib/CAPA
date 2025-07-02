# src/analysis.py

import pandas as pd
import re
from typing import Dict, Tuple
from datetime import datetime, timedelta

class ReturnReasonCategorizer:
    # ... (class code is unchanged)

class MetricsCalculator:
    @staticmethod
    def calculate_return_rates(sales_df: pd.DataFrame, returns_df: pd.DataFrame) -> pd.DataFrame:
        if sales_df.empty or 'sku' not in sales_df.columns: return pd.DataFrame()
        sales_summary = sales_df.groupby('sku')['quantity'].sum().reset_index().rename(columns={'quantity': 'total_sold'})
        if returns_df.empty or 'sku' not in returns_df.columns:
            summary_df = sales_summary
            summary_df['total_returned'] = 0
        else:
            returns_summary = returns_df.groupby('sku')['quantity'].sum().reset_index().rename(columns={'quantity': 'total_returned'})
            summary_df = pd.merge(sales_summary, returns_summary, on='sku', how='left')
        summary_df['total_returned'].fillna(0, inplace=True)
        summary_df['return_rate'] = summary_df.apply(lambda row: (row['total_returned'] / row['total_sold'] * 100) if row['total_sold'] > 0 else 0, axis=1)
        return summary_df.round(2)

def run_full_analysis(sales_df: pd.DataFrame, returns_df: pd.DataFrame, report_period_days: int) -> Dict:
    """Orchestrates the full analysis pipeline with a fix for manual entry."""
    if sales_df is None or returns_df is None or sales_df.empty:
        return {"error": "Insufficient sales data for analysis."}

    if 'return_date' in returns_df.columns:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=report_period_days)
        analysis_returns_df = returns_df[returns_df['return_date'] >= start_date].copy()
    else:
        analysis_returns_df = returns_df.copy()

    return_summary = MetricsCalculator.calculate_return_rates(sales_df, analysis_returns_df)
    
    total_sales = sales_df['quantity'].sum()
    total_returns = analysis_returns_df['quantity'].sum()
    overall_return_rate = (total_returns / total_sales * 100) if total_sales > 0 else 0

    return {
        'overall_return_rate': overall_return_rate,
        'total_sales': total_sales,
        'total_returns': total_returns,
        'return_summary': return_summary,
        'analysis_period_start_date': (datetime.now() - timedelta(days=report_period_days)).strftime('%Y-%m-%d'),
        'analysis_period_end_date': datetime.now().strftime('%Y-%m-%d'),
    }

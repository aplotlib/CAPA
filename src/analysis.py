# src/analysis.py

import pandas as pd
import re
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

class ReturnReasonCategorizer:
    """Categorizes return reasons using a robust set of predefined patterns."""
    CATEGORIES = {
        'QUALITY_DEFECTS': {'patterns': [r'defective', r'broken', r'damaged', r'doesn\'?t?\s+work', r'poor\s+quality', r'fell?\s+apart', r'cheap', r'malfunction', r'not\s+working', r'stopped?\s+working', r'dead\s+on\s+arrival', r'doa', r'faulty', r'ripped', r'torn', r'hole']},
        'SIZE_FIT_ISSUES': {'patterns': [r'too\s+(small|large|big|tight|loose)', r'doesn\'?t?\s+fit', r'wrong\s+size', r'size\s+(issue|problem)', r'(small|large)r?\s+than\s+expected', r'runs?\s+(small|large|big)', r'fit\s+(issue|problem)', r'not\s+the\s+right\s+size']},
        'WRONG_PRODUCT_OR_DESCRIPTION': {'patterns': [r'wrong\s+(item|product|model|color)', r'not\s+as\s+described', r'incorrect\s+(item|product)', r'different\s+than\s+(pictured|described|ordered)', r'not\s+what\s+i\s+ordered', r'received?\s+(wrong|different)', r'misrepresented', r'missing\s+parts']},
        'BUYER_REMORSE_OR_MISTAKE': {'patterns': [r'bought?\s+by\s+mistake', r'accidentally\s+ordered', r'ordered?\s+(wrong|incorrect)\s+item', r'no\s+longer\s+need', r'don\'?t?\s+need', r'changed?\s+my?\s+mind', r'found?\s+(better|cheaper|different)', r'duplicate\s+order']},
    }
    def __init__(self):
        self.compiled_patterns = {cat: [re.compile(p, re.IGNORECASE) for p in data['patterns']] for cat, data in self.CATEGORIES.items()}
    def categorize_reason(self, reason: str, comment: str = "") -> Tuple[str, float]:
        combined_text = f"{reason or ''} {comment or ''}".lower().strip()
        if not combined_text: return "UNCATEGORIZED", 0.0
        scores = {cat: sum(1 for p in pats if p.search(combined_text)) for cat, pats in self.compiled_patterns.items()}
        best_cat = max(scores, key=scores.get)
        return (best_cat, 1.0) if scores[best_cat] > 0 else ("UNCATEGORIZED", 0.0)
    def categorize_dataframe(self, df: pd.DataFrame, reason_col: str, comment_col: str) -> pd.DataFrame:
        if reason_col not in df.columns: return df
        if comment_col not in df.columns: df[comment_col] = ''
        df[comment_col] = df[comment_col].fillna('')
        results = df.apply(lambda row: self.categorize_reason(row.get(reason_col, ''), row.get(comment_col, '')), axis=1)
        df['category'] = [res[0] for res in results]
        return df

class MetricsCalculator:
    """Calculates key quality and sales metrics."""
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
    """Orchestrates the full analysis pipeline."""
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

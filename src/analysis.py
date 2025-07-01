# src/analysis.py

"""
Module for performing data analysis, including metric calculations, return
reason categorization, and quality insights generation.
"""

import pandas as pd
import re
from typing import Dict, List, Optional, Tuple

class ReturnReasonCategorizer:
    """
    Categorizes return reasons using a robust set of predefined patterns.
    """
    # Expanded and refined categories for better accuracy
    CATEGORIES = {
        'QUALITY_DEFECTS': {
            'patterns': [
                r'defective', r'broken', r'damaged', r'doesn\'?t?\s+work',
                r'poor\s+quality', r'fell?\s+apart', r'cheap', r'malfunction',
                r'not\s+working', r'stopped?\s+working', r'dead\s+on\s+arrival',
                r'doa', r'faulty', r'ripped', r'torn', r'hole'
            ],
            'keywords': ['defect', 'broken', 'damage', 'quality', 'malfunction', 'faulty', 'rip', 'tear']
        },
        'SIZE_FIT_ISSUES': {
            'patterns': [
                r'too\s+(small|large|big|tight|loose)', r'doesn\'?t?\s+fit',
                r'wrong\s+size', r'size\s+(issue|problem)',
                r'(small|large)r?\s+than\s+expected', r'runs?\s+(small|large|big)',
                r'fit\s+(issue|problem)', r'not\s+the\s+right\s+size'
            ],
            'keywords': ['size', 'fit', 'small', 'large', 'tight', 'loose', 'big']
        },
        'WRONG_PRODUCT_OR_DESCRIPTION': {
            'patterns': [
                r'wrong\s+(item|product|model|color)', r'not\s+as\s+described',
                r'incorrect\s+(item|product)', r'different\s+than\s+(pictured|described|ordered)',
                r'not\s+what\s+i\s+ordered', r'received?\s+(wrong|different)',
                r'misrepresented', r'missing\s+parts'
            ],
            'keywords': ['wrong', 'incorrect', 'different', 'not as described', 'misrepresent', 'missing']
        },
        'BUYER_REMORSE_OR_MISTAKE': {
            'patterns': [
                r'bought?\s+by\s+mistake', r'accidentally\s+ordered',
                r'ordered?\s+(wrong|incorrect)\s+item', r'no\s+longer\s+need',
                r'don\'?t?\s+need', r'changed?\s+my?\s+mind',
                r'found?\s+(better|cheaper|different)', r'duplicate\s+order'
            ],
            'keywords': ['mistake', 'accident', 'no longer', 'changed mind', 'duplicate']
        },
        'FUNCTIONALITY_OR_USABILITY': {
            'patterns': [
                r'not\s+comfortable', r'hard\s+to\s+use',
                r'difficult\s+to\s+(use|operate|handle)', r'unstable',
                r'complicated', r'confusing', r'uncomfortable', r'awkward',
                r'not\s+user\s+friendly', r'design\s+(flaw|issue|problem)'
            ],
            'keywords': ['uncomfortable', 'difficult', 'hard to use', 'unstable', 'design']
        },
        'COMPATIBILITY_ISSUES': {
            'patterns': [
                r'doesn\'?t?\s+fit\s+(my|the|our)?\s*(toilet|chair|walker|bed)',
                r'not\s+compatible', r'incompatible',
                r'won\'?t?\s+(fit|work)\s+with'
            ],
            'keywords': ['compatible', 'incompatible', 'fit with']
        }
    }

    def __init__(self):
        self.compiled_patterns = {
            category: [re.compile(p, re.IGNORECASE) for p in data['patterns']]
            for category, data in self.CATEGORIES.items()
        }

    def categorize_reason(self, reason: str, comment: str = "") -> Tuple[str, float]:
        """Categorizes a single return reason based on text analysis."""
        combined_text = f"{reason or ''} {comment or ''}".lower().strip()
        if not combined_text:
            return "UNCATEGORIZED", 0.0

        category_scores = {}
        for category, patterns in self.compiled_patterns.items():
            score = sum(1 for pattern in patterns if pattern.search(combined_text))
            category_scores[category] = score

        best_category = max(category_scores, key=category_scores.get)
        if category_scores[best_category] > 0:
            return best_category, 1.0
        
        return "UNCATEGORIZED", 0.0

    def categorize_dataframe(self, df: pd.DataFrame, reason_col: str, comment_col: str) -> pd.DataFrame:
        """Applies return categorization to an entire DataFrame."""
        if reason_col not in df.columns or comment_col not in df.columns:
            return df
        
        # Ensure comment column exists and is filled to prevent errors
        if comment_col not in df.columns:
            df[comment_col] = ''
        df[comment_col] = df[comment_col].fillna('')

        results = df.apply(
            lambda row: self.categorize_reason(row.get(reason_col, ''), row.get(comment_col, '')),
            axis=1
        )
        df['category'] = [res[0] for res in results]
        df['category_confidence'] = [res[1] for res in results]
        return df


class MetricsCalculator:
    """
    Calculates key quality and sales metrics from sales and returns data.
    """
    @staticmethod
    def calculate_return_rates(sales_df: pd.DataFrame, returns_df: pd.DataFrame, group_by: str = 'sku') -> pd.DataFrame:
        """Calculates return rates grouped by a specific column (e.g., SKU)."""
        if sales_df.empty or returns_df.empty or group_by not in sales_df.columns or group_by not in returns_df.columns:
            return pd.DataFrame()

        sales_summary = sales_df.groupby(group_by)['quantity'].sum().reset_index()
        sales_summary.rename(columns={'quantity': 'total_sold'}, inplace=True)

        returns_summary = returns_df.groupby(group_by)['quantity'].sum().reset_index()
        returns_summary.rename(columns={'quantity': 'total_returned'}, inplace=True)

        summary_df = pd.merge(sales_summary, returns_summary, on=group_by, how='left')
        summary_df['total_returned'].fillna(0, inplace=True)
        
        summary_df['return_rate'] = summary_df.apply(
            lambda row: (row['total_returned'] / row['total_sold'] * 100) if row['total_sold'] > 0 else 0,
            axis=1
        )
        return summary_df.round(2)

    @staticmethod
    def identify_quality_hotspots(returns_df: pd.DataFrame, threshold: int = 5) -> pd.DataFrame:
        """Identifies products with a high number of quality-related returns."""
        if 'category' not in returns_df.columns:
            return pd.DataFrame()

        quality_returns = returns_df[returns_df['category'] == 'QUALITY_DEFECTS']
        hotspots = quality_returns.groupby('sku')['quantity'].sum().reset_index()
        hotspots.rename(columns={'quantity': 'quality_return_units'}, inplace=True)
        
        return hotspots[hotspots['quality_return_units'] >= threshold].sort_values('quality_return_units', ascending=False)


class QualityInsightsGenerator:
    """
    Generates actionable recommendations based on quality metrics and return data.
    """
    @staticmethod
    def generate_recommendations(metrics: Dict) -> List[Dict]:
        """Generates a list of recommendations based on analysis results."""
        recommendations = []
        
        # Recommendation for high overall return rate
        if metrics.get('overall_return_rate', 0) > 10:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Overall Performance',
                'issue': f"Overall return rate is critical at {metrics['overall_return_rate']:.1f}%.",
                'action': 'Initiate a cross-functional team to review top returning products and systemic issues.'
            })

        # Recommendation for product-specific high return rates
        if 'return_summary' in metrics and not metrics['return_summary'].empty:
            high_rate_products = metrics['return_summary'][metrics['return_summary']['return_rate'] > 15]
            for _, product in high_rate_products.iterrows():
                recommendations.append({
                    'priority': 'HIGH',
                    'category': 'Product Specific',
                    'issue': f"SKU {product['sku']} has an extremely high return rate of {product['return_rate']:.1f}%.",
                    'action': f"Conduct an immediate deep-dive investigation into SKU {product['sku']}, starting with quality inspection and listing accuracy."
                })

        # Recommendation for quality hotspots
        if 'quality_hotspots' in metrics and not metrics['quality_hotspots'].empty:
            hotspot = metrics['quality_hotspots'].iloc[0]
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Quality Control',
                'issue': f"SKU {hotspot['sku']} has a significant number of quality-related returns ({hotspot['quality_return_units']} units).",
                'action': 'Review manufacturing batch records and implement enhanced QC checks for this specific product.'
            })
        
        return recommendations


def run_full_analysis(sales_df: pd.DataFrame, returns_df: pd.DataFrame) -> Dict:
    """
    Orchestrates the full analysis pipeline.

    Args:
        sales_df: DataFrame with sales data.
        returns_df: DataFrame with returns data.

    Returns:
        A dictionary containing all analysis results.
    """
    if sales_df is None or returns_df is None or sales_df.empty or returns_df.empty:
        return {"error": "Insufficient data for analysis. Please provide both sales and returns data."}

    # 1. Categorize return reasons
    categorizer = ReturnReasonCategorizer()
    returns_df = categorizer.categorize_dataframe(returns_df, reason_col='reason', comment_col='customer_comments')

    # 2. Calculate metrics
    calc = MetricsCalculator()
    return_summary = calc.calculate_return_rates(sales_df, returns_df)
    quality_hotspots = calc.identify_quality_hotspots(returns_df)
    
    total_sales = sales_df['quantity'].sum()
    total_returns = returns_df['quantity'].sum()
    overall_return_rate = (total_returns / total_sales * 100) if total_sales > 0 else 0

    metrics = {
        'overall_return_rate': overall_return_rate,
        'total_sales': total_sales,
        'total_returns': total_returns,
        'products_affected_count': returns_df['sku'].nunique(),
        'quality_issues_count': len(quality_hotspots),
        'return_summary': return_summary,
        'quality_hotspots': quality_hotspots,
        'categorized_returns_df': returns_df
    }

    # 3. Generate insights and recommendations
    insights_gen = QualityInsightsGenerator()
    metrics['recommendations'] = insights_gen.generate_recommendations(metrics)

    return metrics

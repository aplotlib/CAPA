# src/fba_returns_processor.py

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from io import StringIO
import re

# Return reason categories for quality management
RETURN_CATEGORIES = {
    'SIZE_FIT_ISSUES': [
        'too small', 'too large', 'doesn\'t fit', 'wrong size', 'size issue',
        'too big', 'too tight', 'too loose', 'incorrect size'
    ],
    'QUALITY_DEFECTS': [
        'defective', 'broken', 'damaged', 'doesn\'t work', 'poor quality',
        'faulty', 'malfunction', 'not working', 'stopped working', 'dead'
    ],
    'WRONG_PRODUCT': [
        'wrong item', 'not as described', 'inaccurate description', 
        'different product', 'incorrect item', 'not what ordered'
    ],
    'BUYER_MISTAKE': [
        'bought by mistake', 'accidentally ordered', 'ordered wrong',
        'changed mind', 'duplicate order', 'no longer want'
    ],
    'NO_LONGER_NEEDED': [
        'no longer needed', 'don\'t need', 'not needed anymore',
        'found alternative', 'circumstances changed'
    ],
    'FUNCTIONALITY_ISSUES': [
        'not comfortable', 'hard to use', 'unstable', 'difficult to use',
        'uncomfortable', 'complicated', 'not user friendly'
    ],
    'COMPATIBILITY_ISSUES': [
        'doesn\'t fit toilet', 'not compatible', 'incompatible',
        'doesn\'t match', 'wrong connector', 'doesn\'t work with'
    ],
    'NOT_COMPATIBLE': [
        'not_compatible', 'not compatible'  # FBA specific code
    ]
}

class FBAReturnsProcessor:
    """Process FBA return reports from Amazon Seller Central."""
    
    @staticmethod
    def parse_fba_return_file(file_content: str) -> pd.DataFrame:
        """Parse FBA return report text file."""
        try:
            # FBA files are tab-delimited
            df = pd.read_csv(StringIO(file_content), delimiter='\t', dtype=str)
            
            # Clean column names
            df.columns = df.columns.str.strip().str.lower().str.replace('-', '_')
            
            return df
            
        except Exception as e:
            print(f"Error parsing FBA file: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def categorize_return_reason(reason: str, comment: str = None) -> str:
        """Categorize return reason based on text analysis."""
        
        # Combine reason and comment for analysis
        text_to_analyze = f"{reason or ''} {comment or ''}".lower().strip()
        
        if not text_to_analyze:
            return 'UNCATEGORIZED'
        
        # Check each category
        for category, keywords in RETURN_CATEGORIES.items():
            for keyword in keywords:
                if keyword in text_to_analyze:
                    return category
        
        # Special handling for common FBA codes
        if 'customer_damaged' in text_to_analyze:
            return 'QUALITY_DEFECTS'
        elif 'unwanted' in text_to_analyze:
            return 'NO_LONGER_NEEDED'
        
        return 'UNCATEGORIZED'
    
    @staticmethod
    def process_fba_returns(df: pd.DataFrame, target_sku: Optional[str] = None) -> Dict:
        """Process FBA returns data and generate insights."""
        
        if df.empty:
            return {"error": "No data to process"}
        
        # Filter by SKU if provided
        if target_sku and 'sku' in df.columns:
            df = df[df['sku'].str.strip() == target_sku.strip()]
            
            if df.empty:
                return {"error": f"No returns found for SKU: {target_sku}"}
        
        # Categorize returns
        if 'reason' in df.columns:
            comment_col = 'customer_comments' if 'customer_comments' in df.columns else None
            
            df['category'] = df.apply(
                lambda row: FBAReturnsProcessor.categorize_return_reason(
                    row.get('reason', ''),
                    row.get(comment_col, '') if comment_col else ''
                ),
                axis=1
            )
        else:
            df['category'] = 'UNCATEGORIZED'
        
        # Generate summary
        total_returns = len(df)
        category_counts = df['category'].value_counts().to_dict()
        
        # Calculate percentages
        category_percentages = {
            cat: (count / total_returns * 100) 
            for cat, count in category_counts.items()
        }
        
        # Identify top issues
        top_categories = sorted(
            category_percentages.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:3]
        
        # Generate insights
        insights = []
        
        if top_categories:
            insights.append(f"**Top Return Categories:**")
            for cat, pct in top_categories:
                readable_cat = cat.replace('_', ' ').title()
                insights.append(f"• {readable_cat}: {pct:.1f}%")
        
        # Quality-specific alerts
        quality_defects_pct = category_percentages.get('QUALITY_DEFECTS', 0)
        if quality_defects_pct > 20:
            insights.append(f"\n⚠️ **Quality Alert**: {quality_defects_pct:.1f}% of returns are due to quality defects!")
        
        # Size/fit issues for medical devices
        size_issues_pct = category_percentages.get('SIZE_FIT_ISSUES', 0)
        if size_issues_pct > 15:
            insights.append(f"\n📏 **Sizing Issue**: {size_issues_pct:.1f}% of returns are size-related. Consider reviewing product sizing guides.")
        
        # Date range if available
        if 'return_date' in df.columns:
            try:
                df['return_date'] = pd.to_datetime(df['return_date'])
                date_range = f"{df['return_date'].min().date()} to {df['return_date'].max().date()}"
                insights.append(f"\n📅 **Date Range**: {date_range}")
            except:
                pass
        
        return {
            'total_returns': total_returns,
            'category_counts': category_counts,
            'category_percentages': category_percentages,
            'top_issues': top_categories,
            'insights': '\n'.join(insights),
            'data': df
        }
    
    @staticmethod
    def generate_category_report(processed_data: Dict) -> pd.DataFrame:
        """Generate a summary report by category."""
        
        if 'category_counts' not in processed_data:
            return pd.DataFrame()
        
        report_data = []
        for category, count in processed_data['category_counts'].items():
            percentage = processed_data['category_percentages'].get(category, 0)
            
            # Determine action based on category
            if category == 'QUALITY_DEFECTS':
                action = "Investigate manufacturing/quality control"
            elif category == 'SIZE_FIT_ISSUES':
                action = "Review sizing guides and product specifications"
            elif category == 'WRONG_PRODUCT':
                action = "Review product listings and descriptions"
            elif category == 'FUNCTIONALITY_ISSUES':
                action = "Consider design improvements or user instructions"
            elif category == 'COMPATIBILITY_ISSUES':
                action = "Update compatibility information"
            else:
                action = "Monitor trends"
            
            report_data.append({
                'Category': category.replace('_', ' ').title(),
                'Count': count,
                'Percentage': f"{percentage:.1f}%",
                'Recommended Action': action
            })
        
        return pd.DataFrame(report_data).sort_values('Count', ascending=False)
    
    @staticmethod
    def compare_with_pivot_returns(fba_returns: int, pivot_returns: int) -> Dict:
        """Compare FBA returns with pivot report returns."""
        
        difference = abs(fba_returns - pivot_returns)
        percentage_diff = (difference / pivot_returns * 100) if pivot_returns > 0 else 0
        
        insights = []
        
        if percentage_diff > 10:
            insights.append(
                f"⚠️ **Data Discrepancy**: FBA reports show {fba_returns} returns "
                f"while pivot report shows {pivot_returns} ({percentage_diff:.1f}% difference). "
                "This may be due to different date ranges or return channels."
            )
        else:
            insights.append(
                f"✅ **Data Consistency**: FBA returns ({fba_returns}) align well "
                f"with pivot report ({pivot_returns})."
            )
        
        return {
            'fba_returns': fba_returns,
            'pivot_returns': pivot_returns,
            'difference': difference,
            'percentage_difference': percentage_diff,
            'insights': '\n'.join(insights)
        }

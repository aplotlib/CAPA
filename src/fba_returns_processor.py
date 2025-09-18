# src/fba_returns_processor.py

import pandas as pd
from io import StringIO

class FBAReturnsProcessor:
    """Processes and analyzes FBA return reports."""
    
    @staticmethod
    def parse_fba_return_file(file_content: str) -> pd.DataFrame:
        """Parses the text content of an FBA return report."""
        try:
            # FBA files are typically tab-delimited
            return pd.read_csv(StringIO(file_content), delimiter='\t', dtype=str)
        except Exception as e:
            print(f"Error parsing FBA file: {e}")
            return pd.DataFrame()

    @staticmethod
    def analyze_return_reasons(df: pd.DataFrame, target_sku: str) -> dict:
        """Analyzes return reasons for a specific SKU."""
        if df.empty or 'sku' not in df.columns or 'reason' not in df.columns:
            return {}
        
        sku_df = df[df['sku'] == target_sku]
        if sku_df.empty:
            return {"message": "No returns found for the target SKU in this file."}
            
        reason_counts = sku_df['reason'].value_counts().to_dict()
        top_reason = sku_df['reason'].mode()[0] if not sku_df['reason'].mode().empty else "N/A"
        
        return {
            "total_returns_in_file": len(sku_df),
            "top_return_reason": top_reason,
            "reason_breakdown": reason_counts
        }

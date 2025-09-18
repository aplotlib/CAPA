# src/returns_processor.py

import pandas as pd
from io import StringIO
from typing import Optional

class ReturnsProcessor:
    """Processes and analyzes return reports from various channels (FBA, FBM, etc.)."""
    
    @staticmethod
    def parse_returns_file(file_content: str) -> pd.DataFrame:
        """Parses the text content of a returns report."""
        try:
            # Universal parser that tries tab, then comma
            try:
                df = pd.read_csv(StringIO(file_content), delimiter='\t', dtype=str)
                if len(df.columns) <= 1:
                    raise ValueError("Not tab-separated")
                return df
            except (ValueError, pd.errors.ParserError):
                return pd.read_csv(StringIO(file_content), delimiter=',', dtype=str)
        except Exception as e:
            print(f"Error parsing returns file: {e}")
            return pd.DataFrame()

    @staticmethod
    def analyze_return_reasons(df: pd.DataFrame, target_sku: Optional[str] = None) -> dict:
        """Analyzes return reasons for a specific SKU."""
        if df.empty:
            return {}
            
        if target_sku:
             sku_col = next((col for col in df.columns if 'sku' in str(col).lower()), None)
             if sku_col:
                 df = df[df[sku_col].astype(str) == str(target_sku)]

        if df.empty:
            return {"message": "No returns found for the target SKU in this file."}
        
        reason_col = next((col for col in df.columns if 'reason' in str(col).lower()), None)
        if not reason_col:
             return {"message": "Could not find a 'reason' column in the returns file."}
            
        reason_counts = df[reason_col].value_counts().to_dict()
        top_reason = df[reason_col].mode()[0] if not df[reason_col].mode().empty else "N/A"
        
        return {
            "total_returns_in_file": len(df),
            "top_return_reason": top_reason,
            "reason_breakdown": reason_counts
        }

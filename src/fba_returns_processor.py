# src/fba_returns_processor.py

import pandas as pd
from io import StringIO
from typing import Optional, Dict

class ReturnsProcessor:
    """Processes and analyzes return reports from various channels (e.g., FBA, FBM)."""
    
    @staticmethod
    def parse_returns_file(file_content: str) -> pd.DataFrame:
        """
        Parses the text content of a returns report, attempting to handle
        both tab-separated and comma-separated formats.
        """
        if not file_content:
            return pd.DataFrame()
        
        try:
            # Attempt to parse as a tab-separated file first
            df = pd.read_csv(StringIO(file_content), delimiter='\t', dtype=str, on_bad_lines='warn')
            # If parsing results in a single column, it's likely not tab-separated
            if len(df.columns) <= 1:
                raise ValueError("File is not tab-separated, trying comma-separated.")
            return df
        except (ValueError, pd.errors.ParserError):
            try:
                # Fallback to comma-separated
                return pd.read_csv(StringIO(file_content), delimiter=',', dtype=str, on_bad_lines='warn')
            except Exception as e:
                print(f"Error parsing returns file as CSV: {e}")
                return pd.DataFrame()

    @staticmethod
    def analyze_return_reasons(df: pd.DataFrame, target_sku: Optional[str] = None) -> Dict:
        """
        Analyzes the return reasons within the DataFrame, optionally filtering
        for a specific target SKU.
        """
        if df.empty:
            return {"message": "Input DataFrame is empty."}

        # --- Find SKU column (case-insensitive) ---
        sku_col = next((col for col in df.columns if 'sku' in str(col).lower()), None)
        if target_sku and sku_col:
            df = df[df[sku_col].astype(str).str.strip() == str(target_sku).strip()].copy()

        if df.empty:
            return {"message": f"No returns found for the target SKU '{target_sku}' in this file."}
        
        # --- Find Reason column (case-insensitive) ---
        reason_col = next((col for col in df.columns if 'reason' in str(col).lower()), None)
        if not reason_col:
             return {"message": "Could not find a 'reason' column in the returns file."}
            
        # Drop rows where the reason is missing
        df.dropna(subset=[reason_col], inplace=True)
        
        if df.empty:
            return {"message": "No valid return reasons found in the data."}
            
        reason_counts = df[reason_col].value_counts().to_dict()
        top_reason = df[reason_col].mode().iloc[0] if not df[reason_col].mode().empty else "N/A"
        
        return {
            "total_returns_in_file": len(df),
            "top_return_reason": top_reason,
            "reason_breakdown": reason_counts
        }

# src/data_processing.py

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta

# Original helper function
def _find_column_name(df_columns: list, possible_names: list) -> Optional[str]:
    """Find column name from list of possibilities (case-insensitive)."""
    column_map = {str(col).lower().strip(): str(col) for col in df_columns}
    for name in possible_names:
        cleaned_name = name.lower().strip()
        if cleaned_name in column_map:
            return column_map[cleaned_name]
    return None

# Original functions for backward compatibility
def standardize_sales_data(df: pd.DataFrame, target_sku: str) -> Tuple[Optional[pd.DataFrame], Optional[List[str]]]:
    """Standardize sales data to common format."""
    sku_col = _find_column_name(df.columns, ['SKU'])
    sales_col = _find_column_name(df.columns, ['Sales'])
    if not sku_col or not sales_col: 
        return None, None

    df[sku_col] = df[sku_col].astype(str).str.strip()
    target_sku = target_sku.strip()
    
    df = df.rename(columns={sku_col: 'sku', sales_col: 'quantity'})
    
    product_data = df[df['sku'] == target_sku].copy()

    if product_data.empty:
        debug_sku_list = list(df['sku'].unique()[:10])
        return None, debug_sku_list

    product_data['quantity'] = pd.to_numeric(product_data['quantity'], errors='coerce')
    product_data.dropna(subset=['sku', 'quantity'], inplace=True)
    return product_data[['sku', 'quantity']], None

def standardize_returns_data(df: pd.DataFrame, target_sku: str) -> Optional[pd.DataFrame]:
    """Standardize returns data to common format."""
    if 'total_returned_quantity' not in df.columns or df.empty: 
        return None
    total_returns = df['total_returned_quantity'].iloc[0]
    return pd.DataFrame({'sku': [target_sku], 'quantity': [total_returns]})


# Enhanced DataProcessor class
class DataProcessor:
    """Enhanced data processor with optional AI capabilities."""
    
    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize with optional Anthropic API client."""
        self.client = None
        self.model = "claude-3-5-sonnet-20241022"
        
        if anthropic_api_key:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=anthropic_api_key)
            except ImportError:
                print("Anthropic library not available. AI features disabled.")
            except Exception as e:
                print(f"Failed to initialize Anthropic client: {e}")
    
    def process_sales_data(self, sales_df: pd.DataFrame, target_sku: str) -> pd.DataFrame:
        """Process and normalize sales data."""
        
        if sales_df is None or sales_df.empty:
            return pd.DataFrame()
        
        # Ensure we have required columns
        if 'sku' not in sales_df.columns:
            sales_df['sku'] = target_sku
        
        if 'quantity' not in sales_df.columns:
            # Try to find a quantity column
            qty_cols = [col for col in sales_df.columns if 'qty' in col.lower() or 'quantity' in col.lower()]
            if qty_cols:
                sales_df['quantity'] = sales_df[qty_cols[0]]
            else:
                # Sum all numeric columns as last resort
                numeric_cols = sales_df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    sales_df['quantity'] = sales_df[numeric_cols].sum(axis=1)
                else:
                    sales_df['quantity'] = 0
        
        # Ensure quantity is numeric
        sales_df['quantity'] = pd.to_numeric(sales_df['quantity'], errors='coerce').fillna(0)
        
        # Ensure we have a date column
        if 'date' not in sales_df.columns:
            sales_df['date'] = datetime.now()
        
        # Clean SKU column
        sales_df['sku'] = sales_df['sku'].astype(str).str.strip()
        
        # Group by SKU to get total
        result = sales_df.groupby('sku').agg({
            'quantity': 'sum'
        }).reset_index()
        
        # Add metadata
        result['data_source'] = 'sales_forecast'
        result['processed_date'] = datetime.now()
        
        return result
    
    def process_returns_data(self, returns_data: Any, target_sku: str) -> pd.DataFrame:
        """Process and normalize returns data."""
        
        if returns_data is None:
            return pd.DataFrame([{
                'sku': target_sku,
                'quantity': 0,
                'data_source': 'returns_pivot',
                'processed_date': datetime.now()
            }])
        
        # Handle dict format from parser
        if isinstance(returns_data, dict):
            return pd.DataFrame([{
                'sku': returns_data.get('sku', target_sku),
                'quantity': returns_data.get('quantity', 0),
                'data_source': 'returns_pivot',
                'pre_filtered': returns_data.get('pre_filtered', True),
                'processed_date': datetime.now()
            }])
        
        # Handle DataFrame format
        if isinstance(returns_data, pd.DataFrame):
            if returns_data.empty:
                return pd.DataFrame([{
                    'sku': target_sku,
                    'quantity': 0,
                    'data_source': 'returns_pivot',
                    'processed_date': datetime.now()
                }])
            
            # Ensure required columns
            if 'sku' not in returns_data.columns:
                returns_data['sku'] = target_sku
            
            if 'quantity' not in returns_data.columns:
                # Find quantity column
                qty_cols = [col for col in returns_data.columns if any(x in col.lower() for x in ['qty', 'quantity', 'return', 'total'])]
                if qty_cols:
                    returns_data['quantity'] = returns_data[qty_cols[0]]
                else:
                    returns_data['quantity'] = 0
            
            # Group by SKU
            result = returns_data.groupby('sku').agg({
                'quantity': 'sum'
            }).reset_index()
            
            result['data_source'] = 'returns_pivot'
            result['processed_date'] = datetime.now()
            
            return result
        
        # Fallback
        return pd.DataFrame([{
            'sku': target_sku,
            'quantity': 0,
            'data_source': 'returns_pivot',
            'processed_date': datetime.now()
        }])
    
    def analyze_quality_patterns(self, sales_df: pd.DataFrame, returns_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze quality patterns in the data."""
        
        if sales_df.empty or returns_df.empty:
            return {"insights": "Insufficient data for pattern analysis"}
        
        # Calculate metrics
        total_sales = sales_df['quantity'].sum()
        total_returns = returns_df['quantity'].sum()
        return_rate = (total_returns / total_sales * 100) if total_sales > 0 else 0
        
        # Generate insights
        insights = []
        
        if return_rate > 10:
            insights.append(f"⚠️ Critical: Return rate of {return_rate:.2f}% indicates serious quality issues")
        elif return_rate > 5:
            insights.append(f"⚠️ Warning: Return rate of {return_rate:.2f}% suggests quality concerns")
        else:
            insights.append(f"✅ Good: Return rate of {return_rate:.2f}% is within acceptable limits")
        
        # If AI client available, get enhanced insights
        if self.client:
            try:
                prompt = f"""
                Analyze this medical device quality data:
                - SKU: {sales_df['sku'].iloc[0] if not sales_df.empty else 'Unknown'}
                - Total Sales: {total_sales:,.0f} units
                - Total Returns: {total_returns:,.0f} units
                - Return Rate: {return_rate:.2f}%
                
                Provide 3-5 actionable quality insights.
                """
                
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                ai_insights = response.content[0].text
                insights.append("\n" + ai_insights)
                
            except Exception as e:
                print(f"AI insights unavailable: {e}")
        
        return {
            "insights": "\n".join(insights),
            "return_rate": return_rate,
            "severity": self._determine_severity(return_rate)
        }
    
    def _determine_severity(self, return_rate: float) -> str:
        """Determine severity based on return rate."""
        if return_rate > 10:
            return "Critical"
        elif return_rate > 5:
            return "Major"
        else:
            return "Minor"
    
    def correlate_data_sources(self, 
                             sales_data: pd.DataFrame, 
                             returns_data: pd.DataFrame,
                             misc_data: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Correlate data from multiple sources for comprehensive analysis."""
        
        correlation_results = {
            'data_quality': self._assess_data_quality(sales_data, returns_data),
            'temporal_patterns': self._analyze_temporal_patterns(sales_data, returns_data),
            'anomalies': self._detect_anomalies(sales_data, returns_data)
        }
        
        # Add miscellaneous data insights if available
        if misc_data is not None and not misc_data.empty:
            correlation_results['supporting_evidence'] = {
                'document_count': len(misc_data),
                'file_types': misc_data['type'].value_counts().to_dict() if 'type' in misc_data else {}
            }
        
        return correlation_results
    
    def _assess_data_quality(self, sales_df: pd.DataFrame, returns_df: pd.DataFrame) -> Dict[str, Any]:
        """Assess the quality and completeness of the data."""
        
        quality_metrics = {
            'sales_data_complete': not sales_df.empty,
            'returns_data_complete': not returns_df.empty,
            'sales_records': len(sales_df),
            'returns_records': len(returns_df),
            'data_coverage': 'Complete' if not sales_df.empty and not returns_df.empty else 'Partial'
        }
        
        # Check for data anomalies
        if not sales_df.empty and not returns_df.empty:
            total_sales = sales_df['quantity'].sum()
            total_returns = returns_df['quantity'].sum()
            
            if total_returns > total_sales:
                quality_metrics['warning'] = 'Returns exceed sales - please verify data'
            
            quality_metrics['confidence_level'] = 'High' if total_sales > 0 else 'Low'
        
        return quality_metrics
    
    def _analyze_temporal_patterns(self, sales_df: pd.DataFrame, returns_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze temporal patterns if date information is available."""
        
        patterns = {
            'sales_trend': 'Not available',
            'returns_trend': 'Not available'
        }
        
        # Add temporal analysis if we have date columns
        if 'date' in sales_df.columns:
            try:
                sales_df['date'] = pd.to_datetime(sales_df['date'])
                patterns['sales_date_range'] = {
                    'start': sales_df['date'].min().strftime('%Y-%m-%d'),
                    'end': sales_df['date'].max().strftime('%Y-%m-%d')
                }
            except:
                pass
        
        return patterns
    
    def _detect_anomalies(self, sales_df: pd.DataFrame, returns_df: pd.DataFrame) -> List[str]:
        """Detect any anomalies in the data."""
        
        anomalies = []
        
        if not sales_df.empty and not returns_df.empty:
            total_sales = sales_df['quantity'].sum()
            total_returns = returns_df['quantity'].sum()
            
            # Check for impossible scenarios
            if total_returns > total_sales:
                anomalies.append("Returns quantity exceeds sales quantity")
            
            # Check for extreme return rates
            if total_sales > 0:
                return_rate = (total_returns / total_sales) * 100
                if return_rate > 50:
                    anomalies.append(f"Extremely high return rate: {return_rate:.1f}%")
                elif return_rate > 20:
                    anomalies.append(f"High return rate: {return_rate:.1f}%")
            
            # Check for zero sales but positive returns
            if total_sales == 0 and total_returns > 0:
                anomalies.append("Returns recorded with no sales")
        
        return anomalies

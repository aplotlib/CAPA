# src/analysis.py

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime, timedelta

class MetricsCalculator:
    """Calculate quality metrics from sales and returns data."""
    
    @staticmethod
    def calculate_return_rates(sales_df: pd.DataFrame, returns_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate return rates with proper error handling."""
        
        if sales_df.empty:
            return pd.DataFrame()
        
        # Ensure we have the required columns
        if 'sku' not in sales_df.columns or 'quantity' not in sales_df.columns:
            raise ValueError("Sales data must have 'sku' and 'quantity' columns")
        
        # Group by SKU to get totals
        sales_summary = sales_df.groupby('sku')['quantity'].sum().reset_index()
        sales_summary.rename(columns={'quantity': 'total_sold'}, inplace=True)
        
        # Handle returns data
        if returns_df.empty:
            # No returns
            summary_df = sales_summary.copy()
            summary_df['total_returned'] = 0
        else:
            returns_summary = returns_df.groupby('sku')['quantity'].sum().reset_index()
            returns_summary.rename(columns={'quantity': 'total_returned'}, inplace=True)
            
            # Merge sales and returns
            summary_df = pd.merge(
                sales_summary, 
                returns_summary, 
                on='sku', 
                how='left'
            )
            
            # Fill NaN values with 0 for SKUs with no returns
            summary_df['total_returned'] = summary_df['total_returned'].fillna(0)
        
        # Calculate return rate
        summary_df['return_rate'] = summary_df.apply(
            lambda row: (row['total_returned'] / row['total_sold'] * 100) 
            if row['total_sold'] > 0 else 0, 
            axis=1
        )
        
        # Round values
        summary_df = summary_df.round(2)
        
        # Add quality indicators based on medical device standards
        summary_df['quality_status'] = summary_df['return_rate'].apply(
            lambda x: 'Critical' if x > 15 else ('Warning' if x > 10 else 'Good')
        )
        
        return summary_df
    
    @staticmethod
    def calculate_quality_score(return_rate: float) -> float:
        """
        Calculate quality score appropriate for medical devices.
        
        Medical device industry standards:
        - < 5% return rate: Excellent (90-100 score)
        - 5-10% return rate: Good (70-90 score) - Industry standard
        - 10-15% return rate: Acceptable (50-70 score)
        - 15-20% return rate: Needs Improvement (30-50 score)
        - > 20% return rate: Poor (0-30 score)
        """
        if return_rate < 5:
            # Excellent: Linear scale from 90-100
            quality_score = 90 + (5 - return_rate) * 2
        elif return_rate < 10:
            # Good: Linear scale from 70-90
            quality_score = 70 + (10 - return_rate) * 4
        elif return_rate < 15:
            # Acceptable: Linear scale from 50-70
            quality_score = 50 + (15 - return_rate) * 4
        elif return_rate < 20:
            # Needs Improvement: Linear scale from 30-50
            quality_score = 30 + (20 - return_rate) * 4
        else:
            # Poor: Scale from 0-30
            quality_score = max(0, 30 - (return_rate - 20) * 3)
        
        return round(quality_score)
    
    @staticmethod
    def calculate_quality_metrics(return_rate: float) -> Dict[str, any]:
        """Calculate additional quality metrics based on return rate."""
        
        # Calculate quality score using medical device standards
        quality_score = MetricsCalculator.calculate_quality_score(return_rate)
        
        # Determine risk level based on medical device thresholds
        if return_rate > 15:
            risk_level = 'High'
        elif return_rate > 10:
            risk_level = 'Medium'
        else:
            risk_level = 'Low'
        
        metrics = {
            'return_rate': return_rate,
            'quality_score': quality_score,
            'risk_level': risk_level,
            'investigation_required': return_rate > 10,  # Changed from 5% to 10%
            'capa_recommended': return_rate > 15  # Changed from 10% to 15%
        }
        
        # Add specific recommendations based on medical device standards
        if return_rate > 15:
            metrics['recommendations'] = [
                "Critical quality issue - immediate investigation required",
                "Consider product hold or recall evaluation",
                "Implement immediate corrective actions",
                "Review manufacturing process controls",
                "Notify quality management and regulatory affairs"
            ]
        elif return_rate > 10:
            metrics['recommendations'] = [
                "Above industry standard - investigation recommended",
                "Analyze return reasons and patterns",
                "Review quality control procedures",
                "Consider preventive actions",
                "Monitor trend closely"
            ]
        elif return_rate > 5:
            metrics['recommendations'] = [
                "Within industry standard range",
                "Continue monitoring for trends",
                "Review for continuous improvement opportunities"
            ]
        else:
            metrics['recommendations'] = [
                "Excellent quality performance",
                "Maintain current quality standards",
                "Share best practices across product lines"
            ]
        
        return metrics
    
    @staticmethod
    def calculate_financial_impact(sales_df: pd.DataFrame, returns_df: pd.DataFrame, 
                                 unit_cost: float = 100.0) -> Dict[str, float]:
        """Calculate financial impact of returns."""
        
        total_sales = sales_df['quantity'].sum() if not sales_df.empty else 0
        total_returns = returns_df['quantity'].sum() if not returns_df.empty else 0
        
        financial_metrics = {
            'total_revenue': total_sales * unit_cost,
            'return_cost': total_returns * unit_cost,
            'net_revenue': (total_sales - total_returns) * unit_cost,
            'return_percentage_of_revenue': (total_returns * unit_cost) / (total_sales * unit_cost) * 100 if total_sales > 0 else 0
        }
        
        return financial_metrics

def run_full_analysis(sales_df: pd.DataFrame, returns_df: pd.DataFrame, 
                     report_period_days: int = 30) -> Dict:
    """Run comprehensive analysis on sales and returns data."""
    
    # Validate input data
    if sales_df is None or sales_df.empty:
        return {
            "error": "Sales data is empty or invalid",
            "total_sales": 0,
            "total_returns": 0,
            "return_summary": pd.DataFrame()
        }
    
    # Initialize calculator
    calculator = MetricsCalculator()
    
    # Calculate return rates
    try:
        return_summary = calculator.calculate_return_rates(sales_df, returns_df)
    except Exception as e:
        return {
            "error": f"Failed to calculate return rates: {str(e)}",
            "total_sales": sales_df['quantity'].sum() if 'quantity' in sales_df else 0,
            "total_returns": returns_df['quantity'].sum() if returns_df is not None and 'quantity' in returns_df else 0,
            "return_summary": pd.DataFrame()
        }
    
    if return_summary.empty:
        return {
            "error": "Could not calculate return rates",
            "total_sales": 0,
            "total_returns": 0,
            "return_summary": pd.DataFrame()
        }
    
    # Get totals
    total_sales = sales_df['quantity'].sum() if 'quantity' in sales_df else 0
    total_returns = returns_df['quantity'].sum() if returns_df is not None and 'quantity' in returns_df else 0
    
    # Get primary SKU metrics
    primary_sku_data = return_summary.iloc[0] if not return_summary.empty else None
    
    # Calculate quality metrics
    quality_metrics = {}
    if primary_sku_data is not None:
        quality_metrics = calculator.calculate_quality_metrics(
            primary_sku_data['return_rate']
        )
    
    # Calculate financial impact
    financial_impact = calculator.calculate_financial_impact(
        sales_df, 
        returns_df if returns_df is not None else pd.DataFrame()
    )
    
    # Prepare insights
    insights = _generate_insights(
        return_summary,
        quality_metrics,
        financial_impact,
        report_period_days
    )
    
    # Compile results
    results = {
        'total_sales': total_sales,
        'total_returns': total_returns,
        'return_summary': return_summary,
        'quality_metrics': quality_metrics,
        'financial_impact': financial_impact,
        'insights': insights,
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'report_period_days': report_period_days
    }
    
    return results

def _generate_insights(return_summary: pd.DataFrame, quality_metrics: Dict,
                      financial_impact: Dict, period_days: int) -> str:
    """Generate human-readable insights from the analysis."""
    
    if return_summary.empty:
        return "No data available for analysis."
    
    primary_data = return_summary.iloc[0]
    insights = []
    
    # Return rate insight with medical device context
    insights.append(
        f"📊 **Return Rate Analysis**: The product has a {primary_data['return_rate']:.2f}% return rate "
        f"over the {period_days}-day period. (Medical device industry standard: 5-10%)"
    )
    
    # Quality status based on medical device standards
    if primary_data['return_rate'] > 15:
        insights.append(
            "🚨 **Critical Alert**: Return rate exceeds 15%, significantly above industry standards. "
            "This indicates serious quality issues requiring immediate investigation and corrective action."
        )
    elif primary_data['return_rate'] > 10:
        insights.append(
            "⚠️ **Warning**: Return rate is between 10-15%, above the industry standard of 5-10%. "
            "Investigation is recommended to identify and address quality concerns."
        )
    elif primary_data['return_rate'] > 5:
        insights.append(
            "✅ **Good Standing**: Return rate is between 5-10%, within industry standards. "
            "Continue monitoring for quality improvement opportunities."
        )
    else:
        insights.append(
            "🌟 **Excellent Performance**: Return rate is below 5%, indicating exceptional quality. "
            "This is well below industry standards."
        )
    
    # Financial impact
    if financial_impact:
        return_cost = financial_impact.get('return_cost', 0)
        insights.append(
            f"💰 **Financial Impact**: Returns have cost approximately ${return_cost:,.2f} "
            f"in the analysis period."
        )
    
    # Medical device specific insights
    if primary_data['return_rate'] > 10:
        insights.append(
            "\n**📋 Regulatory Considerations**:\n"
            "• Review per ISO 13485 requirements\n"
            "• Consider CAPA documentation\n"
            "• Evaluate need for regulatory notifications"
        )
    
    # Recommendations
    if quality_metrics and 'recommendations' in quality_metrics:
        insights.append("\n**Recommended Actions**:")
        for rec in quality_metrics['recommendations']:
            insights.append(f"• {rec}")
    
    return "\n\n".join(insights)

def analyze_return_trends(returns_df: pd.DataFrame, time_column: str = 'date') -> Dict:
    """Analyze trends in returns over time if date information is available."""
    
    if returns_df is None or returns_df.empty or time_column not in returns_df.columns:
        return {"trend_analysis": "Insufficient temporal data for trend analysis"}
    
    try:
        # Convert to datetime
        returns_df[time_column] = pd.to_datetime(returns_df[time_column])
        
        # Group by week
        weekly_returns = returns_df.groupby(
            pd.Grouper(key=time_column, freq='W')
        )['quantity'].sum()
        
        # Calculate trend
        if len(weekly_returns) > 1:
            trend = "increasing" if weekly_returns.iloc[-1] > weekly_returns.iloc[0] else "decreasing"
            
            return {
                "trend_analysis": f"Return trend is {trend}",
                "weekly_data": weekly_returns.to_dict(),
                "peak_week": weekly_returns.idxmax().strftime('%Y-%m-%d'),
                "peak_returns": float(weekly_returns.max())
            }
        else:
            return {"trend_analysis": "Not enough data points for trend analysis"}
            
    except Exception as e:
        return {"trend_analysis": f"Error analyzing trends: {str(e)}"}

def generate_capa_metrics(analysis_results: Dict) -> Dict:
    """Generate specific metrics for CAPA reporting."""
    
    if not analysis_results or 'return_summary' not in analysis_results:
        return {}
    
    summary = analysis_results['return_summary']
    if summary.empty:
        return {}
    
    primary_data = summary.iloc[0]
    
    # Determine investigation priority based on medical device standards
    if primary_data['return_rate'] > 15:
        investigation_priority = 'Critical'
    elif primary_data['return_rate'] > 10:
        investigation_priority = 'High'
    elif primary_data['return_rate'] > 5:
        investigation_priority = 'Medium'
    else:
        investigation_priority = 'Low'
    
    capa_metrics = {
        'defect_rate': primary_data['return_rate'],
        'total_defects': int(primary_data['total_returned']),
        'total_production': int(primary_data['total_sold']),
        'quality_level': primary_data['quality_status'],
        'investigation_priority': investigation_priority,
        'regulatory_risk': 'High' if primary_data['return_rate'] > 20 else 'Medium' if primary_data['return_rate'] > 15 else 'Low'
    }
    
    # Add ISO 13485 specific metrics
    capa_metrics['iso_13485_indicators'] = {
        'nonconformity_rate': primary_data['return_rate'],
        'customer_satisfaction_impact': 'Significant' if primary_data['return_rate'] > 15 else 'Moderate' if primary_data['return_rate'] > 10 else 'Minor',
        'process_capability': 'Needs improvement' if primary_data['return_rate'] > 10 else 'Acceptable'
    }
    
    # Add medical device specific risk assessment
    capa_metrics['medical_device_risk'] = {
        'patient_safety_impact': 'High' if primary_data['return_rate'] > 20 else 'Medium' if primary_data['return_rate'] > 15 else 'Low',
        'clinical_risk_assessment_required': primary_data['return_rate'] > 15,
        'design_review_recommended': primary_data['return_rate'] > 20
    }
    
    return capa_metrics

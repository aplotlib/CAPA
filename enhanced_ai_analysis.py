"""
Enhanced AI Analysis Module
Specialized for categorizing return reasons and generating quality insights
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import re
from datetime import datetime
import logging
import pdfplumber
import PyPDF2
from io import BytesIO
import streamlit as st

logger = logging.getLogger(__name__)

class ReturnReasonCategorizer:
    """Categorize return reasons using pattern matching and AI"""
    
    # Define return categories and their patterns
    CATEGORIES = {
        'SIZE_FIT_ISSUES': {
            'patterns': [
                r'too\s+(small|large|big|tight|loose)',
                r'doesn\'?t?\s+fit',
                r'wrong\s+size',
                r'size\s+(issue|problem)',
                r'(small|large)r?\s+than\s+expected',
                r'runs?\s+(small|large|big)',
                r'fit\s+(issue|problem)',
                r'not\s+the\s+right\s+size'
            ],
            'keywords': ['size', 'fit', 'small', 'large', 'tight', 'loose', 'big']
        },
        'QUALITY_DEFECTS': {
            'patterns': [
                r'defective',
                r'broken',
                r'damaged',
                r'doesn\'?t?\s+work',
                r'poor\s+quality',
                r'fell?\s+apart',
                r'cheap',
                r'malfunction',
                r'not\s+working',
                r'stopped?\s+working',
                r'dead\s+on\s+arrival',
                r'doa',
                r'faulty',
                r'ripped',
                r'torn',
                r'hole'
            ],
            'keywords': ['defect', 'broken', 'damage', 'quality', 'malfunction', 'faulty', 'rip', 'tear']
        },
        'WRONG_PRODUCT': {
            'patterns': [
                r'wrong\s+(item|product|model|color)',
                r'not\s+as\s+described',
                r'incorrect\s+(item|product)',
                r'different\s+than\s+(pictured|described|ordered)',
                r'not\s+what\s+i\s+ordered',
                r'received?\s+(wrong|different)',
                r'misrepresented'
            ],
            'keywords': ['wrong', 'incorrect', 'different', 'not as described', 'misrepresent']
        },
        'BUYER_MISTAKE': {
            'patterns': [
                r'bought?\s+by\s+mistake',
                r'accidentally\s+ordered',
                r'ordered?\s+(wrong|incorrect)',
                r'my\s+(mistake|fault|error)',
                r'didn\'?t?\s+mean\s+to',
                r'wrong\s+selection',
                r'user\s+error'
            ],
            'keywords': ['mistake', 'accident', 'error', 'fault', 'wrong order']
        },
        'NO_LONGER_NEEDED': {
            'patterns': [
                r'no\s+longer\s+need',
                r'don\'?t?\s+need',
                r'changed?\s+my?\s+mind',
                r'found?\s+(better|cheaper|different)',
                r'not\s+needed?\s+anymore',
                r'plans?\s+changed',
                r'duplicate\s+order'
            ],
            'keywords': ['no longer', 'not need', 'changed mind', 'duplicate']
        },
        'FUNCTIONALITY_ISSUES': {
            'patterns': [
                r'not\s+comfortable',
                r'hard\s+to\s+use',
                r'difficult\s+to\s+(use|operate|handle)',
                r'unstable',
                r'complicated',
                r'confusing',
                r'uncomfortable',
                r'awkward',
                r'not\s+user\s+friendly',
                r'design\s+(flaw|issue|problem)'
            ],
            'keywords': ['uncomfortable', 'difficult', 'hard to use', 'unstable', 'awkward', 'design']
        },
        'COMPATIBILITY_ISSUES': {
            'patterns': [
                r'doesn\'?t?\s+fit\s+(my|the|our)?\s*(toilet|chair|walker|bed)',
                r'not\s+compatible',
                r'incompatible',
                r'won\'?t?\s+(fit|work)\s+with',
                r'doesn\'?t?\s+match',
                r'not\s+suitable\s+for'
            ],
            'keywords': ['compatible', 'fit toilet', 'fit chair', 'match', 'suitable']
        }
    }
    
    def __init__(self):
        self.compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency"""
        compiled = {}
        for category, data in self.CATEGORIES.items():
            compiled[category] = [re.compile(pattern, re.IGNORECASE) for pattern in data['patterns']]
        return compiled
    
    def categorize_reason(self, reason: str, comment: str = "") -> Tuple[str, float]:
        """
        Categorize a return reason
        Returns: (category, confidence_score)
        """
        if pd.isna(reason):
            reason = ""
        if pd.isna(comment):
            comment = ""
            
        combined_text = f"{reason} {comment}".lower().strip()
        
        if not combined_text:
            return "UNCATEGORIZED", 0.0
        
        # Score each category
        category_scores = {}
        
        for category, patterns in self.compiled_patterns.items():
            score = 0
            matches = 0
            
            # Check regex patterns
            for pattern in patterns:
                if pattern.search(combined_text):
                    matches += 1
                    score += 2  # Pattern match weight
            
            # Check keywords
            keywords = self.CATEGORIES[category]['keywords']
            for keyword in keywords:
                if keyword.lower() in combined_text:
                    score += 1  # Keyword match weight
            
            # Normalize score
            max_possible = len(patterns) * 2 + len(keywords)
            confidence = (score / max_possible) if max_possible > 0 else 0
            category_scores[category] = confidence
        
        # Get best match
        if category_scores:
            best_category = max(category_scores, key=category_scores.get)
            confidence = category_scores[best_category]
            
            # Require minimum confidence
            if confidence >= 0.2:
                return best_category, confidence
        
        return "UNCATEGORIZED", 0.0
    
    def categorize_dataframe(self, df: pd.DataFrame, reason_col: str = 'reason', 
                           comment_col: str = 'customer_comments') -> pd.DataFrame:
        """Categorize all returns in a dataframe"""
        
        # Apply categorization
        results = df.apply(
            lambda row: self.categorize_reason(
                row.get(reason_col, ''),
                row.get(comment_col, '')
            ),
            axis=1
        )
        
        # Split results
        df['category'] = results.apply(lambda x: x[0])
        df['category_confidence'] = results.apply(lambda x: x[1])
        
        return df

class PDFReturnExtractor:
    """Extract return data from Amazon Seller Central PDFs"""
    
    @staticmethod
    def extract_from_pdf(pdf_file) -> pd.DataFrame:
        """Extract return data from PDF file"""
        try:
            returns_data = []
            
            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract tables
                    tables = page.extract_tables()
                    
                    for table in tables:
                        if not table:
                            continue
                        
                        # Try to identify return data table
                        headers = table[0] if table else []
                        
                        # Check for return-related headers
                        if any('return' in str(h).lower() for h in headers):
                            # Process table rows
                            for row in table[1:]:  # Skip header
                                if len(row) >= 3:  # Minimum columns needed
                                    return_entry = PDFReturnExtractor._parse_return_row(row, headers)
                                    if return_entry:
                                        returns_data.append(return_entry)
                    
                    # Also try text extraction for non-table data
                    text = page.extract_text()
                    if text:
                        # Look for return patterns in text
                        text_returns = PDFReturnExtractor._extract_from_text(text)
                        returns_data.extend(text_returns)
            
            if returns_data:
                df = pd.DataFrame(returns_data)
                return PDFReturnExtractor._standardize_columns(df)
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error extracting from PDF: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def _parse_return_row(row: List, headers: List) -> Optional[Dict]:
        """Parse a single row of return data"""
        try:
            # Map common header variations
            header_mapping = {
                'order': 'order_id',
                'order id': 'order_id',
                'order-id': 'order_id',
                'sku': 'sku',
                'asin': 'asin',
                'reason': 'reason',
                'return reason': 'reason',
                'comments': 'customer_comments',
                'customer comments': 'customer_comments',
                'date': 'return_date',
                'return date': 'return_date',
                'quantity': 'quantity',
                'qty': 'quantity'
            }
            
            # Create entry
            entry = {}
            for i, (header, value) in enumerate(zip(headers, row)):
                if header and value:
                    header_lower = str(header).lower().strip()
                    for pattern, field in header_mapping.items():
                        if pattern in header_lower:
                            entry[field] = str(value).strip()
                            break
            
            # Require minimum fields
            if 'order_id' in entry or 'sku' in entry:
                return entry
                
        except Exception as e:
            logger.debug(f"Error parsing row: {e}")
        
        return None
    
    @staticmethod
    def _extract_from_text(text: str) -> List[Dict]:
        """Extract return information from unstructured text"""
        returns = []
        
        # Pattern for order IDs (Amazon format)
        order_pattern = re.compile(r'\b\d{3}-\d{7}-\d{7}\b')
        
        # Split by lines and look for return information
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            order_match = order_pattern.search(line)
            if order_match:
                entry = {'order_id': order_match.group()}
                
                # Look for SKU nearby
                sku_pattern = re.compile(r'\b[A-Z]{3}\d{4}[A-Z0-9]*\b')
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    sku_match = sku_pattern.search(lines[j])
                    if sku_match:
                        entry['sku'] = sku_match.group()
                        break
                
                # Look for return reason
                for j in range(max(0, i-2), min(len(lines), i+5)):
                    line_lower = lines[j].lower()
                    if 'return' in line_lower or 'reason' in line_lower:
                        # Next line might be the reason
                        if j+1 < len(lines):
                            entry['reason'] = lines[j+1].strip()
                        break
                
                if 'sku' in entry:
                    returns.append(entry)
        
        return returns
    
    @staticmethod
    def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Standardize DataFrame columns"""
        
        # Ensure quantity is numeric
        if 'quantity' in df.columns:
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(1)
        else:
            df['quantity'] = 1
        
        # Parse dates
        date_cols = ['return_date', 'order_date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Add default return_date if missing
        if 'return_date' not in df.columns:
            df['return_date'] = pd.Timestamp.now()
        
        return df

class QualityInsightsGenerator:
    """Generate actionable quality insights from return data"""
    
    @staticmethod
    def generate_insights(categorized_df: pd.DataFrame, sales_df: Optional[pd.DataFrame] = None) -> Dict:
        """Generate comprehensive quality insights"""
        
        insights = {
            'summary': {},
            'category_breakdown': {},
            'product_specific': {},
            'trends': {},
            'recommendations': []
        }
        
        # Overall summary
        total_returns = len(categorized_df)
        insights['summary'] = {
            'total_returns': total_returns,
            'unique_products': categorized_df['sku'].nunique() if 'sku' in categorized_df else 0,
            'date_range': {
                'start': categorized_df['return_date'].min() if 'return_date' in categorized_df else None,
                'end': categorized_df['return_date'].max() if 'return_date' in categorized_df else None
            }
        }
        
        # Category breakdown
        if 'category' in categorized_df:
            category_counts = categorized_df['category'].value_counts()
            total = category_counts.sum()
            
            for category, count in category_counts.items():
                insights['category_breakdown'][category] = {
                    'count': int(count),
                    'percentage': round((count / total * 100), 2),
                    'products_affected': categorized_df[categorized_df['category'] == category]['sku'].nunique()
                }
        
        # Product-specific insights
        if 'sku' in categorized_df:
            for sku in categorized_df['sku'].unique():
                sku_data = categorized_df[categorized_df['sku'] == sku]
                
                insights['product_specific'][sku] = {
                    'total_returns': len(sku_data),
                    'primary_issue': sku_data['category'].mode()[0] if 'category' in sku_data else 'Unknown',
                    'category_distribution': sku_data['category'].value_counts().to_dict() if 'category' in sku_data else {}
                }
                
                # Calculate return rate if sales data available
                if sales_df is not None and 'sku' in sales_df:
                    sku_sales = sales_df[sales_df['sku'] == sku]['quantity'].sum()
                    if sku_sales > 0:
                        return_rate = (len(sku_data) / sku_sales * 100)
                        insights['product_specific'][sku]['return_rate'] = round(return_rate, 2)
        
        # Trend analysis
        if 'return_date' in categorized_df and 'category' in categorized_df:
            # Monthly trends
            categorized_df['month'] = pd.to_datetime(categorized_df['return_date']).dt.to_period('M')
            monthly_trends = categorized_df.groupby(['month', 'category']).size().unstack(fill_value=0)
            
            insights['trends']['monthly'] = monthly_trends.to_dict()
        
        # Generate recommendations
        insights['recommendations'] = QualityInsightsGenerator._generate_recommendations(insights)
        
        return insights
    
    @staticmethod
    def _generate_recommendations(insights: Dict) -> List[Dict]:
        """Generate actionable recommendations based on insights"""
        
        recommendations = []
        
        # Check for high quality defect rate
        if 'category_breakdown' in insights:
            quality_defects = insights['category_breakdown'].get('QUALITY_DEFECTS', {})
            if quality_defects.get('percentage', 0) > 20:
                recommendations.append({
                    'priority': 'HIGH',
                    'category': 'Quality Control',
                    'issue': f"Quality defects account for {quality_defects['percentage']}% of returns",
                    'action': 'Implement enhanced quality control inspection at manufacturing',
                    'impact': 'Could reduce returns by up to ' + str(quality_defects['count']) + ' units'
                })
        
        # Check for size/fit issues
        size_issues = insights['category_breakdown'].get('SIZE_FIT_ISSUES', {})
        if size_issues.get('percentage', 0) > 15:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Product Information',
                'issue': f"Size/fit issues represent {size_issues['percentage']}% of returns",
                'action': 'Update product listings with detailed sizing charts and fit guidance',
                'impact': 'Improve customer satisfaction and reduce size-related returns'
            })
        
        # Check for wrong product issues
        wrong_product = insights['category_breakdown'].get('WRONG_PRODUCT', {})
        if wrong_product.get('percentage', 0) > 10:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Listing Accuracy',
                'issue': f"Wrong product returns at {wrong_product['percentage']}%",
                'action': 'Review and update product images and descriptions for accuracy',
                'impact': 'Reduce customer confusion and wrong product shipments'
            })
        
        # Product-specific recommendations
        if 'product_specific' in insights:
            for sku, data in insights['product_specific'].items():
                if data.get('return_rate', 0) > 10:
                    recommendations.append({
                        'priority': 'HIGH',
                        'category': 'Product-Specific',
                        'issue': f"SKU {sku} has {data['return_rate']}% return rate",
                        'action': f"Investigate root cause for {sku} - primary issue: {data['primary_issue']}",
                        'impact': f"Address {data['total_returns']} returns for this product"
                    })
        
        return recommendations

# Integration function for Streamlit app
def analyze_returns_with_ai(returns_df: pd.DataFrame, sales_df: Optional[pd.DataFrame] = None) -> Dict:
    """Main function to analyze returns with AI categorization"""
    
    # Initialize categorizer
    categorizer = ReturnReasonCategorizer()
    
    # Categorize returns
    categorized_df = categorizer.categorize_dataframe(returns_df)
    
    # Generate insights
    insights = QualityInsightsGenerator.generate_insights(categorized_df, sales_df)
    
    # Add categorization confidence metrics
    if 'category_confidence' in categorized_df:
        avg_confidence = categorized_df['category_confidence'].mean()
        low_confidence = len(categorized_df[categorized_df['category_confidence'] < 0.3])
        
        insights['categorization_quality'] = {
            'average_confidence': round(avg_confidence, 3),
            'low_confidence_count': low_confidence,
            'uncategorized_count': len(categorized_df[categorized_df['category'] == 'UNCATEGORIZED'])
        }
    
    return {
        'categorized_data': categorized_df,
        'insights': insights
    }

# Streamlit UI component for the enhanced analysis
def display_ai_analysis(returns_df: pd.DataFrame, sales_df: Optional[pd.DataFrame] = None):
    """Display AI analysis results in Streamlit"""
    
    st.subheader("🤖 AI-Powered Return Analysis")
    
    with st.spinner("Analyzing returns with AI..."):
        results = analyze_returns_with_ai(returns_df, sales_df)
    
    categorized_df = results['categorized_data']
    insights = results['insights']
    
    # Display category breakdown
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Return Categories")
        
        if insights['category_breakdown']:
            # Create pie chart
            categories = list(insights['category_breakdown'].keys())
            values = [insights['category_breakdown'][cat]['count'] for cat in categories]
            
            import plotly.express as px
            fig = px.pie(
                values=values,
                names=categories,
                title="Return Reason Distribution",
                color_discrete_map={
                    'QUALITY_DEFECTS': '#dc2626',
                    'SIZE_FIT_ISSUES': '#f59e0b',
                    'WRONG_PRODUCT': '#eab308',
                    'FUNCTIONALITY_ISSUES': '#3b82f6',
                    'COMPATIBILITY_ISSUES': '#8b5cf6',
                    'BUYER_MISTAKE': '#10b981',
                    'NO_LONGER_NEEDED': '#6b7280',
                    'UNCATEGORIZED': '#e5e7eb'
                }
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Key Metrics")
        
        # Categorization quality
        if 'categorization_quality' in insights:
            quality = insights['categorization_quality']
            
            confidence_color = "#10b981" if quality['average_confidence'] > 0.7 else "#f59e0b"
            st.metric(
                "AI Confidence",
                f"{quality['average_confidence']:.1%}",
                help="Average confidence in categorization"
            )
            
            if quality['uncategorized_count'] > 0:
                st.warning(f"⚠️ {quality['uncategorized_count']} returns could not be categorized")
    
    # Recommendations
    if insights['recommendations']:
        st.markdown("### 💡 AI Recommendations")
        
        for rec in sorted(insights['recommendations'], key=lambda x: x['priority'] == 'HIGH', reverse=True):
            priority_color = "#dc2626" if rec['priority'] == 'HIGH' else "#f59e0b"
            
            st.markdown(f"""
            <div style="padding: 1rem; border-left: 4px solid {priority_color}; background: #f9fafb; margin-bottom: 1rem;">
                <strong style="color: {priority_color};">{rec['priority']} PRIORITY - {rec['category']}</strong><br>
                <strong>Issue:</strong> {rec['issue']}<br>
                <strong>Action:</strong> {rec['action']}<br>
                <strong>Impact:</strong> {rec['impact']}
            </div>
            """, unsafe_allow_html=True)
    
    # Show categorized data
    with st.expander("View Categorized Returns Data"):
        display_cols = ['order_id', 'sku', 'reason', 'category', 'category_confidence']
        available_cols = [col for col in display_cols if col in categorized_df.columns]
        
        st.dataframe(
            categorized_df[available_cols].style.background_gradient(
                subset=['category_confidence'],
                cmap='RdYlGn'
            ),
            use_container_width=True
        )

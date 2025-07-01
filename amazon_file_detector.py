"""
Amazon File Detector Module
Specialized for processing Amazon Seller Central returns data from PDFs and text files
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import re
from datetime import datetime
import pdfplumber
import logging
from io import StringIO, BytesIO

logger = logging.getLogger(__name__)

class AmazonReturnProcessor:
    """Process Amazon Seller Central return files in various formats"""
    
    # Amazon-specific return reason codes
    AMAZON_REASON_CODES = {
        'DEFECTIVE': 'Product defective or doesn\'t work',
        'NOT_COMPATIBLE': 'Item not compatible',
        'QUALITY_NOT_ADEQUATE': 'Quality not adequate',
        'DAMAGED_BY_FC': 'Damaged by fulfillment center',
        'DAMAGED_BY_CARRIER': 'Damaged by carrier',
        'CUSTOMER_DAMAGED': 'Customer damaged',
        'MISSING_PARTS': 'Missing parts or accessories',
        'FOUND_BETTER_PRICE': 'Found better price',
        'NOT_AS_DESCRIBED': 'Product not as described',
        'WRONG_ITEM': 'Wrong item sent',
        'UNWANTED_ITEM': 'No longer wanted',
        'UNAUTHORIZED_PURCHASE': 'Bought by mistake',
        'MISSED_ESTIMATED_DELIVERY': 'Missed estimated delivery',
        'SWITCHEROO': 'Different product returned',
        'UNDELIVERABLE_FAILED_DELIVERY': 'Undeliverable',
        'UNDELIVERABLE_UNABLE_TO_DELIVER': 'Unable to deliver',
        'ORDERED_WRONG_ITEM': 'Customer ordered wrong item'
    }
    
    @staticmethod
    def detect_file_type(file_content: bytes, filename: str) -> str:
        """Detect the type of Amazon file"""
        
        # Check file extension first
        if filename.lower().endswith('.pdf'):
            return 'pdf'
        elif filename.lower().endswith('.txt'):
            # Check if it's FBA returns format
            try:
                content = file_content.decode('utf-8')
                if 'return-date' in content and 'order-id' in content:
                    return 'fba_returns'
            except:
                pass
            return 'txt'
        elif filename.lower().endswith(('.csv', '.xlsx', '.xls')):
            return 'spreadsheet'
        
        return 'unknown'
    
    @staticmethod
    def process_fba_returns_txt(file_content: bytes) -> pd.DataFrame:
        """Process FBA returns text file"""
        try:
            # Decode content
            content = file_content.decode('utf-8')
            
            # Read tab-delimited file
            df = pd.read_csv(StringIO(content), sep='\t', 
                           parse_dates=['return-date'],
                           dtype={'order-id': str, 'sku': str, 'asin': str})
            
            # Standardize columns
            column_mapping = {
                'return-date': 'return_date',
                'order-id': 'order_id',
                'sku': 'sku',
                'asin': 'asin',
                'fnsku': 'fnsku',
                'product-name': 'product_name',
                'quantity': 'quantity',
                'fulfillment-center-id': 'fc_id',
                'detailed-disposition': 'disposition',
                'reason': 'reason_code',
                'status': 'status',
                'license-plate-number': 'lpn',
                'customer-comments': 'customer_comments'
            }
            
            df = df.rename(columns=column_mapping)
            
            # Add human-readable reason
            df['reason_description'] = df['reason_code'].map(
                AmazonReturnProcessor.AMAZON_REASON_CODES
            ).fillna(df['reason_code'])
            
            # Ensure quantity is numeric
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(1)
            
            # Add processing metadata
            df['source'] = 'FBA_RETURNS'
            df['processed_date'] = datetime.now()
            
            return df
            
        except Exception as e:
            logger.error(f"Error processing FBA returns file: {e}")
            raise
    
    @staticmethod
    def process_seller_central_pdf(pdf_file) -> pd.DataFrame:
        """Extract returns data from Seller Central PDF"""
        
        all_returns = []
        
        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract text
                    text = page.extract_text()
                    
                    # Extract tables
                    tables = page.extract_tables()
                    
                    # Process tables
                    for table in tables:
                        if table and len(table) > 1:
                            # Try to identify return table
                            headers = [str(h).lower() if h else '' for h in table[0]]
                            
                            # Check if this is a returns table
                            if any(keyword in ' '.join(headers) for keyword in ['return', 'order', 'reason']):
                                returns = AmazonReturnProcessor._parse_return_table(table)
                                all_returns.extend(returns)
                    
                    # Also extract from text using patterns
                    if text:
                        text_returns = AmazonReturnProcessor._extract_returns_from_text(text)
                        all_returns.extend(text_returns)
            
            if all_returns:
                df = pd.DataFrame(all_returns)
                # Remove duplicates based on order_id
                if 'order_id' in df.columns:
                    df = df.drop_duplicates(subset=['order_id'], keep='first')
                return AmazonReturnProcessor._standardize_pdf_data(df)
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise
    
    @staticmethod
    def _parse_return_table(table: List[List]) -> List[Dict]:
        """Parse a table that might contain return data"""
        
        if not table or len(table) < 2:
            return []
        
        returns = []
        headers = table[0]
        
        # Normalize headers
        header_mapping = {
            'order': 'order_id',
            'order id': 'order_id',
            'order number': 'order_id',
            'sku': 'sku',
            'asin': 'asin',
            'product': 'product_name',
            'item': 'product_name',
            'reason': 'reason',
            'return reason': 'reason',
            'qty': 'quantity',
            'quantity': 'quantity',
            'date': 'return_date',
            'return date': 'return_date',
            'comments': 'customer_comments',
            'buyer comments': 'customer_comments'
        }
        
        # Map headers to indices
        header_indices = {}
        for i, header in enumerate(headers):
            if header:
                header_lower = str(header).lower().strip()
                for pattern, field in header_mapping.items():
                    if pattern in header_lower:
                        header_indices[field] = i
                        break
        
        # Extract data from rows
        for row in table[1:]:
            if not row or all(not cell for cell in row):
                continue
            
            entry = {}
            for field, index in header_indices.items():
                if index < len(row) and row[index]:
                    entry[field] = str(row[index]).strip()
            
            # Only add if we have meaningful data
            if entry.get('order_id') or entry.get('sku'):
                # Default quantity to 1 if not specified
                if 'quantity' not in entry:
                    entry['quantity'] = '1'
                returns.append(entry)
        
        return returns
    
    @staticmethod
    def _extract_returns_from_text(text: str) -> List[Dict]:
        """Extract return information from unstructured text"""
        
        returns = []
        
        # Common patterns in Amazon return pages
        patterns = {
            'order_id': re.compile(r'\b(\d{3}-\d{7}-\d{7})\b'),
            'sku': re.compile(r'\b([A-Z]{2,4}\d{3,6}[A-Z0-9]*)\b'),
            'asin': re.compile(r'\b(B[0-9]{2}[A-Z0-9]{7})\b'),
            'date': re.compile(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w{3,9}\s+\d{1,2},?\s+\d{4})'),
        }
        
        # Split text into potential record blocks
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Look for order ID as anchor
            order_match = patterns['order_id'].search(line)
            if order_match:
                entry = {'order_id': order_match.group(1)}
                
                # Search nearby lines for related data
                search_window = 5
                for j in range(max(0, i-2), min(len(lines), i+search_window)):
                    current_line = lines[j]
                    
                    # SKU
                    if 'sku' not in entry:
                        sku_match = patterns['sku'].search(current_line)
                        if sku_match:
                            entry['sku'] = sku_match.group(1)
                    
                    # ASIN
                    if 'asin' not in entry:
                        asin_match = patterns['asin'].search(current_line)
                        if asin_match:
                            entry['asin'] = asin_match.group(1)
                    
                    # Return reason
                    if 'reason' not in entry:
                        reason_keywords = ['reason:', 'return reason:', 'returned:']
                        for keyword in reason_keywords:
                            if keyword in current_line.lower():
                                # Extract text after the keyword
                                reason_start = current_line.lower().find(keyword) + len(keyword)
                                reason_text = current_line[reason_start:].strip()
                                if not reason_text and j+1 < len(lines):
                                    reason_text = lines[j+1].strip()
                                if reason_text:
                                    entry['reason'] = reason_text
                                break
                
                if 'sku' in entry or 'asin' in entry:
                    entry['quantity'] = '1'  # Default
                    entry['source'] = 'PDF_TEXT'
                    returns.append(entry)
                
                i += search_window  # Skip processed lines
            else:
                i += 1
        
        return returns
    
    @staticmethod
    def _standardize_pdf_data(df: pd.DataFrame) -> pd.DataFrame:
        """Standardize data extracted from PDFs"""
        
        # Ensure required columns
        if 'quantity' in df.columns:
            df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(1)
        else:
            df['quantity'] = 1
        
        # Parse dates
        if 'return_date' in df.columns:
            df['return_date'] = pd.to_datetime(df['return_date'], errors='coerce')
        else:
            df['return_date'] = pd.Timestamp.now()
        
        # Add metadata
        df['source'] = df.get('source', 'SELLER_CENTRAL_PDF')
        df['processed_date'] = datetime.now()
        
        # Map common reason variations
        reason_mapping = {
            'defective': 'DEFECTIVE',
            'not working': 'DEFECTIVE',
            'broken': 'DEFECTIVE',
            'damaged': 'CUSTOMER_DAMAGED',
            'wrong item': 'WRONG_ITEM',
            'not as described': 'NOT_AS_DESCRIBED',
            'doesnt fit': 'NOT_COMPATIBLE',
            'changed mind': 'UNWANTED_ITEM',
            'no longer needed': 'UNWANTED_ITEM',
            'bought by mistake': 'UNAUTHORIZED_PURCHASE'
        }
        
        if 'reason' in df.columns:
            df['reason_normalized'] = df['reason'].str.lower().str.strip()
            for pattern, code in reason_mapping.items():
                mask = df['reason_normalized'].str.contains(pattern, na=False)
                df.loc[mask, 'reason_code'] = code
            
            # Add description for codes
            df['reason_description'] = df.get('reason_code', '').map(
                AmazonReturnProcessor.AMAZON_REASON_CODES
            ).fillna(df.get('reason', 'Unknown'))
        
        return df

class ReturnDataMerger:
    """Merge return data from multiple sources"""
    
    @staticmethod
    def merge_return_sources(pdf_returns: pd.DataFrame, 
                           fba_returns: pd.DataFrame,
                           review_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Intelligently merge return data from multiple sources"""
        
        all_dfs = []
        
        # Add source identifiers
        if not pdf_returns.empty:
            pdf_returns['data_source'] = 'PDF'
            all_dfs.append(pdf_returns)
        
        if not fba_returns.empty:
            fba_returns['data_source'] = 'FBA'
            all_dfs.append(fba_returns)
        
        if not all_dfs:
            return pd.DataFrame()
        
        # Combine all sources
        combined = pd.concat(all_dfs, ignore_index=True)
        
        # Remove duplicates intelligently
        # Prefer FBA data over PDF data for the same order
        combined = combined.sort_values('data_source', ascending=False)  # FBA comes before PDF
        
        if 'order_id' in combined.columns:
            combined = combined.drop_duplicates(subset=['order_id'], keep='first')
        
        # Merge with review data if available
        if review_data is not None and not review_data.empty:
            combined = ReturnDataMerger._merge_with_reviews(combined, review_data)
        
        # Sort by date
        if 'return_date' in combined.columns:
            combined = combined.sort_values('return_date', ascending=False)
        
        return combined
    
    @staticmethod
    def _merge_with_reviews(returns_df: pd.DataFrame, reviews_df: pd.DataFrame) -> pd.DataFrame:
        """Merge return data with product reviews"""
        
        # Find reviews that mention returns
        return_keywords = ['return', 'sent back', 'refund', 'exchange']
        
        # Create a mask for reviews mentioning returns
        review_mask = reviews_df['review_text'].str.lower().str.contains(
            '|'.join(return_keywords), na=False
        )
        
        return_reviews = reviews_df[review_mask].copy()
        return_reviews['data_source'] = 'REVIEW'
        return_reviews['inferred_return'] = True
        
        # Try to match reviews with returns by date proximity
        # (This is a simplified approach - could be enhanced with better matching logic)
        
        return returns_df

def analyze_amazon_returns(files: List[Tuple[bytes, str]], 
                         sales_data: Optional[pd.DataFrame] = None) -> Dict:
    """Main function to analyze Amazon returns from multiple file sources"""
    
    processor = AmazonReturnProcessor()
    all_returns = []
    file_summary = {
        'processed': 0,
        'failed': 0,
        'file_types': {}
    }
    
    for file_content, filename in files:
        try:
            file_type = processor.detect_file_type(file_content, filename)
            file_summary['file_types'][file_type] = file_summary['file_types'].get(file_type, 0) + 1
            
            if file_type == 'fba_returns':
                df = processor.process_fba_returns_txt(file_content)
                all_returns.append(df)
                file_summary['processed'] += 1
                
            elif file_type == 'pdf':
                df = processor.process_seller_central_pdf(BytesIO(file_content))
                if not df.empty:
                    all_returns.append(df)
                    file_summary['processed'] += 1
                else:
                    file_summary['failed'] += 1
                    
            else:
                logger.warning(f"Unsupported file type: {file_type} for {filename}")
                file_summary['failed'] += 1
                
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            file_summary['failed'] += 1
    
    # Merge all returns
    if all_returns:
        merged_returns = pd.concat(all_returns, ignore_index=True)
        
        # Remove duplicates
        if 'order_id' in merged_returns.columns:
            merged_returns = merged_returns.drop_duplicates(subset=['order_id'])
        
        # Analyze with enhanced AI
        from enhanced_ai_analysis import analyze_returns_with_ai
        analysis_results = analyze_returns_with_ai(merged_returns, sales_data)
        
        return {
            'success': True,
            'file_summary': file_summary,
            'total_returns': len(merged_returns),
            'returns_data': merged_returns,
            'analysis': analysis_results
        }
    
    return {
        'success': False,
        'file_summary': file_summary,
        'error': 'No return data could be extracted from the provided files'
    }

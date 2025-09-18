# src/parsers.py

import pandas as pd
from typing import Optional, Dict, Any, IO
from io import BytesIO
import json
import pytesseract
from PIL import Image
import anthropic

class AIFileParser:
    """Enhanced AI-powered file parser for various formats."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                self.model = "claude-3-5-sonnet-20240620"
            except Exception as e:
                print(f"Failed to initialize Anthropic client: {e}")

    def _get_file_preview(self, file: IO[bytes]) -> str:
        """Creates a text preview of a file."""
        file.seek(0)
        try: # Excel
            df = pd.read_excel(file, header=None).head(15)
            return f"EXCEL PREVIEW:\n{df.to_string()}"
        except Exception:
            file.seek(0)
            try: # CSV/TXT
                content = file.read(2000).decode('utf-8', errors='ignore')
                return f"TEXT PREVIEW:\n{content}"
            except Exception:
                return "Could not generate file preview."

    def _extract_text_from_image(self, file: IO[bytes]) -> str:
        """Extracts text from an image using OCR."""
        try:
            image = Image.open(file)
            return pytesseract.image_to_string(image)
        except Exception as e:
            return f"OCR Error: {e}"

    def analyze_file_structure(self, file: IO[bytes], target_sku: str) -> Dict[str, Any]:
        """Uses AI to analyze a file's structure and categorize its content."""
        if not self.client:
            return {"error": "AI client not initialized.", "filename": file.name}

        preview = ""
        file_extension = file.name.split('.')[-1].lower()
        if file_extension in ['png', 'jpg', 'jpeg']:
            preview = self._extract_text_from_image(file)
            if not preview:
                return {"error": "Could not extract text from image.", "filename": file.name}
            preview = f"OCR TEXT FROM IMAGE:\n{preview[:2000]}"
        else:
            preview = self._get_file_preview(file)

        prompt = f"""
        You are a data analysis expert for a quality management system.
        Analyze the following file preview and determine its content type and key data.
        The analysis is for the product with SKU: "{target_sku}".

        File Preview:
        {preview}

        Based on the preview, identify the file's primary purpose. Choose one content type from this list:
        ['sales', 'returns', 'inspection', 'voice_of_customer', 'other'].

        Then, extract the relevant data.
        - For 'sales' or 'returns', find the total quantity for the target SKU.
        - For 'inspection', summarize the pass/fail results.
        - For 'voice_of_customer', extract the NCX rate or key customer complaints.

        Return a JSON object with:
        "filename": "{file.name}"
        "content_type": "...",
        "key_data": {{...}},
        "summary": "A brief one-sentence summary of the file's content."
        
        Return ONLY the valid JSON object.
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text
            return json.loads(response)
        except Exception as e:
            return {"error": f"AI analysis failed: {e}", "filename": file.name}

    def extract_data(self, file: IO[bytes], analysis: Dict[str, Any], target_sku: str) -> Optional[pd.DataFrame]:
        """Extracts and standardizes data based on AI analysis."""
        content_type = analysis.get('content_type')
        if content_type not in ['sales', 'returns']:
            return None

        key_data = analysis.get('key_data', {})
        quantity = key_data.get('total_quantity', key_data.get('quantity'))

        if quantity is not None:
            try:
                # Handle cases where quantity might be a string with commas
                quantity = int(float(str(quantity).replace(',', '')))
                return pd.DataFrame([{'sku': target_sku, 'quantity': quantity}])
            except (ValueError, TypeError):
                # If direct extraction fails, fall back to reading the file
                pass
        
        # Fallback for complex files: read and let data_processing handle it
        file.seek(0)
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            # Simple search for SKU and quantity columns
            sku_col = next((col for col in df.columns if 'sku' in str(col).lower()), None)
            qty_col = next((col for col in df.columns if any(q in str(col).lower() for q in ['quantity', 'sales', 'units', 'returned'])), None)

            if sku_col and qty_col:
                df.rename(columns={sku_col: 'sku', qty_col: 'quantity'}, inplace=True)
                sku_data = df[df['sku'] == target_sku]
                return sku_data[['sku', 'quantity']]
                
        except Exception as e:
            print(f"Fallback parsing failed for {file.name}: {e}")
            return None
        
        return None

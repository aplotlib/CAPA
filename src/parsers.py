# src/parsers.py

import pandas as pd
from typing import Optional, Dict, Any, IO
import json
import pytesseract
from PIL import Image
import openai
from .utils import retry_with_backoff

class AIFileParser:
    """Enhanced AI-powered file parser for various formats using OpenAI."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = None
        if api_key:
            try:
                self.client = openai.OpenAI(api_key=api_key)
                self.model = "gpt-4o"
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")

    def _get_file_preview(self, file: IO[bytes]) -> str:
        """Creates a text preview of a file."""
        file.seek(0)
        try: # Excel
            df = pd.read_excel(file, header=None).head(15)
            return f"EXCEL PREVIEW:\n{df.to_string()}"
        except Exception:
            file.seek(0)
            try: # CSV/TXT
                # Read a limited number of bytes for preview
                preview_content = file.read(2000)
                # Decode safely, replacing errors
                content = preview_content.decode('utf-8', errors='replace')
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

    @retry_with_backoff()
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

        system_prompt = """
        You are a data analysis expert for a quality management system.
        Analyze the provided file preview to determine its content type and extract key data.
        Return ONLY a valid JSON object.
        """
        user_prompt = f"""
        Analyze the following file preview for the product with SKU: "{target_sku}".

        File Preview:
        {preview}

        Based on the preview, identify the file's primary purpose. Choose one content type from this list:
        ['sales', 'returns', 'inspection', 'voice_of_customer', 'other'].

        Then, extract the relevant data.
        - For 'sales' or 'returns', find the total quantity for the target SKU.
        - For 'inspection', summarize the pass/fail results.
        - For 'voice_of_customer', extract the NCX rate or key customer complaints.

        Return a JSON object with these exact keys:
        "filename": "{file.name}"
        "content_type": "...",
        "key_data": {{...}},
        "summary": "A brief one-sentence summary of the file's content."
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from AI file analysis: {e}")
            return {"error": "Failed to parse AI response.", "filename": file.name}
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
                quantity = int(float(str(quantity).replace(',', '')))
                return pd.DataFrame([{'sku': target_sku, 'quantity': quantity}])
            except (ValueError, TypeError):
                pass
        
        file.seek(0)
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
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

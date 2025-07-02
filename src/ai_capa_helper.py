# src/ai_capa_helper.py

import json
from typing import Dict, Optional
import anthropic

class AICAPAHelper:
    """AI assistant for generating CAPA form suggestions."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Anthropic API key."""
        self.client = None
        if api_key:
            try:
                self.client = anthropic.Anthropic(api_key=api_key)
                self.model = "claude-3-5-sonnet-20241022"
            except Exception as e:
                print(f"Failed to initialize AI helper: {e}")
    
    def generate_capa_suggestions(self, 
                                issue_summary: str, 
                                analysis_results: Dict,
                                product_info: Optional[Dict] = None) -> Dict[str, str]:
        """Generate AI suggestions for CAPA form fields."""
        
        if not self.client:
            return {}
        
        # Extract key metrics from analysis
        return_rate = 0
        total_returns = 0
        total_sales = 0
        sku = ""
        quality_status = ""
        
        if analysis_results and 'return_summary' in analysis_results:
            summary_df = analysis_results['return_summary']
            if not summary_df.empty:
                summary = summary_df.iloc[0]
                return_rate = summary.get('return_rate', 0)
                total_returns = int(summary.get('total_returned', 0))
                total_sales = int(summary.get('total_sold', 0))
                sku = summary.get('sku', '')
                quality_status = summary.get('quality_status', '')
        
        # Build context from available data
        context_parts = [
            f"Issue Summary: {issue_summary}",
            f"SKU: {sku}",
            f"Return Rate: {return_rate:.2f}% (Industry standard: 5-10%)",
            f"Total Returns: {total_returns} out of {total_sales} units",
            f"Quality Status: {quality_status}"
        ]
        
        if product_info:
            context_parts.append(f"Product: {product_info.get('name', 'Medical Device')}")
        
        context = "\n".join(context_parts)
        
        prompt = f"""
        You are a medical device quality expert helping to complete a CAPA (Corrective and Preventive Action) form.
        
        Context:
        {context}
        
        Based on this information, generate appropriate content for each CAPA form field following ISO 13485 standards.
        
        Requirements:
        1. Issue Description: Provide a detailed problem statement (150-250 words) that includes:
           - Clear description of the quality issue
           - Quantitative data (return rate, volumes)
           - Impact on customers/patients
           - Regulatory implications if applicable
        
        2. Root Cause Analysis: Provide a thorough root cause analysis (150-250 words) that:
           - Uses 5 Whys or Fishbone methodology
           - Identifies both immediate and underlying causes
           - References specific failure modes
           - Considers design, manufacturing, and supply chain factors
        
        3. Corrective Actions: List immediate actions (100-200 words) to:
           - Address existing inventory
           - Handle customer complaints
           - Implement temporary controls
           - Include specific timelines and responsibilities
        
        4. Preventive Actions: List long-term actions (100-200 words) to:
           - Prevent recurrence across all products
           - Update procedures and specifications
           - Implement permanent controls
           - Include verification and validation plans
        
        Return a JSON object with these exact fields:
        {{
            "issue_description": "...",
            "root_cause": "...",
            "corrective_action": "...",
            "preventive_action": "..."
        }}
        
        Make the content specific, actionable, and compliant with medical device regulations.
        Return ONLY valid JSON without any additional text.
        """
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2500,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse the response
            response_text = response.content[0].text.strip()
            
            # Clean up response if needed
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            suggestions = json.loads(response_text)
            
            # Validate all required fields are present
            required_fields = ['issue_description', 'root_cause', 'corrective_action', 'preventive_action']
            for field in required_fields:
                if field not in suggestions:
                    suggestions[field] = ""
            
            return suggestions
            
        except json.JSONDecodeError as e:
            print(f"Error parsing AI response: {e}")
            return {}
        except Exception as e:
            print(f"Error generating suggestions: {e}")
            return {}
    
    def enhance_existing_text(self, field_name: str, current_text: str, context: Dict) -> str:
        """Enhance existing text in a specific field."""
        
        if not self.client or not current_text:
            return current_text
        
        prompt = f"""
        You are a medical device quality expert. Enhance the following {field_name} text to be more comprehensive and compliant with ISO 13485:
        
        Current text:
        {current_text}
        
        Context:
        - Return Rate: {context.get('return_rate', 'Unknown')}%
        - Product: {context.get('product', 'Medical Device')}
        
        Improve the text by:
        1. Adding specific details and metrics
        2. Ensuring regulatory compliance language
        3. Making actions more specific and measurable
        4. Adding timelines where appropriate
        
        Return only the enhanced text, no additional commentary.
        """
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            print(f"Error enhancing text: {e}")
            return current_text
    
    def suggest_severity(self, return_rate: float, issue_description: str = "") -> str:
        """Suggest appropriate severity level based on return rate and issue description."""
        
        # Basic logic based on return rate
        if return_rate > 15:
            base_severity = "Critical"
        elif return_rate > 10:
            base_severity = "Major"
        else:
            base_severity = "Minor"
        
        # If AI is available, get more nuanced suggestion
        if self.client and issue_description:
            try:
                prompt = f"""
                Based on:
                - Return rate: {return_rate}%
                - Issue: {issue_description[:200]}
                
                For a medical device, should the CAPA severity be Critical, Major, or Minor?
                Consider patient safety, regulatory requirements, and business impact.
                
                Respond with only one word: Critical, Major, or Minor.
                """
                
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=10,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                severity = response.content[0].text.strip()
                if severity in ["Critical", "Major", "Minor"]:
                    return severity
                    
            except:
                pass
        
        return base_severity

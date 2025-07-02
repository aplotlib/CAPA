# src/document_generator.py

import json
from typing import Dict, Optional, List
from io import BytesIO
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import anthropic

class CapaDocumentGenerator:
    """Generates formal, table-based CAPA reports from structured data."""
    
    def __init__(self, anthropic_api_key: Optional[str] = None):
        """Initialize with Anthropic API client if key provided."""
        self.anthropic_client = None
        if anthropic_api_key:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
                self.model = "claude-3-5-sonnet-20241022"
            except Exception as e:
                print(f"Failed to initialize Anthropic client: {e}")

    def _build_capa_prompt(self, capa_data: Dict, analysis_results: Dict) -> str:
        """Construct a detailed prompt for AI to generate JSON-structured CAPA report."""
        
        # Extract return rate safely
        return_rate = 'N/A'
        total_sales = 'N/A'
        total_returns = 'N/A'
        
        if 'return_summary' in analysis_results and not analysis_results['return_summary'].empty:
            summary = analysis_results['return_summary'].iloc[0]
            return_rate = f"{summary['return_rate']:.2f}%"
            total_sales = f"{int(summary['total_sold']):,}"
            total_returns = f"{int(summary['total_returned']):,}"
        
        # Extract quality insights
        insights = analysis_results.get('insights', 'No insights available')
        quality_status = 'Unknown'
        if 'quality_metrics' in analysis_results:
            quality_status = analysis_results['quality_metrics'].get('risk_level', 'Unknown')

        prompt = f"""
        You are a medical device quality assurance expert creating a formal CAPA report.
        Based on the following data, generate comprehensive content for each section.
        Return ONLY a valid JSON object with no additional text or formatting.

        **CAPA DETAILS:**
        - CAPA Number: {capa_data.get('capa_number', 'TBD')}
        - Product: {capa_data.get('product', 'TBD')}
        - SKU: {capa_data.get('sku', 'TBD')}
        - Severity: {capa_data.get('severity', 'TBD')}
        - Date: {capa_data.get('date', 'TBD')}
        - Prepared By: {capa_data.get('prepared_by', 'TBD')}

        **QUALITY DATA:**
        - Return Rate: {return_rate}
        - Total Units Sold: {total_sales}
        - Total Units Returned: {total_returns}
        - Quality Risk Level: {quality_status}

        **PROVIDED INFORMATION:**
        - Issue Description: {capa_data.get('issue_description', 'No description provided.')}
        - Root Cause: {capa_data.get('root_cause', 'To be determined')}
        - Corrective Actions: {capa_data.get('corrective_action', 'To be determined')}
        - Preventive Actions: {capa_data.get('preventive_action', 'To be determined')}

        **ANALYSIS INSIGHTS:**
        {insights}

        Generate a complete CAPA report with the following JSON structure:
        {{
          "executive_summary": "Brief overview of the issue and its impact",
          "issue": "Detailed description expanding on the provided issue, including quantitative data",
          "immediate_actions": "List specific immediate containment actions taken or to be taken",
          "investigation_methodology": "Describe the investigation approach (5 Whys, Fishbone, FMEA, etc.)",
          "root_cause": "Detailed root cause analysis findings with supporting evidence",
          "corrective_action_plan": "Specific actions to address the root cause with timelines",
          "corrective_action_implementation": "Implementation details including responsible parties and deadlines",
          "preventive_action_plan": "Actions to prevent recurrence in this and similar products",
          "preventive_action_implementation": "How preventive actions will be implemented across the organization",
          "effectiveness_check_plan": "Specific metrics and methods to verify effectiveness",
          "effectiveness_check_timeline": "When and how effectiveness will be measured",
          "effectiveness_check_findings": "To be completed after implementation",
          "risk_assessment": "Assessment of risks if CAPA is not implemented",
          "regulatory_considerations": "Any regulatory requirements or notifications needed",
          "resource_requirements": "Resources needed for implementation",
          "additional_comments": "Any other relevant information or context"
        }}
        """
        
        return prompt

    def generate_ai_structured_content(self, capa_data: Dict, analysis_results: Dict) -> Optional[Dict]:
        """Generate structured CAPA content using AI model."""
        
        if not self.anthropic_client:
            # Return a template structure if AI is not available
            return self._get_default_template(capa_data, analysis_results)
        
        prompt = self._build_capa_prompt(capa_data, analysis_results)
        
        try:
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            # Extract and parse JSON response
            response_text = response.content[0].text
            
            # Clean response if needed
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            return json.loads(response_text.strip())
            
        except json.JSONDecodeError as e:
            print(f"Error parsing AI response as JSON: {e}")
            return self._get_default_template(capa_data, analysis_results)
        except Exception as e:
            print(f"Error generating AI content: {e}")
            return self._get_default_template(capa_data, analysis_results)

    def _get_default_template(self, capa_data: Dict, analysis_results: Dict) -> Dict:
        """Provide a default template when AI is unavailable."""
        
        return_rate = 'N/A'
        if 'return_summary' in analysis_results and not analysis_results['return_summary'].empty:
            return_rate = f"{analysis_results['return_summary'].iloc[0]['return_rate']:.2f}%"
        
        return {
            "executive_summary": f"This CAPA addresses quality issues identified for SKU {capa_data.get('sku', 'N/A')} with a return rate of {return_rate}.",
            "issue": capa_data.get('issue_description', 'Issue description to be provided'),
            "immediate_actions": "1. Quarantine affected inventory\n2. Notify quality team\n3. Begin investigation",
            "investigation_methodology": "Root cause analysis using 5 Whys and Fishbone diagram",
            "root_cause": capa_data.get('root_cause', 'Root cause to be determined'),
            "corrective_action_plan": capa_data.get('corrective_action', 'Corrective actions to be determined'),
            "corrective_action_implementation": "To be determined by quality team",
            "preventive_action_plan": capa_data.get('preventive_action', 'Preventive actions to be determined'),
            "preventive_action_implementation": "To be implemented across all product lines",
            "effectiveness_check_plan": "Monitor return rates for 90 days post-implementation",
            "effectiveness_check_timeline": "90 days from implementation date",
            "effectiveness_check_findings": "To be completed after implementation",
            "risk_assessment": "Medium to High risk if not addressed",
            "regulatory_considerations": "Review required per ISO 13485",
            "resource_requirements": "Quality team, Engineering support",
            "additional_comments": "Document generated on " + datetime.now().strftime('%Y-%m-%d')
        }

    def export_to_docx(self, capa_data: Dict, content: Dict) -> BytesIO:
        """Export content to a professionally formatted Word document."""
        
        doc = Document()
        
        # Set document properties
        doc.core_properties.title = f"CAPA Report - {capa_data.get('capa_number', 'Draft')}"
        doc.core_properties.author = capa_data.get('prepared_by', 'Quality Team')
        
        # Add header
        self._add_header(doc, capa_data)
        
        # Add CAPA information table
        self._add_capa_info_table(doc, capa_data)
        
        # Add executive summary
        if 'executive_summary' in content:
            doc.add_heading('Executive Summary', level=2)
            doc.add_paragraph(content['executive_summary'])
            doc.add_paragraph()
        
        # Add main sections
        sections = [
            ('Issue Description', 'issue'),
            ('Immediate Actions/Corrections', 'immediate_actions'),
            ('Investigation Methodology', 'investigation_methodology'),
            ('Root Cause Analysis', 'root_cause'),
            ('Corrective Action Plan', 'corrective_action_plan'),
            ('Corrective Action Implementation', 'corrective_action_implementation'),
            ('Preventive Action Plan', 'preventive_action_plan'),
            ('Preventive Action Implementation', 'preventive_action_implementation'),
            ('Effectiveness Check Plan', 'effectiveness_check_plan'),
            ('Effectiveness Check Timeline', 'effectiveness_check_timeline'),
            ('Effectiveness Check Findings', 'effectiveness_check_findings'),
            ('Risk Assessment', 'risk_assessment'),
            ('Regulatory Considerations', 'regulatory_considerations'),
            ('Resource Requirements', 'resource_requirements'),
            ('Additional Comments', 'additional_comments')
        ]
        
        for heading, key in sections:
            if key in content and content[key]:
                doc.add_heading(heading, level=2)
                
                # Handle multi-line content
                if '\n' in str(content[key]):
                    for line in str(content[key]).split('\n'):
                        if line.strip():
                            doc.add_paragraph(line.strip())
                else:
                    doc.add_paragraph(content[key])
                
                doc.add_paragraph()  # Add spacing
        
        # Add signature section
        self._add_signature_section(doc, capa_data)
        
        # Save to BytesIO
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        return buffer

    def _add_header(self, doc: Document, capa_data: Dict):
        """Add document header with title and company info."""
        
        # Add title
        title = doc.add_heading('CORRECTIVE AND PREVENTIVE ACTION (CAPA) REPORT', level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add subtitle with CAPA number
        subtitle = doc.add_paragraph(f"CAPA Number: {capa_data.get('capa_number', 'TBD')}")
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle.runs[0].font.size = Pt(14)
        subtitle.runs[0].font.bold = True
        
        # Add date
        date_para = doc.add_paragraph(f"Date: {capa_data.get('date', datetime.now().strftime('%Y-%m-%d'))}")
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph()  # Add spacing

    def _add_capa_info_table(self, doc: Document, capa_data: Dict):
        """Add CAPA information table."""
        
        # Create table
        table = doc.add_table(rows=6, cols=2)
        table.style = 'Light Shading'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        
        # Populate table
        info_items = [
            ('CAPA Number:', capa_data.get('capa_number', 'TBD')),
            ('Product Name:', capa_data.get('product', 'TBD')),
            ('SKU:', capa_data.get('sku', 'TBD')),
            ('Severity:', capa_data.get('severity', 'TBD')),
            ('Prepared By:', capa_data.get('prepared_by', 'TBD')),
            ('Date:', capa_data.get('date', datetime.now().strftime('%Y-%m-%d')))
        ]
        
        for i, (label, value) in enumerate(info_items):
            table.cell(i, 0).text = label
            table.cell(i, 1).text = str(value)
            
            # Format label cell
            table.cell(i, 0).paragraphs[0].runs[0].font.bold = True
            
            # Set column widths
            table.cell(i, 0).width = Inches(2)
            table.cell(i, 1).width = Inches(4)
        
        doc.add_paragraph()  # Add spacing

    def _add_signature_section(self, doc: Document, capa_data: Dict):
        """Add signature section at the end of the document."""
        
        doc.add_page_break()
        doc.add_heading('Approvals', level=2)
        
        # Create signature table
        table = doc.add_table(rows=4, cols=3)
        table.style = 'Light List'
        
        # Headers
        headers = ['Role', 'Name/Signature', 'Date']
        for i, header in enumerate(headers):
            table.cell(0, i).text = header
            table.cell(0, i).paragraphs[0].runs[0].font.bold = True
        
        # Signature rows
        roles = [
            'Prepared By (Quality)',
            'Reviewed By (Engineering)',
            'Approved By (Management)'
        ]
        
        for i, role in enumerate(roles, 1):
            table.cell(i, 0).text = role
            table.cell(i, 1).text = '_' * 30
            table.cell(i, 2).text = '_' * 15
        
        # Add note
        doc.add_paragraph()
        note = doc.add_paragraph('Note: This document is part of the Quality Management System and should be retained according to document control procedures.')
        note.runs[0].font.size = Pt(10)
        note.runs[0].font.italic = True

    def generate_investigation_template(self, capa_data: Dict) -> BytesIO:
        """Generate an investigation template for the CAPA."""
        
        doc = Document()
        
        doc.add_heading(f'CAPA Investigation Template - {capa_data.get("capa_number", "TBD")}', level=1)
        
        # Investigation sections
        sections = [
            ('Problem Statement', 'Clearly define the problem including Who, What, When, Where, and How'),
            ('Data Collection', 'List all data sources and evidence collected'),
            ('5 Whys Analysis', 'Why 1:\nWhy 2:\nWhy 3:\nWhy 4:\nWhy 5:'),
            ('Fishbone Diagram Categories', 'Man:\nMachine:\nMethod:\nMaterial:\nMeasurement:\nEnvironment:'),
            ('Potential Root Causes', 'List all potential root causes identified'),
            ('Root Cause Verification', 'How will you verify the true root cause?'),
            ('Proposed Solutions', 'List potential corrective and preventive actions')
        ]
        
        for heading, content in sections:
            doc.add_heading(heading, level=2)
            doc.add_paragraph(content)
            doc.add_paragraph()  # Add spacing
        
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        return buffer

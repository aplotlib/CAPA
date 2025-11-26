import pandas as pd
from io import BytesIO
from fpdf import FPDF

class UniversalExporter:
    """Handles export of data to non-Word formats (PDF, Excel)."""

    def export_to_excel(self, data_dict: dict) -> BytesIO:
        """Flattens a dictionary and exports it to an Excel file."""
        output = BytesIO()
        # Flatten dictionary to simple key-value pairs for Excel
        flat_data = {k: [str(v)] for k, v in data_dict.items() if isinstance(v, (str, int, float, type(None)))}
        
        df = pd.DataFrame(flat_data)
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Data')
            # Auto-adjust column width
            for column in df:
                column_width = max(df[column].astype(str).map(len).max(), len(column))
                col_idx = df.columns.get_loc(column)
                writer.sheets['Data'].set_column(col_idx, col_idx, column_width + 2)
        
        output.seek(0)
        return output

    def export_to_pdf(self, capa_data: dict) -> BytesIO:
        """Generates a professional PDF report for a CAPA."""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        # Title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt=f"CAPA Report: {capa_data.get('capa_number', 'Draft')}", ln=True, align='C')
        pdf.ln(10)

        # Content
        pdf.set_font("Arial", size=10)
        fields = [
            ("Product", 'product_name'),
            ("Date", 'date'),
            ("Issue Description", 'issue_description'),
            ("Root Cause", 'root_cause'),
            ("Corrective Action", 'corrective_action'),
            ("Preventive Action", 'preventive_action'),
            ("Effectiveness Check", 'effectiveness_check_findings'),
            ("Status", 'status')
        ]

        for label, key in fields:
            val = str(capa_data.get(key, 'N/A'))
            # Heading
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, txt=label, ln=True)
            # Text
            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 6, txt=val)
            pdf.ln(4)

        # Output
        return BytesIO(pdf.output(dest='S').encode('latin-1', 'replace'))

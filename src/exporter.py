# src/exporter.py

from fpdf import FPDF
import pandas as pd
from io import BytesIO

class UniversalExporter:
    """A class to handle exporting data to multiple formats."""

    def export_to_pdf(self, data: dict) -> bytes:
        """Exports data to a PDF file."""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        for key, value in data.items():
            pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)
        return pdf.output(dest='S').encode('latin-1')

    def export_to_excel(self, data: dict) -> bytes:
        """Exports data to an Excel file."""
        df = pd.DataFrame.from_dict(data, orient='index', columns=['Value'])
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Export')
        return output.getvalue()

# src/document_generator.py
from io import BytesIO
from docx import Document

def export_to_docx(capa_data: dict, analysis_results: dict) -> BytesIO:
    doc = Document()
    doc.add_heading('CAPA Report', 0)
    # Add content to the document
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

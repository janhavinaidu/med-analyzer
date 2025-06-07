from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import os
from datetime import datetime
import tempfile

router = APIRouter()

class ReportData(BaseModel):
    patient_info: Optional[Dict[str, str]] = None
    analysis_results: Dict[str, Any]
    summary: Optional[Dict[str, str]] = None
    entities: Optional[List[Dict[str, Any]]] = None
    icd_codes: Optional[List[Dict[str, str]]] = None
    blood_tests: Optional[List[Dict[str, Any]]] = None

def create_pdf_report(data: ReportData, output_path: str):
    """
    Create a PDF report using ReportLab.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = styles["Heading1"]
    heading_style = styles["Heading2"]
    normal_style = styles["Normal"]
    
    # Create custom style for tables
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    
    # Build content
    content = []
    
    # Title
    content.append(Paragraph("Medical Analysis Report", title_style))
    content.append(Spacer(1, 12))
    
    # Date
    content.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    content.append(Spacer(1, 12))
    
    # Patient Info
    if data.patient_info:
        content.append(Paragraph("Patient Information", heading_style))
        content.append(Spacer(1, 12))
        patient_data = [[k, v] for k, v in data.patient_info.items()]
        patient_table = Table(patient_data)
        patient_table.setStyle(table_style)
        content.append(patient_table)
        content.append(Spacer(1, 12))
    
    # Analysis Summary
    if data.summary:
        content.append(Paragraph("Analysis Summary", heading_style))
        content.append(Spacer(1, 12))
        for key, value in data.summary.items():
            content.append(Paragraph(f"<b>{key}:</b> {value}", normal_style))
            content.append(Spacer(1, 6))
    
    # Entities
    if data.entities:
        content.append(Paragraph("Medical Entities", heading_style))
        content.append(Spacer(1, 12))
        entity_data = [["Text", "Type", "Confidence"]]
        entity_data.extend([[e["text"], e["type"], f"{e['confidence']:.2%}"] for e in data.entities])
        entity_table = Table(entity_data)
        entity_table.setStyle(table_style)
        content.append(entity_table)
        content.append(Spacer(1, 12))
    
    # ICD Codes
    if data.icd_codes:
        content.append(Paragraph("ICD-10 Codes", heading_style))
        content.append(Spacer(1, 12))
        icd_data = [["Code", "Description"]]
        icd_data.extend([[c["code"], c["description"]] for c in data.icd_codes])
        icd_table = Table(icd_data)
        icd_table.setStyle(table_style)
        content.append(icd_table)
        content.append(Spacer(1, 12))
    
    # Blood Tests
    if data.blood_tests:
        content.append(Paragraph("Blood Test Results", heading_style))
        content.append(Spacer(1, 12))
        test_data = [["Test", "Value", "Unit", "Status", "Normal Range"]]
        test_data.extend([
            [t["test_name"], str(t["value"]), t["unit"], t["status"], t["normal_range"]]
            for t in data.blood_tests
        ])
        test_table = Table(test_data)
        test_table.setStyle(table_style)
        content.append(test_table)
    
    # Build PDF
    doc.build(content)

@router.post("/generate", response_model=Dict[str, Any])
async def generate_report(data: ReportData):
    """
    Generate a PDF report from analysis results.
    """
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            output_path = tmp_file.name
        
        # Generate PDF
        create_pdf_report(data, output_path)
        
        # Return file download response
        return FileResponse(
            path=output_path,
            filename="medical_analysis_report.pdf",
            media_type="application/pdf",
            background=None  # Run in main thread to ensure file exists
        )
    except Exception as e:
        # Clean up temporary file if it exists
        if "output_path" in locals():
            try:
                os.unlink(output_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}") 
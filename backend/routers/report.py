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
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    try:
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
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        
        # Build content
        content = []
        
        # Title
        content.append(Paragraph("Blood Test Analysis Report", title_style))
        content.append(Spacer(1, 20))
        
        # Date
        content.append(Paragraph(f'<b>Generated on:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', normal_style))
        content.append(Spacer(1, 20))
        
        # Patient Info (if available)
        if data.patient_info:
            content.append(Paragraph("Patient Information", heading_style))
            content.append(Spacer(1, 12))
            patient_data = [["Field", "Value"]]
            patient_data.extend([[k, v] for k, v in data.patient_info.items()])
            patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
            patient_table.setStyle(table_style)
            content.append(patient_table)
            content.append(Spacer(1, 20))
        
        # Analysis Summary
        if data.summary:
            content.append(Paragraph("Analysis Summary", heading_style))
            content.append(Spacer(1, 12))
            summary_data = [["Metric", "Value"]]
            summary_data.extend([[k, v] for k, v in data.summary.items()])
            summary_table = Table(summary_data, colWidths=[2.5*inch, 3.5*inch])
            summary_table.setStyle(table_style)
            content.append(summary_table)
            content.append(Spacer(1, 20))
        
        # Blood Tests - Main section
        if data.blood_tests and len(data.blood_tests) > 0:
            content.append(Paragraph("Blood Test Results", heading_style))
            content.append(Spacer(1, 12))
            
            # Create table data
            test_data = [["Test Name", "Value", "Unit", "Status", "Normal Range"]]
            
            for test in data.blood_tests:
                test_name = str(test.get("test_name", test.get("testName", "Unknown")))
                value = str(test.get("value", "N/A"))
                unit = str(test.get("unit", ""))
                status = str(test.get("status", "Unknown")).upper()
                normal_range = str(test.get("normal_range", test.get("normalRange", "N/A")))
                
                test_data.append([test_name, value, unit, status, normal_range])
            
            # Create table with proper column widths
            test_table = Table(test_data, colWidths=[2*inch, 1*inch, 0.8*inch, 1*inch, 1.5*inch])
            test_table.setStyle(table_style)
            content.append(test_table)
            content.append(Spacer(1, 20))
        
        # Add medications if available
        analysis = data.analysis_results
        if analysis and analysis.get("prescribed_medication"):
            content.append(Paragraph("Prescribed Medications", heading_style))
            content.append(Spacer(1, 12))
            for i, med in enumerate(analysis["prescribed_medication"], 1):
                content.append(Paragraph(f'{i}. {med}', normal_style))
                content.append(Spacer(1, 6))
            content.append(Spacer(1, 20))
        
        # ICD Codes
        if data.icd_codes:
            content.append(Paragraph("ICD-10 Diagnostic Codes", heading_style))
            content.append(Spacer(1, 12))
            icd_data = [["Code", "Description"]]
            icd_data.extend([[c.get("code", ""), c.get("description", "")] for c in data.icd_codes])
            icd_table = Table(icd_data, colWidths=[1.5*inch, 4.5*inch])
            icd_table.setStyle(table_style)
            content.append(icd_table)
            content.append(Spacer(1, 20))
        
        # Medical Entities
        if data.entities:
            content.append(Paragraph("Medical Entities Identified", heading_style))
            content.append(Spacer(1, 12))
            entity_data = [["Text", "Type", "Confidence"]]
            entity_data.extend([
                [e.get("text", ""), e.get("type", ""), f'{e.get("confidence", 0):.1%}'] 
                for e in data.entities
            ])
            entity_table = Table(entity_data, colWidths=[2.5*inch, 2*inch, 1.5*inch])
            entity_table.setStyle(table_style)
            content.append(entity_table)
            content.append(Spacer(1, 20))
        
        # Add interpretation and recommendations from analysis results
        analysis = data.analysis_results
        if analysis:
            # Primary diagnosis
            if analysis.get("primary_diagnosis"):
                content.append(Paragraph("Primary Diagnosis", heading_style))
                content.append(Spacer(1, 12))
                content.append(Paragraph(analysis["primary_diagnosis"], normal_style))
                content.append(Spacer(1, 20))
            
            # Follow-up instructions
            if analysis.get("followup_instructions"):
                content.append(Paragraph("Follow-up Instructions", heading_style))
                content.append(Spacer(1, 12))
                content.append(Paragraph(analysis["followup_instructions"], normal_style))
                content.append(Spacer(1, 20))
            
            # Legacy format support
            if analysis.get("interpretation"):
                content.append(Paragraph("Clinical Interpretation", heading_style))
                content.append(Spacer(1, 12))
                content.append(Paragraph(analysis["interpretation"], normal_style))
                content.append(Spacer(1, 20))
            
            if analysis.get("recommendations"):
                content.append(Paragraph("Recommendations", heading_style))
                content.append(Spacer(1, 12))
                for i, rec in enumerate(analysis["recommendations"], 1):
                    content.append(Paragraph(f'{i}. {rec}', normal_style))
                    content.append(Spacer(1, 6))
                content.append(Spacer(1, 20))
        
        # Footer
        content.append(Spacer(1, 30))
        content.append(Paragraph('<i>This report is generated for informational purposes only. Please consult with a healthcare professional for medical advice.</i>', normal_style))
        
        # Build PDF
        doc.build(content)
        logger.info(f"PDF report created successfully at: {output_path}")
        
    except Exception as e:
        logger.error(f"Error creating PDF: {str(e)}")
        raise

@router.post("/generate")
async def generate_report(data: ReportData):
    """
    Generate a PDF report from analysis results.
    """
    try:
        logger.info("Starting PDF report generation")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            output_path = tmp_file.name
        
        logger.info(f"Temporary file created: {output_path}")
        
        # Generate PDF
        create_pdf_report(data, output_path)
        
        # Verify file exists and has content
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="PDF file was not created")
        
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            raise HTTPException(status_code=500, detail="PDF file is empty")
        
        logger.info(f"PDF file created successfully, size: {file_size} bytes")
        
        # Return file download response
        return FileResponse(
            path=output_path,
            filename=f"Blood_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=blood_report.pdf"}
        )
        
    except Exception as e:
        logger.error(f"Error in generate_report: {str(e)}")
        # Clean up temporary file if it exists
        if "output_path" in locals():
            try:
                os.unlink(output_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")

# Optional: Add a simple GET endpoint for testing
@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify the router is working"""
    return {"message": "Reports API is working", "timestamp": datetime.now().isoformat()}
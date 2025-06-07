import pdfplumber
import re
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import io
import tabula
from pathlib import Path
import pytesseract
from pdf2image import convert_from_path
import numpy as np
import cv2
from dataclasses import dataclass
from enum import Enum

class ProcessingError(Exception):
    """Custom exception for PDF processing errors with detailed information."""
    def __init__(self, message: str, error_type: str, details: Dict[str, Any]):
        self.message = message
        self.error_type = error_type
        self.details = details
        super().__init__(self.message)

class PDFType(Enum):
    DIGITAL = "digital"
    SCANNED = "scanned"
    UNKNOWN = "unknown"

@dataclass
class ExtractionResult:
    """Structured result from extraction attempts."""
    success: bool
    tests: List[Dict[str, Any]]
    method_used: str
    error_type: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

class BloodTestExtractor:
    """Extract blood test results from PDF medical reports with enhanced error handling and OCR support."""
    
    def __init__(self):
        # Common blood test patterns and their variations
        self.test_patterns = {
            "hemoglobin": r"(?i)(hemoglobin|hgb|hb)\s*:?\s*([\d.]+)\s*(g/dL|g/L|g%)",
            "wbc": r"(?i)(white\s*blood\s*cells?|wbc|leukocytes?)\s*:?\s*([\d,.]+)\s*(K/µL|×10³/μL|10\^3/µL)",
            "platelets": r"(?i)(platelets?|plt)\s*:?\s*([\d,.]+)\s*(K/µL|×10³/μL|10\^3/µL)",
            "glucose_fasting": r"(?i)(fasting\s*glucose|blood\s*sugar|fbs)\s*:?\s*([\d.]+)\s*(mg/dL|mmol/L)",
            "cholesterol_total": r"(?i)(total\s*cholesterol)\s*:?\s*([\d.]+)\s*(mg/dL|mmol/L)",
            "rbc": r"(?i)(red\s*blood\s*cells?|rbc|erythrocytes?)\s*:?\s*([\d.]+)\s*(M/µL|×10⁶/μL)",
            "hematocrit": r"(?i)(hematocrit|hct|pcv)\s*:?\s*([\d.]+)\s*(%)",
            "mcv": r"(?i)(mean\s*corpuscular\s*volume|mcv)\s*:?\s*([\d.]+)\s*(fL)",
            "mch": r"(?i)(mean\s*corpuscular\s*hemoglobin|mch)\s*:?\s*([\d.]+)\s*(pg)",
            "mchc": r"(?i)(mchc)\s*:?\s*([\d.]+)\s*(g/dL|%)",
        }
        
        # Common table headers for recognition
        self.table_headers = [
            "test", "parameter", "analyte", "investigation",
            "result", "value", "reading",
            "unit", "units", "reference", "range", "normal"
        ]
        
        # Unit conversions if needed
        self.unit_conversions = {
            "g/L": ("g/dL", lambda x: x / 10),  # Convert g/L to g/dL
            "mmol/L": ("mg/dL", lambda x: x * 18.018),  # Glucose conversion
        }

    def detect_pdf_type(self, pdf_path: str) -> PDFType:
        """Determine if PDF is digital or scanned."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                first_page = pdf.pages[0]
                text = first_page.extract_text()
                
                # If we get substantial text, it's likely digital
                if text and len(text.strip()) > 100:
                    return PDFType.DIGITAL
                
                # Check for text in different areas of the page
                height = first_page.height
                width = first_page.width
                
                # Try extracting text from different regions
                regions = [
                    (0, 0, width/2, height/2),
                    (width/2, 0, width, height/2),
                    (0, height/2, width/2, height),
                    (width/2, height/2, width, height)
                ]
                
                for region in regions:
                    crop = first_page.crop(region)
                    if crop.extract_text().strip():
                        return PDFType.DIGITAL
                
                return PDFType.SCANNED
        except Exception:
            return PDFType.UNKNOWN

    def extract_from_pdf(self, pdf_path: str) -> ExtractionResult:
        """
        Extract blood test results from a PDF file using multiple methods.
        Returns structured results with extraction details.
        """
        pdf_type = self.detect_pdf_type(pdf_path)
        
        # Try different extraction methods in order
        methods = [
            (self._extract_from_tables, "table_extraction"),
            (self._extract_from_text, "text_extraction")
        ]
        
        if pdf_type == PDFType.SCANNED:
            methods.append((self._extract_with_ocr, "ocr_extraction"))
        
        all_errors = {}
        for extract_method, method_name in methods:
            try:
                results = extract_method(pdf_path)
                if results:
                    normalized_results = self._normalize_results(results)
                    if normalized_results:
                        return ExtractionResult(
                            success=True,
                            tests=normalized_results,
                            method_used=method_name
                        )
            except Exception as e:
                all_errors[method_name] = str(e)
        
        # If we get here, all methods failed
        raise ProcessingError(
            message="Could not extract valid blood test results",
            error_type="extraction_failed",
            details={
                "pdf_type": pdf_type.value,
                "attempted_methods": list(all_errors.keys()),
                "method_errors": all_errors
            }
        )

    def _extract_from_tables(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract blood test results from tables in the PDF."""
        try:
            tables = tabula.read_pdf(
                pdf_path,
                pages='all',
                multiple_tables=True,
                guess=True,
                lattice=True,
                stream=True
            )
            
            if not tables:
                raise ValueError("No tables found in PDF")
            
            results = []
            for table in tables:
                if table.empty:
                    continue
                
                # Try to identify column names
                test_col = None
                value_col = None
                unit_col = None
                
                for col in table.columns:
                    col_lower = str(col).lower()
                    if any(term in col_lower for term in self.table_headers[:4]):
                        test_col = col
                    elif any(term in col_lower for term in self.table_headers[4:7]):
                        value_col = col
                    elif any(term in col_lower for term in self.table_headers[7:]):
                        unit_col = col
                
                if not (test_col and value_col):
                    continue
                
                # Process each row
                for _, row in table.iterrows():
                    test_name = str(row[test_col])
                    value = row[value_col]
                    unit = row[unit_col] if unit_col else None
                    
                    # Clean and validate the data
                    if pd.isna(value) or not test_name:
                        continue
                    
                    try:
                        value = float(str(value).replace(',', ''))
                    except ValueError:
                        continue
                    
                    results.append({
                        'test_name': test_name.strip(),
                        'value': value,
                        'unit': str(unit).strip() if unit else None
                    })
            
            return results
            
        except Exception as e:
            raise ProcessingError(
                message="Table extraction failed",
                error_type="table_extraction_error",
                details={"error": str(e)}
            )

    def _extract_from_text(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract blood test results from text content using regex patterns."""
        results = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
                
                if not text.strip():
                    raise ValueError("No text content found in PDF")
                
                # Search for each test pattern
                for test_name, pattern in self.test_patterns.items():
                    matches = re.finditer(pattern, text)
                    for match in matches:
                        try:
                            value = float(match.group(2).replace(',', ''))
                            unit = match.group(3)
                            
                            results.append({
                                'test_name': test_name,
                                'value': value,
                                'unit': unit
                            })
                        except (ValueError, IndexError):
                            continue
        
        except Exception as e:
            raise ProcessingError(
                message="Text extraction failed",
                error_type="text_extraction_error",
                details={"error": str(e)}
            )
        
        return results

    def _extract_with_ocr(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract blood test results using OCR for scanned PDFs."""
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path)
            
            text = ""
            for image in images:
                # Convert PIL image to OpenCV format
                img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # Preprocess image
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                
                # Perform OCR
                text += pytesseract.image_to_string(thresh) + "\n"
            
            if not text.strip():
                raise ValueError("OCR could not extract any text")
            
            results = []
            # Search for each test pattern
            for test_name, pattern in self.test_patterns.items():
                matches = re.finditer(pattern, text)
                for match in matches:
                    try:
                        value = float(match.group(2).replace(',', ''))
                        unit = match.group(3)
                        
                        results.append({
                            'test_name': test_name,
                            'value': value,
                            'unit': unit
                        })
                    except (ValueError, IndexError):
                        continue
            
            return results
            
        except Exception as e:
            raise ProcessingError(
                message="OCR extraction failed",
                error_type="ocr_error",
                details={"error": str(e)}
            )

    def _normalize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize test results by converting units and standardizing names."""
        if not results:
            return []
            
        normalized = []
        
        for result in results:
            test_name = result['test_name']
            value = result['value']
            unit = result['unit']
            
            # Convert units if needed
            if unit in self.unit_conversions:
                target_unit, converter = self.unit_conversions[unit]
                value = converter(value)
                unit = target_unit
            
            # Standardize test name
            test_name = test_name.lower()
            test_name = re.sub(r'[^a-z0-9]', '_', test_name)
            test_name = re.sub(r'_+', '_', test_name)
            test_name = test_name.strip('_')
            
            normalized.append({
                'testName': test_name,
                'value': round(value, 2),
                'unit': unit
            })
        
        return normalized

def process_blood_report(file_path: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Process a blood report PDF and extract test results.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Tuple containing:
        - List of dictionaries containing test results
        - Dictionary containing processing metadata and diagnostics
    """
    extractor = BloodTestExtractor()
    try:
        result = extractor.extract_from_pdf(file_path)
        metadata = {
            "success": True,
            "pdf_type": extractor.detect_pdf_type(file_path).value,
            "extraction_method": result.method_used,
            "test_count": len(result.tests)
        }
        return result.tests, metadata
    except ProcessingError as e:
        raise ProcessingError(
            message=e.message,
            error_type=e.error_type,
            details={
                "pdf_type": extractor.detect_pdf_type(file_path).value,
                **e.details
            }
        ) 
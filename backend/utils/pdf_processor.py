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
from thefuzz import fuzz
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProcessingError(Exception):
    """Custom exception for PDF processing errors with detailed information."""
    def __init__(self, message: str, error_type: str, details: Dict[str, Any]):
        self.message = message
        self.error_type = error_type
        self.details = details
        super().__init__(self.message)

class PDFType(str, Enum):
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
            "hemoglobin": {
                "names": ["hemoglobin", "hgb", "hb", "haemoglobin"],
                "pattern": r"(?i)(hemoglobin|hgb|hb|haemoglobin)\s*[:=-]?\s*([\d.]+)\s*(g/dL|g/L|g%)"
            },
            "wbc": {
                "names": ["white blood cells", "wbc", "leukocytes", "white cell count"],
                "pattern": r"(?i)(white\s*blood\s*cells?|wbc|leukocytes?|white\s*cell\s*count)\s*[:=-]?\s*([\d,.]+)\s*(K/µL|×10³/μL|10\^3/µL)"
            },
            "platelets": {
                "names": ["platelets", "plt", "thrombocytes"],
                "pattern": r"(?i)(platelets?|plt|thrombocytes?)\s*[:=-]?\s*([\d,.]+)\s*(K/µL|×10³/μL|10\^3/µL)"
            },
            "glucose_fasting": {
                "names": ["fasting glucose", "blood sugar", "fbs", "glucose"],
                "pattern": r"(?i)(fasting\s*glucose|blood\s*sugar|fbs|glucose)\s*[:=-]?\s*([\d.]+)\s*(mg/dL|mmol/L)"
            },
            "cholesterol_total": {
                "names": ["total cholesterol", "cholesterol", "tc"],
                "pattern": r"(?i)(total\s*cholesterol|cholesterol|tc)\s*[:=-]?\s*([\d.]+)\s*(mg/dL|mmol/L)"
            },
            "rbc": {
                "names": ["red blood cells", "rbc", "erythrocytes"],
                "pattern": r"(?i)(red\s*blood\s*cells?|rbc|erythrocytes?)\s*[:=-]?\s*([\d.]+)\s*(M/µL|×10⁶/μL)"
            },
            "hematocrit": {
                "names": ["hematocrit", "hct", "pcv"],
                "pattern": r"(?i)(hematocrit|hct|pcv)\s*[:=-]?\s*([\d.]+)\s*(%)"
            }
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

    def _fuzzy_match_test_name(self, test_str: str, min_score: int = 80) -> Optional[str]:
        """
        Find the best matching standardized test name using fuzzy string matching.
        Returns None if no good match is found.
        """
        test_str = test_str.lower().strip()
        best_match = None
        best_score = 0

        for std_name, variations in self.test_patterns.items():
            for name in variations["names"]:
                score = fuzz.ratio(test_str, name)
                if score > best_score and score >= min_score:
                    best_score = score
                    best_match = std_name

        return best_match

    def _extract_from_text_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Extract test result from a single line of text using flexible pattern matching.
        """
        # Try exact pattern matching first
        for test_name, test_info in self.test_patterns.items():
            match = re.search(test_info["pattern"], line)
            if match:
                try:
                    value = float(match.group(2).replace(',', ''))
                    unit = match.group(3)
                    return {
                        'test_name': test_name,
                        'value': value,
                        'unit': unit
                    }
                except (ValueError, IndexError):
                    continue

        # Try more flexible pattern matching
        # Look for number + unit combinations
        value_unit_pattern = r"([\d,.]+)\s*(g/dL|mg/dL|K/µL|%|fL|pg)"
        number_matches = re.finditer(value_unit_pattern, line)
        
        for match in number_matches:
            try:
                value = float(match.group(1).replace(',', ''))
                unit = match.group(2)
                
                # Look for test name before the value
                text_before = line[:match.start()].strip()
                if text_before:
                    test_name = self._fuzzy_match_test_name(text_before)
                    if test_name:
                        return {
                            'test_name': test_name,
                            'value': value,
                            'unit': unit
                        }
            except (ValueError, IndexError):
                continue

        return None

    def _extract_from_text(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract blood test results from text content using enhanced pattern matching."""
        results = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
                
                if not text.strip():
                    raise ValueError("No text content found in PDF")
                
                logger.debug("Extracted text content:\n%s", text)
                
                # Process text line by line
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    result = self._extract_from_text_line(line)
                    if result:
                        results.append(result)
        
        except Exception as e:
            raise ProcessingError(
                message="Text extraction failed",
                error_type="text_extraction_error",
                details={"error": str(e)}
            )
        
        return results

    def _extract_from_tables(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract blood test results from tables with improved header detection."""
        results = []
        
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
            
            for table in tables:
                if table.empty:
                    continue
                
                # Try to identify column names using fuzzy matching
                test_col = None
                value_col = None
                unit_col = None
                
                for col in table.columns:
                    col_lower = str(col).lower()
                    # Use fuzzy matching for column identification
                    for header in self.table_headers[:4]:
                        if fuzz.partial_ratio(col_lower, header) > 80:
                            test_col = col
                            break
                    for header in self.table_headers[4:7]:
                        if fuzz.partial_ratio(col_lower, header) > 80:
                            value_col = col
                            break
                    for header in self.table_headers[7:]:
                        if fuzz.partial_ratio(col_lower, header) > 80:
                            unit_col = col
                            break
                
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
                    
                    # Use fuzzy matching to standardize test name
                    std_test_name = self._fuzzy_match_test_name(test_name)
                    if std_test_name:
                        results.append({
                            'test_name': std_test_name,
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

    def _extract_with_ocr(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract blood test results using OCR with improved image preprocessing."""
        try:
            # Convert PDF to images
            images = convert_from_path(pdf_path)
            
            text = ""
            for image in images:
                # Convert PIL image to OpenCV format
                img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # Enhanced image preprocessing
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                
                # Adaptive thresholding for better text extraction
                thresh = cv2.adaptiveThreshold(
                    gray, 255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY,
                    11, 2
                )
                
                # Noise reduction
                kernel = np.ones((1, 1), np.uint8)
                thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
                
                # Improve OCR accuracy with custom configuration
                custom_config = r'--oem 3 --psm 6'
                text += pytesseract.image_to_string(thresh, config=custom_config) + "\n"
            
            if not text.strip():
                raise ValueError("OCR could not extract any text")
            
            logger.debug("OCR extracted text:\n%s", text)
            
            results = []
            # Process text line by line
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                result = self._extract_from_text_line(line)
                if result:
                    results.append(result)
            
            return results
            
        except Exception as e:
            raise ProcessingError(
                message="OCR extraction failed",
                error_type="ocr_error",
                details={"error": str(e)}
            )

    def _normalize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize test results with improved unit conversion and deduplication."""
        if not results:
            return []
            
        normalized = []
        seen_tests = set()
        
        for result in results:
            test_name = result['test_name']
            value = result['value']
            unit = result['unit']
            
            # Skip if we've already seen this test (keep first occurrence)
            if test_name in seen_tests:
                continue
            
            # Convert units if needed
            if unit in self.unit_conversions:
                target_unit, converter = self.unit_conversions[unit]
                value = converter(value)
                unit = target_unit
            
            # Add to normalized results
            normalized.append({
                'testName': test_name,
                'value': round(value, 2),
                'unit': unit
            })
            seen_tests.add(test_name)
        
        return normalized

def process_blood_report(file_path: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Process a blood report PDF and extract test results with enhanced error handling.
    
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
from fastapi import APIRouter, UploadFile, HTTPException
import pdfplumber
import tempfile
import os
from io import BytesIO
from typing import Dict, Any, Optional
import logging
from pdf2image import convert_from_path
import pytesseract
import cv2
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

def extract_text_with_pdfplumber(pdf_path: str) -> str:
    """Extract text from PDF using pdfplumber."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
                logger.info(f"Extracted {len(extracted.strip()) if extracted else 0} characters from page")
    except Exception as e:
        logger.error(f"Error in pdfplumber extraction: {str(e)}")
        raise
    return text

def extract_text_with_ocr(pdf_path: str) -> str:
    """Extract text from PDF using OCR as fallback."""
    text = ""
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path)
        logger.info(f"Converting PDF to {len(images)} images for OCR")
        
        for i, image in enumerate(images):
            # Convert PIL image to OpenCV format
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Preprocess image for better OCR
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            
            # Perform OCR
            page_text = pytesseract.image_to_string(thresh)
            text += page_text + "\n"
            logger.info(f"OCR extracted {len(page_text.strip())} characters from page {i+1}")
            
    except Exception as e:
        logger.error(f"Error in OCR extraction: {str(e)}")
        raise
    return text

@router.post("/upload", response_model=Dict[str, Any])
async def upload_pdf(file: UploadFile) -> Dict[str, Any]:
    """
    Upload and process a PDF file to extract text content.
    Falls back to OCR if initial text extraction fails.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
            
            try:
                # First attempt: Extract with pdfplumber
                logger.info("Attempting text extraction with pdfplumber")
                text = extract_text_with_pdfplumber(tmp_path)
                method = "pdfplumber"
                
                # If no text found, try OCR
                if not text.strip():
                    logger.info("No text found with pdfplumber, falling back to OCR")
                    text = extract_text_with_ocr(tmp_path)
                    method = "ocr"
                
                if not text.strip():
                    raise HTTPException(
                        status_code=422,
                        detail="No text could be extracted from the PDF using either method"
                    )
                
                # Count pages
                with pdfplumber.open(tmp_path) as pdf:
                    page_count = len(pdf.pages)
                
                return {
                    "success": True,
                    "text": text,
                    "filename": file.filename,
                    "page_count": page_count,
                    "extraction_method": method,
                    "text_length": len(text)
                }
                
            except Exception as e:
                logger.error(f"Error processing PDF: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing PDF: {str(e)}"
                )
            
    except Exception as e:
        logger.error(f"Error handling upload: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error handling upload: {str(e)}"
        )
        
    finally:
        # Clean up temporary file
        if 'tmp_path' in locals():
            os.unlink(tmp_path) 
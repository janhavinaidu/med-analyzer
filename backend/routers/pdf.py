from fastapi import APIRouter, UploadFile, HTTPException
from PyPDF2 import PdfReader
from io import BytesIO
from typing import Dict, Any

router = APIRouter()

@router.post("/upload", response_model=Dict[str, Any])
async def upload_pdf(file: UploadFile):
    """
    Upload and process a PDF file to extract text content.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        # Read the uploaded file
        contents = await file.read()
        pdf_file = BytesIO(contents)
        
        # Extract text using PyPDF2
        pdf_reader = PdfReader(pdf_file)
        text = ""
        
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        if not text.strip():
            raise HTTPException(status_code=422, detail="No text could be extracted from the PDF")
        
        return {
            "success": True,
            "text": text,
            "filename": file.filename,
            "page_count": len(pdf_reader.pages)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    finally:
        await file.close() 
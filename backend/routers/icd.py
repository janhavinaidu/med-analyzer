# routers/icd.py
from fastapi import APIRouter, HTTPException
from typing import List, Dict
from pydantic import BaseModel
from utils.icd_extractor import icd_extractor

router = APIRouter()

class TextAnalysisRequest(BaseModel):
    text: str

@router.post("/analyze")
async def analyze_text_for_icd_codes(request: TextAnalysisRequest) -> Dict:
    """
    Analyze medical text and return relevant ICD codes
    """
    try:
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        results = icd_extractor.identify_icd_codes_from_text(request.text)
        return {
            "success": True,
            "icd_codes": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing text: {str(e)}")

@router.get("/search")
async def search_icd_codes(query: str) -> List[dict]:
    """
    Search ICD-10 codes by code or description
    """
    try:
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        results = icd_extractor.search_codes_by_description(query, limit=10)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching ICD codes: {str(e)}")

@router.get("/code/{icd_code}")
async def get_icd_code(icd_code: str) -> dict:
    """
    Get specific ICD-10 code details
    """
    try:
        icd_code = icd_code.upper()
        
        # Search for the specific code
        for code in icd_extractor.icd_codes:
            if code["code"] == icd_code:
                return {
                    "success": True,
                    "code": code
                }
        
        raise HTTPException(status_code=404, detail="ICD code not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving ICD code: {str(e)}")

# Legacy function for backward compatibility
def identify_icd_codes_from_text(text: str) -> List[Dict[str, str]]:
    """
    Legacy function to maintain compatibility with existing imports
    """
    return icd_extractor.identify_icd_codes_from_text(text)
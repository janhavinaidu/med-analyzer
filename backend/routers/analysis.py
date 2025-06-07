from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import json
from rapidfuzz import fuzz, process

router = APIRouter()

# Load ICD-10 codes from JSON file
with open("data/icd10_codes.json", "r") as f:
    ICD10_CODES = json.load(f)

# Load Hugging Face biomedical NER model
try:
    tokenizer = AutoTokenizer.from_pretrained("d4data/biomedical-ner-all")
    model = AutoModelForTokenClassification.from_pretrained("d4data/biomedical-ner-all")
    ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")
except Exception as e:
    raise RuntimeError(f"Failed to load biomedical NER model: {str(e)}")

class TextInput(BaseModel):
    text: str = Field(..., description="The medical text to analyze")

    class Config:
        schema_extra = {
            "example": {
                "text": "Patient has hypertension and is taking Lisinopril 10mg daily."
            }
        }

class Entity(BaseModel):
    text: str
    type: str
    confidence: float

class IcdCode(BaseModel):
    code: str
    description: str

class AnalysisResponse(BaseModel):
    success: bool
    entities: List[Entity]
    icd_codes: List[IcdCode]
    originalText: str
    error: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "entities": [
                    {"text": "hypertension", "type": "DISEASE", "confidence": 0.95},
                    {"text": "Lisinopril", "type": "MEDICATION", "confidence": 0.98}
                ],
                "icd_codes": [
                    {"code": "I10", "description": "Essential (primary) hypertension"}
                ],
                "originalText": "Patient has hypertension and is taking Lisinopril 10mg daily.",
                "error": None
            }
        }

class BloodTestInput(BaseModel):
    test_name: str
    value: float
    unit: str

def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Extract biomedical entities using Hugging Face transformer.
    """
    try:
        results = ner_pipeline(text)
        entities = []
        for ent in results:
            entities.append({
                "text": ent["word"],
                "type": ent["entity_group"],
                "confidence": round(ent["score"], 3)
            })
        return entities
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting entities: {str(e)}"
        )

def predict_icd_codes(text: str) -> List[Dict[str, str]]:
    """
    Predict ICD-10 codes using fuzzy matching.
    """
    try:
        medical_terms = [ent["word"] for ent in ner_pipeline(text)]
        
        predicted_codes = []
        for term in medical_terms:
            matches = process.extract(
                term,
                [(code, desc) for code, desc in ICD10_CODES.items()],
                limit=1,
                scorer=fuzz.token_set_ratio
            )
            
            if matches and matches[0][1] > 80:
                code, desc = matches[0][0]
                predicted_codes.append({
                    "code": code,
                    "description": desc
                })
        
        return predicted_codes
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error predicting ICD codes: {str(e)}"
        )

def analyze_blood_test(test: BloodTestInput) -> Dict[str, Any]:
    NORMAL_RANGES = {
        "glucose": {"min": 70, "max": 100, "unit": "mg/dL"},
        "hemoglobin": {"min": 13.5, "max": 17.5, "unit": "g/dL"},
        "wbc": {"min": 4.5, "max": 11.0, "unit": "K/µL"},
    }

    test_key = test.test_name.lower()
    if test_key in NORMAL_RANGES:
        range_data = NORMAL_RANGES[test_key]
        if range_data["unit"] != test.unit:
            raise HTTPException(status_code=400, detail=f"Invalid unit. Expected {range_data['unit']}")

        status = "normal"
        if test.value < range_data["min"]:
            status = "low"
        elif test.value > range_data["max"]:
            status = "high"

        return {
            "test_name": test.test_name,
            "value": test.value,
            "unit": test.unit,
            "status": status,
            "normal_range": f"{range_data['min']} - {range_data['max']} {range_data['unit']}"
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unknown test: {test.test_name}")

@router.post("/entities", response_model=Dict[str, Any])
async def get_entities(input_data: TextInput):
    try:
        entities = extract_entities(input_data.text)
        return {
            "success": True,
            "entities": entities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting entities: {str(e)}")

@router.post("/icd-codes", response_model=Dict[str, Any])
async def get_icd_codes(input_data: TextInput):
    try:
        codes = predict_icd_codes(input_data.text)
        return {
            "success": True,
            "icd_codes": codes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predicting ICD codes: {str(e)}")

@router.post("/blood-test", response_model=Dict[str, Any])
async def analyze_blood_test_values(test: BloodTestInput):
    try:
        result = analyze_blood_test(test)
        return {
            "success": True,
            "analysis": result
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing blood test: {str(e)}")

@router.post("/full", response_model=AnalysisResponse)
async def full_analysis(input_data: TextInput):
    """
    Perform full analysis on medical text.
    
    Args:
        input_data (TextInput): The input text to analyze
        
    Returns:
        AnalysisResponse: The analysis results including entities and ICD codes
        
    Raises:
        HTTPException: If text is empty or processing fails
    """
    try:
        # Validate input
        if not input_data.text.strip():
            raise HTTPException(
                status_code=400,
                detail="Text input cannot be empty"
            )

        # Extract entities and predict ICD codes
        entities = extract_entities(input_data.text)
        icd_codes = predict_icd_codes(input_data.text)

        return AnalysisResponse(
            success=True,
            entities=entities,
            icd_codes=icd_codes,
            originalText=input_data.text
        )

    except HTTPException as he:
        # Re-raise HTTP exceptions as is
        raise he
    except Exception as e:
        # Log the error (you should add proper logging)
        print(f"Error in full_analysis: {str(e)}")
        
        # Return a structured error response
        return AnalysisResponse(
            success=False,
            entities=[],
            icd_codes=[],
            originalText=input_data.text,
            error=f"Error performing analysis: {str(e)}"
        )

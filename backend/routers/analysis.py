from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import json
from rapidfuzz import fuzz, process
from utils.section_extractor import SectionExtractor
from utils.type_converter import convert_numpy_types
from fastapi.responses import JSONResponse

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

class StructuredAnalysisResponse(BaseModel):
    success: bool
    primary_diagnosis: str
    prescribed_medication: List[str]
    followup_instructions: str
    medical_entities: List[Entity]
    icd_codes: List[IcdCode]
    error: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "primary_diagnosis": "Diagnosed with acute pharyngitis.",
                "prescribed_medication": [
                    "Amoxicillin 500mg twice daily",
                    "Ibuprofen 200mg as needed"
                ],
                "followup_instructions": "Return in 1 week if symptoms persist.",
                "medical_entities": [
                    {"text": "pharyngitis", "type": "DISEASE", "confidence": 0.92},
                    {"text": "Amoxicillin", "type": "MEDICATION", "confidence": 0.95}
                ],
                "icd_codes": [
                    {"code": "J02.9", "description": "Acute pharyngitis, unspecified"}
                ],
                "error": None
            }
        }

def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Extract biomedical entities using Hugging Face transformer.
    Returns confidence scores as native Python floats.
    """
    try:
        results = ner_pipeline(text)
        entities = []
        for ent in results:
            # Convert NumPy float32/float64 to native Python float
            confidence = float(ent["score"])
            entities.append({
                "text": str(ent["word"]),  # Ensure string type
                "type": str(ent["entity_group"]),  # Ensure string type
                "confidence": round(confidence, 3)  # Native Python float
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
    Returns all strings as native Python strings.
    """
    try:
        medical_terms = [str(ent["word"]) for ent in ner_pipeline(text)]  # Ensure string type
        
        predicted_codes = []
        for term in medical_terms:
            matches = process.extract(
                term,
                [(str(code), str(desc)) for code, desc in ICD10_CODES.items()],  # Ensure string type
                limit=1,
                scorer=fuzz.token_set_ratio
            )
            
            if matches and matches[0][1] > 80:  # matches[0][1] is already a native Python int
                code, desc = matches[0][0]
                predicted_codes.append({
                    "code": str(code),  # Ensure string type
                    "description": str(desc)  # Ensure string type
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

@router.post("/structured-analysis")
async def structured_analysis(input_data: TextInput):
    """
    Perform structured analysis on medical text, extracting sections, entities, and ICD codes.
    Returns all numeric values as native Python types.
    
    Args:
        input_data (TextInput): The input text to analyze
        
    Returns:
        JSONResponse containing:
        - primary_diagnosis (List[str]): List of diagnoses
        - prescribed_medication (List[str]): List of medications
        - followup_instructions (List[str]): List of follow-up instructions
        - medical_entities (List[Entity]): List of extracted medical entities with native Python confidence scores
        - icd_codes (List[IcdCode]): List of relevant ICD codes
        
    Raises:
        HTTPException: If text is empty or processing fails
    """
    try:
        # Validate input
        if not input_data.text.strip():
            raise HTTPException(
                status_code=400,
                detail="Input text cannot be empty"
            )

        # Extract structured sections
        section_extractor = SectionExtractor()
        sections = section_extractor.extract_sections(input_data.text)
        
        # Extract entities and ICD codes
        entities = extract_entities(input_data.text)
        icd_codes = predict_icd_codes(input_data.text)
        
        # Prepare response data
        response_data = {
            "success": True,
            "primary_diagnosis": sections["primary_diagnosis"],
            "prescribed_medication": sections["prescribed_medication"],
            "followup_instructions": sections["followup_instructions"],
            "medical_entities": entities,
            "icd_codes": icd_codes,
            "error": None
        }
        
        # Convert any NumPy types to native Python types
        response_data = convert_numpy_types(response_data)
        
        # Return as JSONResponse to ensure proper serialization
        return JSONResponse(content=response_data)
        
    except Exception as e:
        error_response = {
            "success": False,
            "error": f"Error performing structured analysis: {str(e)}",
            "primary_diagnosis": [],
            "prescribed_medication": [],
            "followup_instructions": [],
            "medical_entities": [],
            "icd_codes": []
        }
        return JSONResponse(
            status_code=500,
            content=error_response
        )

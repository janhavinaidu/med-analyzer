# routers/analysis.py
from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Set
import json
import logging
from fastapi.responses import JSONResponse
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the enhanced ICD extractor
from utils.icd_extractor import icd_extractor

# For NER (if you want to keep the biomedical NER)
try:
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
    tokenizer = AutoTokenizer.from_pretrained("d4data/biomedical-ner-all")
    model = AutoModelForTokenClassification.from_pretrained("d4data/biomedical-ner-all")
    ner_pipeline = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="simple")
    NER_AVAILABLE = True
except Exception as e:
    logger.error(f"Biomedical NER model not available: {str(e)}")
    NER_AVAILABLE = False

# For PDF text extraction
try:
    import PyPDF2
    import io
    PDF_EXTRACTION_AVAILABLE = True
except ImportError:
    print("PyPDF2 not available. PDF extraction will not work.")
    PDF_EXTRACTION_AVAILABLE = False

router = APIRouter()

# Pydantic models
class TextInput(BaseModel):
    text: str = Field(..., description="The medical text to analyze")

    class Config:
        schema_extra = {
            "example": {
                "text": "Patient diagnosed with type 2 diabetes and hypertension. Prescribed metformin and lisinopril."
            }
        }

class Entity(BaseModel):
    text: str
    type: str
    confidence: float

class IcdCode(BaseModel):
    code: str
    description: str
    confidence: Optional[float] = None

class AnalysisResponse(BaseModel):
    success: bool
    entities: List[Entity]
    icd_codes: List[IcdCode]
    originalText: str
    error: Optional[str] = None

class PrescriptionAnalysisResponse(BaseModel):
    success: bool
    extracted_text: str
    detected_conditions: List[str]
    icd_codes: List[IcdCode]
    medications: List[str]
    recommendations: List[str]
    error: Optional[str] = None

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF content"""
    if not PDF_EXTRACTION_AVAILABLE:
        raise HTTPException(status_code=500, detail="PDF extraction not available")
    
    try:
        pdf_file = io.BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        extracted_text = ""
        for page in pdf_reader.pages:
            extracted_text += page.extract_text() + "\n"
        
        return extracted_text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error extracting text from PDF: {str(e)}")

def clean_entity_text(text: str) -> str:
    """Clean and normalize entity text."""
    # Remove unwanted characters and normalize whitespace
    text = re.sub(r'[,.;:!?"\']', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def is_valid_medical_term(text: str) -> bool:
    """Check if the text appears to be a valid medical term."""
    # Common medical word endings
    medical_suffixes = {
        'itis', 'emia', 'osis', 'pathy', 'algia', 'ectomy', 'plasty',
        'otomy', 'ology', 'gram', 'graph', 'scopy', 'tomy', 'opsy'
    }
    
    # Common medical prefixes
    medical_prefixes = {
        'hyper', 'hypo', 'anti', 'poly', 'hemi', 'neo', 'post',
        'pre', 'peri', 'endo', 'exo', 'meta', 'para', 'dys'
    }
    
    text_lower = text.lower()
    
    # Check for medical suffixes and prefixes
    if any(text_lower.endswith(suffix) for suffix in medical_suffixes):
        return True
    if any(text_lower.startswith(prefix) for prefix in medical_prefixes):
        return True
        
    return False

def categorize_entity(text: str, original_type: str) -> str:
    """Categorize the entity into a more specific medical category."""
    text_lower = text.lower()
    
    # Define category patterns
    patterns = {
        'DISEASE': [
            r'disease', r'syndrome', r'disorder', r'infection', r'itis',
            r'emia', r'osis', r'pathy', r'cancer', r'tumor', r'carcinoma',
            r'failure', r'deficiency'
        ],
        'MEDICATION': [
            r'tablet', r'capsule', r'injection', r'pill', r'medication',
            r'drug', r'antibiotic', r'dose', r'supplement', r'medicine'
        ],
        'SYMPTOM': [
            r'pain', r'ache', r'discomfort', r'swelling', r'inflammation',
            r'fever', r'nausea', r'vomiting', r'dizziness', r'fatigue'
        ],
        'PROCEDURE': [
            r'surgery', r'operation', r'procedure', r'scan', r'test',
            r'examination', r'screening', r'therapy', r'treatment'
        ],
        'ANATOMY': [
            r'artery', r'vein', r'nerve', r'muscle', r'bone', r'organ',
            r'tissue', r'cell', r'blood', r'brain', r'heart', r'lung'
        ],
        'VITAL_SIGN': [
            r'pressure', r'rate', r'temperature', r'pulse', r'oxygen',
            r'saturation', r'glucose', r'bpm', r'mmhg'
        ],
        'LAB_TEST': [
            r'level', r'count', r'test', r'measurement', r'analysis',
            r'profile', r'panel', r'screening', r'culture', r'biopsy'
        ]
    }
    
    # Try to categorize based on patterns
    for category, pattern_list in patterns.items():
        if any(re.search(pattern, text_lower) for pattern in pattern_list):
            return category
            
    # If no specific category found, try to use the original type if it's medical
    if original_type in patterns.keys():
        return original_type
        
    # Default to MEDICAL_TERM if no specific category found
    return 'MEDICAL_TERM'

def extract_entities_with_ner(text: str) -> List[Dict[str, Any]]:
    """Extract biomedical entities using NER if available"""
    if not NER_AVAILABLE:
        return []
    
    try:
        results = ner_pipeline(text)
        entities = []
        seen_entities: Set[str] = set()
        
        # Minimum confidence threshold
        MIN_CONFIDENCE = 0.4
        
        # Words to filter out
        filter_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
            'patient', 'doctor', 'hospital', 'clinic', 'day', 'days',
            'week', 'weeks', 'month', 'months', 'year', 'years'
        }
        
        for ent in results:
            confidence = float(ent["score"])
            if confidence < MIN_CONFIDENCE:
                continue
                
            # Clean and normalize the entity text
            entity_text = clean_entity_text(str(ent["word"]))
            
            # Skip if too short or in filter words
            if len(entity_text) < 3 or entity_text.lower() in filter_words:
                continue
                
            # Skip if it's just numbers
            if re.match(r'^\d+$', entity_text):
                continue
                
            # Skip if we've seen this entity before (case-insensitive)
            if entity_text.lower() in seen_entities:
                continue
                
            # Additional validation for medical terms
            if not is_valid_medical_term(entity_text) and len(entity_text.split()) == 1:
                continue
                
            # Categorize the entity
            entity_type = categorize_entity(entity_text, str(ent["entity_group"]))
            
            # Add to results
            seen_entities.add(entity_text.lower())
            entities.append({
                "text": entity_text,
                "type": entity_type,
                "confidence": round(confidence, 3)
            })
        
        # Sort by confidence score (highest first)
        entities.sort(key=lambda x: x["confidence"], reverse=True)
        
        return entities
    except Exception as e:
        logger.error(f"Error extracting entities: {str(e)}")
        return []

def extract_medications_from_text(text: str) -> List[str]:
    """Extract medication names from text using pattern matching"""
    import re
    
    # Common medication patterns
    medication_patterns = [
        r'prescribed\s+([a-zA-Z]+(?:\s+\d+\s*mg)?)',
        r'taking\s+([a-zA-Z]+(?:\s+\d+\s*mg)?)',
        r'medication:\s*([a-zA-Z]+(?:\s+\d+\s*mg)?)',
        r'drug:\s*([a-zA-Z]+(?:\s+\d+\s*mg)?)',
        r'([a-zA-Z]+)\s+\d+\s*mg',
        r'([a-zA-Z]+)\s+tablets?',
    ]
    
    medications = set()
    text_lower = text.lower()
    
    for pattern in medication_patterns:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            med_name = match.group(1).strip()
            if len(med_name) > 2:  # Filter out very short matches
                medications.add(med_name.title())
    
    return list(medications)

def generate_recommendations(icd_codes: List[Dict], medications: List[str]) -> List[str]:
    """Generate basic recommendations based on detected conditions"""
    recommendations = []
    
    # Extract condition types from ICD codes
    condition_types = []
    for code_info in icd_codes:
        description = code_info["description"].lower()
        if "diabetes" in description:
            condition_types.append("diabetes")
        elif "hypertension" in description:
            condition_types.append("hypertension")
        elif "heart" in description or "cardiac" in description:
            condition_types.append("cardiac")
        elif "asthma" in description or "respiratory" in description:
            condition_types.append("respiratory")
    
    # Generate recommendations based on conditions
    if "diabetes" in condition_types:
        recommendations.extend([
            "Monitor blood glucose levels regularly",
            "Follow diabetic diet recommendations",
            "Regular exercise as advised by physician"
        ])
    
    if "hypertension" in condition_types:
        recommendations.extend([
            "Monitor blood pressure regularly",
            "Limit sodium intake",
            "Maintain healthy weight"
        ])
    
    if "cardiac" in condition_types:
        recommendations.extend([
            "Regular cardiac follow-up appointments",
            "Avoid excessive physical exertion",
            "Take medications as prescribed"
        ])
    
    if medications:
        recommendations.append("Take all prescribed medications as directed")
        recommendations.append("Do not stop medications without consulting physician")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_recommendations = []
    for rec in recommendations:
        if rec not in seen:
            seen.add(rec)
            unique_recommendations.append(rec)
    
    return unique_recommendations

@router.post("/entities", response_model=Dict[str, Any])
async def get_entities(input_data: TextInput):
    """Extract medical entities from text"""
    try:
        entities = extract_entities_with_ner(input_data.text)
        return {
            "success": True,
            "entities": entities
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting entities: {str(e)}")

@router.post("/icd-codes", response_model=Dict[str, Any])
async def get_icd_codes(input_data: TextInput):
    """Extract ICD codes from medical text"""
    try:
        codes = icd_extractor.identify_icd_codes_from_text(input_data.text)
        return {
            "success": True,
            "icd_codes": codes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predicting ICD codes: {str(e)}")

@router.post("/full", response_model=AnalysisResponse)
async def full_analysis(input_data: TextInput):
    """Perform comprehensive analysis on medical text"""
    try:
        if not input_data.text.strip():
            raise HTTPException(status_code=400, detail="Text input cannot be empty")

        # Extract entities using NER
        entities = extract_entities_with_ner(input_data.text)
        
        # Extract ICD codes using enhanced system
        icd_codes = icd_extractor.identify_icd_codes_from_text(input_data.text)

        return AnalysisResponse(
            success=True,
            entities=entities,
            icd_codes=icd_codes,
            originalText=input_data.text
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in full_analysis: {str(e)}")
        return AnalysisResponse(
            success=False,
            entities=[],
            icd_codes=[],
            originalText=input_data.text,
            error=f"Error performing analysis: {str(e)}"
        )

@router.post("/prescription-text", response_model=PrescriptionAnalysisResponse)
async def analyze_prescription_text(input_data: TextInput):
    """Analyze prescription text for conditions, medications, and ICD codes"""
    try:
        text = input_data.text.strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text input cannot be empty")

        # Extract ICD codes and conditions
        icd_codes = icd_extractor.identify_icd_codes_from_text(text)
        
        # Extract detected conditions (readable format)
        detected_conditions = []
        for code_info in icd_codes:
            detected_conditions.append(code_info["description"])
        
        # Extract medications
        medications = extract_medications_from_text(text)
        
        # Generate recommendations
        recommendations = generate_recommendations(icd_codes, medications)

        return PrescriptionAnalysisResponse(
            success=True,
            extracted_text=text,
            detected_conditions=detected_conditions,
            icd_codes=icd_codes,
            medications=medications,
            recommendations=recommendations
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in prescription text analysis: {str(e)}")
        return PrescriptionAnalysisResponse(
            success=False,
            extracted_text=input_data.text,
            detected_conditions=[],
            icd_codes=[],
            medications=[],
            recommendations=[],
            error=f"Error analyzing prescription: {str(e)}"
        )

@router.post("/prescription-pdf", response_model=PrescriptionAnalysisResponse)
async def analyze_prescription_pdf(file: UploadFile = File(...)):
    """Analyze prescription PDF for conditions, medications, and ICD codes"""
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file content
        file_content = await file.read()
        
        # Extract text from PDF
        extracted_text = extract_text_from_pdf(file_content)
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the PDF")

        # Analyze the extracted text
        icd_codes = icd_extractor.identify_icd_codes_from_text(extracted_text)
        
        # Extract detected conditions
        detected_conditions = []
        for code_info in icd_codes:
            detected_conditions.append(code_info["description"])
        
        # Extract medications
        medications = extract_medications_from_text(extracted_text)
        
        # Generate recommendations
        recommendations = generate_recommendations(icd_codes, medications)

        return PrescriptionAnalysisResponse(
            success=True,
            extracted_text=extracted_text,
            detected_conditions=detected_conditions,
            icd_codes=icd_codes,
            medications=medications,
            recommendations=recommendations
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in prescription PDF analysis: {str(e)}")
        return PrescriptionAnalysisResponse(
            success=False,
            extracted_text="",
            detected_conditions=[],
            icd_codes=[],
            medications=[],
            recommendations=[],
            error=f"Error analyzing prescription PDF: {str(e)}"
        )

@router.get("/search-icd")
async def search_icd_codes(query: str, limit: int = 10):
    """Search ICD codes by description or code"""
    try:
        results = icd_extractor.search_codes_by_description(query, limit)
        return {
            "success": True,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching ICD codes: {str(e)}")

@router.get("/test-icd-extraction")
async def test_icd_extraction():
    """Test endpoint to verify ICD extraction is working"""
    test_text = "Patient diagnosed with type 2 diabetes and hypertension. Also has history of asthma."
    
    try:
        results = icd_extractor.identify_icd_codes_from_text(test_text)
        return {
            "success": True,
            "test_text": test_text,
            "extracted_codes": results,
            "icd_codes_loaded": len(icd_extractor.icd_codes),
            "condition_mappings": len(icd_extractor.condition_mappings)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "icd_codes_loaded": len(icd_extractor.icd_codes),
            "condition_mappings": len(icd_extractor.condition_mappings)
        }
# routers/analysis.py
from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Set, Tuple
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
    # Remove ## artifacts
    text = re.sub(r'##(\w+)', r'\1', text)
    
    # Fix hyphenation
    text = re.sub(r'(\w+)\s*-\s*(\w+)', r'\1 \2', text)
    
    # Normalize spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove leading articles
    text = re.sub(r'^(?:the|a|an)\s+', '', text, flags=re.IGNORECASE)
    
    return text

def is_valid_medical_term(text: str) -> bool:
    """Check if the text appears to be a valid medical term."""
    # Common medical word endings
    medical_suffixes = {
        # Conditions and diseases
        'itis', 'emia', 'osis', 'pathy', 'algia', 'ectomy', 'plasty',
        'otomy', 'ology', 'gram', 'graph', 'scopy', 'tomy', 'opsy',
        'oma', 'ase', 'ism', 'sia', 'trophy', 'plasia', 'rrhagia',
        'rrhea', 'phobia', 'esthesia', 'plegia', 'paresis', 'spasm',
        
        # Lab tests and measurements
        'crit', 'stat', 'assay', 'level', 'count', 'ratio', 'index',
        
        # Treatments and procedures
        'therapy', 'tomy', 'ectomy', 'ostomy', 'plasty', 'pexy',
        'centesis', 'scopy', 'gram', 'graphy'
    }
    
    # Common medical prefixes
    medical_prefixes = {
        # Anatomical
        'cardio', 'neuro', 'gastro', 'hepato', 'nephro', 'dermato',
        'osteo', 'arthro', 'myelo', 'cerebro', 'broncho', 'pneumo',
        
        # Descriptive
        'hyper', 'hypo', 'anti', 'poly', 'hemi', 'neo', 'post',
        'pre', 'peri', 'endo', 'exo', 'meta', 'para', 'dys',
        'brady', 'tachy', 'mal', 'macro', 'micro', 'iso', 'hetero',
        
        # Common medical
        'hemo', 'immuno', 'onco', 'cyto', 'bio', 'patho'
    }
    
    # Common medical terms (for exact matches or contains)
    medical_terms = {
        # Common conditions
        'diabetes', 'hypertension', 'asthma', 'arthritis', 'cancer',
        'infection', 'disease', 'syndrome', 'disorder', 'deficiency',
        
        # Vital signs and measurements
        'pressure', 'rate', 'pulse', 'temperature', 'saturation',
        'glucose', 'cholesterol', 'count', 'level', 'index',
        
        # Anatomy
        'blood', 'heart', 'liver', 'kidney', 'lung', 'brain',
        'muscle', 'bone', 'joint', 'artery', 'vein', 'nerve',
        
        # Common symptoms
        'pain', 'swelling', 'inflammation', 'fever', 'fatigue',
        'nausea', 'vomiting', 'dizziness', 'weakness', 'numbness'
    }
    
    text_lower = text.lower()
    
    # Check for exact matches in medical terms
    if text_lower in medical_terms:
        return True
    
    # Check for medical terms contained in the text
    if any(term in text_lower for term in medical_terms):
        return True
    
    # Check for medical suffixes and prefixes
    if any(text_lower.endswith(suffix) for suffix in medical_suffixes):
        return True
    if any(text_lower.startswith(prefix) for prefix in medical_prefixes):
        return True
        
    # Check for specific patterns
    patterns = [
        r'\b[A-Z][a-z]+(?:[-\s][A-Z][a-z]+)*\s+(?:disease|syndrome|disorder|deficiency)',  # Named conditions
        r'\b(?:Type|Grade|Stage|Phase|Class)\s+[1-4I-IV]+\b',  # Classifications
        r'\b[A-Z]{2,}\d*\b',  # Medical abbreviations (e.g., HIV, COPD)
        r'\b\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|mmol|units)/?\w*\b'  # Measurements
    ]
    
    if any(re.search(pattern, text) for pattern in patterns):
        return True
        
    return False

def categorize_entity(text: str, original_type: str) -> str:
    """Categorize the entity into a more specific medical category."""
    text_lower = text.lower()
    
    # Define category patterns with more specific subcategories
    patterns = {
        'DISEASE': {
            'patterns': [
                r'disease', r'syndrome', r'disorder', r'infection', r'itis',
                r'emia', r'osis', r'pathy', r'failure', r'deficiency'
            ],
            'subcategories': {
                'CANCER': [r'cancer', r'tumor', r'carcinoma', r'sarcoma', r'lymphoma', r'leukemia'],
                'CHRONIC_DISEASE': [r'diabetes', r'hypertension', r'arthritis', r'asthma', r'copd'],
                'INFECTION': [r'infection', r'itis$', r'viral', r'bacterial', r'fungal'],
                'AUTOIMMUNE': [r'lupus', r'arthritis', r'sclerosis', r'psoriasis']
            }
        },
        'MEDICATION': {
            'patterns': [
                r'tablet', r'capsule', r'injection', r'pill', r'medication',
                r'drug', r'antibiotic', r'dose', r'supplement', r'medicine'
            ],
            'subcategories': {
                'ANTIBIOTIC': [r'cillin$', r'mycin$', r'antibiotic'],
                'ANALGESIC': [r'pain', r'relief', r'aspirin', r'ibuprofen', r'acetaminophen'],
                'CARDIOVASCULAR': [r'olol$', r'pril$', r'sartan$', r'statin$'],
                'PSYCHIATRIC': [r'antidepress', r'anxiety', r'psychiatric']
            }
        },
        'LAB_TEST': {
            'patterns': [
                r'test', r'level', r'count', r'measurement', r'analysis',
                r'profile', r'panel', r'screening', r'culture', r'biopsy'
            ],
            'subcategories': {
                'BLOOD_TEST': [r'blood', r'cbc', r'hemoglobin', r'wbc', r'rbc'],
                'IMAGING': [r'xray', r'mri', r'ct', r'ultrasound', r'scan'],
                'PATHOLOGY': [r'biopsy', r'culture', r'cytology', r'histology'],
                'DIAGNOSTIC': [r'diagnostic', r'screening', r'assessment']
            }
        },
        'VITAL_SIGN': {
            'patterns': [
                r'pressure', r'rate', r'temperature', r'pulse', r'oxygen',
                r'saturation', r'glucose', r'bpm', r'mmhg'
            ],
            'subcategories': {
                'BLOOD_PRESSURE': [r'pressure', r'systolic', r'diastolic', r'mmhg'],
                'HEART_RATE': [r'pulse', r'rate', r'bpm', r'rhythm'],
                'TEMPERATURE': [r'temp', r'fever', r'celsius', r'fahrenheit'],
                'RESPIRATORY': [r'breathing', r'respiratory', r'oxygen', r'saturation']
            }
        },
        'SYMPTOM': {
            'patterns': [
                r'pain', r'ache', r'discomfort', r'swelling', r'inflammation',
                r'fever', r'nausea', r'vomiting', r'dizziness', r'fatigue'
            ],
            'subcategories': {
                'PAIN': [r'pain', r'ache', r'discomfort', r'soreness'],
                'NEUROLOGICAL': [r'dizz', r'headache', r'numbness', r'tingling'],
                'GASTROINTESTINAL': [r'nausea', r'vomit', r'diarrhea', r'constipation'],
                'RESPIRATORY': [r'cough', r'breath', r'wheez', r'dyspnea']
            }
        }
    }
    
    # First try to find a main category
    main_category = 'MEDICAL_TERM'
    subcategory = None
    
    for category, data in patterns.items():
        # Check main category patterns
        if any(re.search(pattern, text_lower) for pattern in data['patterns']):
            main_category = category
            # Check subcategories
            for sub, sub_patterns in data['subcategories'].items():
                if any(re.search(pattern, text_lower) for pattern in sub_patterns):
                    subcategory = sub
                    break
            break
    
    # Return the most specific category available
    return subcategory if subcategory else main_category

def extract_entities_with_ner(text: str) -> List[Dict[str, Any]]:
    """Extract biomedical entities using NER with enhanced clinical categorization"""
    if not NER_AVAILABLE:
        return []
    
    try:
        # Pre-process text
        text = clean_text_for_processing(text)
        logger.info(f"Cleaned text: {text}")
        
        # Get base entities
        base_results = ner_pipeline(text)
        logger.info(f"Base NER results: {base_results}")
        
        # Initialize lists for different entity types
        entities = []
        seen_entities: Set[str] = set()
        
        # Define medical patterns
        medical_patterns = {
            'DISEASE': [
                r'(?:chronic|acute)\s+\w+(?:\s+disease)?',
                r'type\s+[12]\s+diabetes(?:\s+mellitus)?',
                r'\w+(?:itis|osis|emia|opathy)\b',
                r'(?:heart|kidney|liver|lung)\s+(?:disease|failure)',
                r'(?:hypertension|diabetes|asthma|copd|cancer)\b'
            ],
            'MEDICATION': [
                r'\w+(?:cin|zole|olol|ide|ate|ine|one|il|in)\b',
                r'(?:insulin|aspirin|warfarin|heparin)\b',
                r'\d+\s*(?:mg|mcg|g)\s+\w+',
                r'(?:tablet|capsule|injection)\s+of\s+\w+'
            ],
            'SYMPTOM': [
                r'(?:fever|cough|pain|fatigue|nausea|vomiting)',
                r'shortness\s+of\s+breath',
                r'(?:chest|abdominal)\s+pain',
                r'(?:headache|dizziness|weakness)'
            ],
            'TEST_PROCEDURE': [
                r'(?:blood|urine)\s+test',
                r'(?:mri|ct|pet)\s+scan',
                r'(?:x-ray|xray|ultrasound)',
                r'(?:ecg|ekg|echocardiogram)'
            ],
            'BODY_PART': [
                r'(?:heart|lung|liver|kidney|brain)',
                r'(?:chest|abdomen|head|neck)',
                r'(?:left|right)\s+\w+',
                r'(?:upper|lower)\s+\w+'
            ],
            'DOSAGE': [
                r'\d+(?:\.\d+)?\s*(?:mg|g|ml|mcg|units?)',
                r'(?:once|twice|thrice)\s+(?:daily|a\s+day)',
                r'\d+\s+times?\s+(?:per|a)\s+day'
            ],
            'TEMPORAL': [
                r'\d+\s+(?:day|week|month|year)s?\s+(?:ago|before|after)',
                r'(?:every|each)\s+(?:day|morning|evening)',
                r'(?:daily|weekly|monthly)'
            ]
        }
        
        # First pass: Extract entities from NER
        for ent in base_results:
            entity_text = clean_entity_text(str(ent["word"]))
            if not is_valid_entity(entity_text):
                continue
            
            # Get context
            context_start = max(0, text.lower().find(entity_text.lower()) - 50)
            context_end = min(len(text), text.lower().find(entity_text.lower()) + len(entity_text) + 50)
            context = text[context_start:context_end].lower()
            
            # Try to classify the entity
            entity_type = 'UNKNOWN'
            confidence = float(ent["score"])
            
            # Check against patterns
            for category, patterns in medical_patterns.items():
                if any(re.search(pattern, entity_text.lower()) for pattern in patterns):
                    entity_type = category
                    confidence += 0.3
                    break
            
            if entity_type != 'UNKNOWN' and confidence >= 0.4:
                entity_key = f"{entity_text.lower()}_{entity_type}"
                if entity_key not in seen_entities:
                    entities.append({
                        "text": entity_text,
                        "type": entity_type,
                        "confidence": round(confidence, 3)
                    })
                    seen_entities.add(entity_key)
        
        # Second pass: Pattern-based extraction
        for match in re.finditer(r'\b\w+(?:\s+\w+){0,4}\b', text):
            phrase = match.group(0)
            if not is_valid_entity(phrase):
                continue
            
            for category, patterns in medical_patterns.items():
                if any(re.search(pattern, phrase.lower()) for pattern in patterns):
                    entity_key = f"{phrase.lower()}_{category}"
                    if entity_key not in seen_entities:
                        entities.append({
                            "text": phrase,
                            "type": category,
                            "confidence": 0.7
                        })
                        seen_entities.add(entity_key)
                        break
        
        # Post-process entities
        processed = []
        seen = set()
        
        for entity in sorted(entities, key=lambda x: (-x['confidence'], -len(x['text']))):
            text = entity['text'].lower()
            if not any(text in seen_text for seen_text in seen if text != seen_text):
                processed.append(entity)
                seen.add(text)
        
        logger.info(f"Extracted entities: {processed}")
        return processed
        
    except Exception as e:
        logger.error(f"Error in entity extraction: {str(e)}")
        return []

def classify_clinical_entity(text: str, context: str, base_confidence: float, categories: Dict) -> Tuple[str, float]:
    """Classify entity into clinical categories with confidence score."""
    entity_type = 'UNKNOWN'
    max_confidence = base_confidence
    
    text_lower = text.lower()
    context_lower = context.lower()
    
    for category, rules in categories.items():
        confidence = base_confidence
        
        # Check patterns
        if any(re.search(pattern, text_lower) for pattern in rules['patterns']):
            confidence += 0.3
            
        # Check keywords
        if any(keyword in text_lower for keyword in rules['keywords']):
            confidence += 0.2
            
        # Check context keywords
        if any(keyword in context_lower for keyword in rules['keywords']):
            confidence += 0.1
            
        # Special rules for each category
        if category == 'DISEASE':
            if rules.get('min_word_length') and len(text) >= rules['min_word_length']:
                confidence += 0.1
                
        elif category == 'MEDICATION':
            if not any(word in text_lower for word in rules.get('exclude_words', set())):
                confidence += 0.1
                
        elif category == 'BODY_PART':
            if rules.get('require_context') and not any(keyword in context_lower for keyword in rules['keywords']):
                confidence -= 0.2
                
        elif category == 'DOSAGE':
            if rules.get('require_number') and not re.search(r'\d+', text):
                confidence -= 0.3
                
        if confidence > max_confidence:
            max_confidence = confidence
            entity_type = category
            
    return entity_type, max_confidence

def validate_clinical_entity(text: str, entity_type: str, categories: Dict) -> bool:
    """Validate clinical entity based on its type."""
    if entity_type not in categories:
        return False
        
    category = categories[entity_type]
    text_lower = text.lower()
    
    # General validation
    if len(text.split()) == 1 and len(text) < 3:
        return False
        
    # Category-specific validation
    if entity_type == 'DISEASE':
        if len(text) < category.get('min_word_length', 0):
            return False
            
    elif entity_type == 'MEDICATION':
        if text_lower in category.get('exclude_words', set()):
            return False
            
    elif entity_type == 'DOSAGE':
        if category.get('require_number') and not re.search(r'\d+', text):
            return False
            
    elif entity_type == 'TEMPORAL':
        if not any(re.search(pattern, text_lower) for pattern in category['patterns']):
            return False
            
    return True

def post_process_clinical_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Post-process clinical entities for improved accuracy."""
    processed = []
    seen = set()
    
    # Sort by confidence and length
    sorted_entities = sorted(
        entities,
        key=lambda x: (-x['confidence'], -len(x['text']))
    )
    
    for entity in sorted_entities:
        text = entity['text'].lower()
        
        # Skip if this is a substring of an already seen entity
        if any(text in seen_text for seen_text in seen if text != seen_text):
            continue
            
        # Skip single words that are too generic
        if len(text.split()) == 1 and text in {
            'test', 'scan', 'pain', 'dose', 'daily',
            'normal', 'high', 'low', 'mild', 'severe'
        }:
            continue
            
        processed.append(entity)
        seen.add(text)
    
    return processed

def is_valid_entity(text: str) -> bool:
    """Validate if an entity should be included in results."""
    # Skip if too short or too long
    if len(text) < 2 or len(text) > 100:
        return False
    
    # Skip common irrelevant terms
    irrelevant_terms = {
        'the', 'and', 'was', 'were', 'had', 'has', 'have', 'been',
        'patient', 'doctor', 'normal', 'mild', 'moderate', 'severe',
        'none', 'room', 'ward', 'clinic', 'hospital', 'occasional',
        'activity', 'referred', 'elevated', 'slightly', 'raised',
        'high', 'low', 'regular', 'routine', 'bed', 'note', 'report'
    }
    
    if text.lower() in irrelevant_terms:
        return False
    
    # Must contain at least one letter
    if not re.search(r'[a-zA-Z]', text):
        return False
    
    return True

def clean_text_for_processing(text: str) -> str:
    """Clean and normalize text for processing."""
    # Remove ## artifacts
    text = re.sub(r'##(\w+)', r'\1', text)
    
    # Fix hyphenation
    text = re.sub(r'(\w+)\s*-\s*(\w+)', r'\1\2', text)
    
    # Normalize spaces around measurements
    text = re.sub(r'(\d+)\s*(mg|mcg|g|ml|units)', r'\1 \2', text)
    
    # Fix age descriptions
    text = re.sub(r'(\d+)\s*(?:year|yr)s?\s*(?:-|\s+)?\s*old', r'\1 years old', text)
    
    return text

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
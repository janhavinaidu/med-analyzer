from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Set, Optional
from transformers import T5ForConditionalGeneration, T5Tokenizer
import torch
from utils.section_extractor import SectionExtractor
import logging
import json
from fastapi.responses import JSONResponse

# Import the enhanced ICD extractor
from utils.icd_extractor import icd_extractor
from routers.analysis import extract_entities_with_ner  # Import the entity extraction function

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Load T5 model and tokenizer
MODEL_NAME = "t5-base"
try:
    tokenizer = T5Tokenizer.from_pretrained(MODEL_NAME)
    model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME)
except Exception as e:
    raise RuntimeError(f"Error loading T5 model: {str(e)}")

class TextInput(BaseModel):
    text: str = Field(..., description="The medical text to analyze")

class Entity(BaseModel):
    text: str
    type: str
    confidence: float

class IcdCode(BaseModel):
    code: str
    description: str

class MedicalAnalysisResponse(BaseModel):
    success: bool
    primary_diagnosis: str
    prescribed_medication: List[str]
    followup_instructions: str
    medical_entities: List[Entity]
    icd_codes: List[IcdCode]
    error: Optional[str] = None

def clean_and_deduplicate(items: List[str], seen_items: Set[str]) -> List[str]:
    """Clean and deduplicate items while preserving order."""
    cleaned = []
    for item in items:
        item = item.strip()
        item_lower = item.lower()
        if item and item_lower not in seen_items:
            cleaned.append(item)
            seen_items.add(item_lower)
    return cleaned

def generate_section_content(text: str, section_type: str) -> List[str]:
    """
    Generate content for a specific section with targeted prompts.
    
    Args:
        text (str): The input medical text
        section_type (str): The type of section to generate
        
    Returns:
        List[str]: List of relevant bullet points
    """
    prompts = {
        "diagnosis": (
            "Extract only current confirmed medical conditions and diagnoses. "
            "Include only active conditions mentioned in the text. "
            "Format as bullet points. "
            "Exclude symptoms, past conditions, and treatments. "
            "Example format: '- Hypertension', '- Type 2 Diabetes'"
        ),
        "clinical_treatment": (
            "Extract only current treatments, medications, and procedures. "
            "Include only active prescriptions and ongoing treatments. "
            "Format as bullet points. "
            "Exclude past treatments and general advice. "
            "Example format: '- Prescribed metformin 500mg twice daily', '- Scheduled physical therapy sessions'"
        ),
        "medical_history": (
            "Extract only past medical conditions and family history. "
            "Include previous illnesses, surgeries, and relevant family conditions. "
            "Format as bullet points. "
            "Exclude current conditions and treatments. "
            "Example format: '- Previous heart surgery in 2019', '- Family history of diabetes'"
        )
    }
    
    # Prepare input text with section-specific prompt
    input_text = f"{prompts[section_type]} Text: {text}"
    
    # Tokenize and generate
    inputs = tokenizer(input_text, return_tensors="pt", max_length=512, truncation=True)
    
    with torch.no_grad():
        outputs = model.generate(
            inputs.input_ids,
            max_length=200,
            num_beams=4,
            length_penalty=2.0,
            early_stopping=True,
            no_repeat_ngram_size=2  # Prevent repetition of phrases
        )
    
    # Decode and split into bullet points
    summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract bullet points and clean
    bullets = []
    for line in summary.split('\n'):
        line = line.strip()
        if line.startswith('- '):
            line = line[2:].strip()
        if line and len(line) > 5:  # Ensure meaningful content
            bullets.append(line)
    
    return bullets

@router.post("/structured-analysis", response_model=MedicalAnalysisResponse)
async def get_structured_analysis(input_data: TextInput):
    """
    Generate structured analysis with distinct sections for diagnosis,
    clinical treatment, and medical history.
    """
    try:
        if not input_data.text.strip():
            logger.warning("Empty text input received")
            return MedicalAnalysisResponse(
                success=False,
                primary_diagnosis="",
                prescribed_medication=[],
                followup_instructions="",
                medical_entities=[],
                icd_codes=[],
                error="Input text cannot be empty"
            )

        logger.info("Starting structured analysis")
        logger.debug("Input text: %s", input_data.text[:200])  # Log first 200 chars

        # Initialize section extractor
        section_extractor = SectionExtractor()
        
        # Extract sections
        sections = section_extractor.extract_sections(input_data.text)
        
        # Keep track of seen items to avoid duplicates across sections
        seen_items: Set[str] = set()
        
        # Clean and deduplicate each section
        diagnosis = clean_and_deduplicate(sections.get("diagnosis", []), seen_items)
        treatments = clean_and_deduplicate(sections.get("clinical_treatment", []), seen_items)
        history = clean_and_deduplicate(sections.get("medical_history", []), seen_items)

        logger.info("Initial extraction results:")
        logger.info("- Diagnoses: %s", diagnosis)
        logger.info("- Treatments: %s", treatments)
        logger.info("- History: %s", history)

        # If sections are empty, try using T5 model
        if not any([diagnosis, treatments, history]):
            logger.info("No sections found, trying T5 model")
            try:
                diagnosis = generate_section_content(input_data.text, "diagnosis")
                treatments = generate_section_content(input_data.text, "clinical_treatment")
                history = generate_section_content(input_data.text, "medical_history")
                
                logger.info("T5 generation results:")
                logger.info("- Diagnoses: %s", diagnosis)
                logger.info("- Treatments: %s", treatments)
                logger.info("- History: %s", history)
            except Exception as e:
                logger.error("Error in T5 generation: %s", str(e))

        # Extract medical entities using NER
        medical_entities = extract_entities_with_ner(input_data.text)
        logger.info("Extracted medical entities: %s", medical_entities)

        # Format response
        response = MedicalAnalysisResponse(
            success=True,
            primary_diagnosis=diagnosis[0] if diagnosis else "",
            prescribed_medication=treatments if treatments else [],
            followup_instructions=history[0] if history else "",
            medical_entities=medical_entities,  # Add extracted entities
            icd_codes=[],  # TODO: Add ICD code prediction
            error=None
        )
        
        logger.info("Final response: %s", response.dict())
        return response
        
    except Exception as e:
        logger.error("Error in structured analysis: %s", str(e), exc_info=True)
        return MedicalAnalysisResponse(
            success=False,
            primary_diagnosis="",
            prescribed_medication=[],
            followup_instructions="",
            medical_entities=[],
            icd_codes=[],
            error=str(e)
        )

@router.post("/bullet-points", response_model=Dict[str, Any])
async def get_bullet_points(input_data: TextInput):
    """Generate bullet-point summary from medical text."""
    try:
        bullets = generate_section_content(input_data.text, "diagnosis")  # Use diagnosis prompt as default
        
        return {
            "success": True,
            "bullet_points": bullets,
            "original_text": input_data.text
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating summary: {str(e)}"
        )

@router.post("/discharge", response_model=Dict[str, Any])
async def summarize_discharge(input_data: TextInput):
    """Generate a structured discharge summary."""
    try:
        # Generate content for each section
        diagnosis = generate_section_content(input_data.text, "diagnosis")
        treatment = generate_section_content(input_data.text, "clinical_treatment")
        followup = generate_section_content(input_data.text, "clinical_treatment")  # Use treatment prompt for followup
        
        return {
            "success": True,
            "summary": {
                "diagnosis": diagnosis,
                "treatment": treatment,
                "followUp": followup
            },
            "original_text": input_data.text
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating discharge summary: {str(e)}"
        ) 
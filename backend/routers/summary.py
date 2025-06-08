from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Set
from transformers import T5ForConditionalGeneration, T5Tokenizer
import torch

router = APIRouter()

# Load T5 model and tokenizer
MODEL_NAME = "t5-base"
try:
    tokenizer = T5Tokenizer.from_pretrained(MODEL_NAME)
    model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME)
except Exception as e:
    raise RuntimeError(f"Error loading T5 model: {str(e)}")

class TextInput(BaseModel):
    text: str

class MedicalAnalysisResponse(BaseModel):
    success: bool
    diagnosis: List[str]
    clinical_treatment: List[str]
    medical_history: List[str]

def clean_and_deduplicate(bullets: List[str], seen_items: Set[str]) -> List[str]:
    """
    Clean bullet points and remove duplicates while maintaining order.
    
    Args:
        bullets (List[str]): List of bullet points to clean
        seen_items (Set[str]): Set of already seen items across sections
        
    Returns:
        List[str]: Cleaned and deduplicated bullet points
    """
    cleaned = []
    for bullet in bullets:
        # Clean and normalize the bullet point
        clean_bullet = bullet.strip().lower()
        
        # Skip if too short or already seen
        if len(clean_bullet) < 5 or clean_bullet in seen_items:
            continue
            
        # Add to seen items and keep original case
        seen_items.add(clean_bullet)
        cleaned.append(bullet.strip())
    
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
        # Keep track of seen items to avoid duplicates across sections
        seen_items: Set[str] = set()
        
        # Generate content for each section
        diagnosis = generate_section_content(input_data.text, "diagnosis")
        diagnosis = clean_and_deduplicate(diagnosis, seen_items)
        
        clinical_treatment = generate_section_content(input_data.text, "clinical_treatment")
        clinical_treatment = clean_and_deduplicate(clinical_treatment, seen_items)
        
        medical_history = generate_section_content(input_data.text, "medical_history")
        medical_history = clean_and_deduplicate(medical_history, seen_items)
        
        return MedicalAnalysisResponse(
            success=True,
            diagnosis=diagnosis,
            clinical_treatment=clinical_treatment,
            medical_history=medical_history
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating structured analysis: {str(e)}"
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
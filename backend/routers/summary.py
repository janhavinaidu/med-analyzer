from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
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

def generate_bullet_points(text: str, max_length: int = 150) -> List[str]:
    """
    Generate bullet-point summary using T5.
    """
    # Prepare input text
    input_text = f"summarize to bullets: {text}"
    
    # Tokenize and generate
    inputs = tokenizer(input_text, return_tensors="pt", max_length=512, truncation=True)
    
    with torch.no_grad():
        outputs = model.generate(
            inputs.input_ids,
            max_length=max_length,
            num_beams=4,
            length_penalty=2.0,
            early_stopping=True
        )
    
    summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Split into bullet points
    bullets = [point.strip() for point in summary.split("-") if point.strip()]
    
    # Add bullet points if none were generated
    if not bullets:
        bullets = [summary]
    
    return [f"• {point}" for point in bullets]

@router.post("/bullet-points", response_model=Dict[str, Any])
async def get_bullet_points(input_data: TextInput):
    """
    Generate bullet-point summary from medical text.
    """
    try:
        bullets = generate_bullet_points(input_data.text)
        
        return {
            "success": True,
            "bullet_points": bullets,
            "original_text": input_data.text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

@router.post("/discharge", response_model=Dict[str, Any])
async def summarize_discharge(input_data: TextInput):
    """
    Generate a structured discharge summary.
    """
    try:
        # Generate summaries for different sections
        diagnosis_text = f"summarize diagnosis from: {input_data.text}"
        treatment_text = f"summarize treatment from: {input_data.text}"
        followup_text = f"summarize follow-up instructions from: {input_data.text}"
        
        with torch.no_grad():
            # Generate diagnosis summary
            diagnosis_inputs = tokenizer(diagnosis_text, return_tensors="pt", max_length=512, truncation=True)
            diagnosis_outputs = model.generate(diagnosis_inputs.input_ids, max_length=100)
            diagnosis = tokenizer.decode(diagnosis_outputs[0], skip_special_tokens=True)
            
            # Generate treatment summary
            treatment_inputs = tokenizer(treatment_text, return_tensors="pt", max_length=512, truncation=True)
            treatment_outputs = model.generate(treatment_inputs.input_ids, max_length=100)
            treatment = tokenizer.decode(treatment_outputs[0], skip_special_tokens=True)
            
            # Generate follow-up summary
            followup_inputs = tokenizer(followup_text, return_tensors="pt", max_length=512, truncation=True)
            followup_outputs = model.generate(followup_inputs.input_ids, max_length=100)
            followup = tokenizer.decode(followup_outputs[0], skip_special_tokens=True)
        
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
        raise HTTPException(status_code=500, detail=f"Error generating discharge summary: {str(e)}") 
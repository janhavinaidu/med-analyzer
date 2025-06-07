from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import openai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

router = APIRouter()

class TextInput(BaseModel):
    text: str

@router.post("/correct", response_model=Dict[str, Any])
async def correct_text(input_data: TextInput):
    """
    Use OpenAI to correct and refine manually entered medical text.
    """
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a medical text correction assistant. Your task is to correct and refine medical text while preserving all medical information. Maintain medical terminology and correct any spelling or grammatical errors."},
                {"role": "user", "content": input_data.text}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        corrected_text = response.choices[0].message.content
        
        return {
            "success": True,
            "original_text": input_data.text,
            "corrected_text": corrected_text
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error correcting text: {str(e)}")

@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_text(input_data: TextInput):
    """
    Analyze medical text and return structured information.
    """
    try:
        # This endpoint will be implemented in the analysis router
        # Here we just validate the input
        if not input_data.text.strip():
            raise HTTPException(status_code=400, detail="Text input is required")
            
        return {
            "success": True,
            "text": input_data.text,
            "message": "Text received for analysis"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing text: {str(e)}") 
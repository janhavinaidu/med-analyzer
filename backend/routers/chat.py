from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import re
from datetime import datetime

router = APIRouter()

class Message(BaseModel):
    text: str
    context: Optional[Dict[str, Any]] = None

class ChatHistory(BaseModel):
    messages: List[Dict[str, Any]]
    context: Optional[Dict[str, Any]] = None

def get_response_by_pattern(question: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Get chatbot response based on pattern matching and context.
    """
    # Convert question to lowercase for matching
    question_lower = question.lower()
    
    # Patterns for different types of questions
    patterns = {
        r"what (does|is|are) (the )?icd.*code": (
            lambda: "The ICD codes represent standardized medical diagnosis codes. "
            "In your analysis, each code corresponds to a specific medical condition. "
            "For example, I10 represents Essential Hypertension."
        ),
        r"what (does|is|are) (the )?normal range": (
            lambda: "Normal ranges vary by test. For example:\n"
            "- Glucose: 70-100 mg/dL\n"
            "- Hemoglobin: 13.5-17.5 g/dL\n"
            "- White Blood Cells: 4.5-11.0 K/µL"
        ),
        r"what (does|is|are) (the )?confidence score": (
            lambda: "Confidence scores indicate how certain the AI is about its predictions. "
            "Scores above 0.9 (90%) indicate high confidence, while lower scores suggest "
            "the prediction may need human verification."
        ),
        r"how (can|do) i interpret": (
            lambda: "To interpret your results:\n"
            "1. Check the identified medical entities\n"
            "2. Review the ICD codes for formal diagnoses\n"
            "3. Compare test values to normal ranges\n"
            "4. Read the summary points for key takeaways"
        ),
        r"what (should|do) i do next": (
            lambda: "For next steps:\n"
            "1. Review the follow-up instructions in your summary\n"
            "2. Discuss results with your healthcare provider\n"
            "3. Schedule recommended follow-up appointments\n"
            "4. Follow any prescribed treatment plans"
        )
    }
    
    # Check for matches and return appropriate response
    for pattern, response_func in patterns.items():
        if re.search(pattern, question_lower):
            return response_func()
    
    # Default response if no pattern matches
    return (
        "I can help explain your medical analysis results, including ICD codes, "
        "test ranges, and findings. Please ask a specific question about your results."
    )

@router.post("/message", response_model=Dict[str, Any])
async def send_message(message: Message):
    """
    Process a single chat message and return a response.
    """
    try:
        response = get_response_by_pattern(message.text, message.context)
        
        return {
            "success": True,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@router.post("/conversation", response_model=Dict[str, Any])
async def process_conversation(chat_history: ChatHistory):
    """
    Process a conversation history and return a contextual response.
    """
    try:
        if not chat_history.messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        # Get the last user message
        last_message = chat_history.messages[-1]
        
        # Generate response considering conversation context
        response = get_response_by_pattern(
            last_message["text"],
            chat_history.context
        )
        
        return {
            "success": True,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing conversation: {str(e)}") 
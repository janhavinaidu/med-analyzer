from fastapi import APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
import requests

router = APIRouter()

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / '.env'  
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("COHERE_API_KEY")  # Changed from API_KEY
print("Loaded COHERE_API_KEY:", api_key[:10] + "..." if api_key else None) 
if not api_key:
    raise RuntimeError("COHERE_API_KEY not found in environment variables. Please check your .env file.")

class MessageContext(BaseModel):
    role: str
    content: str

class Message(BaseModel):
    text: str
    context: Optional[List[MessageContext]] = None

class ChatResponse(BaseModel):
    success: bool
    message: str
    timestamp: str

def get_ai_response(prompt: str, context: List[MessageContext] = None) -> str:
    try:
        url = "https://api.cohere.ai/v1/chat"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Build conversation history
        chat_history = []
        if context:
            for msg in context:
                chat_history.append({
                    "role": "USER" if msg.role == "user" else "CHATBOT",
                    "message": msg.content
                })
        
        payload = {
            "model": "command-r-plus",  # Updated to current model
            "message": prompt,
            "chat_history": chat_history,
            "temperature": 0.3,  # Lower temperature for more consistent responses
            "max_tokens": 800,   # Increased token limit
            "preamble": "You are MedBot, a helpful and knowledgeable medical assistant AI. Provide clear, accurate, and concise medical information. Always recommend consulting healthcare professionals for personalized medical advice. Focus on being direct and helpful without unnecessary examples or role-play scenarios."
        }

        response = requests.post(url, headers=headers, json=payload)
        
        print("Cohere API response status:", response.status_code)
        if response.status_code != 200:
            print("Cohere API error response:", response.text)
            
        response.raise_for_status()
        data = response.json()

        return data["text"].strip()
    except requests.exceptions.RequestException as e:
        print(f"Request error in get_ai_response: {e}")
        raise RuntimeError(f"AI service unavailable: {e}")
    except KeyError as e:
        print(f"Response parsing error: {e}")
        print("Full response:", response.text if 'response' in locals() else "No response")
        raise RuntimeError("Invalid response format from AI service")
    except Exception as e:
        print(f"Unexpected error in get_ai_response: {e}")
        raise RuntimeError(f"AI response error: {e}")

@router.post("/message", response_model=ChatResponse)
async def send_message(message: Message):
    try:
        # Create a more direct prompt without examples
        medical_prompt = f"""You are MedBot, a helpful medical assistant AI. Please provide a clear, concise, and helpful response to the user's question about: {message.text}

Guidelines:
- Give direct, accurate medical information
- Use simple, understandable language
- Be concise but thorough
- Always recommend consulting healthcare professionals for personalized medical advice
- If it's about a medication, explain what it is, how it works, and common uses
- Keep the response under 300 words for better readability

User's question: {message.text}"""
        
        response_text = get_ai_response(medical_prompt, message.context)

        return ChatResponse(
            success=True,
            message=response_text,
            timestamp=datetime.now().isoformat()
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        print(f"Unexpected error in send_message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Health check endpoint
@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
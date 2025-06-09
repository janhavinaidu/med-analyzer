# main.py
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from dotenv import load_dotenv
import logging

# Import routers
from routers import pdf, text, analysis, summary, chat, report, blood_analysis, icd

# Load environment variables (e.g., AI_API_KEY from .env)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Medical Analysis API",
    description="API for analyzing medical texts, prescriptions, and blood test reports",
    version="2.0.0"
)

# Configure CORS to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React default
        "http://localhost:8080",  # Your frontend
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with proper prefixes
app.include_router(pdf.router, prefix="/api/pdf", tags=["PDF Processing"])
app.include_router(text.router, prefix="/api/text", tags=["Text Processing"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Medical Analysis"])
app.include_router(icd.router, prefix="/api/icd", tags=["ICD-10 Codes"])
app.include_router(summary.router, prefix="/api/summary", tags=["Summarization"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chatbot"])
app.include_router(report.router, prefix="/api/report", tags=["Report Generation"])
app.include_router(blood_analysis.router, prefix="/api/blood", tags=["Blood Analysis"])

# Custom error handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "detail": exc.errors()}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "Medical Analysis API is running",
        "version": "2.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Medical Analysis API",
        "documentation": "/docs",
        "health": "/health"
    }

# Test endpoint for ICD functionality
@app.get("/test-icd")
async def test_icd_functionality():
    """Test endpoint to verify ICD extraction is working"""
    try:
        from utils.icd_extractor import icd_extractor
        
        test_cases = [
            "Patient diagnosed with type 2 diabetes and hypertension",
            "History of asthma and chronic obstructive pulmonary disease",
            "Patient has depression and anxiety disorder",
            "Prescribed metformin for diabetes management"
        ]
        
        results = {}
        for i, test_text in enumerate(test_cases):
            codes = icd_extractor.identify_icd_codes_from_text(test_text)
            results[f"test_{i+1}"] = {
                "input": test_text,
                "codes": codes
            }
        
        return {
            "success": True,
            "icd_codes_loaded": len(icd_extractor.icd_codes),
            "condition_mappings": len(icd_extractor.condition_mappings),
            "test_results": results
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
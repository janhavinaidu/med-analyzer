from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from dotenv import load_dotenv

from routers import pdf, text, analysis, summary, chat, report, blood_analysis

# Load environment variables (e.g., AI_API_KEY from .env)
load_dotenv()

app = FastAPI(
    title="Blood Test Analyzer API",
    description="API for analyzing blood test reports in PDF format",
    version="1.0.0"
)

# Configure CORS to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(pdf.router, prefix="/api/pdf", tags=["PDF Processing"])
app.include_router(text.router, prefix="/api/text", tags=["Text Processing"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Medical Analysis"])
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

# Run with: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

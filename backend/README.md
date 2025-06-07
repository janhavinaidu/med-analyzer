# Medical Document Analysis Backend

A FastAPI backend service for analyzing medical documents, extracting information, and generating reports.

## Features

1. **PDF Processing**
   - Upload and extract text from medical PDFs
   - Supports prescriptions and blood test reports

2. **Text Analysis**
   - Manual text entry with OpenAI-powered correction
   - Medical entity extraction using scispaCy
   - ICD-10 code prediction
   - Blood test value analysis

3. **Summarization**
   - T5-based bullet-point summarization
   - Structured discharge summary generation

4. **Chatbot**
   - Context-aware medical query responses
   - Pattern-based answer generation

5. **Report Generation**
   - PDF report generation with ReportLab
   - Includes all analysis results and summaries

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd medical-doc-analysis
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install scispaCy model:
   ```bash
   pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_sm-0.5.3.tar.gz
   ```

5. Create `.env` file:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Usage

1. Start the server:
   ```bash
   uvicorn main:app --reload
   ```

2. Access the API documentation:
   - OpenAPI UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## API Endpoints

### PDF Processing
- `POST /api/pdf/upload`: Upload and process PDF files

### Text Processing
- `POST /api/text/correct`: Correct and refine medical text
- `POST /api/text/analyze`: Analyze medical text

### Medical Analysis
- `POST /api/analysis/entities`: Extract medical entities
- `POST /api/analysis/icd-codes`: Predict ICD-10 codes
- `POST /api/analysis/blood-test`: Analyze blood test values
- `POST /api/analysis/full`: Perform full analysis

### Summarization
- `POST /api/summary/bullet-points`: Generate bullet-point summary
- `POST /api/summary/discharge`: Generate discharge summary

### Chatbot
- `POST /api/chat/message`: Process single message
- `POST /api/chat/conversation`: Process conversation history

### Report Generation
- `POST /api/report/generate`: Generate PDF report

## Environment Variables

- `OPENAI_API_KEY`: OpenAI API key for text correction
- `T5_MODEL_NAME`: T5 model name for summarization (default: t5-base)
- `SCISPACY_MODEL`: scispaCy model name (default: en_core_sci_sm)
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `RELOAD`: Enable auto-reload (default: True)
- `FRONTEND_URL`: Frontend URL for CORS (default: http://localhost:5173)

## Dependencies

- FastAPI
- PyPDF2
- OpenAI
- scispaCy
- Transformers (T5)
- ReportLab
- RapidFuzz

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License 
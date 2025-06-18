# 🩺 Med Analyzer Pro

> An AI-powered full-stack web application that analyzes medical reports, extracts diagnosis codes, interprets blood results, summarizes documents, performs OCR on scanned PDFs, and includes a chatbot.

---

## 🧠 Project Overview

**Med Analyzer Pro** is a smart healthcare assistant that allows users to:
- 📄 Upload PDFs or scanned images (OCR-enabled)
- 🧾 Extract critical medical information
- 🧬 Predict **ICD-10 diagnosis codes** from free text
- 🩸 Analyze **blood test values**
- 📝 Summarize long reports using a **T5 Transformer model**
- 💬 Ask health-related queries via a **Cohere-powered chatbot**

This application is built to automate and assist in processing complex medical documents using AI and NLP.

---

## 📽️ Demo Video

> 🚫 **Not deployed** due to memory limits of Docker-based hosting.  
> 📹 Instead, [https://drive.google.com/drive/folders/1-lbfyS0chIhR4NwcWBJikQoFhgfOMDnO?usp=sharing]

---

## 💡 Features

| Feature                      | Tech Used              | Description |
|-----------------------------|------------------------|-------------|
| 📂 PDF/Text Upload          | React + File Reader    | Upload medical reports as PDFs or plain text |
| 🧠 ICD-10 Prediction        | Rule-based NLP         | Extract diagnosis codes from medical text |
| 🩸 Blood Report Analyzer    | Regex + Logic Engine   | Interprets common blood parameters |
| 📝 Medical Summarizer       | HuggingFace T5 Model   | Summarizes long textual reports |
| 📷 OCR Extraction           | Tesseract OCR + OpenCV | Extract text from scanned images/PDFs |
| 💬 AI Chatbot               | Cohere API             | Ask questions and get insights on reports |
| 🧵 REST API Backend         | FastAPI                | API endpoints for all processing |
| 🎨 Frontend UI              | React + Vite           | Responsive interface with result cards |
| 🐳 Dockerized App           | Docker Multi-Stage     | Unified container for both frontend & backend |

---

## 🛠️ Tech Stack

- **Frontend**: React.js, Vite
- **Backend**: FastAPI,Python
- **AI Models**:
  - 🤖 T5 (Summarization)
  - 🧠 Cohere API (Chatbot)
- **OCR**: Tesseract OCR
- **PDF Handling**: pdfplumber
- **Deployment Ready**: Docker, Render/Fly.io/Vercel compatible

---

## 🧪 How to Run Locally

```bash
git clone https://github.com/janhavinaidu/med-analyzer.git
cd med-analyzer
Docker Commands for Local Deployment

# 1. Pull the latest changes from GitHub
git pull

# 2. Rebuild the Docker image with the API URL for the frontend to access the backend
docker build -t health-assist-app --build-arg REACT_APP_API_URL=/api .

# 3. Stop and remove any existing containers with the same name
docker stop health-assist-container || true
docker rm health-assist-container || true

# 4. Run the new container
docker run -d -p 8000:8000 --name health-assist-container health-assist-app

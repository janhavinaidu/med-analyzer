# Stage 1: Build React frontend
FROM node:20 as frontend-build
WORKDIR /app/frontend
COPY docu-health-assist/package.json docu-health-assist/package-lock.json ./
RUN npm install
COPY docu-health-assist/ ./
RUN npm run build

# Stage 2: Build FastAPI backend
FROM python:3.11-slim as backend
WORKDIR /app
COPY backend/ ./backend
COPY --from=frontend-build /app/frontend/dist ./frontend-dist
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Start FastAPI app with uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

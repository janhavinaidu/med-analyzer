# Stage 1: Build React frontend
FROM node:20 AS frontend-build
WORKDIR /app/frontend

# Copy package files and install dependencies
COPY docu-health-assist/package*.json ./
RUN npm install

# Copy the rest of the frontend code
COPY docu-health-assist/ ./

# Build the React app
RUN npm run build

# Stage 2: Build FastAPI backend
FROM python:3.11-slim AS backend
WORKDIR /app

# Copy backend code
COPY backend/ ./backend

# Copy frontend build output into backend
COPY --from=frontend-build /app/frontend/dist ./frontend-dist

# Install backend dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Expose backend port
EXPOSE 8000

# Start the FastAPI app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

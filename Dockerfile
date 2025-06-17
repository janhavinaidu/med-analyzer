# Stage 1: Build React frontend
FROM node:20 AS frontend-build
WORKDIR /app/frontend

# Install system dependencies that might be needed for npm packages
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy package files and install dependencies
COPY docu-health-assist/package*.json ./
RUN npm ci --only=production

# Copy the rest of the frontend code
COPY docu-health-assist/ ./

# Install dev dependencies for build
RUN npm install

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

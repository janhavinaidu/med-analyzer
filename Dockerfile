# Stage 1: Build React frontend
FROM node:20 as frontend-build
WORKDIR /app/frontend

# Set environment variable passed from Render during build
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=$REACT_APP_API_URL

# Install dependencies
COPY docu-health-assist/package.json docu-health-assist/package-lock.json ./
RUN npm install

# Copy rest of the frontend source code
COPY docu-health-assist/ ./

# Dynamically create .env file for build with provided variable
RUN echo "REACT_APP_API_URL=$REACT_APP_API_URL" > .env

# Build the React app
RUN npm run build

# Stage 2: Build FastAPI backend
FROM python:3.11-slim as backend
WORKDIR /app

# --- Add system dependencies for nmslib ---
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    g++ \
 && rm -rf /var/lib/apt/lists/*

# Copy backend source
COPY backend/ ./backend
COPY backend/requirements.txt .

# Copy built React frontend into backend to serve
COPY --from=frontend-build /app/frontend/dist ./frontend-dist

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Expose backend port
EXPOSE 8000

# Run FastAPI app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

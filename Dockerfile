# Stage 1: Build React frontend
FROM node:20 AS frontend-build
WORKDIR /app/frontend

ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=$REACT_APP_API_URL

# Copy package files and install dependencies
COPY docu-health-assist/package*.json ./
RUN npm install

# Copy the rest of the frontend code
COPY docu-health-assist/ ./

# Build the React app
RUN echo "REACT_APP_API_URL=$REACT_APP_API_URL" > .env
RUN npm run build

# Stage 2: Build FastAPI backend
FROM python:3.10-slim AS backend
WORKDIR /app

# Install build tools and system dependencies for cv2
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    g++ \
    libgl1 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgtk-3-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libatlas-base-dev \
    gfortran \
    && rm -rf /var/lib/apt/lists/*

# Copy backend code into backend directory
COPY backend/ ./backend/

# Copy requirements from backend
COPY backend/requirements.txt ./backend/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./frontend-dist

# Install Python dependencies with increased timeout and retry settings
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --timeout 1000 --retries 3 -r backend/requirements.txt

# Expose backend port
EXPOSE 8000

# Start the FastAPI app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

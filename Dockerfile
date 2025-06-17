# Stage 1: Build React frontend
FROM node:20 as frontend-build
WORKDIR /app/frontend

# Set environment variable passed from Render during build
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=$REACT_APP_API_URL

COPY docu-health-assist/package.json docu-health-assist/package-lock.json ./
RUN npm install

COPY docu-health-assist/ ./
RUN echo "REACT_APP_API_URL=$REACT_APP_API_URL" > .env
RUN npm run build

# Stage 2: Build FastAPI backend (Python 3.10)
FROM python:3.10-slim as backend
WORKDIR /app

# Install OS dependencies for nmslib and building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    g++ \
 && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY requirements.txt .                     # Main/global requirements
COPY backend/requirements.txt ./backend/   # Backend-specific requirements

# Install dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend source
COPY backend/ ./backend

# Copy built React frontend into backend to serve
COPY --from=frontend-build /app/frontend/dist ./frontend-dist

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

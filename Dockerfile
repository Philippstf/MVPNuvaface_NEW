# Google Cloud Run Dockerfile for NuvaFace API
FROM python:3.10-slim

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies required for OpenCV and MediaPipe
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    wget \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements-cloudrun.txt .
RUN pip install --no-cache-dir -r requirements-cloudrun.txt

# Copy application code
COPY api/ ./api/
COPY engine/ ./engine/
COPY models/ ./models/
COPY gemini_worker.py .

# Create directories for temporary files
RUN mkdir -p temp_inputs temp_outputs

# Copy environment file (will be overridden by Cloud Run env vars)
COPY .env* ./

# Expose port (Cloud Run will set PORT env var)
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Start command - Cloud Run will provide PORT
CMD uvicorn api.main:app --host 0.0.0.0 --port $PORT
# Medical AI Assistant Backend Dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies for OpenCV and MediaPipe
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Note: Knowledge base will be loaded from memory if assets not available

# Expose port (Cloud Run uses PORT env var, defaults to 8080)
EXPOSE 8080
ENV PORT=8080

# Set Python path
ENV PYTHONPATH=/app

# Command to run the application
CMD ["python", "risk_map/app.py"]
# Medical AI Assistant Backend - Simplified
FROM python:3.10-slim

WORKDIR /app

# Install minimal system dependencies
# Note: libgl1-mesa-glx is replaced by libgl1 in newer Debian versions
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Environment
ENV PYTHONPATH=/app
ENV PORT=8080

# Run with uvicorn for production
CMD ["uvicorn", "risk_map.app:app", "--host", "0.0.0.0", "--port", "8080"]
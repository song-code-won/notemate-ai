# NoteMate AI Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies (build tools and audio processing libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./app/

# Create persistent data and uploads directories
RUN mkdir -p data app/uploads

# Expose FastAPI application port
EXPOSE 8000

# Default command to run NoteMate AI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

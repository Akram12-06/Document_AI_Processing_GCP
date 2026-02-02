# Use official Python runtime as base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir \
    google-cloud-documentai>=2.20.0 \
    google-cloud-storage>=2.10.0 \
    psycopg2-binary>=2.9.9 \
    python-dotenv>=1.0.0

# Copy application code
COPY config/ ./config/
COPY src/ ./src/
COPY main.py ./

# Set environment variable for Python unbuffered output (helps with Cloud Run logging)
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "main.py"]

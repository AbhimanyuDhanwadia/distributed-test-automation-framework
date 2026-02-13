# Dockerfile for Distributed Test Automation Framework
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    redis \
    pydantic \
    pytest \
    httpx \
    prometheus-client \
    requests

# Copy source code and tests
COPY src/ /app/src/
COPY tests/ /app/tests/

# Set Python path
ENV PYTHONPATH=/app

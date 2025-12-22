# LocalLLM Studio Docker Image
# Multi-stage build for optimal size

# Base image with Python
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY localllm_studio/ ./localllm_studio/

# Expose ports
EXPOSE 7860 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - run API server
CMD ["python", "-m", "localllm_studio", "--api", "--port", "8000"]

# =============================================================================
# CUDA variant
# =============================================================================
FROM nvidia/cuda:12.1-runtime-ubuntu22.04 as cuda

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install Python and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    build-essential \
    cmake \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install CUDA-enabled llama-cpp-python
RUN CMAKE_ARGS="-DLLAMA_CUDA=on" pip3 install --no-cache-dir llama-cpp-python

# Install other dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY localllm_studio/ ./localllm_studio/

EXPOSE 7860 8000

CMD ["python3", "-m", "localllm_studio", "--api", "--port", "8000"]

# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for spaCy and networking
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt-lib/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the NLP model inside the container
RUN python -m spacy download en_core_web_sm

# --- NEW: Copy both the Backend and Frontend ---
COPY src/ ./src/
COPY frontend/ ./frontend/
# -----------------------------------------------

# Create a data directory for JSON exports
RUN mkdir -p /app/data

# EXPOSE the port FastAPI is running on
EXPOSE 8000

# Set environment variable to ensure Python finds our modules
ENV PYTHONPATH=/app/src

# Boot the FastAPI server
# Update the CMD in your Dockerfile to point to the src folder
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
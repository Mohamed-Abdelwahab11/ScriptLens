FROM python:3.10-slim

WORKDIR /app

# Install only necessary packages for minimal image size
RUN pip install --no-cache-dir fastapi uvicorn groq python-dotenv

# Copy the source code
COPY src/ ./src/

# Set environment variables
ENV PYTHONPATH=/app
EXPOSE 8000

# Start Uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
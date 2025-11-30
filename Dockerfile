FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY device_data/ ./device_data/
COPY src/ ./src/
COPY pyproject.toml ./

# Install package in editable mode
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (Cloud Run uses $PORT, defaults to 8080)
EXPOSE 8080

# Run the application - Cloud Run injects PORT env var
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}

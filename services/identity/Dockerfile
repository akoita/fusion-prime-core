# Identity Service Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 identity && chown -R identity:identity /app
USER identity

# Environment variables
ENV PYTHONUNBUFFERED=1
# PORT will be set by Cloud Run (8080), or default to 8002 for local dev
ENV PORT=8080

# Expose port (Cloud Run uses 8080)
EXPOSE 8080

# Health check (use PORT env var)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import os; import requests; port = os.getenv('PORT', '8080'); requests.get(f'http://localhost:{port}/health', timeout=5)"

# Run application
CMD ["python", "-m", "app.main"]

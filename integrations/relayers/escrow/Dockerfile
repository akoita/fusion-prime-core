# Dockerfile for Escrow Event Relayer
# Production-ready event relayer for blockchain events

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    build-essential \
    postgresql-client \
    postgresql-server-dev-all \
    libpq-dev \
    curl \
    rustc \
    cargo \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools>=69.0.0 wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 relayer
RUN chown -R relayer:relayer /app
USER relayer

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)" || exit 1

# Expose health check port
EXPOSE 8080

# Run the relayer (use main_job.py for Cloud Run Jobs, relayer_service.py for Cloud Run Services)
CMD ["python", "relayer_service.py"]

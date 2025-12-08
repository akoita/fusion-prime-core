FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY services/relayer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/relayer/app/ ./app/

# Create contracts directory and copy ABIs
RUN mkdir -p /app/contracts
COPY contracts/abi/EscrowFactory.json /app/contracts/EscrowFactory.json
COPY contracts/abi/Escrow.json /app/contracts/Escrow.json

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the relayer
CMD ["python", "app/main.py"]

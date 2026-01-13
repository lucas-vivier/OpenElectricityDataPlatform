# Dockerfile for OpenEnergyData API
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for geopandas
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY data/ data/

# Set Python path to include src directory
ENV PYTHONPATH=/app/src

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn openenergydata.api.main:app --host 0.0.0.0 --port ${PORT}"]

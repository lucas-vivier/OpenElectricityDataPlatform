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
COPY pyproject.toml .
COPY src/ src/
COPY data/ data/

RUN pip install --no-cache-dir -e .

# Expose port
EXPOSE 8000

# Run the API
CMD ["uvicorn", "openenergydata.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

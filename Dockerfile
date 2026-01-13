# Dockerfile for OpenEnergyData API
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies for geopandas
# Using bookworm (Debian 12) which has GDAL 3.6
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    gdal-bin \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set environment variables for GDAL
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy pyproject.toml first for better caching
COPY pyproject.toml .

# Copy source code
COPY src/ src/

# Copy data directory (includes metadata/regions.json)
COPY data/ data/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the API
CMD ["uvicorn", "openenergydata.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

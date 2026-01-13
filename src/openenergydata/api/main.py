"""FastAPI main application."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import regions, power_plants, load_profiles, renewables, treatments, exports, hydropower, resource_potential, socioeconomic


def _get_allowed_origins() -> list[str]:
    origins = os.getenv("ALLOWED_ORIGINS", "")
    if origins:
        return [origin.strip() for origin in origins.split(",") if origin.strip()]
    return [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:5173",
    ]


app = FastAPI(
    title="OpenEnergyData API",
    description="Unified API for open energy data - capacity expansion modeling",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(regions.router, prefix="/api/regions", tags=["Regions"])
app.include_router(power_plants.router, prefix="/api/power-plants", tags=["Power Plants"])
app.include_router(load_profiles.router, prefix="/api/load-profiles", tags=["Load Profiles"])
app.include_router(renewables.router, prefix="/api/renewables", tags=["Renewables"])
app.include_router(treatments.router, prefix="/api/treatments", tags=["Treatments"])
app.include_router(exports.router, prefix="/api/exports", tags=["Exports"])
app.include_router(hydropower.router, prefix="/api/hydropower", tags=["Hydropower"])
app.include_router(resource_potential.router, prefix="/api/resource-potential", tags=["Resource Potential"])
app.include_router(socioeconomic.router, prefix="/api/socioeconomic", tags=["Socio-Economic"])


@app.get("/", tags=["Health"])
async def root():
    """API root - health check."""
    return {
        "name": "OpenEnergyData API",
        "version": "0.1.0",
        "status": "healthy",
        "docs": "/docs",
    }


@app.get("/api", tags=["Health"])
async def api_info():
    """API information."""
    return {
        "endpoints": {
            "regions": "/api/regions",
            "power_plants": "/api/power-plants",
            "load_profiles": "/api/load-profiles",
            "renewables": "/api/renewables",
            "treatments": "/api/treatments",
            "exports": "/api/exports",
            "hydropower": "/api/hydropower",
            "resource_potential": "/api/resource-potential",
            "socioeconomic": "/api/socioeconomic",
        },
        "documentation": "/docs",
    }

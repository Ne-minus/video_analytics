from fastapi import APIRouter, HTTPException
from app.schemas import HealthCheck


health_router = APIRouter()

@health_router.get("/", status_code=200)
async def health() -> HealthCheck:
    try:
        return HealthCheck(healthy=True)
    except Exception as e:
        raise HTTPException(status_code=503, detail="Healthy test unsuccessfull")
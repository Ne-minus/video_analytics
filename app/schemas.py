from pydantic import BaseModel

class HealthCheck(BaseModel):
    healthy: bool
from fastapi import FastAPI
from app.routers import health, auth

app = FastAPI(title='AI Health Assistant API')

app.include_router(auth.router)
app.include_router(health.router)
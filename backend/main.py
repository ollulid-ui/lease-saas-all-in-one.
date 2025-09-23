import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .settings import settings
from .core.database import Base, engine
from . import models
from .routers import auth as auth_router
from .routers import upload as upload_router
from .routers import quota as quota_router
from .routers import billing as billing_router

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(upload_router.router)
app.include_router(quota_router.router)
app.include_router(billing_router.router)

@app.get("/health")
def health():
    return {"status": "ok"}

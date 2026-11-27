from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.candidates import router as candidates_router
from app.api.job_descriptions import router as job_descriptions_router
from app.api.candidate_job_matches import (
    router as candidate_job_matches_router,
)
from app.api.auth import router as auth_router
from app.api.candidate_access import router as candidate_access_router


# Create the FastAPI application first.
app = FastAPI(
    title="FlexTech CareerOS",
    description="AI-powered job application and career intelligence platform",
    version="0.1.0",
)


# Configure CORS after creating the application.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register existing API routers.
app.include_router(candidates_router)
app.include_router(job_descriptions_router)
app.include_router(candidate_job_matches_router)
app.include_router(auth_router)
app.include_router(candidate_access_router)


@app.get("/")
def root():
    return {
        "message": "FlexTech CareerOS is running",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
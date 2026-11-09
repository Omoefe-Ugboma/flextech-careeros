from fastapi import FastAPI

from app.api.candidates import router as candidates_router

app = FastAPI(
    title="FlexTech CareerOS",
    description="AI-powered job application and career intelligence platform",
    version="0.1.0",
)

app.include_router(candidates_router)


@app.get("/")
def root():
    return {
        "message": "FlexTech CareerOS is running",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Generic GT Holidays Tour Package Scraper API",
)

# Mount local storage directory for previewing / downloading images
if settings.storage_root.exists():
    app.mount("/storage", StaticFiles(directory=str(settings.storage_root)), name="storage")

# CORS configuration allowing frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
async def root():
    return {
        "message": "GT Holidays Generic Package Scraper API is running.",
        "docs": "/docs",
        "health": "/api/health",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

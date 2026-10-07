import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.models.package import (
    ScrapeRequest,
    ScrapeJobResponse,
    JobStatusResponse,
    ScrapeResult,
)
from app.scraper.utils import is_valid_url
from app.services.scraper_service import scraper_service
from app.exporters.json_exporter import serialize_public_result

router = APIRouter(prefix="/api")

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Tour Package Scraper & Django Formatter",
    }

@router.post("/scrape", response_model=ScrapeJobResponse)
async def start_scrape(req: ScrapeRequest, background_tasks: BackgroundTasks):
    url = req.url.strip()
    if not is_valid_url(url):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Please submit a valid supported tour package listing URL.",
        )

    job_id = scraper_service.create_job(url, download_images=req.download_images)
    # Run scrape in background task
    background_tasks.add_task(scraper_service.run_scrape_job, job_id)

    return ScrapeJobResponse(job_id=job_id, status="started")

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    status = scraper_service.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job ID not found")
    return status

@router.get("/jobs/{job_id}/json")
async def get_job_json(job_id: str):
    job = scraper_service.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found")
    if not job.result:
        raise HTTPException(
            status_code=400,
            detail=f"Job is currently '{job.status}'. Tour package result is not yet available.",
        )
    return serialize_public_result(job.result)

@router.get("/jobs/{job_id}/internal-audit")
async def get_job_internal_audit(job_id: str):
    """Internal audit endpoint preserving source URLs and extraction metadata."""
    job = scraper_service.jobs.get(job_id)
    if not job or not job.result:
        raise HTTPException(status_code=404, detail="Job or result not found")
    return job.result.model_dump(mode="json")

@router.get("/jobs/{job_id}/download")
async def download_job_json(job_id: str):
    job = scraper_service.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found")
    if not job.output_file or not Path(job.output_file).is_file():
        raise HTTPException(status_code=400, detail="Tour package output file not ready for download")

    filepath = Path(job.output_file)
    return FileResponse(
        path=filepath,
        media_type="application/json",
        filename=filepath.name,
    )

@router.get("/jobs/{job_id}/django-json")
async def get_job_django_json(job_id: str):
    """Returns transformed Django-compatible payload (India or International)."""
    job = scraper_service.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found")
    if not job.django_payload:
        raise HTTPException(
            status_code=400,
            detail=f"Job is currently '{job.status}'. Django transformed payload is not yet available.",
        )
    return job.django_payload

@router.get("/jobs/{job_id}/download-django")
async def download_job_django_json(job_id: str):
    """Downloads transformed Django-compatible JSON file."""
    job = scraper_service.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found")
    if not job.django_output_file or not Path(job.django_output_file).is_file():
        raise HTTPException(status_code=400, detail="Django output file not ready for download")

    filepath = Path(job.django_output_file)
    return FileResponse(
        path=filepath,
        media_type="application/json",
        filename=filepath.name,
    )

@router.post("/jobs/{job_id}/download-images")
async def trigger_download_images(job_id: str, background_tasks: BackgroundTasks):
    """Triggers on-demand downloading of package images for a completed scrape job."""
    job = scraper_service.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found")
    if not job.result or not job.result.packages:
        raise HTTPException(
            status_code=400,
            detail="Tour package scrape results are not yet available for downloading images.",
        )
    if job.image_download_status == "in_progress":
        return {
            "status": "in_progress",
            "message": "Image download is already in progress.",
        }

    background_tasks.add_task(scraper_service.download_job_images, job_id)
    return {
        "status": "started",
        "message": "Package image download initiated successfully.",
    }

@router.get("/jobs/{job_id}/download-images-zip")
async def download_job_images_zip(job_id: str):
    """Downloads a zip archive containing all downloaded package images."""
    job = scraper_service.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found")
    if not job.result or not job.result.packages:
        raise HTTPException(
            status_code=400,
            detail="Tour package data not available.",
        )

    zip_path = scraper_service.create_images_zip(job_id)
    if not zip_path or not zip_path.is_file():
        raise HTTPException(
            status_code=400,
            detail="No local images downloaded yet. Please click 'Fetch & Download Images' first.",
        )

    return FileResponse(
        path=zip_path,
        media_type="application/zip",
        filename=zip_path.name,
    )

# Backward-compatible aliases for endpoints
@router.get("/jobs/{job_id}/focus-json")
async def get_job_focus_json_alias(job_id: str):
    return await get_job_django_json(job_id)

@router.get("/jobs/{job_id}/download-focus")
async def download_job_focus_json_alias(job_id: str):
    return await download_job_django_json(job_id)

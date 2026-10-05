import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path

from app.config import settings
from app.models.package import (
    ScrapeResult,
    JobStatusResponse,
    PackageDetail,
    ScrapeError,
    ListingMetadata,
    ImageDownloadSummary,
)
from app.scraper.client import ScraperClient, BotProtectionException
from app.scraper.metadata import extract_page_metadata
from app.scraper.listing import discover_package_urls
from app.scraper.package import scrape_package
from app.services.image_downloader import ImageDownloaderService
from app.exporters.json_exporter import export_to_json, export_django_to_json
from app.transformers import detect_market, transform_india, transform_international

logger = logging.getLogger(__name__)

class JobState:
    def __init__(self, job_id: str, url: str, download_images: bool = True):
        self.job_id = job_id
        self.url = url
        self.download_images = download_images
        self.status = "queued"
        self.stage = "initialization"
        self.total = 0
        self.completed = 0
        self.success = 0
        self.failed = 0
        self.progress_percent = 0
        self.current_package: Optional[str] = None
        self.output_file: Optional[str] = None  # Raw GT Holidays JSON
        self.django_output_file: Optional[str] = None  # Django-compatible JSON
        self.market: Optional[str] = None  # india, international
        self.django_schema: Optional[str] = None  # /bulk-import/india/, /bulk-import/international/
        self.image_download_status: str = "pending"
        self.image_download_summary: ImageDownloadSummary = ImageDownloadSummary()
        self.error_message: Optional[str] = None
        self.result: Optional[ScrapeResult] = None
        self.django_payload: Optional[Dict[str, Any]] = None

class ScraperService:
    def __init__(self):
        self.jobs: Dict[str, JobState] = {}
        self._lock = asyncio.Lock()

    def create_job(self, url: str, download_images: Optional[bool] = None) -> str:
        job_id = str(uuid.uuid4())
        should_download = download_images if download_images is not None else settings.enable_image_download
        self.jobs[job_id] = JobState(job_id=job_id, url=url, download_images=should_download)
        return job_id

    def get_job_status(self, job_id: str) -> Optional[JobStatusResponse]:
        job = self.jobs.get(job_id)
        if not job:
            return None
        return JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            stage=job.stage,
            total=job.total,
            completed=job.completed,
            success=job.success,
            failed=job.failed,
            progress_percent=job.progress_percent,
            current_package=job.current_package,
            output_file=job.output_file,
            django_output_file=job.django_output_file,
            market=job.market,
            django_schema=job.django_schema,
            image_download_status=job.image_download_status,
            image_download_summary=job.image_download_summary,
            error_message=job.error_message,
        )

    def get_job_result(self, job_id: str) -> Optional[ScrapeResult]:
        job = self.jobs.get(job_id)
        if not job:
            return None
        return job.result

    def get_job_django_payload(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self.jobs.get(job_id)
        if not job:
            return None
        return job.django_payload

    async def run_scrape_job(self, job_id: str):
        job = self.jobs.get(job_id)
        if not job:
            return

        client = ScraperClient()
        try:
            # 1. Analyzing Stage
            job.status = "analyzing"
            job.stage = "fetching_listing"
            job.progress_percent = 5
            
            try:
                listing_html = await client.fetch_html(job.url)
            except BotProtectionException as e:
                job.status = "failed"
                job.stage = "bot_protection_detected"
                job.error_message = e.message
                return
            except Exception as e:
                job.status = "failed"
                job.stage = "failed_listing_fetch"
                job.error_message = f"Failed to fetch listing page: {e}"
                return

            # Extract dynamic listing metadata
            job.stage = "resolving_metadata"
            job.progress_percent = 15
            metadata = extract_page_metadata(listing_html, job.url)

            # 2. Discovering Stage
            job.status = "discovering"
            job.stage = "discovering_packages"
            job.progress_percent = 25

            package_urls = discover_package_urls(listing_html, job.url)
            total_packages = len(package_urls)
            job.total = total_packages

            if total_packages == 0:
                job.status = "failed"
                job.stage = "no_packages_found"
                job.error_message = "No tour packages were discovered on this page."
                return

            # 3. Scraping Stage
            job.status = "scraping"
            job.stage = "package_scraping"
            job.progress_percent = 30

            scraped_packages: list[PackageDetail] = []
            errors: list[ScrapeError] = []
            semaphore = asyncio.Semaphore(settings.max_concurrency)

            async def scrape_single(url: str):
                async with semaphore:
                    job.current_package = url
                    pkg, err = await scrape_package(client, url, metadata)
                    
                    job.completed += 1
                    if pkg:
                        job.success += 1
                        scraped_packages.append(pkg)
                        job.current_package = pkg.name
                    else:
                        job.failed += 1
                        if err:
                            errors.append(err)

                    if job.total > 0:
                        progress = 30 + int((job.completed / job.total) * 60)
                        job.progress_percent = min(90, progress)

            tasks = [scrape_single(url) for url in package_urls]
            await asyncio.gather(*tasks)

            # 4. Image Downloading Stage
            if job.download_images and scraped_packages:
                job.status = "downloading_images"
                job.stage = "downloading_package_images"
                job.progress_percent = 80
                job.image_download_status = "in_progress"

                image_downloader = ImageDownloaderService()
                try:
                    def on_image_progress(done: int, total: int, pkg: PackageDetail):
                        job.current_package = f"Images: {pkg.name}"
                        if total > 0:
                            job.progress_percent = min(91, 80 + int((done / total) * 11))

                    summary = await image_downloader.download_all_packages(
                        scraped_packages,
                        progress_callback=on_image_progress,
                    )
                    job.image_download_summary = summary
                    if summary.total == 0:
                        job.image_download_status = "skipped"
                    elif summary.failed == 0:
                        job.image_download_status = "completed"
                    elif summary.downloaded > 0 or summary.skipped > 0:
                        job.image_download_status = "partial"
                    else:
                        job.image_download_status = "failed"
                except Exception as img_err:
                    logger.warning("Image download error in job %s: %s", job_id, img_err)
                    job.image_download_status = "failed"
                finally:
                    await image_downloader.close()
            else:
                job.image_download_status = "skipped"

            # 5. Exporting Raw JSON Stage
            job.status = "exporting"
            job.stage = "generating_raw_output"
            job.progress_percent = 92

            scraped_at = datetime.now().astimezone().isoformat()
            result = ScrapeResult(
                source="GT Holidays",
                listing_url=job.url,
                page_title=metadata.page_title,
                country=metadata.country,
                region=metadata.region,
                destination=metadata.destination,
                total_packages=total_packages,
                success_count=job.success,
                failed_count=job.failed,
                scraped_at=scraped_at,
                packages=scraped_packages,
                errors=errors,
                image_download_status=job.image_download_status,
                image_download_summary=job.image_download_summary,
            )

            # Save versioned raw output file
            output_filepath, timestamp_str = export_to_json(result)
            job.output_file = str(output_filepath)
            job.result = result

            # 6. Transforming to Django-Compatible Structure
            job.status = "transforming"
            job.stage = "preparing_django_data"
            job.progress_percent = 96

            # Dynamic Market Detection
            market = detect_market(result)
            job.market = market
            job.django_schema = "/bulk-import/india/" if market == "india" else "/bulk-import/international/"

            try:
                if market == "india":
                    django_payload = transform_india(result)
                else:
                    django_payload = transform_international(result)
                
                job.django_payload = django_payload

                # Save versioned Django-compatible output file
                django_filepath = export_django_to_json(
                    django_payload,
                    dest_name=result.destination,
                    timestamp_str=timestamp_str,
                )
                job.django_output_file = str(django_filepath)

                # 7. Completed Stage
                job.progress_percent = 100
                has_image_failures = (job.image_download_summary.failed > 0)
                if job.failed > 0 or has_image_failures:
                    job.status = "completed_with_errors"
                    err_parts = []
                    if job.failed > 0:
                        err_parts.append(f"{job.failed} failed packages")
                    if has_image_failures:
                        err_parts.append(f"{job.image_download_summary.failed} failed image downloads")
                    job.stage = f"Completed with {', '.join(err_parts)} (both Raw & Django JSON exported)"
                else:
                    job.status = "completed"
                    job.stage = f"Scrape and {market.upper()} Django transformation completed successfully"

            except Exception as e:
                logger.exception("Django data transformation failed: %s", e)
                # Raw JSON is preserved safely
                job.status = "completed_with_errors"
                job.stage = f"Scrape succeeded, but Django data transformation failed: {str(e)}"
                job.error_message = f"Django transformation error: {str(e)}"
                job.progress_percent = 100

        except Exception as e:
            logger.exception("Fatal error in scrape job %s: %s", job_id, e)
            job.status = "failed"
            job.stage = "fatal_error"
            job.error_message = str(e)
        finally:
            await client.close()

scraper_service = ScraperService()


from typing import Optional, Union, List
from pydantic import BaseModel, Field, HttpUrl

class ItineraryItem(BaseModel):
    day: int
    title: str = ""
    description: str = ""

class PackageDetail(BaseModel):
    name: str
    slug: str
    source_url: str
    country: Optional[str] = None
    region: Optional[str] = None
    destination: Optional[str] = None
    destinations: List[str] = Field(default_factory=list)
    duration: Optional[str] = None
    nights: Optional[int] = None
    days: Optional[int] = None
    tour_type: Optional[str] = None
    group_size: Optional[Union[int, str]] = None
    languages: List[str] = Field(default_factory=list)
    price: Optional[float] = None
    currency: Optional[str] = None
    overview: Optional[str] = None
    itinerary: List[ItineraryItem] = Field(default_factory=list)
    included: List[str] = Field(default_factory=list)
    excluded: List[str] = Field(default_factory=list)
    banner_image: Optional[str] = None
    images: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    source: str = "GT Holidays"
    scraped_at: str
    
    # Backward-compatible image download metadata
    banner_image_local: Optional[str] = None
    images_local: List[Optional[str]] = Field(default_factory=list)
    image_download_status: str = "pending"  # pending, completed, partial, failed, skipped
    image_download_summary: Optional["ImageDownloadSummary"] = None
    image_errors: List["ImageErrorDetail"] = Field(default_factory=list)

class ImageDownloadSummary(BaseModel):
    total: int = 0
    downloaded: int = 0
    failed: int = 0
    skipped: int = 0

class ImageErrorDetail(BaseModel):
    url: str
    error: str

class ScrapeError(BaseModel):
    url: str
    error: str
    type: Optional[str] = None
    message: Optional[str] = None

class ListingMetadata(BaseModel):
    country: Optional[str] = None
    region: Optional[str] = None
    destination: Optional[str] = None
    category: Optional[str] = None
    page_title: Optional[str] = None

class ScrapeResult(BaseModel):
    source: str = "GT Holidays"
    listing_url: str
    page_title: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    destination: Optional[str] = None
    total_packages: int = 0
    success_count: int = 0
    failed_count: int = 0
    scraped_at: str
    packages: List[PackageDetail] = Field(default_factory=list)
    errors: List[ScrapeError] = Field(default_factory=list)
    image_download_status: Optional[str] = None  # completed, partial, failed, skipped
    image_download_summary: Optional[ImageDownloadSummary] = None

class ScrapeRequest(BaseModel):
    url: str
    download_images: bool = True

class ScrapeJobResponse(BaseModel):
    job_id: str
    status: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # queued, analyzing, discovering, scraping, downloading_images, exporting, transforming, completed, completed_with_errors, failed
    stage: str
    total: int = 0
    completed: int = 0
    success: int = 0
    failed: int = 0
    progress_percent: int = 0
    current_package: Optional[str] = None
    output_file: Optional[str] = None  # Raw GT Holidays JSON filepath
    django_output_file: Optional[str] = None  # Django-compatible JSON filepath
    market: Optional[str] = None  # india, international
    django_schema: Optional[str] = None  # /bulk-import/india/, /bulk-import/international/
    image_download_status: Optional[str] = None  # pending, in_progress, completed, partial, failed, skipped
    image_download_summary: Optional[ImageDownloadSummary] = None
    error_message: Optional[str] = None


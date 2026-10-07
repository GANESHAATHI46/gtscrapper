import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from slugify import slugify

from app.config import settings
from app.models.package import ScrapeResult, PackageDetail

def serialize_public_package(pkg: PackageDetail) -> Dict[str, Any]:
    """
    Serializes a package for public/exported JSON without source-specific branding,
    adapter names, or internal diagnostic metadata.
    Preserves all package details, itinerary, pricing, and local/remote image paths.
    """
    itinerary_items = []
    for it in pkg.itinerary:
        if hasattr(it, "model_dump"):
            itinerary_items.append(it.model_dump(mode="json"))
        elif isinstance(it, dict):
            itinerary_items.append(it)
        else:
            itinerary_items.append({
                "day": getattr(it, "day", 1),
                "title": getattr(it, "title", ""),
                "description": getattr(it, "description", ""),
            })

    image_download_summary = None
    if pkg.image_download_summary:
        if hasattr(pkg.image_download_summary, "model_dump"):
            image_download_summary = pkg.image_download_summary.model_dump(mode="json")
        elif isinstance(pkg.image_download_summary, dict):
            image_download_summary = pkg.image_download_summary

    return {
        "name": pkg.name,
        "slug": pkg.slug,
        "country": pkg.country,
        "region": pkg.region,
        "destination": pkg.destination,
        "destinations": list(pkg.destinations) if pkg.destinations else [],
        "duration": pkg.duration,
        "nights": pkg.nights,
        "days": pkg.days,
        "tour_type": pkg.tour_type,
        "group_size": pkg.group_size,
        "languages": list(pkg.languages) if pkg.languages else [],
        "price": pkg.price,
        "currency": pkg.currency,
        "overview": pkg.overview,
        "itinerary": itinerary_items,
        "included": list(pkg.included) if pkg.included else [],
        "excluded": list(pkg.excluded) if pkg.excluded else [],
        "banner_image": pkg.banner_image,
        "banner_image_local": pkg.banner_image_local,
        "images": list(pkg.images) if pkg.images else [],
        "images_local": list(pkg.images_local) if pkg.images_local else [],
        "image_download_status": pkg.image_download_status,
        "image_download_summary": image_download_summary,
        "location": pkg.location,
        "scraped_at": pkg.scraped_at,
    }

def serialize_public_result(result: ScrapeResult) -> Dict[str, Any]:
    """
    Serializes a complete scraping result for generic public export.
    Excludes internal source branding ('GT Holidays'), source URLs, and internal audit data.
    """
    image_download_summary = None
    if result.image_download_summary:
        if hasattr(result.image_download_summary, "model_dump"):
            image_download_summary = result.image_download_summary.model_dump(mode="json")
        elif isinstance(result.image_download_summary, dict):
            image_download_summary = result.image_download_summary

    public_packages = [serialize_public_package(p) for p in result.packages]

    public_errors = []
    if result.errors:
        for err in result.errors:
            public_errors.append({
                "message": getattr(err, "message", None) or getattr(err, "error", "Failed to extract package"),
            })

    return {
        "page_title": result.page_title,
        "country": result.country,
        "region": result.region,
        "destination": result.destination,
        "total_packages": result.total_packages,
        "success_count": result.success_count,
        "failed_count": result.failed_count,
        "scraped_at": result.scraped_at,
        "image_download_status": result.image_download_status,
        "image_download_summary": image_download_summary,
        "packages": public_packages,
        "errors": public_errors,
    }

def serialize_internal_result(result: ScrapeResult) -> Dict[str, Any]:
    """
    Serializes full internal data including source URLs and audit records for debugging.
    """
    return result.model_dump(mode="json")

def export_to_json(result: ScrapeResult, timestamp_str: str = None) -> tuple[Path, str]:
    """
    Exports generic public Tour Packages JSON to a versioned, timestamped file.
    Format: output/{destination-slug}-tour-packages-{YYYYMMDD-HHMMSS}.json
    Fallback: output/tour-packages-{YYYYMMDD-HHMMSS}.json
    Returns (filepath, timestamp_str)
    """
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    if not timestamp_str:
        timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")

    dest_name = result.destination
    if dest_name:
        dest_slug = slugify(dest_name)
    else:
        dest_slug = None

    if dest_slug:
        clean_slug = dest_slug.removesuffix("-tour-packages").removesuffix("-tour").removesuffix("-packages")
        filename = f"{clean_slug}-tour-packages-{timestamp_str}.json"
    else:
        filename = f"tour-packages-{timestamp_str}.json"

    filepath = settings.output_dir / filename

    # Use generic public serializer (omits source-specific URLs and branding)
    data = serialize_public_result(result)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath, timestamp_str

def export_django_to_json(django_data: dict, dest_name: str = None, timestamp_str: str = None) -> Path:
    """
    Exports transformed Django-compatible JSON to:
    output/{destination-slug}-tour-packages-django-{YYYYMMDD-HHMMSS}.json
    """
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    if not timestamp_str:
        timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")

    if dest_name:
        dest_slug = slugify(dest_name)
    else:
        dest_slug = None

    if dest_slug:
        clean_slug = dest_slug.removesuffix("-tour-packages").removesuffix("-tour").removesuffix("-packages")
        filename = f"{clean_slug}-tour-packages-django-{timestamp_str}.json"
    else:
        filename = f"tour-packages-django-{timestamp_str}.json"

    filepath = settings.output_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(django_data, f, indent=2, ensure_ascii=False)

    return filepath

# Alias for backwards compatibility
export_focus_to_json = export_django_to_json

def export_images_to_zip(result: ScrapeResult, timestamp_str: Optional[str] = None) -> Optional[Path]:
    """
    Creates a zip archive containing all downloaded local images for the scraped packages.
    Format: output/{destination-slug}-tour-packages-images-{YYYYMMDD-HHMMSS}.zip
    """
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    if not timestamp_str:
        timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")

    dest_name = result.destination
    if dest_name:
        dest_slug = slugify(dest_name)
    else:
        dest_slug = None

    if dest_slug:
        clean_slug = dest_slug.removesuffix("-tour-packages").removesuffix("-tour").removesuffix("-packages")
        filename = f"{clean_slug}-tour-packages-images-{timestamp_str}.zip"
    else:
        filename = f"tour-packages-images-{timestamp_str}.zip"

    zip_filepath = settings.output_dir / filename

    # Collect all local image files
    files_to_zip: List[Tuple[Path, str]] = []
    for pkg in result.packages:
        if pkg.banner_image_local:
            p = settings.storage_root / pkg.banner_image_local
            if p.is_file():
                files_to_zip.append((p, pkg.banner_image_local))
        if pkg.images_local:
            for img_rel in pkg.images_local:
                if img_rel:
                    p = settings.storage_root / img_rel
                    if p.is_file():
                        files_to_zip.append((p, img_rel))

    if not files_to_zip:
        return None

    seen_arcnames = set()
    with zipfile.ZipFile(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path, arcname in files_to_zip:
            if arcname not in seen_arcnames:
                zf.write(file_path, arcname=arcname)
                seen_arcnames.add(arcname)

    return zip_filepath

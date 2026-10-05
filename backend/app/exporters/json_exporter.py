import json
from datetime import datetime
from pathlib import Path
from slugify import slugify

from app.config import settings
from app.models.package import ScrapeResult

def export_to_json(result: ScrapeResult, timestamp_str: str = None) -> tuple[Path, str]:
    """
    Exports ScrapeResult to a versioned, timestamped JSON file.
    Format: output/{destination-slug}-tour-packages-{YYYYMMDD-HHMMSS}.json
    Fallback: output/gt-holidays-packages-{YYYYMMDD-HHMMSS}.json
    Returns (filepath, timestamp_str)
    """
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    if not timestamp_str:
        timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Determine destination slug
    dest_name = result.destination
    if dest_name:
        dest_slug = slugify(dest_name)
    else:
        dest_slug = None

    if dest_slug:
        # Avoid double -tour-packages in filename
        clean_slug = dest_slug.removesuffix("-tour-packages").removesuffix("-tour").removesuffix("-packages")
        filename = f"{clean_slug}-tour-packages-{timestamp_str}.json"
    else:
        clean_slug = "gt-holidays"
        filename = f"gt-holidays-packages-{timestamp_str}.json"

    filepath = settings.output_dir / filename

    # Serialize Pydantic model to clean JSON dictionary
    data = result.model_dump(mode="json")

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
        filename = f"gt-holidays-packages-django-{timestamp_str}.json"

    filepath = settings.output_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(django_data, f, indent=2, ensure_ascii=False)

    return filepath

# Alias for backwards compatibility
export_focus_to_json = export_django_to_json

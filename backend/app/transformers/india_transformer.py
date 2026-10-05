import logging
from typing import Dict, Any, List, Union
from app.models.package import ScrapeResult, PackageDetail
from app.models.focus import IndiaBulkImportPayload
from app.transformers.common import (
    safe_slug,
    normalize_string,
    normalize_destination,
    normalize_language,
    normalize_price,
    deduplicate_urls,
    normalize_day,
)

logger = logging.getLogger(__name__)

def transform_india(scraped_data: Union[Dict[str, Any], ScrapeResult]) -> Dict[str, Any]:
    """
    Transforms raw GT Holidays scraper data into the exact JSON structure
    expected by Focus Tourism Django backend: POST /bulk-import/india/
    """
    # Normalize input to dictionary or model access
    if isinstance(scraped_data, ScrapeResult):
        raw = scraped_data.model_dump(mode="json")
    elif isinstance(scraped_data, dict):
        raw = scraped_data
    else:
        raw = dict(scraped_data)

    # 1. Resolve Top-Level Metadata
    raw_region = raw.get("region")
    raw_destination = raw.get("destination")
    packages_raw = raw.get("packages", [])

    # If top-level region is missing, attempt to get from first package or fallback
    if not raw_region and packages_raw:
        raw_region = packages_raw[0].get("region")
    region_name = normalize_string(raw_region) or "India"
    region_slug = safe_slug(region_name, fallback="india")

    # If top-level destination is missing, attempt to get from first package or fallback
    if not raw_destination and packages_raw:
        raw_destination = packages_raw[0].get("destination")
    destination_name = normalize_string(raw_destination) or "India Tours"
    destination_slug = safe_slug(destination_name, fallback="india-tours")

    # 2. Build Regions
    regions = [
        {
            "name": region_name,
            "slug": region_slug,
        }
    ]

    # 3. Build Cities (category/destination grouping in Django India API)
    cities = [
        {
            "region": region_slug,
            "name": destination_name,
            "slug": destination_slug,
        }
    ]

    # 4. Build Package Types & Transform Packages
    package_types_map: Dict[str, Dict[str, Any]] = {}
    transformed_packages: List[Dict[str, Any]] = []
    package_errors: List[Dict[str, Any]] = []

    for idx, pkg in enumerate(packages_raw):
        try:
            pkg_name = normalize_string(pkg.get("name")) or f"Tour Package {idx + 1}"
            pkg_slug = safe_slug(pkg.get("slug") or pkg_name, fallback=f"package-{idx + 1}")

            # Determine Package Type
            raw_pkg_type = (
                pkg.get("package_type")
                or pkg.get("tour_type")
                or raw.get("category")
                or "General"
            )
            pt_name = normalize_string(raw_pkg_type) or "General"
            pt_slug = safe_slug(pt_name, fallback="general")

            if pt_slug not in package_types_map:
                package_types_map[pt_slug] = {
                    "name": pt_name,
                    "slug": pt_slug,
                    "is_active": True,
                }

            # Language formatting (e.g. ["English", "Tamil"] -> "English, Tamil")
            raw_languages = pkg.get("languages")
            if isinstance(raw_languages, str):
                raw_languages = [raw_languages]
            language_str = normalize_language(raw_languages)

            # Price formatting
            price_val = normalize_price(pkg.get("price"))

            # Destination string formatting (e.g. "Guruvayur - Munnar - Thekkady")
            pkg_dest = normalize_destination(pkg.get("destination"))

            # Image & Banner Handling
            raw_banner = normalize_string(pkg.get("banner_image"))
            raw_images = deduplicate_urls(pkg.get("images", []))

            # Package main image
            package_image = raw_banner
            if not package_image and raw_images:
                package_image = raw_images[0]

            # Build gallery images array
            gallery_images = []
            gallery_urls = []
            for u in raw_images:
                if u not in gallery_urls:
                    gallery_urls.append(u)

            # Do not duplicate banner inside gallery if it's already the only image,
            # but ensure gallery has proper primary and sort_order
            for s_idx, img_url in enumerate(gallery_urls):
                gallery_images.append({
                    "image": img_url,
                    "is_primary": (s_idx == 0),
                    "sort_order": s_idx + 1,
                })

            # Itinerary Handling
            itinerary_items = []
            raw_itinerary = pkg.get("itinerary", [])
            for item in raw_itinerary:
                if not isinstance(item, dict):
                    continue
                day_int = normalize_day(item.get("day"))
                if day_int is None:
                    continue

                itinerary_items.append({
                    "day": day_int,
                    "title": normalize_string(item.get("title")) or f"Day {day_int}",
                    "description": normalize_string(item.get("description")) or "",
                })

            # Sort itinerary by day
            itinerary_items.sort(key=lambda x: x["day"])

            transformed_pkg = {
                "city": destination_slug,
                "package_type": pt_slug,
                "name": pkg_name,
                "slug": pkg_slug,
                "duration": normalize_string(pkg.get("duration")),
                "tour_type": normalize_string(pkg.get("tour_type")) or pt_name,
                "group_size": pkg.get("group_size"),
                "language": language_str,
                "destination": pkg_dest,
                "price": price_val,
                "image": package_image,
                "is_featured": False,
                "is_active": True,
                "images": gallery_images,
                "itinerary": itinerary_items,
            }
            transformed_packages.append(transformed_pkg)

        except Exception as e:
            logger.warning("Error transforming India package %s: %s", pkg.get("name"), e)
            package_errors.append({
                "package_name": pkg.get("name"),
                "slug": pkg.get("slug"),
                "error": str(e),
            })
            continue

    # Assemble final payload
    payload = {
        "regions": regions,
        "cities": cities,
        "package_types": list(package_types_map.values()),
        "packages": transformed_packages,
    }

    # Validate schema against Pydantic contract
    validated = IndiaBulkImportPayload.model_validate(payload)
    return validated.model_dump(mode="json")

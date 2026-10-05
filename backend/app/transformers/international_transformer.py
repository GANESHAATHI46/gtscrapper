import logging
from typing import Dict, Any, List, Union
from app.models.package import ScrapeResult
from app.models.focus import InternationalBulkImportPayload
from app.transformers.common import (
    safe_slug,
    normalize_string,
    normalize_destination,
    normalize_language,
    normalize_price,
    deduplicate_urls,
    extract_best_banner,
    normalize_day,
)

logger = logging.getLogger(__name__)

def transform_international(scraped_data: Union[Dict[str, Any], ScrapeResult]) -> Dict[str, Any]:
    """
    Transforms raw GT Holidays scraper data into the exact JSON structure
    expected by Focus Tourism Django backend: POST /bulk-import/international/
    """
    if isinstance(scraped_data, ScrapeResult):
        raw = scraped_data.model_dump(mode="json")
    elif isinstance(scraped_data, dict):
        raw = scraped_data
    else:
        raw = dict(scraped_data)

    packages_raw = raw.get("packages", [])

    # 1. Resolve Region & Country
    # User Rule: "Never infer/override international region names when reliable scraped metadata already exists. Preserve scraped region."
    raw_region = raw.get("region")
    if not raw_region and packages_raw:
        raw_region = packages_raw[0].get("region")
    region_name = normalize_string(raw_region) or "International"
    region_slug = safe_slug(region_name, fallback="international")

    # Scraped Country
    raw_country = raw.get("country")
    if not raw_country and packages_raw:
        raw_country = packages_raw[0].get("country")
    # Fallback to destination if country is not explicitly present
    if not raw_country:
        raw_country = raw.get("destination")
    country_name = normalize_string(raw_country) or "International Tours"
    country_slug = safe_slug(country_name, fallback="international-tours")

    # Determine Country Banner Image
    best_banner = extract_best_banner(raw.get("banner_image"), packages_raw)

    # 2. Build Regions
    regions = [
        {
            "name": region_name,
            "slug": region_slug,
        }
    ]

    # 3. Build Countries
    countries = [
        {
            "region": region_slug,
            "name": country_name,
            "slug": country_slug,
            "banner_image": best_banner,
            "is_active": True,
        }
    ]

    # 4. Build Package Types & Transform Packages
    package_types_map: Dict[str, Dict[str, Any]] = {}
    transformed_packages: List[Dict[str, Any]] = []
    package_errors: List[Dict[str, Any]] = []

    for idx, pkg in enumerate(packages_raw):
        try:
            pkg_name = normalize_string(pkg.get("name")) or f"International Package {idx + 1}"
            pkg_slug = safe_slug(pkg.get("slug") or pkg_name, fallback=f"package-{idx + 1}")

            # Determine Package Type
            raw_pkg_type = (
                pkg.get("package_type")
                or pkg.get("tour_type")
                or raw.get("category")
                or "Daily Tour"
            )
            pt_name = normalize_string(raw_pkg_type) or "Daily Tour"
            pt_slug = safe_slug(pt_name, fallback="daily-tour")

            if pt_slug not in package_types_map:
                package_types_map[pt_slug] = {
                    "name": pt_name,
                    "slug": pt_slug,
                    "description": "",
                }

            # Language formatting
            raw_languages = pkg.get("languages")
            if isinstance(raw_languages, str):
                raw_languages = [raw_languages]
            language_str = normalize_language(raw_languages)

            # Price formatting
            price_val = normalize_price(pkg.get("price"))

            # Destination string formatting
            pkg_dest = normalize_destination(pkg.get("destination"))

            # Image & Banner Handling
            raw_banner = normalize_string(pkg.get("banner_image"))
            raw_images = deduplicate_urls(pkg.get("images", []))

            package_banner = raw_banner
            if not package_banner and raw_images:
                package_banner = raw_images[0]

            # Build gallery images array
            gallery_images = []
            gallery_urls = []
            for u in raw_images:
                if u not in gallery_urls:
                    gallery_urls.append(u)

            for s_idx, img_url in enumerate(gallery_urls):
                gallery_images.append({
                    "image": img_url,
                    "alt_text": pkg_name,
                    "display_order": s_idx + 1,
                    "is_active": True,
                })

            # Itinerary Handling
            itinerary_items = []
            raw_itinerary = pkg.get("itinerary", [])
            for item in raw_itinerary:
                if not isinstance(item, dict):
                    continue
                day_int = normalize_day(item.get("day") or item.get("day_number"))
                if day_int is None:
                    continue

                order_val = item.get("display_order")
                try:
                    display_order = int(order_val) if order_val is not None else day_int
                except (ValueError, TypeError):
                    display_order = day_int

                itinerary_items.append({
                    "day_number": day_int,
                    "title": normalize_string(item.get("title")) or f"Day {day_int}",
                    "description": normalize_string(item.get("description")) or "",
                    "display_order": display_order,
                    "is_active": True,
                })

            itinerary_items.sort(key=lambda x: x["display_order"])

            transformed_pkg = {
                "country": country_slug,
                "package_type": pt_slug,
                "name": pkg_name,
                "slug": pkg_slug,
                "duration": normalize_string(pkg.get("duration")),
                "tour_type": normalize_string(pkg.get("tour_type")) or pt_name,
                "group_size": pkg.get("group_size"),
                "language": language_str,
                "destination": pkg_dest,
                "price": price_val,
                "banner_image": package_banner,
                "is_featured": False,
                "is_active": True,
                "groups": [],  # Never fabricate seat counts or group dates
                "images": gallery_images,
                "itinerary": itinerary_items,
            }
            transformed_packages.append(transformed_pkg)

        except Exception as e:
            logger.warning("Error transforming International package %s: %s", pkg.get("name"), e)
            package_errors.append({
                "package_name": pkg.get("name"),
                "slug": pkg.get("slug"),
                "error": str(e),
            })
            continue

    payload = {
        "regions": regions,
        "countries": countries,
        "package_types": list(package_types_map.values()),
        "packages": transformed_packages,
    }

    validated = InternationalBulkImportPayload.model_validate(payload)
    return validated.model_dump(mode="json")

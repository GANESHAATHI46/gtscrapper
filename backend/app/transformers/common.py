import re
from typing import Optional, List, Any
from slugify import slugify

def safe_slug(text: Optional[str], fallback: str = "general") -> str:
    """
    Generate a normalized lowercase slug.
    Removes duplicate hyphens, trims whitespace, handles non-ASCII.
    """
    if not text or not str(text).strip():
        return fallback
    slug = slugify(str(text).strip(), lowercase=True)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug if slug else fallback

def normalize_string(text: Optional[str]) -> Optional[str]:
    """
    Cleans up string whitespace and returns None if empty.
    """
    if text is None:
        return None
    cleaned = str(text).strip()
    return cleaned if cleaned else None

def normalize_destination(dest: Optional[str]) -> Optional[str]:
    """
    Normalizes separator characters (–, —, etc.) to a clean ' - '
    while preserving place names.
    """
    if not dest:
        return None
    cleaned = str(dest).strip()
    # Normalize long dashes or arrows to standard spaced hyphen
    cleaned = re.sub(r"\s*[–—→]\s*", " - ", cleaned)
    # Collapse multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned else None

def normalize_language(languages: Optional[List[str]]) -> Optional[str]:
    """
    Django expects:
    - 1 language: "English"
    - multiple: "English, Tamil"
    - empty/none: None
    """
    if not languages:
        return None
    valid = [str(lang).strip() for lang in languages if lang and str(lang).strip()]
    if not valid:
        return None
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for l in valid:
        if l.lower() not in seen:
            seen.add(l.lower())
            unique.append(l)
    return ", ".join(unique) if unique else None

def normalize_price(price: Any) -> Optional[float]:
    """
    Normalizes numeric price. Does not invent or estimate prices.
    """
    if price is None:
        return None
    try:
        val = float(price)
        return val if val > 0 else None
    except (ValueError, TypeError):
        return None

def deduplicate_urls(urls: Optional[List[str]]) -> List[str]:
    """
    Deduplicates URLs preserving original order, removes empty or invalid strings.
    """
    if not urls:
        return []
    result = []
    seen = set()
    for u in urls:
        if not u:
            continue
        cleaned = str(u).strip()
        if cleaned and cleaned.startswith("http") and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result

def extract_best_banner(listing_banner: Optional[str], packages: List[Any]) -> Optional[str]:
    """
    Finds best available country/listing banner image:
    1. Listing banner image if provided
    2. First valid package banner_image
    3. First valid package gallery image
    4. None
    """
    if listing_banner and listing_banner.strip().startswith("http"):
        return listing_banner.strip()
    
    for pkg in packages:
        pkg_banner = getattr(pkg, "banner_image", None) if not isinstance(pkg, dict) else pkg.get("banner_image")
        if pkg_banner and str(pkg_banner).strip().startswith("http"):
            return str(pkg_banner).strip()
            
    for pkg in packages:
        pkg_images = getattr(pkg, "images", []) if not isinstance(pkg, dict) else pkg.get("images", [])
        if pkg_images:
            for img in pkg_images:
                img_url = img if isinstance(img, str) else getattr(img, "image", None) or (img.get("image") if isinstance(img, dict) else None)
                if img_url and str(img_url).strip().startswith("http"):
                    return str(img_url).strip()

    return None

def normalize_day(day_val: Any) -> Optional[int]:
    """
    Safely converts day identifier to positive integer. Returns None if malformed.
    """
    if day_val is None:
        return None
    try:
        val = int(day_val)
        return val if val > 0 else None
    except (ValueError, TypeError):
        return None

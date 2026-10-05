import re
from urllib.parse import urlparse
from typing import List
from bs4 import BeautifulSoup

from app.scraper.utils import to_absolute_url

EXCLUDED_PATH_KEYWORDS = (
    "/packages/",  # Category listing, not individual package
    "/blog/",
    "/news/",
    "/about",
    "/contact",
    "/terms",
    "/privacy",
    "/disclaimer",
    "/career",
    "/gallery",
    "/faq",
)

EXCLUDED_CONTAINER_SELECTORS = [
    "header",
    "#header",
    ".header",
    "nav",
    ".menu",
    ".has-mega-menu",
    ".widget_nav_menu",
    "footer",
    "#footer",
    ".site-footer",
    "#reviews",
    ".st-related-service-new",
    ".st-related-service",
    ".gt-mobile-sticky-item",
]

def discover_package_urls(html: str, base_url: str) -> List[str]:
    """
    Dynamically discovers unique package detail URLs from a GT Holidays listing page.
    Combines:
    - Main listing container scope (.grid-container, .grid-item, #gt-more-packages)
    - Hidden/View More DOM elements
    - Scope-aware /package/ anchor extraction
    - Filters out navigation, footer, blog, and related tour links.
    - Preserves listing order and deduplicates.
    """
    soup = BeautifulSoup(html, "lxml")

    # Decompose or remove unrelated sections from listing extraction
    for selector in EXCLUDED_CONTAINER_SELECTORS:
        for node in soup.select(selector):
            node.decompose()

    discovered_links: List[str] = []

    # Priority 1: Package card anchors in primary listing containers & hidden View More containers
    card_selectors = [
        ".grid-container .grid-item a[href*='/package/']",
        "#gt-more-packages .grid-item a[href*='/package/']",
        ".gt-all-packages .grid-item a[href*='/package/']",
        ".grid-item a[href*='/package/']",
        ".st-hotel-result a[href*='/package/']",
        ".item-service a[href*='/package/']",
        ".service-title a[href*='/package/']",
    ]

    for sel in card_selectors:
        elements = soup.select(sel)
        for el in elements:
            href = el.get("href")
            if href:
                discovered_links.append(href)

    # Priority 2: Any anchor pointing to /package/ in the remaining body
    if not discovered_links:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/package/" in href:
                discovered_links.append(href)

    # Priority 3: Fallback regex in case of unparsed script data or inline JS cards
    if not discovered_links:
        raw_matches = re.findall(r'href=["\'](https?://(?:www\.)?gtholidays\.in/package/[^"\'#?]+)["\']', html)
        discovered_links.extend(raw_matches)

    # Clean, validate, and deduplicate
    unique_urls: List[str] = []
    seen: set[str] = set()

    for raw_url in discovered_links:
        abs_url = to_absolute_url(raw_url, base_url).split("#")[0].split("?")[0].strip()
        parsed = urlparse(abs_url)

        # Enforce /package/ (singular) pattern for individual tour detail pages
        if "/package/" not in parsed.path:
            continue

        # Reject excluded path keywords
        if any(bad in parsed.path for bad in EXCLUDED_PATH_KEYWORDS):
            continue

        # Reject top-level /package/ root if present
        if parsed.path.strip("/") == "package":
            continue

        # Canonicalize trailing slash
        if not abs_url.endswith("/"):
            abs_url += "/"

        if abs_url not in seen:
            seen.add(abs_url)
            unique_urls.append(abs_url)

    return unique_urls

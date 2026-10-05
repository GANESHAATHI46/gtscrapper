import re
import json
from urllib.parse import urlparse
from typing import Optional, List
from bs4 import BeautifulSoup

from app.models.package import ListingMetadata
from app.scraper.utils import clean_text

def _strip_package_suffix(name: str) -> str:
    """Strips suffixes like ' Tour Packages', ' Packages', ' Tour'."""
    clean = clean_text(name)
    clean = re.sub(r'(?i)\s+tour\s+packages?$', '', clean)
    clean = re.sub(r'(?i)\s+holiday\s+packages?$', '', clean)
    clean = re.sub(r'(?i)\s+packages?$', '', clean)
    clean = re.sub(r'(?i)\s+tour$', '', clean)
    return clean.strip()

def _parse_breadcrumbs_schema(soup: BeautifulSoup) -> List[str]:
    """Finds BreadcrumbList items from Schema.org JSON-LD scripts."""
    breadcrumb_items: List[str] = []
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
            graphs = data.get("@graph", [data]) if isinstance(data, dict) else [data]
            for item in graphs:
                if isinstance(item, dict):
                    # Check direct breadcrumb list or nested
                    b_list = item if item.get("@type") == "BreadcrumbList" else item.get("breadcrumb")
                    if isinstance(b_list, dict) and "itemListElement" in b_list:
                        elems = b_list["itemListElement"]
                        if isinstance(elems, list):
                            # Sort by position
                            sorted_elems = sorted(elems, key=lambda x: x.get("position", 0))
                            breadcrumb_items = [
                                x.get("name") or (x.get("item", {}).get("name") if isinstance(x.get("item"), dict) else "")
                                for x in sorted_elems
                            ]
                            breadcrumb_items = [clean_text(b) for b in breadcrumb_items if clean_text(b)]
                            if breadcrumb_items:
                                return breadcrumb_items
        except Exception:
            continue
    return breadcrumb_items

def _parse_breadcrumbs_html(soup: BeautifulSoup) -> List[str]:
    """Finds breadcrumbs from standard HTML markup."""
    selectors = [
        "ol.breadcrumb li",
        "ul.breadcrumb li",
        ".breadcrumb li",
        ".st-breadcrumb li",
        "nav[aria-label='breadcrumb'] li",
        ".breadcrumbs span",
    ]
    for sel in selectors:
        nodes = soup.select(sel)
        if nodes:
            texts = [clean_text(n.get_text()) for n in nodes]
            texts = [t for t in texts if t and t != "/"]
            if len(texts) >= 2:
                return texts
    return []

def extract_page_metadata(html: str, url: str) -> ListingMetadata:
    """
    Dynamically extracts listing page metadata in priority order:
    1. Schema BreadcrumbList
    2. HTML breadcrumbs
    3. Structured page metadata
    4. H1
    5. OpenGraph title
    6. URL segments
    Returns null/None if confidence is insufficient. Never guesses.
    """
    soup = BeautifulSoup(html, "lxml")

    country: Optional[str] = None
    region: Optional[str] = None
    destination: Optional[str] = None
    category: Optional[str] = None
    page_title: Optional[str] = None

    # Page Title extraction
    h1_tag = soup.find("h1")
    if h1_tag:
        page_title = clean_text(h1_tag.get_text())

    if not page_title:
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            page_title = clean_text(og_title["content"])

    if not page_title and soup.title:
        title_text = clean_text(soup.title.get_text())
        page_title = re.sub(r'\s*\|\s*GT\s*Holidays.*$', '', title_text, flags=re.I).strip()

    # Priority 1: Schema Breadcrumbs
    breadcrumbs = _parse_breadcrumbs_schema(soup)

    # Priority 2: HTML Breadcrumbs fallback
    if not breadcrumbs:
        breadcrumbs = _parse_breadcrumbs_html(soup)

    # Resolve from breadcrumbs
    # Typical GT Holidays structure:
    # [Home, Tour Packages, India Tour Packages, North India Tour Packages, Delhi Tour Packages]
    # or [Home, Packages, International Tour Packages, Asia Tour Packages, Dubai Tour Packages]
    if len(breadcrumbs) >= 3:
        filtered = [b for b in breadcrumbs if clean_text(b).lower() not in ("home", "tour packages", "packages")]
        if len(filtered) == 3:
            country = _strip_package_suffix(filtered[0])
            region = _strip_package_suffix(filtered[1])
            destination = _strip_package_suffix(filtered[2])
        elif len(filtered) == 2:
            country = _strip_package_suffix(filtered[0])
            destination = _strip_package_suffix(filtered[1])
        elif len(filtered) == 1:
            destination = _strip_package_suffix(filtered[0])

    # Priority 3 & 4: Page headings / OpenGraph for Destination
    if not destination and page_title:
        cleaned_dest = _strip_package_suffix(page_title)
        if cleaned_dest and len(cleaned_dest) < 60:
            destination = cleaned_dest

    # Priority 6: URL segments fallback
    parsed = urlparse(url)
    segments = [s for s in parsed.path.strip("/").split("/") if s]

    # Check if URL matches /packages/{country}/{region}/{destination}-tour-packages/
    if segments and segments[0].lower() in ("packages", "package"):
        sub_segments = segments[1:]
        if len(sub_segments) >= 3:
            if not country:
                country = sub_segments[0].replace("-", " ").title()
            if not region:
                region = sub_segments[1].replace("-", " ").title()
            if not destination:
                destination = _strip_package_suffix(sub_segments[2].replace("-", " ").title())
        elif len(sub_segments) == 2:
            if not country:
                country = sub_segments[0].replace("-", " ").title()
            if not destination:
                destination = _strip_package_suffix(sub_segments[1].replace("-", " ").title())
        elif len(sub_segments) == 1:
            if not destination:
                destination = _strip_package_suffix(sub_segments[0].replace("-", " ").title())

    # Detect Category (e.g. International vs Domestic / India)
    if country and country.lower() in ("international", "international packages"):
        category = "International"
        country = None
    elif country and country.lower() in ("india", "domestic"):
        category = "Domestic"

    return ListingMetadata(
        country=country or None,
        region=region or None,
        destination=destination or None,
        category=category or None,
        page_title=page_title or None,
    )

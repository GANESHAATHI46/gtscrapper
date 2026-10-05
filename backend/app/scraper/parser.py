import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup

from app.models.package import PackageDetail, ItineraryItem, ListingMetadata
from app.scraper.utils import (
    clean_text,
    extract_price_and_currency,
    generate_slug,
    to_absolute_url,
)

IMAGE_EXCLUDE_KEYWORDS = (
    "logo",
    "icon",
    "avatar",
    "user",
    "payment",
    "facebook",
    "twitter",
    "instagram",
    "youtube",
    "linkedin",
    "tripadvisor",
    "badge",
    "arrow",
    "star",
    "map",
    "marker",
    "svg",
    "footer",
)

def extract_duration_parts(text: Optional[str]) -> tuple[Optional[str], Optional[int], Optional[int]]:
    """Extracts duration string, nights count, and days count."""
    if not text:
        return None, None, None

    # Common patterns: '4 Nights 5 Days', '4N/5D', '4 Nights / 5 Days'
    m = re.search(r'(\d+)\s*(?:Nights?|N)\s*[/&,]?\s*(\d+)\s*(?:Days?|D)', text, re.I)
    if m:
        nights = int(m.group(1))
        days = int(m.group(2))
        return f"{nights} Nights {days} Days", nights, days

    m_days = re.search(r'(\d+)\s*(?:Days?|D)', text, re.I)
    if m_days:
        days = int(m_days.group(1))
        nights = max(0, days - 1)
        return f"{nights} Nights {days} Days", nights, days

    return None, None, None

def parse_package_detail(
    html: str,
    source_url: str,
    listing_meta: Optional[ListingMetadata] = None,
) -> PackageDetail:
    """
    Parses a GT Holidays package detail page into a structured, validated PackageDetail object.
    Strictly adheres to generic selectors with multi-layered fallbacks.
    """
    soup = BeautifulSoup(html, "lxml")

    # Scope package content by removing related services and footers
    for related in soup.select(".st-related-service-new, .st-related-service, footer, #footer, #reviews"):
        related.decompose()

    # 1. Package Name
    raw_name = ""
    h1 = soup.find("h1")
    if h1:
        raw_name = clean_text(h1.get_text())

    if not raw_name:
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            raw_name = clean_text(og_title["content"])

    if not raw_name and soup.title:
        title_clean = clean_text(soup.title.get_text())
        raw_name = re.sub(r'\s*\|\s*GT\s*Holidays.*$', '', title_clean, flags=re.I).strip()

    # Duration extraction (from H1 or feature section)
    duration, nights, days = extract_duration_parts(raw_name)

    # Clean Name: Strip duration suffixes like ' - 4 Nights 5 Days' or ' | 4 Nights 5 Days'
    clean_name = re.sub(r'[\s–—\-|/]+\s*\d+\s*(?:Nights?|N)\s*[/&,]?\s*\d+\s*(?:Days?|D).*$', '', raw_name, flags=re.I).strip()
    if not clean_name:
        clean_name = raw_name or "GT Holidays Tour Package"

    # 2. Slug
    slug = generate_slug(clean_name, source_url)

    # 3. Features: Tour Type, Group Size, Languages, Duration fallback
    tour_type: Optional[str] = None
    group_size: Optional[int] = None
    languages: List[str] = []

    feature_items = soup.select(".st-tour-feature .item")
    for item in feature_items:
        name_p = item.select_one(".name, .gth_name")
        val_p = item.select_one(".value")
        if not name_p or not val_p:
            continue
        feat_name = clean_text(name_p.get_text()).lower()
        feat_val = clean_text(val_p.get_text())

        if "tour type" in feat_name:
            tour_type = feat_val or tour_type
        elif "group size" in feat_name:
            num_m = re.search(r'\d+', feat_val)
            if num_m:
                group_size = int(num_m.group(0))
            elif "unlimited" in feat_val.lower():
                group_size = None
        elif "language" in feat_name:
            if feat_val:
                langs = [clean_text(l) for l in re.split(r'[,/]', feat_val) if clean_text(l)]
                languages.extend(langs)
        elif "duration" in feat_name and not duration:
            duration, nights, days = extract_duration_parts(feat_val)

    if not languages:
        languages = ["English"]
    else:
        # Deduplicate languages
        languages = list(dict.fromkeys(languages))

    # 4. Location and Destinations
    # Priority order:
    # 1. Explicit "Destinations:" field
    # 2. Tour's Location field
    # 3. Structured tour metadata (sub-heading under H1)
    # 4. Listing/Category destination
    destination_str: Optional[str] = None
    destinations: List[str] = []

    # Priority 1: Explicit "Destinations:" field
    dest_label_elem = soup.find(
        lambda el: el.name in ('strong', 'b', 'span', 'p', 'div', 'dt', 'li')
        and bool(re.match(r'^\s*destinations?\s*:', el.get_text().strip(), re.I))
    )
    if dest_label_elem:
        container = dest_label_elem.parent if dest_label_elem.name in ('strong', 'b', 'span') else dest_label_elem
        full_text = container.get_text().replace('\xa0', ' ').strip()
        cleaned_dest = re.sub(r'^\s*destinations?\s*:\s*', '', full_text, flags=re.I).strip()
        if cleaned_dest and len(cleaned_dest) < 200:
            destination_str = cleaned_dest

    # Priority 2: Tour's Location field
    if not destination_str:
        loc_sec = soup.select_one(".st-map-wrapper, .tour-location, div:has(> h2:-soup-contains(\"Tour's Location\"))")
        if loc_sec:
            c_grey = loc_sec.select_one(".c-grey, .desc")
            if c_grey:
                for svg in c_grey.find_all("svg"):
                    svg.decompose()
                loc_text = clean_text(c_grey.get_text())
                if loc_text:
                    destination_str = loc_text

    # Priority 3: Structured tour metadata (sub-heading under H1)
    if not destination_str:
        sub_head = soup.select_one(".st-hotel-header .sub-heading")
        if sub_head:
            for svg in sub_head.find_all("svg"):
                svg.decompose()
            loc_str = clean_text(sub_head.get_text())
            if loc_str and len(loc_str) < 150:
                destination_str = loc_str

    # Priority 4: Listing/Category destination
    if not destination_str and listing_meta and listing_meta.destination:
        destination_str = listing_meta.destination

    # Parse separators: , – — → / or ' - ' (avoiding breaking hyphenated names without spaces)
    if destination_str:
        separator_pattern = r'\s*,\s*|\s*[–—→/]\s*|\s+-\s+'
        raw_parts = re.split(separator_pattern, destination_str)
        seen_dests: set[str] = set()
        for part in raw_parts:
            cleaned_part = clean_text(part)
            if cleaned_part and cleaned_part not in seen_dests and len(cleaned_part) > 1 and not re.match(r'^\d+$', cleaned_part):
                seen_dests.add(cleaned_part)
                destinations.append(cleaned_part)

    location_text = destination_str

    # Country & Region
    country = listing_meta.country if listing_meta else None
    region = listing_meta.region if listing_meta else None

    # Fallback to breadcrumbs inside detail page
    if not country or not region:
        b_items = soup.select(".breadcrumb li, ol.breadcrumb li")
        if len(b_items) >= 3:
            texts = [clean_text(b.get_text()) for b in b_items if clean_text(b.get_text()).lower() not in ("home", "packages", "tour packages")]
            if len(texts) >= 2 and not country:
                country = texts[0]
            if len(texts) >= 3 and not region:
                region = texts[1]

    # 5. Price and Currency
    price_text: Optional[str] = None
    price_selectors = [
        ".hotel-target-book-mobile .price",
        ".hotel-target-book-mobile .price-wrapper",
        ".price-wrapper .price",
        ".service-price .price",
        ".booking-item-price",
        ".st-tour-booking-form .price",
    ]
    for sel in price_selectors:
        p_elem = soup.select_one(sel)
        if p_elem:
            price_text = clean_text(p_elem.get_text())
            if price_text:
                break

    price, currency = extract_price_and_currency(price_text)

    # 6. Overview
    # Must contain only descriptive package content.
    # Priority:
    # 1. Dedicated Overview section (filtering out metadata labels)
    # 2. Dedicated description section / package-specific descriptive text
    # 3. OpenGraph description only if clearly package descriptive
    # Reject overview candidates consisting mainly of:
    # Duration, Destinations, Tour Type, Group Size, Languages, Price.
    # If no real overview exists: overview = None
    overview: Optional[str] = None

    METADATA_LINE_PATTERN = re.compile(
        r'^\s*(?:duration|destinations?|tour\s*type|group\s*size|languages?|price|cost|inclusions?|exclusions?)\s*:',
        re.I
    )

    def is_descriptive_overview(text: Optional[str]) -> bool:
        if not text:
            return False
        clean = clean_text(text)
        if len(clean) < 30:
            return False
        # If it consists largely of metadata labels
        if METADATA_LINE_PATTERN.search(clean):
            lines = [l.strip() for l in re.split(r'[\r\n]+', text) if l.strip()]
            non_meta = [l for l in lines if not METADATA_LINE_PATTERN.match(l)]
            if len(" ".join(non_meta).strip()) < 30:
                return False
        if re.match(r'^(?:duration|destinations?)\s*:', clean, re.I):
            return False
        return True

    # Priority 1: Dedicated Overview section
    overview_elem = soup.select_one(".st-overview .st-description, .st-overview, #heading-package-overview")
    if overview_elem:
        for title_tag in overview_elem.select(".st-section-title, .gth_tourHeadingSing, h2, h3, h4"):
            title_tag.decompose()
        p_texts = []
        for p in overview_elem.find_all(["p", "div"]):
            p_str = clean_text(p.get_text())
            if p_str and not METADATA_LINE_PATTERN.match(p_str) and not re.search(r'^\d+\s*nights?.*days?', p_str, re.I):
                p_texts.append(p_str)
        combined_ov = " ".join(p_texts).strip()
        if is_descriptive_overview(combined_ov):
            overview = combined_ov

    # Priority 2: Dedicated description section / package-specific descriptive text
    if not overview:
        desc_elem = soup.select_one(".gth_itinerary_content p, .package-description p")
        if desc_elem:
            cand = clean_text(desc_elem.get_text())
            if is_descriptive_overview(cand):
                overview = cand

    # Priority 3: OpenGraph description only if clearly package descriptive
    if not overview:
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            cand = clean_text(og_desc["content"])
            if is_descriptive_overview(cand):
                overview = cand

    # 7. Itinerary Parsing
    itinerary: List[ItineraryItem] = []
    # Traveler theme: .st-program-list .item or accordion items
    program_items = soup.select(".st-program-list .item, .st-program .item")
    for idx, item in enumerate(program_items, start=1):
        header = item.select_one(".gth_tabhead, .header h3, .header h4, .header")
        body = item.select_one(".body, .content, p")

        day_num = idx
        title = ""
        description = ""

        if header:
            h_text = clean_text(header.get_text())
            # Extract day number if available
            day_match = re.search(r'Day\s*(\d+)', h_text, re.I)
            if day_match:
                day_num = int(day_match.group(1))
            # Strip Day X: prefix from title
            title = re.sub(r'^(?:Day\s*\d+[\s:\-–—]+)+', '', h_text, flags=re.I).strip()
            if not title:
                title = h_text

        if body:
            description = clean_text(body.get_text())

        if title or description:
            itinerary.append(
                ItineraryItem(
                    day=day_num,
                    title=title,
                    description=description,
                )
            )

    # Fallback itinerary: search for Day 1, Day 2 in paragraphs if list is empty
    if not itinerary:
        paragraphs = soup.find_all(["p", "div"], string=re.compile(r'^Day\s*\d+\s*:', re.I))
        for p in paragraphs:
            text = clean_text(p.get_text())
            m = re.match(r'^Day\s*(\d+)\s*:\s*([^\.\n\-]+)(?:[\.\n\-]+(.*))?$', text, re.I)
            if m:
                itinerary.append(
                    ItineraryItem(
                        day=int(m.group(1)),
                        title=clean_text(m.group(2)),
                        description=clean_text(m.group(3)) if m.group(3) else "",
                    )
                )

    # Sort itinerary by day
    itinerary.sort(key=lambda x: x.day)

    # 8. Inclusions and Exclusions
    included: List[str] = []
    excluded: List[str] = []

    inc_ul = soup.select("ul.include li, .st-include li")
    for li in inc_ul:
        t = clean_text(li.get_text())
        if t:
            included.append(t)

    exc_ul = soup.select("ul.exclude li, .st-exclude li")
    for li in exc_ul:
        t = clean_text(li.get_text())
        if t:
            excluded.append(t)

    # 9. Images & Banner Image
    images: List[str] = []
    img_nodes = soup.select(".st-gallery .fotorama img, .st-gallery img, .fotorama img, .featured-image img")
    for img in img_nodes:
        src = img.get("src") or img.get("data-src") or img.get("data-full")
        if not src:
            continue
        abs_img = to_absolute_url(src, source_url)
        # Check exclusion keywords
        if any(bad in abs_img.lower() for bad in IMAGE_EXCLUDE_KEYWORDS):
            continue
        if abs_img not in images:
            images.append(abs_img)

    banner_image: Optional[str] = None
    if images:
        banner_image = images[0]
    else:
        og_img = soup.find("meta", property="og:image")
        if og_img and og_img.get("content"):
            banner_image = to_absolute_url(og_img["content"], source_url)
            images.append(banner_image)

    # Scraped At timestamp (ISO-8601)
    scraped_at = datetime.now().astimezone().isoformat()

    return PackageDetail(
        name=clean_name,
        slug=slug,
        source_url=source_url,
        country=country,
        region=region,
        destination=destination_str,
        destinations=destinations,
        duration=duration,
        nights=nights,
        days=days,
        tour_type=tour_type,
        group_size=group_size,
        languages=languages,
        price=price,
        currency=currency,
        overview=overview,
        itinerary=itinerary,
        included=included,
        excluded=excluded,
        banner_image=banner_image,
        images=images,
        location=location_text,
        source="GT Holidays",
        scraped_at=scraped_at,
    )

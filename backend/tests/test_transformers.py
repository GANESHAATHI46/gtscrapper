import pytest
from app.transformers.detector import detect_market
from app.transformers.india_transformer import transform_india
from app.transformers.international_transformer import transform_international
from app.transformers.common import (
    safe_slug,
    normalize_destination,
    normalize_language,
    normalize_price,
    deduplicate_urls,
)

# Sample Fixture: Kerala India Scrape
KERALA_RAW_DATA = {
    "source": "GT Holidays",
    "listing_url": "https://www.gtholidays.in/packages/india/south-india/kerala-tour-packages/",
    "page_title": "Kerala Tour Packages",
    "country": "India",
    "region": "South India",
    "destination": "Kerala",
    "total_packages": 2,
    "packages": [
        {
            "name": "Best of Kerala Tour Package",
            "slug": "best-of-kerala-tour-package",
            "source_url": "https://www.gtholidays.in/packages/best-of-kerala/",
            "duration": "5 Nights 6 Days",
            "tour_type": "Daily Tour",
            "languages": ["English"],
            "destination": "Guruvayur – Munnar – Thekkady – Alleppey – Kochi",
            "price": None,
            "banner_image": "https://example.com/kerala-banner.jpg",
            "images": [
                "https://example.com/kerala-1.jpg",
                "https://example.com/kerala-2.jpg",
                "https://example.com/kerala-1.jpg",  # duplicate to test deduplication
            ],
            "itinerary": [
                {"day": 1, "title": "Arrive in Kochi", "description": "Welcome to Kerala"},
                {"day": 2, "title": "Munnar Sightseeing", "description": "Tea plantations"},
                {"day": "invalid", "title": "Bad item", "description": "Should be ignored"},
            ],
        },
        {
            "name": "Wayanad Nature Tour",
            "slug": "wayanad-nature-tour",
            "source_url": "https://www.gtholidays.in/packages/wayanad-nature/",
            "duration": "3 Nights 4 Days",
            "tour_type": "Group Tour",
            "languages": ["English", "Tamil", "Hindi"],
            "destination": "Calicut – Wayanad",
            "price": 14999.0,
            "banner_image": None,
            "images": ["https://example.com/wayanad-1.jpg"],
            "itinerary": [
                {"day": 1, "title": "Arrival in Calicut", "description": "Drive to Wayanad"}
            ],
        },
    ],
}

# Sample Fixture: Thailand International Scrape
THAILAND_RAW_DATA = {
    "source": "GT Holidays",
    "listing_url": "https://www.gtholidays.in/packages/international/asia/thailand-tour-packages/",
    "page_title": "Thailand Tour Packages",
    "country": "Thailand",
    "region": "Asia",
    "destination": "Thailand",
    "total_packages": 2,
    "packages": [
        {
            "name": "Amazing Thailand",
            "slug": "amazing-thailand",
            "source_url": "https://www.gtholidays.in/packages/amazing-thailand/",
            "duration": "4 Nights 5 Days",
            "tour_type": "Daily Tour",
            "languages": ["English"],
            "destination": "Bangkok – Pattaya",
            "price": 28500.0,
            "banner_image": "https://example.com/thai-banner.jpg",
            "images": [
                "https://example.com/thai-1.jpg",
                "https://example.com/thai-2.jpg",
            ],
            "itinerary": [
                {"day": 1, "title": "Arrival in Bangkok", "description": "Transfer to Pattaya"},
                {"day": 2, "title": "Coral Island Tour", "description": "Speedboat ride"},
            ],
        },
        {
            "name": "Phuket & Krabi Escapade",
            "slug": "phuket-krabi-escapade",
            "source_url": "https://www.gtholidays.in/packages/phuket-krabi/",
            "duration": "5 Nights 6 Days",
            "tour_type": "Daily Tour",
            "languages": ["English"],
            "destination": "Phuket – Krabi",
            "price": None,
            "banner_image": None,
            "images": [],
            "itinerary": [],
        },
    ],
}

# Sample Fixture: Dubai International Scrape
DUBAI_RAW_DATA = {
    "source": "GT Holidays",
    "listing_url": "https://www.gtholidays.in/packages/international/middle-east/dubai-tour-packages/",
    "page_title": "Dubai Tour Packages",
    "country": "United Arab Emirates",
    "region": "Middle East",
    "destination": "Dubai",
    "total_packages": 1,
    "packages": [
        {
            "name": "Dazzling Dubai Experience",
            "slug": "dazzling-dubai-experience",
            "source_url": "https://www.gtholidays.in/packages/dazzling-dubai/",
            "duration": "4 Nights 5 Days",
            "tour_type": "Luxury Tour",
            "languages": ["English", "Arabic"],
            "destination": "Dubai – Abu Dhabi",
            "price": 45000.0,
            "banner_image": "https://example.com/dubai-banner.jpg",
            "images": ["https://example.com/dubai-1.jpg"],
            "itinerary": [
                {"day": 1, "title": "Welcome to Dubai", "description": "Dhow cruise dinner"}
            ],
        }
    ],
}


def test_market_detector():
    assert detect_market({"country": "India"}) == "india"
    assert detect_market({"country": "INDIA "}) == "india"
    assert detect_market({"country": "india"}) == "india"
    assert detect_market({"country": "Thailand"}) == "international"
    assert detect_market({"country": "United Arab Emirates"}) == "international"
    assert detect_market({"country": "Singapore"}) == "international"
    assert detect_market({"country": None, "packages": [{"country": "India"}]}) == "india"
    assert detect_market({"country": None, "packages": [{"country": "France"}]}) == "international"


def test_kerala_india_transformation():
    payload = transform_india(KERALA_RAW_DATA)

    # 1. Regions
    assert "regions" in payload
    assert len(payload["regions"]) == 1
    assert payload["regions"][0]["name"] == "South India"
    assert payload["regions"][0]["slug"] == "south-india"

    # 2. Cities
    assert "cities" in payload
    assert len(payload["cities"]) == 1
    assert payload["cities"][0]["region"] == "south-india"
    assert payload["cities"][0]["name"] == "Kerala"
    assert payload["cities"][0]["slug"] == "kerala"

    # 3. Package Types
    assert "package_types" in payload
    type_slugs = {pt["slug"] for pt in payload["package_types"]}
    assert "daily-tour" in type_slugs
    assert "group-tour" in type_slugs
    for pt in payload["package_types"]:
        assert pt["is_active"] is True

    # 4. Packages
    assert "packages" in payload
    assert len(payload["packages"]) == 2

    pkg1 = payload["packages"][0]
    assert pkg1["city"] == "kerala"
    assert pkg1["package_type"] == "daily-tour"
    assert pkg1["name"] == "Best of Kerala Tour Package"
    assert pkg1["slug"] == "best-of-kerala-tour-package"
    assert pkg1["duration"] == "5 Nights 6 Days"
    assert pkg1["language"] == "English"
    assert pkg1["destination"] == "Guruvayur - Munnar - Thekkady - Alleppey - Kochi"
    assert pkg1["price"] is None
    assert pkg1["image"] == "https://example.com/kerala-banner.jpg"
    assert pkg1["is_featured"] is False
    assert pkg1["is_active"] is True

    # Images check
    assert len(pkg1["images"]) == 2  # Deduplicated from 3 to 2
    assert pkg1["images"][0]["image"] == "https://example.com/kerala-1.jpg"
    assert pkg1["images"][0]["is_primary"] is True
    assert pkg1["images"][0]["sort_order"] == 1
    assert pkg1["images"][1]["image"] == "https://example.com/kerala-2.jpg"
    assert pkg1["images"][1]["is_primary"] is False
    assert pkg1["images"][1]["sort_order"] == 2

    # Itinerary check
    assert len(pkg1["itinerary"]) == 2  # Malformed string day record safely omitted
    assert pkg1["itinerary"][0]["day"] == 1
    assert pkg1["itinerary"][0]["title"] == "Arrive in Kochi"
    assert pkg1["itinerary"][1]["day"] == 2
    assert pkg1["itinerary"][1]["title"] == "Munnar Sightseeing"

    # Second package language and banner fallback check
    pkg2 = payload["packages"][1]
    assert pkg2["language"] == "English, Tamil, Hindi"
    assert pkg2["price"] == 14999.0
    assert pkg2["image"] == "https://example.com/wayanad-1.jpg"  # Fallback to first image


def test_thailand_international_transformation():
    payload = transform_international(THAILAND_RAW_DATA)

    # 1. Regions (User correction 3: Preserve scraped region)
    assert "regions" in payload
    assert len(payload["regions"]) == 1
    assert payload["regions"][0]["name"] == "Asia"
    assert payload["regions"][0]["slug"] == "asia"

    # 2. Countries
    assert "countries" in payload
    assert len(payload["countries"]) == 1
    c = payload["countries"][0]
    assert c["region"] == "asia"
    assert c["name"] == "Thailand"
    assert c["slug"] == "thailand"
    assert c["banner_image"] == "https://example.com/thai-banner.jpg"
    assert c["is_active"] is True

    # 3. Package Types
    assert "package_types" in payload
    assert len(payload["package_types"]) >= 1
    pt = payload["package_types"][0]
    assert pt["slug"] == "daily-tour"
    assert "description" in pt

    # 4. Packages
    assert "packages" in payload
    assert len(payload["packages"]) == 2

    pkg1 = payload["packages"][0]
    assert pkg1["country"] == "thailand"
    assert pkg1["package_type"] == "daily-tour"
    assert pkg1["name"] == "Amazing Thailand"
    assert pkg1["slug"] == "amazing-thailand"
    assert pkg1["banner_image"] == "https://example.com/thai-banner.jpg"
    assert pkg1["groups"] == []  # Zero fake data

    # Images
    assert len(pkg1["images"]) == 2
    assert pkg1["images"][0]["alt_text"] == "Amazing Thailand"
    assert pkg1["images"][0]["display_order"] == 1
    assert pkg1["images"][0]["is_active"] is True

    # Itinerary (day -> day_number)
    assert len(pkg1["itinerary"]) == 2
    assert pkg1["itinerary"][0]["day_number"] == 1
    assert pkg1["itinerary"][0]["display_order"] == 1
    assert pkg1["itinerary"][0]["is_active"] is True


def test_dubai_international_transformation():
    payload = transform_international(DUBAI_RAW_DATA)
    assert payload["regions"][0]["name"] == "Middle East"
    assert payload["regions"][0]["slug"] == "middle-east"
    assert payload["countries"][0]["name"] == "United Arab Emirates"
    assert payload["countries"][0]["slug"] == "united-arab-emirates"
    assert payload["packages"][0]["country"] == "united-arab-emirates"
    assert payload["packages"][0]["destination"] == "Dubai - Abu Dhabi"


def test_edge_cases_and_helpers():
    # safe_slug
    assert safe_slug("South India") == "south-india"
    assert safe_slug("Daily Tour") == "daily-tour"
    assert safe_slug("United Arab Emirates") == "united-arab-emirates"
    assert safe_slug("  Kerala--Backwaters--  ") == "kerala-backwaters"
    assert safe_slug(None, fallback="general") == "general"

    # normalize_destination
    assert normalize_destination("Kochi – Munnar — Thekkady") == "Kochi - Munnar - Thekkady"
    assert normalize_destination("Goa – North Goa – South Goa") == "Goa - North Goa - South Goa"

    # normalize_language
    assert normalize_language([]) is None
    assert normalize_language(["English"]) == "English"
    assert normalize_language(["English", "English"]) == "English"
    assert normalize_language(["English", "Tamil"]) == "English, Tamil"

    # normalize_price
    assert normalize_price(None) is None
    assert normalize_price(0) is None
    assert normalize_price("abc") is None
    assert normalize_price("15000") == 15000.0
    assert normalize_price(25000.50) == 25000.50

    # deduplicate_urls
    urls = [
        "https://example.com/1.jpg",
        "",
        None,
        "https://example.com/2.jpg",
        "https://example.com/1.jpg",
    ]
    assert deduplicate_urls(urls) == ["https://example.com/1.jpg", "https://example.com/2.jpg"]

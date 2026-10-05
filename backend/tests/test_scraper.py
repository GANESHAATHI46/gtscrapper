import pytest
from app.scraper.utils import (
    is_valid_url,
    extract_price_and_currency,
    clean_text,
    generate_slug,
)
from app.scraper.parser import extract_duration_parts, parse_package_detail
from app.scraper.metadata import extract_page_metadata
from app.scraper.listing import discover_package_urls

def test_url_validation_ssrf():
    # Valid GT Holidays URLs
    assert is_valid_url("https://www.gtholidays.in/packages/india/north-india/delhi-tour-packages/")
    assert is_valid_url("https://gtholidays.in/package/delhi-edu-tour-package/")
    assert is_valid_url("http://www.gtholidays.in/packages/international/asia/dubai-tour-packages/")

    # Invalid / SSRF targets
    assert not is_valid_url("http://localhost:8000")
    assert not is_valid_url("http://127.0.0.1:5000")
    assert not is_valid_url("http://192.168.1.1")
    assert not is_valid_url("http://169.254.169.254/latest/meta-data/")
    assert not is_valid_url("https://google.com")
    assert not is_valid_url("ftp://gtholidays.in")
    assert not is_valid_url("file:///etc/passwd")

def test_price_and_currency_detection():
    # INR with rupee symbol
    p, c = extract_price_and_currency("₹ 24,999")
    assert p == 24999.0
    assert c == "INR"

    # INR textual
    p, c = extract_price_and_currency("Starts from Rs. 15500 per person")
    assert p == 15500.0
    assert c == "INR"

    # USD
    p, c = extract_price_and_currency("$1,250")
    assert p == 1250.0
    assert c == "USD"

    # AED
    p, c = extract_price_and_currency("AED 3,400")
    assert p == 3400.0
    assert c == "AED"

    # EUR
    p, c = extract_price_and_currency("€ 890")
    assert p == 890.0
    assert c == "EUR"

    # Zero or missing price
    p, c = extract_price_and_currency("0 ₹")
    assert p is None
    assert c == "INR"

    p, c = extract_price_and_currency("Price on Request")
    assert p is None

    p, c = extract_price_and_currency("Super Deal Price")
    assert p is None

    p, c = extract_price_and_currency(None)
    assert p is None
    assert c is None

def test_duration_extraction():
    dur, nights, days = extract_duration_parts("Golden Triangle Tour – 4 Nights 5 Days")
    assert dur == "4 Nights 5 Days"
    assert nights == 4
    assert days == 5

    dur, nights, days = extract_duration_parts("3 Nights / 4 Days Special")
    assert dur == "3 Nights 4 Days"
    assert nights == 3
    assert days == 4

    dur, nights, days = extract_duration_parts("5 Days Tour")
    assert dur == "4 Nights 5 Days"
    assert nights == 4
    assert days == 5

def test_slug_generation():
    assert generate_slug("Golden Triangle Tour Package") == "golden-triangle-tour-package"
    assert generate_slug("", "https://www.gtholidays.in/package/kerala-holiday-package/") == "kerala-holiday-package"

def test_clean_text():
    raw = "  Hello \xa0 World \t \n\n Test  "
    assert clean_text(raw) == "Hello World Test"

import re
import ipaddress
from urllib.parse import urlparse, urljoin
from typing import Optional, Tuple
from slugify import slugify

from app.config import settings

def is_valid_url(url: str) -> bool:
    """Validates URL and guards against SSRF."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        hostname = hostname.lower()

        # Disallow loopback / private IP addresses
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                return False
        except ValueError:
            # Not an IP address string, check domain name
            pass

        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            return False

        # Restrict to allowed domains
        if not any(hostname == d or hostname.endswith("." + d) for d in settings.allowed_domains):
            return False

        return True
    except Exception:
        return False

def clean_text(text: Optional[str]) -> str:
    """Cleans whitespace, HTML entities, and special spaces."""
    if not text:
        return ""
    # Replace non-breaking spaces and irregular whitespace
    text = re.sub(r'[\xa0\u200b\u200e\r\n\t]+', ' ', text)
    # Strip HTML tags if any leaked
    text = re.sub(r'<[^>]+>', ' ', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_price_and_currency(text: Optional[str]) -> Tuple[Optional[float], Optional[str]]:
    """
    Dynamically extracts numeric price and currency code.
    Rules:
    - ₹ / INR -> INR
    - $ / USD -> USD
    - AED -> AED
    - € / EUR -> EUR
    - £ / GBP -> GBP
    - Only positive numbers saved as price.
    - Zero, 'Price on Request', 'Starts From', 'Super Deal' without real number -> price: null.
    - If currency cannot be confidently identified -> currency: null.
    """
    if not text:
        return None, None

    clean_str = clean_text(text)
    lower_str = clean_str.lower()

    # Detect currency
    currency: Optional[str] = None
    if "₹" in clean_str or "inr" in lower_str or "rs." in lower_str or "rs " in lower_str:
        currency = "INR"
    elif "$" in clean_str or "usd" in lower_str:
        currency = "USD"
    elif "aed" in lower_str or "dirham" in lower_str:
        currency = "AED"
    elif "€" in clean_str or "eur" in lower_str:
        currency = "EUR"
    elif "£" in clean_str or "gbp" in lower_str:
        currency = "GBP"

    # Match numeric amounts, removing comma separators e.g. 24,999 or 24999.00
    # Avoid matching 0 or 0.00
    price_candidates = re.findall(r'(?:₹|\$|€|£|AED|INR|Rs\.?)\s*([\d,]+(?:\.\d{1,2})?)', clean_str, re.I)
    if not price_candidates:
        price_candidates = re.findall(r'([\d,]+(?:\.\d{1,2})?)\s*(?:₹|\$|€|£|AED|INR|Rs\.?)', clean_str, re.I)
    if not price_candidates:
        # Generic number candidate if phrase doesn't contain obvious non-price words
        if not any(k in lower_str for k in ["request", "super deal", "contact", "call"]):
            price_candidates = re.findall(r'\b([\d,]+(?:\.\d{1,2})?)\b', clean_str)

    price: Optional[float] = None
    for candidate in price_candidates:
        num_str = candidate.replace(',', '').strip()
        try:
            val = float(num_str)
            if val > 0:  # Must be a positive amount, 0 means no price
                price = val
                break
        except ValueError:
            continue

    return price, currency

def generate_slug(text: str, fallback_url: Optional[str] = None) -> str:
    """Generates a URL-friendly slug from text or fallback URL."""
    if text:
        slug = slugify(text)
        if slug:
            return slug
    if fallback_url:
        path_parts = [p for p in urlparse(fallback_url).path.strip('/').split('/') if p]
        if path_parts:
            return slugify(path_parts[-1])
    return "gt-tour-package"

def to_absolute_url(url: str, base_url: str) -> str:
    """Converts relative URL to absolute URL."""
    if not url:
        return ""
    return urljoin(base_url, url.strip())

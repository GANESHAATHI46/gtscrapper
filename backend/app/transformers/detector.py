from typing import Union, Any
from app.models.package import ScrapeResult

def detect_market(scraped_data: Union[dict, ScrapeResult, Any]) -> str:
    """
    Detects whether the scraped data represents domestic (India) or international tours.
    Returns: "india" or "international".
    Rule:
      normalized country == "india" -> "india"
      else -> "international"
    """
    country = None
    if isinstance(scraped_data, dict):
        country = scraped_data.get("country")
    elif hasattr(scraped_data, "country"):
        country = getattr(scraped_data, "country")
    
    # Fallback to checking first package if root country is somehow missing
    if not country:
        packages = []
        if isinstance(scraped_data, dict):
            packages = scraped_data.get("packages", [])
        elif hasattr(scraped_data, "packages"):
            packages = getattr(scraped_data, "packages", [])
        if packages:
            first_pkg = packages[0]
            if isinstance(first_pkg, dict):
                country = first_pkg.get("country")
            elif hasattr(first_pkg, "country"):
                country = getattr(first_pkg, "country")

    if country and str(country).strip().lower() == "india":
        return "india"
    
    return "international"

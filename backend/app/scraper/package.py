from typing import Optional, Tuple
from app.models.package import PackageDetail, ScrapeError, ListingMetadata
from app.scraper.client import ScraperClient, BotProtectionException
from app.scraper.parser import parse_package_detail

async def scrape_package(
    client: ScraperClient,
    url: str,
    listing_meta: Optional[ListingMetadata] = None,
) -> Tuple[Optional[PackageDetail], Optional[ScrapeError]]:
    """
    Fetches and parses a single package detail page with error isolation.
    Enforces minimum package validity:
    - name is not blank
    - source_url is valid
    Optional fields missing do NOT cause rejection.
    """
    try:
        html = await client.fetch_html(url)
        pkg = parse_package_detail(html, url, listing_meta)
        
        # Minimum validation check
        if not pkg.name or not pkg.name.strip():
            return None, ScrapeError(url=url, error="Extracted package name is blank")
        if not pkg.source_url or not pkg.source_url.startswith("http"):
            return None, ScrapeError(url=url, error="Invalid source_url")
            
        return pkg, None
    except BotProtectionException as e:
        return None, ScrapeError(
            url=url,
            error=e.message,
            type="bot_protection",
            message=e.message,
        )
    except Exception as e:
        return None, ScrapeError(url=url, error=str(e))

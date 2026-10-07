from typing import List, Tuple, Optional, Dict, Any
from app.models.package import PackageDetail, ListingMetadata, ScrapeError
from app.scraper.client import ScraperClient
from app.scraper.listing import discover_package_urls
from app.scraper.metadata import extract_page_metadata
from app.scraper.package import scrape_package

class SourceAdapter:
    """
    Source adapter isolating source-specific extraction details from
    the generic scraping and transformation pipeline.
    """
    adapter_id: str = "gt_holidays"
    display_name: str = "GT Holidays"
    allowed_domains: tuple[str, ...] = ("gtholidays.in", "www.gtholidays.in", "wp-content")

    async def fetch_listing_html(self, client: ScraperClient, url: str) -> str:
        return await client.fetch_html(url)

    def discover_package_urls(self, html: str, base_url: str) -> List[str]:
        return discover_package_urls(html, base_url)

    def extract_page_metadata(self, html: str, url: str) -> ListingMetadata:
        return extract_page_metadata(html, url)

    async def scrape_package(
        self,
        client: ScraperClient,
        url: str,
        listing_meta: Optional[ListingMetadata] = None,
    ) -> Tuple[Optional[PackageDetail], Optional[ScrapeError]]:
        pkg, err = await scrape_package(client, url, listing_meta)
        if pkg:
            # Store internal-only audit metadata
            pkg.internal_metadata = {
                "source_adapter": self.adapter_id,
                "source_url": url,
                "scraped_at": pkg.scraped_at,
                "original_banner_url": pkg.banner_image,
                "original_image_urls": list(pkg.images),
            }
        return pkg, err

default_source_adapter = SourceAdapter()

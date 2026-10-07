import json
import pytest
from pathlib import Path
from app.services.scraper_service import scraper_service

TEST_URLS = [
    "https://www.gtholidays.in/packages/india/north-india/delhi-tour-packages/",
    "https://www.gtholidays.in/packages/india/west-india/goa-tour-packages/",
]

@pytest.mark.asyncio
async def test_live_scrape_multiple_destinations():
    results = []
    
    for url in TEST_URLS:
        job_id = scraper_service.create_job(url)
        await scraper_service.run_scrape_job(job_id)
        
        status = scraper_service.get_job_status(job_id)
        result = scraper_service.get_job_result(job_id)
        
        assert status is not None
        assert status.status in ("completed", "completed_with_errors")
        assert result is not None
        
        # 1. Package Count Assertions (Correction 1: NEVER hardcode fixed number)
        discovered_count = result.total_packages
        assert discovered_count > 0, f"No packages discovered for {url}"
        
        # Unique source URLs check
        unique_urls = list({p.source_url for p in result.packages})
        assert len(result.packages) == len(unique_urls), "Duplicate package source_urls found!"
        
        # Count consistency
        assert result.success_count + result.failed_count == discovered_count
        assert len(result.packages) == result.success_count
        
        # 2. Output File Verification (Dual Export: Raw and Django)
        assert status.output_file is not None
        output_path = Path(status.output_file)
        assert output_path.exists(), f"Raw export file does not exist: {output_path}"
        assert "-tour-packages-" in output_path.name

        assert status.django_output_file is not None
        django_path = Path(status.django_output_file)
        assert django_path.exists(), f"Django export file does not exist: {django_path}"
        assert "-tour-packages-django-" in django_path.name
        
        # 3. JSON Validity
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "source" not in data or "GT Holidays" not in str(data.get("source"))
            assert data["total_packages"] == discovered_count
            assert len(data["packages"]) == result.success_count
            
        # 4. Content Verification on Scraped Packages
        for pkg in result.packages:
            # Data quality assertions (Correction 4)
            assert pkg.name and len(pkg.name.strip()) > 0
            assert pkg.source_url.startswith("http")
            assert isinstance(pkg.destinations, list)
            assert isinstance(pkg.itinerary, list)
            assert isinstance(pkg.images, list)

            # Overview must NOT be metadata (Correction 2)
            if pkg.overview:
                assert "Duration :" not in pkg.overview
                assert "Destinations :" not in pkg.overview

            # Currency validation: do not invent currency
            if pkg.price is None and pkg.currency:
                assert pkg.currency in ("INR", "USD", "AED", "EUR", "GBP")

            # Ordered itinerary check
            if pkg.itinerary:
                days = [item.day for item in pkg.itinerary]
                assert days == sorted(days), f"Itinerary days not sorted for {pkg.name}: {days}"

            # Absolute image URLs check
            for img in pkg.images:
                assert img.startswith("http://") or img.startswith("https://"), f"Image URL is not absolute: {img}"
            if pkg.banner_image:
                assert pkg.banner_image.startswith("http://") or pkg.banner_image.startswith("https://")

        # Goa-specific data quality checks (Correction 1 & 2)
        if "goa" in url.lower():
            goa_pkg = next((p for p in result.packages if "goa-tour-package" in p.source_url), None)
            if goa_pkg:
                assert "Goa" in goa_pkg.destinations
                assert "North Goa" in goa_pkg.destinations
                assert "South Goa" in goa_pkg.destinations
                assert "Goa – North Goa – South Goa" in (goa_pkg.destination or "")
                assert "Duration :" not in (goa_pkg.overview or "")
                assert "Destinations :" not in (goa_pkg.overview or "")
                
        results.append((result, output_path))
        
    # Verify metadata and filenames change dynamically between destinations
    res1, file1 = results[0]
    res2, file2 = results[1]
    
    assert res1.listing_url != res2.listing_url
    assert file1.name != file2.name, "Output filenames must be dynamically different"
    assert res1.destination != res2.destination, "Destinations must be dynamically detected differently"

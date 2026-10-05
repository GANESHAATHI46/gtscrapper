import json
import pytest
from pathlib import Path
from app.services.scraper_service import scraper_service
from app.models.focus import InternationalBulkImportPayload

THAILAND_URL = "https://www.gtholidays.in/packages/international/asia/thailand-tour-packages/"

@pytest.mark.asyncio
async def test_international_acceptance_flow():
    """
    International Acceptance Test:
    Tests the complete pipeline on an international listing:
    analyzing -> discovering -> scraping -> exporting raw -> market detection (international) ->
    transforming -> exporting django -> completed.
    Validates dual JSON output and exact Django International bulk-import contract.
    """
    job_id = scraper_service.create_job(THAILAND_URL)

    # 1. Execute scrape job
    await scraper_service.run_scrape_job(job_id)

    status = scraper_service.get_job_status(job_id)
    assert status is not None
    assert status.status in ("completed", "completed_with_errors")
    assert status.market == "international"
    assert status.django_schema == "/bulk-import/international/"

    # 2. Verify Output Files
    assert status.output_file is not None
    assert Path(status.output_file).exists(), f"Raw output file missing: {status.output_file}"
    assert "-tour-packages-" in status.output_file

    assert status.django_output_file is not None
    assert Path(status.django_output_file).exists(), f"Django output file missing: {status.django_output_file}"
    assert "-tour-packages-django-" in status.django_output_file

    # 3. Verify Django-Compatible Transformed JSON Contract
    django_payload = scraper_service.get_job_django_payload(job_id)
    assert django_payload is not None
    assert "regions" in django_payload
    assert "countries" in django_payload
    assert "package_types" in django_payload
    assert "packages" in django_payload

    # Pydantic schema validation
    validated = InternationalBulkImportPayload.model_validate(django_payload)
    assert validated is not None

    # Region verification (Preserved scraped region)
    assert len(django_payload["regions"]) >= 1
    assert django_payload["regions"][0]["slug"] == "asia"

    # Country verification
    assert len(django_payload["countries"]) >= 1
    country_slug = django_payload["countries"][0]["slug"]
    assert country_slug == "thailand"

    # Package verification
    assert len(django_payload["packages"]) > 0
    for pkg in django_payload["packages"]:
        assert pkg["country"] == country_slug
        assert pkg["package_type"] is not None
        assert pkg["name"] and len(pkg["name"]) > 0
        assert pkg["slug"] and len(pkg["slug"]) > 0
        assert pkg["is_active"] is True
        assert pkg["is_featured"] is False
        assert pkg["groups"] == []  # No fabricated groups or seats

        # Images format
        assert isinstance(pkg["images"], list)
        for idx, img in enumerate(pkg["images"]):
            assert "image" in img
            assert img["image"].startswith("http")
            assert img["display_order"] == idx + 1
            assert img["is_active"] is True
            assert "alt_text" in img

        # Itinerary format
        assert isinstance(pkg["itinerary"], list)
        for itin in pkg["itinerary"]:
            assert isinstance(itin["day_number"], int)
            assert itin["day_number"] > 0
            assert isinstance(itin["display_order"], int)
            assert itin["is_active"] is True
            assert isinstance(itin["title"], str)
            assert isinstance(itin["description"], str)

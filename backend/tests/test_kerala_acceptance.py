import json
import pytest
from pathlib import Path
from app.services.scraper_service import scraper_service
from app.models.focus import IndiaBulkImportPayload

KERALA_URL = "https://www.gtholidays.in/packages/india/south-india/kerala-tour-packages/"

@pytest.mark.asyncio
async def test_kerala_acceptance_flow():
    """
    Kerala Acceptance Test:
    Tests the complete pipeline:
    analyzing -> discovering -> scraping -> exporting raw -> market detection -> transforming -> exporting django -> completed.
    Validates dual JSON output and exact Django India bulk-import contract.
    """
    job_id = scraper_service.create_job(KERALA_URL)

    # 1. Execute scrape job
    await scraper_service.run_scrape_job(job_id)

    status = scraper_service.get_job_status(job_id)
    assert status is not None
    assert status.status in ("completed", "completed_with_errors")
    assert status.market == "india"
    assert status.django_schema == "/bulk-import/india/"

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
    assert "cities" in django_payload
    assert "package_types" in django_payload
    assert "packages" in django_payload

    # Pydantic schema validation
    validated = IndiaBulkImportPayload.model_validate(django_payload)
    assert validated is not None

    # Region verification
    assert len(django_payload["regions"]) == 1
    assert django_payload["regions"][0]["slug"] == "south-india"
    assert django_payload["regions"][0]["name"] == "South India"

    # City verification (Kerala category grouping)
    assert len(django_payload["cities"]) == 1
    assert django_payload["cities"][0]["slug"] == "kerala"
    assert django_payload["cities"][0]["name"] == "Kerala"
    assert django_payload["cities"][0]["region"] == "south-india"

    # Package verification
    assert len(django_payload["packages"]) > 0
    for pkg in django_payload["packages"]:
        assert pkg["city"] == "kerala"
        assert pkg["package_type"] is not None
        assert pkg["name"] and len(pkg["name"]) > 0
        assert pkg["slug"] and len(pkg["slug"]) > 0
        assert pkg["is_active"] is True
        assert pkg["is_featured"] is False

        # Language string format (not list)
        if pkg["language"]:
            assert isinstance(pkg["language"], str)

        # Image mapping format
        assert isinstance(pkg["images"], list)
        for idx, img in enumerate(pkg["images"]):
            assert "image" in img
            assert img["image"].startswith("http")
            assert img["sort_order"] == idx + 1
            if idx == 0:
                assert img["is_primary"] is True
            else:
                assert img["is_primary"] is False

        # Itinerary format
        assert isinstance(pkg["itinerary"], list)
        for itin in pkg["itinerary"]:
            assert isinstance(itin["day"], int)
            assert itin["day"] > 0
            assert isinstance(itin["title"], str)
            assert isinstance(itin["description"], str)

import json
import pytest
import httpx
from pathlib import Path

from app.config import settings
from app.models.package import (
    PackageDetail,
    ScrapeResult,
    ItineraryItem,
    ImageDownloadSummary,
)
from app.services.image_downloader import (
    ImageDownloaderService,
    is_valid_image_url,
    detect_image_extension,
)
from app.transformers import transform_india, transform_international

# Sample valid image byte payloads
JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100
PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 100
WEBP_BYTES = b"RIFF\x20\x00\x00\x00WEBPVP8 " + b"\x00" * 100
GIF_BYTES = b"GIF89a" + b"\x00" * 50

# 1. URL & SSRF Validation Tests
def test_image_url_validation_ssrf():
    # Valid GT Holidays URLs
    assert is_valid_image_url("https://www.gtholidays.in/wp-content/uploads/2023/delhi.jpg")
    assert is_valid_image_url("https://gtholidays.in/images/kerala.png")
    assert is_valid_image_url("http://www.gtholidays.in/banner.webp")

    # SSRF & Localhost targets
    assert not is_valid_image_url("http://localhost:8000/image.jpg")
    assert not is_valid_image_url("http://127.0.0.1:8080/image.jpg")
    assert not is_valid_image_url("http://0.0.0.0/test.png")
    assert not is_valid_image_url("http://[::1]/test.png")
    assert not is_valid_image_url("http://192.168.1.1/test.jpg")
    assert not is_valid_image_url("http://10.0.0.5/test.jpg")
    assert not is_valid_image_url("http://172.16.0.1/test.jpg")
    assert not is_valid_image_url("http://169.254.169.254/latest/meta-data/")

    # Disallowed domains & schemes
    assert not is_valid_image_url("https://malicious-external-site.com/image.jpg")
    assert not is_valid_image_url("ftp://gtholidays.in/test.jpg")
    assert not is_valid_image_url("file:///etc/passwd")
    assert not is_valid_image_url("")
    assert not is_valid_image_url(None)

# 2. Magic Bytes & Image Extension Detection Tests
def test_detect_image_extension():
    assert detect_image_extension(JPEG_BYTES) == ".jpg"
    assert detect_image_extension(PNG_BYTES) == ".png"
    assert detect_image_extension(WEBP_BYTES) == ".webp"
    assert detect_image_extension(GIF_BYTES) == ".gif"

    # Rejection of HTML error pages with HTTP 200
    html_page = b"<!DOCTYPE html><html><head><title>404 Not Found</title></head><body>Error</body></html>"
    assert detect_image_extension(html_page) is None

    # Empty bytes
    assert detect_image_extension(b"") is None

    # Fallback to Content-Type if non-HTML
    assert detect_image_extension(b"SOMEBYTES", content_type="image/jpeg") == ".jpg"
    assert detect_image_extension(b"SOMEBYTES", content_type="image/png") == ".png"

# 3. Path Traversal & Sanitization Tests
def test_path_traversal_sanitization(tmp_path: Path):
    service = ImageDownloaderService(storage_root=tmp_path)
    
    # Normal slug
    target_dir, stem = service.sanitize_path("kerala-luxury-package", "banner")
    assert target_dir.name == "kerala-luxury-package"
    assert stem == "banner"
    assert target_dir.resolve().is_relative_to(tmp_path.resolve())

    # Traversal attempts sanitized by safe_slug
    target_dir, stem = service.sanitize_path("../../../etc/passwd", "../../../malicious_stem")
    assert ".." not in str(target_dir)
    assert target_dir.resolve().is_relative_to(tmp_path.resolve())
    assert stem == "malicious_stem"

# 4. Successful Banner and Gallery Download (Mocked HTTP)
@pytest.mark.asyncio
async def test_successful_image_download_flow(tmp_path: Path):
    service = ImageDownloaderService(storage_root=tmp_path, retry_backoff=1.01)

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "banner" in url_str:
            return httpx.Response(200, headers={"Content-Type": "image/jpeg"}, content=JPEG_BYTES)
        elif "gallery1" in url_str:
            return httpx.Response(200, headers={"Content-Type": "image/png"}, content=PNG_BYTES)
        elif "gallery2" in url_str:
            return httpx.Response(200, headers={"Content-Type": "image/webp"}, content=WEBP_BYTES)
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    pkg = PackageDetail(
        name="Splendid Kerala Holiday",
        slug="splendid-kerala-holiday",
        source_url="https://www.gtholidays.in/package/kerala/",
        destination="Kerala",
        banner_image="https://www.gtholidays.in/wp-content/banner.jpg",
        images=[
            "https://www.gtholidays.in/wp-content/gallery1.png",
            "https://www.gtholidays.in/wp-content/gallery2.webp",
        ],
        scraped_at="2026-10-05T12:00:00Z",
    )

    import asyncio
    semaphore = asyncio.Semaphore(5)
    updated_pkg = await service.download_package_images(pkg, semaphore=semaphore, client=mock_client)

    # Verify model fields updated
    assert updated_pkg.banner_image_local == "splendid-kerala-holiday/banner.jpg"
    assert len(updated_pkg.images_local) == 2
    assert updated_pkg.images_local[0] == "splendid-kerala-holiday/image_001.png"
    assert updated_pkg.images_local[1] == "splendid-kerala-holiday/image_002.webp"
    assert updated_pkg.image_download_status == "completed"
    assert updated_pkg.image_download_summary.total == 3
    assert updated_pkg.image_download_summary.downloaded == 3
    assert updated_pkg.image_download_summary.failed == 0

    # Verify actual files written to disk
    assert (tmp_path / "splendid-kerala-holiday" / "banner.jpg").exists()
    assert (tmp_path / "splendid-kerala-holiday" / "image_001.png").exists()
    assert (tmp_path / "splendid-kerala-holiday" / "image_002.webp").exists()

    await mock_client.aclose()

# 5. Duplicate URL Deduplication
@pytest.mark.asyncio
async def test_duplicate_url_deduplication(tmp_path: Path):
    service = ImageDownloaderService(storage_root=tmp_path)

    call_count = 0
    async def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, headers={"Content-Type": "image/jpeg"}, content=JPEG_BYTES)

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    pkg = PackageDetail(
        name="Goa Beach Vacation",
        slug="goa-beach-vacation",
        source_url="https://www.gtholidays.in/package/goa/",
        banner_image="https://www.gtholidays.in/wp-content/same-photo.jpg",
        images=[
            "https://www.gtholidays.in/wp-content/same-photo.jpg",  # duplicate URL
        ],
        scraped_at="2026-10-05T12:00:00Z",
    )

    import asyncio
    semaphore = asyncio.Semaphore(2)
    updated_pkg = await service.download_package_images(pkg, semaphore=semaphore, client=mock_client)

    # Only 1 network call should occur
    assert call_count == 1
    assert updated_pkg.banner_image_local == "goa-beach-vacation/banner.jpg"
    assert updated_pkg.images_local == ["goa-beach-vacation/banner.jpg"]
    assert updated_pkg.image_download_summary.downloaded == 1
    assert updated_pkg.image_download_summary.skipped == 1

    await mock_client.aclose()

# 6. HTTP 404 Permanent Error Handling (No Infinite Retries)
@pytest.mark.asyncio
async def test_http_404_permanent_error_no_retry(tmp_path: Path):
    service = ImageDownloaderService(storage_root=tmp_path, max_retries=3)

    attempts = 0
    async def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    res = await service.download_image(
        url="https://www.gtholidays.in/missing.jpg",
        package_slug="test-slug",
        filename_stem="banner",
        client=mock_client,
    )

    assert not res.success
    assert res.status_code == 404
    # Attempted exactly once (no retry on 404)
    assert attempts == 1
    assert "Permanent HTTP error: 404" in res.error

    await mock_client.aclose()

# 7. Transient HTTP 429 Rate Limit with Retry-After and Success
@pytest.mark.asyncio
async def test_http_429_retry_success(tmp_path: Path):
    service = ImageDownloaderService(storage_root=tmp_path, max_retries=3, retry_backoff=1.01)

    attempts = 0
    async def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0.01"}, text="Too Many Requests")
        return httpx.Response(200, headers={"Content-Type": "image/jpeg"}, content=JPEG_BYTES)

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    res = await service.download_image(
        url="https://www.gtholidays.in/rate-limited.jpg",
        package_slug="test-slug",
        filename_stem="banner",
        client=mock_client,
    )

    assert res.success
    assert attempts == 2
    assert res.relative_path == "test-slug/banner.jpg"

    await mock_client.aclose()

# 8. Maximum Size Threshold Enforcement
@pytest.mark.asyncio
async def test_max_size_enforcement(tmp_path: Path):
    # Set limit to 500 bytes
    service = ImageDownloaderService(storage_root=tmp_path, max_size_bytes=500)

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        # Return 5000 bytes (exceeds 500)
        return httpx.Response(200, headers={"Content-Type": "image/jpeg"}, content=b"A" * 5000)

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    res = await service.download_image(
        url="https://www.gtholidays.in/large.jpg",
        package_slug="test-slug",
        filename_stem="banner",
        client=mock_client,
    )

    assert not res.success
    assert "exceeded maximum size limit" in res.error
    # Temp file must be cleaned up
    assert not (tmp_path / "test-slug" / "banner.tmp").exists()

    await mock_client.aclose()

# 9. HTML Error Page Returned with 200 OK Rejected
@pytest.mark.asyncio
async def test_html_error_page_rejected(tmp_path: Path):
    service = ImageDownloaderService(storage_root=tmp_path)

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html"},
            content=b"<!DOCTYPE html><html><body>Error</body></html>"
        )

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    res = await service.download_image(
        url="https://www.gtholidays.in/fake-image.jpg",
        package_slug="test-slug",
        filename_stem="banner",
        client=mock_client,
    )

    assert not res.success
    assert "Invalid image format" in res.error

    await mock_client.aclose()

# 10. Partial Failure Preserves Package Data
@pytest.mark.asyncio
async def test_partial_failure_preserves_package(tmp_path: Path):
    service = ImageDownloaderService(storage_root=tmp_path)

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        if "good" in str(request.url):
            return httpx.Response(200, headers={"Content-Type": "image/jpeg"}, content=JPEG_BYTES)
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    pkg = PackageDetail(
        name="Kashmir Paradise",
        slug="kashmir-paradise",
        source_url="https://www.gtholidays.in/package/kashmir/",
        duration="5 Days / 4 Nights",
        price=35000.0,
        currency="INR",
        banner_image="https://www.gtholidays.in/good-banner.jpg",
        images=[
            "https://www.gtholidays.in/broken-image.jpg",
        ],
        itinerary=[
            ItineraryItem(day=1, title="Arrival in Srinagar", description="Shikara ride"),
        ],
        scraped_at="2026-10-05T12:00:00Z",
    )

    import asyncio
    semaphore = asyncio.Semaphore(2)
    updated_pkg = await service.download_package_images(pkg, semaphore=semaphore, client=mock_client)

    # Verify status is partial
    assert updated_pkg.image_download_status == "partial"
    assert updated_pkg.banner_image_local == "kashmir-paradise/banner.jpg"
    assert updated_pkg.images_local == [None]
    assert len(updated_pkg.image_errors) == 1
    assert "broken-image.jpg" in updated_pkg.image_errors[0].url

    # Critical requirement: Package data is completely preserved
    assert updated_pkg.name == "Kashmir Paradise"
    assert updated_pkg.price == 35000.0
    assert len(updated_pkg.itinerary) == 1
    assert updated_pkg.itinerary[0].title == "Arrival in Srinagar"

    await mock_client.aclose()

# 11. Unicode (Tamil & English) and JSON Serialization
def test_unicode_and_json_serialization(tmp_path: Path):
    result = ScrapeResult(
        source="GT Holidays",
        listing_url="https://www.gtholidays.in/packages/india/south-india/kerala-tour-packages/",
        page_title="கேரளா சுற்றுலா பேக்கேஜ்கள் - Kerala Tour Packages",
        country="India",
        region="South India",
        destination="கேரளா - Munnar",
        total_packages=1,
        success_count=1,
        failed_count=0,
        scraped_at="2026-10-05T12:00:00Z",
        image_download_status="completed",
        image_download_summary=ImageDownloadSummary(total=2, downloaded=2, failed=0, skipped=0),
        packages=[
            PackageDetail(
                name="மூணார் குடும்ப சுற்றுலா - Munnar Family Tour",
                slug="munnar-family-tour",
                source_url="https://www.gtholidays.in/package/munnar/",
                banner_image="https://www.gtholidays.in/banner.jpg",
                banner_image_local="munnar-family-tour/banner.jpg",
                images=["https://www.gtholidays.in/img1.jpg"],
                images_local=["munnar-family-tour/image_001.jpg"],
                image_download_status="completed",
                image_download_summary=ImageDownloadSummary(total=2, downloaded=2, failed=0, skipped=0),
                scraped_at="2026-10-05T12:00:00Z",
            )
        ]
    )

    out_file = tmp_path / "unicode_test.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    with open(out_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert "கேரளா சுற்றுலா" in loaded["page_title"]
    assert loaded["packages"][0]["banner_image_local"] == "munnar-family-tour/banner.jpg"
    assert loaded["packages"][0]["images_local"] == ["munnar-family-tour/image_001.jpg"]

# 12. Django Bulk-Import Transformer Compatibility
def test_django_transformers_with_local_images():
    scraped = ScrapeResult(
        source="GT Holidays",
        listing_url="https://www.gtholidays.in/packages/india/south-india/kerala-tour-packages/",
        country="India",
        region="South India",
        destination="Kerala",
        total_packages=1,
        success_count=1,
        failed_count=0,
        scraped_at="2026-10-05T12:00:00Z",
        packages=[
            PackageDetail(
                name="Kerala Backwaters Tour",
                slug="kerala-backwaters-tour",
                source_url="https://www.gtholidays.in/package/kerala-backwaters/",
                banner_image="https://www.gtholidays.in/wp-content/banner.jpg",
                banner_image_local="kerala-backwaters-tour/banner.jpg",
                images=["https://www.gtholidays.in/wp-content/gallery1.jpg"],
                images_local=["kerala-backwaters-tour/image_001.jpg"],
                image_download_status="completed",
                itinerary=[ItineraryItem(day=1, title="Day 1", description="Cochin arrival")],
                scraped_at="2026-10-05T12:00:00Z",
            )
        ]
    )

    # 1. India Transformer Contract: Original URLs are preserved in public contract
    india_payload = transform_india(scraped)
    assert len(india_payload["packages"]) == 1
    pkg = india_payload["packages"][0]
    assert pkg["image"] == "https://www.gtholidays.in/wp-content/banner.jpg"
    assert pkg["images"][0]["image"] == "https://www.gtholidays.in/wp-content/gallery1.jpg"

    # 2. International Transformer Contract
    intl_scraped = ScrapeResult(
        source="GT Holidays",
        listing_url="https://www.gtholidays.in/packages/international/asia/thailand-tour-packages/",
        country="Thailand",
        region="Asia",
        destination="Bangkok",
        total_packages=1,
        success_count=1,
        failed_count=0,
        scraped_at="2026-10-05T12:00:00Z",
        packages=[
            PackageDetail(
                name="Bangkok Pattaya Special",
                slug="bangkok-pattaya-special",
                source_url="https://www.gtholidays.in/package/bangkok-pattaya/",
                banner_image="https://www.gtholidays.in/wp-content/bangkok.jpg",
                banner_image_local="bangkok-pattaya-special/banner.jpg",
                images=["https://www.gtholidays.in/wp-content/pattaya.jpg"],
                images_local=["bangkok-pattaya-special/image_001.jpg"],
                image_download_status="completed",
                itinerary=[ItineraryItem(day=1, title="Day 1", description="Bangkok arrival")],
                scraped_at="2026-10-05T12:00:00Z",
            )
        ]
    )

    intl_payload = transform_international(intl_scraped)
    assert len(intl_payload["packages"]) == 1
    intl_pkg = intl_payload["packages"][0]
    assert intl_pkg["banner_image"] == "https://www.gtholidays.in/wp-content/bangkok.jpg"
    assert intl_pkg["images"][0]["image"] == "https://www.gtholidays.in/wp-content/pattaya.jpg"

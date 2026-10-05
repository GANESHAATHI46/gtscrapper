import os
import re
import ipaddress
import asyncio
import logging
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, List, Dict, Tuple, Callable

import httpx
from app.config import settings
from app.models.package import (
    PackageDetail,
    ImageDownloadSummary,
    ImageErrorDetail,
)
from app.transformers.common import safe_slug

logger = logging.getLogger(__name__)

# Magic byte signatures for image formats
MAGIC_NUMBERS: List[Tuple[bytes, str]] = [
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"GIF87a", ".gif"),
    (b"GIF89a", ".gif"),
]

def is_valid_image_url(url: str, allowed_domains: Optional[tuple[str, ...]] = None) -> bool:
    """
    Validates image URL and guards against SSRF, private IPs, and non-allowed domains.
    """
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

        # Disallow loopback / private IP addresses (SSRF defense)
        try:
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                return False
        except ValueError:
            # Domain name, check hostname
            pass

        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            return False

        domains = allowed_domains if allowed_domains is not None else settings.image_allowed_domains
        if not any(hostname == d or hostname.endswith("." + d) or d in hostname for d in domains):
            return False

        return True
    except Exception:
        return False

def detect_image_extension(header_bytes: bytes, content_type: Optional[str] = None) -> Optional[str]:
    """
    Detects actual image format by inspecting magic bytes.
    Rejects HTML error responses with HTTP 200.
    Never defaults to .jpg blindly.
    """
    if not header_bytes:
        return None

    # Check for HTML responses returned with 200 OK
    lower_head = header_bytes[:256].lower()
    if (
        b"<!doctype html" in lower_head
        or b"<html" in lower_head
        or b"<head" in lower_head
        or b"<body" in lower_head
        or b"<title>" in lower_head
    ):
        return None

    # WebP check: RIFF....WEBP
    if header_bytes.startswith(b"RIFF") and len(header_bytes) >= 12 and header_bytes[8:12] == b"WEBP":
        return ".webp"

    # AVIF check: ftyp at offset 4 with avif/avis at offset 8
    if len(header_bytes) >= 12 and header_bytes[4:8] == b"ftyp" and header_bytes[8:12] in (b"avif", b"avis"):
        return ".avif"

    # Standard magic numbers (JPEG, PNG, GIF)
    for magic, ext in MAGIC_NUMBERS:
        if header_bytes.startswith(magic):
            return ext

    # SVG check: XML containing <svg
    if b"<svg" in lower_head:
        return ".svg"

    # Fallback to Content-Type header only if not HTML
    if content_type:
        ct = content_type.lower().split(";")[0].strip()
        ct_map = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
            "image/avif": ".avif",
            "image/svg+xml": ".svg",
        }
        if ct in ct_map:
            return ct_map[ct]

    return None

class ImageDownloadResult:
    def __init__(
        self,
        url: str,
        success: bool,
        relative_path: Optional[str] = None,
        skipped: bool = False,
        error: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        self.url = url
        self.success = success
        self.relative_path = relative_path
        self.skipped = skipped
        self.error = error
        self.status_code = status_code

class ImageDownloaderService:
    def __init__(
        self,
        storage_root: Optional[Path] = None,
        concurrency: int = settings.image_concurrency,
        timeout: float = settings.image_request_timeout,
        max_size_bytes: int = settings.image_max_size_bytes,
        max_retries: int = settings.image_max_retries,
        retry_backoff: float = settings.image_retry_backoff_factor,
        allowed_domains: tuple[str, ...] = settings.image_allowed_domains,
    ):
        self.storage_root = storage_root or settings.storage_root
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self.concurrency = concurrency
        self.timeout = timeout
        self.max_size_bytes = max_size_bytes
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.allowed_domains = allowed_domains
        self._url_cache: Dict[str, str] = {}
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
            self._client = httpx.AsyncClient(
                headers={
                    "User-Agent": settings.user_agent,
                    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Connection": "keep-alive",
                },
                timeout=self.timeout,
                limits=limits,
                follow_redirects=True,
                http2=True,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def sanitize_path(self, package_slug: str, filename_stem: str) -> Tuple[Path, str]:
        """
        Guards against directory traversal and ensures sanitized relative and absolute paths.
        """
        clean_pkg = safe_slug(package_slug, fallback="package")
        clean_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", filename_stem).strip("_") or "image"
        
        target_dir = self.storage_root / clean_pkg
        target_dir.mkdir(parents=True, exist_ok=True)

        # Verification against traversal
        resolved_dir = target_dir.resolve()
        resolved_root = self.storage_root.resolve()
        if not str(resolved_dir).startswith(str(resolved_root)):
            raise ValueError(f"Directory traversal detected for package slug: {package_slug}")

        return target_dir, clean_stem

    async def download_image(
        self,
        url: str,
        package_slug: str,
        filename_stem: str,
        client: Optional[httpx.AsyncClient] = None,
    ) -> ImageDownloadResult:
        """
        Downloads a single image using streaming to disk, content & size validation,
        exponential backoff for transient errors, and atomic file replacement.
        """
        if not is_valid_image_url(url, self.allowed_domains):
            return ImageDownloadResult(
                url=url,
                success=False,
                error="Invalid or disallowed image URL (SSRF protection / invalid scheme)",
            )

        # Check job session URL cache (avoid downloading duplicate URLs)
        clean_pkg = safe_slug(package_slug, fallback="package")
        if url in self._url_cache:
            return ImageDownloadResult(
                url=url,
                success=True,
                relative_path=self._url_cache[url],
                skipped=True,
            )

        try:
            target_dir, clean_stem = self.sanitize_path(package_slug, filename_stem)
        except ValueError as e:
            return ImageDownloadResult(url=url, success=False, error=str(e))

        # Check if file with this stem and any valid image extension already exists
        for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".svg"):
            existing = target_dir / f"{clean_stem}{ext}"
            if existing.exists() and existing.stat().st_size > 0:
                rel_path = f"{clean_pkg}/{existing.name}"
                self._url_cache[url] = rel_path
                return ImageDownloadResult(
                    url=url,
                    success=True,
                    relative_path=rel_path,
                    skipped=True,
                )

        http_client = client or (await self.get_client())
        temp_file = target_dir / f"{clean_stem}.tmp"

        attempt = 0
        last_error: Optional[str] = None
        status_code: Optional[int] = None

        while attempt < self.max_retries:
            attempt += 1
            try:
                if temp_file.exists():
                    temp_file.unlink(missing_ok=True)

                async with http_client.stream("GET", url) as response:
                    status_code = response.status_code
                    
                    # Validate redirect safety
                    final_url = str(response.url)
                    if not is_valid_image_url(final_url, self.allowed_domains):
                        return ImageDownloadResult(
                            url=url,
                            success=False,
                            status_code=status_code,
                            error=f"Redirected to disallowed or unsafe destination: {final_url}",
                        )

                    # Permanent client errors - do not retry
                    if status_code in (400, 401, 403, 404, 410):
                        return ImageDownloadResult(
                            url=url,
                            success=False,
                            status_code=status_code,
                            error=f"Permanent HTTP error: {status_code}",
                        )

                    # Transient rate limits or server errors
                    if status_code in (429, 500, 502, 503, 504):
                        retry_after = response.headers.get("Retry-After")
                        delay = self.retry_backoff ** attempt
                        if retry_after:
                            try:
                                delay = max(delay, float(retry_after))
                            except ValueError:
                                pass
                        if attempt < self.max_retries:
                            logger.warning(
                                "Transient HTTP %s for %s. Retrying in %.2fs (attempt %d/%d)",
                                status_code, url, delay, attempt, self.max_retries
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            return ImageDownloadResult(
                                url=url,
                                success=False,
                                status_code=status_code,
                                error=f"Max retries exceeded for HTTP {status_code}",
                            )

                    if status_code != 200:
                        return ImageDownloadResult(
                            url=url,
                            success=False,
                            status_code=status_code,
                            error=f"Unexpected HTTP status: {status_code}",
                        )

                    # Stream chunks to temp file with size threshold enforcement
                    total_bytes = 0
                    content_type = response.headers.get("content-type")

                    with open(temp_file, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            total_bytes += len(chunk)
                            if total_bytes > self.max_size_bytes:
                                raise ValueError(
                                    f"Image exceeded maximum size limit of {self.max_size_bytes} bytes"
                                )
                            f.write(chunk)

                # Validate non-empty file
                if not temp_file.exists() or total_bytes == 0:
                    raise ValueError("Downloaded image file is empty (0 bytes)")

                # Validate magic bytes / image format
                with open(temp_file, "rb") as f:
                    header_sample = f.read(512)

                ext = detect_image_extension(header_sample, content_type)
                if not ext:
                    raise ValueError("Invalid image format or received HTML error page")

                # Atomic replacement to target path
                final_file = target_dir / f"{clean_stem}{ext}"
                temp_file.replace(final_file)

                # Relative path with forward slash
                rel_path = f"{clean_pkg}/{final_file.name}"
                self._url_cache[url] = rel_path

                return ImageDownloadResult(
                    url=url,
                    success=True,
                    relative_path=rel_path,
                    status_code=200,
                )

            except (httpx.RequestError, httpx.TimeoutException) as exc:
                last_error = f"Network error: {exc}"
                if attempt < self.max_retries:
                    delay = self.retry_backoff ** attempt
                    await asyncio.sleep(delay)
                else:
                    break
            except ValueError as exc:
                # Format or size validation errors - do not retry
                last_error = str(exc)
                break
            except Exception as exc:
                last_error = f"Unexpected download failure: {exc}"
                break
            finally:
                if temp_file.exists():
                    temp_file.unlink(missing_ok=True)

        return ImageDownloadResult(
            url=url,
            success=False,
            status_code=status_code,
            error=last_error or "Download failed",
        )

    async def download_package_images(
        self,
        package: PackageDetail,
        semaphore: asyncio.Semaphore,
        client: Optional[httpx.AsyncClient] = None,
    ) -> PackageDetail:
        """
        Downloads banner and gallery images for a single package.
        Updates local paths and download metadata on the package.
        """
        pkg_slug = safe_slug(package.slug or package.name, fallback="package")
        download_errors: List[ImageErrorDetail] = []
        
        banner_res: Optional[ImageDownloadResult] = None
        gallery_results: List[Optional[ImageDownloadResult]] = []

        total_images = 0
        downloaded_count = 0
        skipped_count = 0
        failed_count = 0

        # 1. Download banner image
        if package.banner_image:
            total_images += 1
            async with semaphore:
                banner_res = await self.download_image(
                    url=package.banner_image,
                    package_slug=pkg_slug,
                    filename_stem="banner",
                    client=client,
                )
            if banner_res.success:
                package.banner_image_local = banner_res.relative_path
                if banner_res.skipped:
                    skipped_count += 1
                else:
                    downloaded_count += 1
            else:
                package.banner_image_local = None
                failed_count += 1
                download_errors.append(ImageErrorDetail(url=package.banner_image, error=banner_res.error or "Banner download failed"))

        # 2. Download gallery images
        images_local: List[Optional[str]] = []
        if package.images:
            for idx, img_url in enumerate(package.images):
                total_images += 1
                async with semaphore:
                    res = await self.download_image(
                        url=img_url,
                        package_slug=pkg_slug,
                        filename_stem=f"image_{idx + 1:03d}",
                        client=client,
                    )
                gallery_results.append(res)
                if res.success:
                    images_local.append(res.relative_path)
                    if res.skipped:
                        skipped_count += 1
                    else:
                        downloaded_count += 1
                else:
                    images_local.append(None)
                    failed_count += 1
                    download_errors.append(ImageErrorDetail(url=img_url, error=res.error or "Gallery image download failed"))
        
        package.images_local = images_local
        package.image_errors = download_errors
        
        # Summary & Status calculation
        package.image_download_summary = ImageDownloadSummary(
            total=total_images,
            downloaded=downloaded_count,
            failed=failed_count,
            skipped=skipped_count,
        )

        if total_images == 0:
            package.image_download_status = "skipped"
        elif failed_count == 0:
            package.image_download_status = "completed"
        elif downloaded_count > 0 or skipped_count > 0:
            package.image_download_status = "partial"
        else:
            package.image_download_status = "failed"

        return package

    async def download_all_packages(
        self,
        packages: List[PackageDetail],
        progress_callback: Optional[Callable[[int, int, PackageDetail], None]] = None,
    ) -> ImageDownloadSummary:
        """
        Orchestrates downloading across all packages using configured concurrency.
        """
        semaphore = asyncio.Semaphore(self.concurrency)
        client = await self.get_client()

        total_overall = 0
        downloaded_overall = 0
        failed_overall = 0
        skipped_overall = 0

        async def process_one(pkg: PackageDetail):
            nonlocal total_overall, downloaded_overall, failed_overall, skipped_overall
            await self.download_package_images(pkg, semaphore=semaphore, client=client)
            if pkg.image_download_summary:
                total_overall += pkg.image_download_summary.total
                downloaded_overall += pkg.image_download_summary.downloaded
                failed_overall += pkg.image_download_summary.failed
                skipped_overall += pkg.image_download_summary.skipped
            if progress_callback:
                progress_callback(downloaded_overall + skipped_overall + failed_overall, total_overall, pkg)

        tasks = [process_one(pkg) for pkg in packages]
        await asyncio.gather(*tasks)

        return ImageDownloadSummary(
            total=total_overall,
            downloaded=downloaded_overall,
            failed=failed_overall,
            skipped=skipped_overall,
        )

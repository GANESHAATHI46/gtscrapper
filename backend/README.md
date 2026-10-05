# GT Holidays Package Scraper & Django Formatter

FastAPI asynchronous scraping backend for GT Holidays tour package category pages with automated transformation into **Focus Tourism Django-compatible JSON** structures.

## Key Features

- **Generic Architecture**: Zero destination hardcoding (`if destination == 'Kerala'` is strictly forbidden). Dynamically handles any public GT Holidays listing.
- **Automated Market Detection**: Automatically detects Domestic (India) vs International listings:
  - If `country == "India"` → `market = "india"`
  - Otherwise → `market = "international"`
- **Dual JSON Output**: For every scrape, generates two files in `backend/output/`:
  1. `<slug>-tour-packages-<timestamp>.json` (Raw GT Holidays scraper output preserved completely)
  2. `<slug>-tour-packages-django-<timestamp>.json` (Validated Django bulk-import compatible data)
- **Django Bulk-Import Target Structures**:
  - **India (`/bulk-import/india/`)**: `regions`, `cities` (grouped by destination slug), `package_types` (with `is_active`), and `packages` (using `city` slug, package `image`, gallery images with `is_primary` / `sort_order`, and itinerary with `day`).
  - **International (`/bulk-import/international/`)**: `regions` (preserving scraped region), `countries` (with `banner_image`), `package_types` (`description: ""`), and `packages` (using `country` slug, package `banner_image`, images with `alt_text` / `display_order`, itinerary with `day_number` / `display_order`, and `groups: []`).
- **Pydantic Validation**: All transformed data is strictly validated against Pydantic contract schemas before saving.
- **Decoupled Architecture**: Scraper operates completely standalone without requiring direct Django API calls, network credentials, or database insertion logic.
- **Asynchronous Image Downloader**: Downloads package banner and gallery images to configurable local storage (`backend/storage/gt_holidays/`):
  - Streams chunk-by-chunk to disk to prevent memory overflow.
  - Automatically identifies format via magic byte signatures (JPEG, PNG, WebP, GIF, AVIF, SVG); never defaults blindly to `.jpg`.
  - Rejects HTML error responses returned with HTTP 200.
  - Concurrent bounded downloads using `asyncio.Semaphore`.
  - Retries transient errors (429, 5xx, timeouts) with exponential backoff while respecting `Retry-After`.
  - Rejects SSRF, localhost, private IP destinations, and directory traversal attempts.
  - Preserves original remote URLs in both Raw and Django payloads for 100% backward compatibility.
  - Mounts `/storage` static files route on FastAPI for browser previewing.

---

## Image Storage & Django Integration

Downloaded images are organized deterministically by sanitized package slug:

```text
backend/storage/gt_holidays/
└── <package-slug>/
    ├── banner.<ext>
    ├── image_001.<ext>
    └── image_002.<ext>
```

### JSON Fields Added (Backward-Compatible):
- `banner_image_local`: relative path e.g. `<package-slug>/banner.jpg` (or null if failed/skipped)
- `images_local`: array of relative paths matching the `images` list order
- `image_download_status`: `completed`, `partial`, `failed`, or `skipped`
- `image_download_summary`: `{ "total": N, "downloaded": N, "failed": N, "skipped": N }`

### Django Bulk Import Compatibility:
- Django bulk import payloads continue to use the public `image` and `banner_image` URLs so Django bulk-import endpoints (`/bulk-import/india/` and `/bulk-import/international/`) remain 100% compatible.
- If Django is deployed on a separate server, the `storage/` directory can be synced via rsync/S3/shared volume, or served over HTTP via the scraper's mounted `/storage/` endpoint.

---

## Configuration Settings

Configurable via environment variables or `backend/app/config.py`:
- `ENABLE_IMAGE_DOWNLOAD`: Enable/disable image downloads (default: `True`)
- `IMAGE_STORAGE_DIR`: Target directory path (default: `backend/storage/gt_holidays`)
- `IMAGE_CONCURRENCY`: Max concurrent downloads (default: `5`)
- `IMAGE_REQUEST_TIMEOUT`: HTTP timeout per image in seconds (default: `25.0`)
- `IMAGE_MAX_SIZE_BYTES`: Max image size before aborting (default: `26,214,400` bytes / 25MB)

---

## Setup & Running (Windows PowerShell)

```powershell
# 1. Activate Virtual Environment
cd d:\github\gtscraper\backend
..\.venv\Scripts\Activate.ps1

# 2. Install Dependencies
pip install -r requirements.txt

# 3. Start Backend
uvicorn app.main:app --reload --port 8000
```

Backend endpoints:
- Swagger Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/health`
- Start Scrape: `POST /api/scrape`
- Job Status: `GET /api/jobs/{job_id}`
- Raw JSON: `GET /api/jobs/{job_id}/json`
- Download Raw JSON: `GET /api/jobs/{job_id}/download`
- Django-Compatible JSON: `GET /api/jobs/{job_id}/django-json`
- Download Django JSON: `GET /api/jobs/{job_id}/download-django`

---

## Frontend Setup & Running

```powershell
cd d:\github\gtscraper\frontend
npm install
npm run dev
```

Frontend will run at `http://localhost:5173`.

---

## Running Automated Tests

```powershell
cd d:\github\gtscraper\backend
..\.venv\Scripts\pytest tests -v
```

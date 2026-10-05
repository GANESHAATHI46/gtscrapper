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

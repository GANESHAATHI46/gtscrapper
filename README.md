# GT Holidays Generic Package Scraper

A generic, production-ready tour package scraper and interactive dashboard for [GT Holidays](https://www.gtholidays.in).

## Key Features

- **Generic Scraper Architecture**: Zero destination-specific hardcoded logic. Works seamlessly with any GT Holidays domestic or international listing URL (e.g. Delhi, Kerala, Goa, Kashmir, Dubai, Singapore, etc.).
- **Dynamic Package Discovery**: Automatically identifies all package cards in the main listing scope, including hidden packages loaded inside `#gt-more-packages` (View More).
- **Dynamic Metadata Detection**: Extracts country, region, destination, category, and page title following the priority chain: Schema BreadcrumbList → HTML breadcrumbs → structured page metadata → H1 → OpenGraph title → URL segments.
- **Dynamic Currency & Price Parsing**: Detects numeric prices and currencies (`₹`/`INR`, `$`/`USD`, `AED`, `€`/`EUR`, `£`/`GBP`). Flags missing or "On Request" pricing cleanly as `null`.
- **Ordered Itinerary**: Extracts structured, day-by-day itineraries with day index, title, and detailed descriptions.
- **Output Versioning**: Automatically exports versioned JSON to `backend/output/{destination-slug}-tour-packages-{YYYYMMDD-HHMMSS}.json` without overwriting previous runs.
- **Modern Interactive Frontend**: React + Vite UI with polling status tracker, live progress bar, package data table, day-by-day itinerary inspector modal, JSON preview modal, and one-click downloads.

---

## Project Structure

```text
gt-holidays-scraper/
│
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint, CORS, routing
│   │   ├── config.py                  # Settings, timeouts, concurrency
│   │   ├── api/
│   │   │   └── routes.py              # REST endpoints (health, scrape, jobs, download)
│   │   ├── scraper/
│   │   │   ├── listing.py             # Generic listing detector & link discoverer
│   │   │   ├── package.py             # Package detail scraper coordinator
│   │   │   ├── parser.py              # Pure HTML extraction functions
│   │   │   ├── metadata.py            # Dynamic breadcrumbs & schema metadata resolver
│   │   │   ├── client.py              # Async HTTPX client with retry and backoff
│   │   │   └── utils.py               # SSRF guards, currency/price parser, slugify
│   │   ├── models/
│   │   │   └── package.py             # Pydantic schemas
│   │   ├── services/
│   │   │   └── scraper_service.py     # Background job manager & state machine
│   │   └── exporters/
│   │       └── json_exporter.py       # Versioned JSON serializer
│   ├── output/                        # Exported JSON files
│   ├── tests/
│   │   ├── test_scraper.py            # Unit tests for utils and parsers
│   │   └── test_live_integration.py   # Live multi-destination integration tests
│   ├── pytest.ini
│   ├── requirements.txt
│   └── README.md
│
└── frontend/
    ├── src/
    │   ├── App.tsx                    # Main interactive UI
    │   ├── App.css                    # Polished Vanilla CSS design system
    │   ├── types.ts                   # TypeScript interfaces
    │   └── components/
    │       ├── URLInput.tsx           # URL input with UI presets
    │       ├── ProgressTracker.tsx    # Step-by-step progress monitor
    │       ├── PackageTable.tsx       # Searchable & filterable package table
    │       ├── PackageDetailModal.tsx # Itinerary accordion & media modal
    │       └── JSONViewer.tsx         # JSON preview & copy modal
    ├── package.json
    └── vite.config.ts
```

---

## Windows Setup & Execution

### 1. Backend Setup

Open Windows PowerShell in the project root:

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend\requirements.txt
```

### 2. Running the Backend Server

```powershell
# From the backend directory
cd backend
uvicorn app.main:app --reload --port 8000
```

- API Base: `http://localhost:8000`
- Interactive Swagger Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/health`

### 3. Frontend Setup & Run

Open a second Windows PowerShell terminal:

```powershell
cd frontend
npm install
npm run dev
```

- Frontend App: `http://localhost:5173`

---

## Running Automated Tests

```powershell
cd backend
..\.venv\Scripts\pytest tests -v
```

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=1,11,21,28&height=220&section=header&text=GT%20Holidays%20Scraper&fontSize=42&fontColor=ffffff&animation=twinkling&fontAlignY=38&desc=Universal%20Tour%20Package%20Intelligence%20%26%20Interactive%20Dashboard&descAlignY=62&descAlign=50" width="100%" alt="GT Holidays Scraper Header Banner" />
</p>

<p align="center">
  <a href="https://github.com/GANESHAATHI46/gtscrapper">
    <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=22&duration=3000&pause=1000&color=38BDF8&center=true&vCenter=true&multiline=false&width=650&height=45&lines=⚡+Zero-Hardcode+Generic+Scraper+Architecture;🚀+Async+HTTPX+Concurrency+Pool+with+Retry+%26+Backoff;🧭+Dynamic+Schema+JSON-LD+%26+Itinerary+Extractor;💎+Modern+React+18+%2B+Vite+%2B+FastAPI+Dashboard;📊+Multi-Currency+Detection+(INR%2C+USD%2C+AED%2C+EUR%2C+GBP)" alt="Typing SVG" />
  </a>
</p>

<p align="center">
  <a href="https://github.com/GANESHAATHI46/gtscrapper/stargazers"><img src="https://img.shields.io/github/stars/GANESHAATHI46/gtscrapper?style=for-the-badge&logo=github&color=F59E0B" alt="Stars" /></a>
  <a href="https://github.com/GANESHAATHI46/gtscrapper/network/members"><img src="https://img.shields.io/github/forks/GANESHAATHI46/gtscrapper?style=for-the-badge&logo=github&color=6366F1" alt="Forks" /></a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Vite-6.0+-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/Tests-Pytest%20Passing-10B981?style=for-the-badge&logo=pytest&logoColor=white" alt="Tests" />
  <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="License" />
</p>

---

<p align="center">
  <a href="#-key-features"><b>✨ Features</b></a> •
  <a href="#%EF%B8%8F-interactive-architecture--workflow"><b>🏗️ Architecture</b></a> •
  <a href="#-terminal-execution-preview"><b>💻 Terminal Demo</b></a> •
  <a href="#-quick-start-guide"><b>🚀 Quick Start</b></a> •
  <a href="#-rest-api-endpoints"><b>📡 API Reference</b></a> •
  <a href="#-automated-testing"><b>🧪 Testing</b></a>
</p>

---

## ✨ Key Features

<table>
  <tr>
    <td width="50%">
      <h3>🌐 Universal Generic Scraper</h3>
      <p>Zero destination-specific hardcoded rules. Automatically scrapes any GT Holidays domestic or international listing (e.g. <i>Delhi, Kerala, Goa, Kashmir, Dubai, Singapore, Thailand, Europe</i>).</p>
    </td>
    <td width="50%">
      <h3>⚡ Dynamic Card Discovery</h3>
      <p>Scans the main package listing scope and dynamically uncovers hidden cards loaded inside <code>#gt-more-packages</code> (View More) without dropping records.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>🧭 Dynamic Schema & Breadcrumbs</h3>
      <p>Robust metadata resolution chain: <code>Schema.org BreadcrumbList</code> ➔ HTML breadcrumbs ➔ Page metadata ➔ H1 ➔ OpenGraph ➔ Normalized URL segments.</p>
    </td>
    <td width="50%">
      <h3>💱 Multi-Currency & Price Intelligence</h3>
      <p>Detects numeric amounts and ISO currencies (<code>₹/INR</code>, <code>$/USD</code>, <code>AED</code>, <code>€/EUR</code>, <code>£/GBP</code>). Safely sets missing or "On Request" pricing as <code>null</code>.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>📅 Day-by-Day Structured Itinerary</h3>
      <p>Extracts ordered timeline schedules with day indices, activity titles, rich narrative descriptions, and tour inclusions.</p>
    </td>
    <td width="50%">
      <h3>💾 Versioned JSON Persistence</h3>
      <p>Auto-generates versioned datasets in <code>backend/output/{destination-slug}-tour-packages-{timestamp}.json</code> with non-destructive runs.</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>🛡️ Built-in SSRF & Concurrency Guard</h3>
      <p>Enforces strict domain whitelisting (<code>*.gtholidays.in</code>), backoff retry strategies, and rate-regulated asynchronous worker pools.</p>
    </td>
    <td width="50%">
      <h3>💎 Modern Interactive Web Dashboard</h3>
      <p>Clean React + Vite single-page application with real-time job polling, progress bars, searchable table, itinerary inspector modal, and instant JSON download.</p>
    </td>
  </tr>
</table>

---

## 🏗️ Interactive Architecture & Workflow

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 User / Dashboard
    participant API as ⚡ FastAPI Backend
    participant Engine as 🕷️ Async Engine (HTTPX)
    participant GT as 🌐 GT Holidays Portal
    participant Exporter as 💾 Versioned JSON Exporter

    User->>API: POST /api/scrape { url: "https://www.gtholidays.in/..." }
    API->>API: Validate URL (Domain Whitelist & SSRF Guard)
    API->>Engine: Spawn Asynchronous Background Worker
    API-->>User: 202 Accepted { job_id: "...", status: "running" }
    
    activate Engine
    Engine->>GT: GET Listing Page (Main Scope + #gt-more-packages)
    GT-->>Engine: 200 OK (HTML Payload)
    Engine->>Engine: Discover all package cards & links
    
    loop Concurrent Async Pool (max_concurrency: 4)
        Engine->>GT: Fetch Detail Page (HTML + Schema JSON-LD)
        GT-->>Engine: 200 OK
        Engine->>Engine: Extract metadata, pricing, days, itineraries
    end
    
    Engine->>Exporter: Serialize to backend/output/{slug}-{timestamp}.json
    Exporter-->>Engine: File Saved Successfully
    deactivate Engine

    loop Live Polling Status (Every 1s)
        User->>API: GET /api/jobs/{job_id}
        API-->>User: Status (progress %, package count, completed)
    end

    User->>API: GET /api/downloads/{filename}
    API-->>User: Download Raw JSON Dataset
```

---

## 💻 Terminal Execution Preview

```ansi
[1;34m╭─────────────────────────────────────────────────────────────────────────────╮[0m
[1;34m│[0m  [1;32m★ GT HOLIDAYS HIGH-PERFORMANCE SCRAPER ENGINE v1.0.0[0m                       [1;34m│[0m
[1;34m│[0m  [1;36mTarget:[0m https://www.gtholidays.in/kerala-tour-packages/                     [1;34m│[0m
[1;34m╰─────────────────────────────────────────────────────────────────────────────╯[0m
[1;33m[i] Initializing Async Engine with 4 concurrent workers...[0m
[1;32m[+] Discovered 28 packages[0m (including 12 loaded inside #gt-more-packages)
[1;35m[●] [1/28] Munnar Scenic Getaway .........[0m [1;32m₹14,999 (3N/4D)[0m [1;30m[OK][0m
[1;35m[●] [2/28] Wayanad Wilderness Trek .......[0m [1;32m₹18,500 (4N/5D)[0m [1;30m[OK][0m
[1;35m[●] [3/28] Alleppey Houseboat Cruise .....[0m [1;32m₹21,200 (2N/3D)[0m [1;30m[OK][0m
[1;35m[●] [4/28] Kerala Honeymoon Special ......[0m [1;32m₹29,999 (5N/6D)[0m [1;30m[OK][0m
[1;32m✔ Pipeline completed in 8.42s![0m
[1;36m💾 Saved versioned JSON:[0m [1;37mbackend/output/kerala-tour-packages-20261005-121500.json[0m
```

---

## 📂 Project Structure

```text
gtscraper/
│
├── 📂 backend/
│   ├── 📂 app/
│   │   ├── main.py                    # FastAPI entrypoint, CORS, routing
│   │   ├── config.py                  # Settings, timeouts, concurrency, SSRF guard
│   │   ├── 📂 api/
│   │   │   └── routes.py              # REST endpoints (health, scrape, jobs, download)
│   │   ├── 📂 scraper/
│   │   │   ├── listing.py             # Generic listing detector & link discoverer
│   │   │   ├── package.py             # Package detail scraper coordinator
│   │   │   ├── parser.py              # Pure HTML extraction functions
│   │   │   ├── metadata.py            # Dynamic breadcrumbs & schema metadata resolver
│   │   │   ├── client.py              # Async HTTPX client with retry and backoff
│   │   │   └── utils.py               # SSRF guards, currency/price parser, slugify
│   │   ├── 📂 models/
│   │   │   └── package.py             # Strict Pydantic models & validation
│   │   ├── 📂 services/
│   │   │   └── scraper_service.py     # Background job manager & state machine
│   │   └── 📂 exporters/
│   │       └── json_exporter.py       # Versioned JSON serializer
│   ├── 📂 output/                     # Exported versioned JSON datasets
│   ├── 📂 tests/
│   │   ├── test_scraper.py            # Unit tests for utils and parsers
│   │   ├── test_live_integration.py   # Live multi-destination integration tests
│   │   ├── test_kerala_acceptance.py  # Acceptance suite for Kerala packages
│   │   └── test_transformers.py       # Data transformation tests
│   ├── pytest.ini
│   └── requirements.txt
│
└── 📂 frontend/
    ├── 📂 src/
    │   ├── App.tsx                    # Main interactive dashboard
    │   ├── App.css                    # Polished design system with glassmorphism
    │   ├── types.ts                   # TypeScript interfaces
    │   └── 📂 components/
    │       ├── URLInput.tsx           # URL input with UI presets (Kerala, Dubai, Delhi, etc.)
    │       ├── ProgressTracker.tsx    # Live animated step-by-step progress monitor
    │       ├── PackageTable.tsx       # Searchable, sortable & filterable package table
    │       ├── PackageDetailModal.tsx # Itinerary accordion & media modal
    │       └── JSONViewer.tsx         # JSON preview & copy modal
    ├── package.json
    └── vite.config.ts
```

---

## 🚀 Quick Start Guide

<details open>
<summary><b>1. 🐍 Backend Setup (FastAPI)</b></summary>

Open Windows PowerShell in the project root:

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend\requirements.txt

# Run the FastAPI server
cd backend
uvicorn app.main:app --reload --port 8000
```

- 🌐 **API Base**: [http://localhost:8000](http://localhost:8000)
- 📖 **Swagger Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 🩺 **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

</details>

<details open>
<summary><b>2. ⚛️ Frontend Setup (React + Vite)</b></summary>

Open a second Windows PowerShell terminal:

```powershell
cd frontend

# Install node dependencies
npm install

# Start the Vite development server
npm run dev
```

- 🖥️ **Interactive Web App**: [http://localhost:5173](http://localhost:5173)

</details>

---

## 📡 REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Service health & uptime probe |
| `POST` | `/api/scrape` | Trigger an async scrape job for a GT Holidays listing URL |
| `GET` | `/api/jobs/{job_id}` | Poll real-time scrape job progress & status |
| `GET` | `/api/downloads/{filename}` | Download generated versioned JSON output |

---

## 🧪 Automated Testing

Run the test suite with verbose reporting:

```powershell
cd backend
..\.venv\Scripts\pytest tests -v
```

<details>
<summary><b>🧪 Test Coverage Highlights</b></summary>

- `test_scraper.py`: Tests HTML parsing, price/currency normalization, and SSRF domain security checks.
- `test_live_integration.py`: Validates live extraction on domestic & international packages.
- `test_kerala_acceptance.py`: Strict validation of package counts, breadcrumbs, and itineraries.
- `test_transformers.py`: Validates data serialization and schema contracts.

</details>

---

<p align="center">
  <sub>Built with ❤️ for generic web scraping and modern data visualization.</sub>
</p>

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=1,11,21,28&height=100&section=footer" width="100%" alt="Footer Wave" />
</p>


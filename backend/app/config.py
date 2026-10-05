import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel

# Load local .env if present
load_dotenv()

class Settings(BaseModel):
    app_name: str = "GT Holidays Generic Package Scraper"
    version: str = "1.0.0"
    
    # Network & Concurrency
    max_concurrency: int = 4
    request_timeout: float = 25.0
    max_retries: int = 3
    retry_backoff_factor: float = 1.5
    
    # Allowed domains for SSRF defense
    allowed_domains: tuple[str, ...] = (
        "gtholidays.in",
        "www.gtholidays.in",
    )
    
    # User Agent simulating a modern browser
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    
    # Directories
    base_dir: Path = Path(__file__).resolve().parent.parent
    output_dir: Path = base_dir / "output"

settings = Settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)

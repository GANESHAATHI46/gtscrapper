import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.config import settings

HEADERS = {
    "User-Agent": settings.user_agent,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
}

class BotProtectionException(Exception):
    def __init__(self, message: str = "The source website requires interactive verification."):
        super().__init__(message)
        self.message = message

class ScraperClient:
    def __init__(self, timeout: float = settings.request_timeout):
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
            self._client = httpx.AsyncClient(
                headers=HEADERS,
                timeout=self.timeout,
                limits=limits,
                follow_redirects=True,
                http2=True,
            )
        return self._client

    @retry(
        stop=stop_after_attempt(settings.max_retries),
        wait=wait_exponential(multiplier=settings.retry_backoff_factor, min=1, max=6),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
        reraise=True,
    )
    async def fetch_html(self, url: str) -> str:
        client = await self.get_client()
        response = await client.get(url)
        
        # Check for CAPTCHA / bot challenge blocks
        lower_body = response.text.lower()
        if response.status_code in (403, 429, 503) or "<title>just a moment...</title>" in lower_body:
            if any(k in lower_body for k in [
                "cf-turnstile",
                "challenges.cloudflare.com",
                "just a moment...",
                "checking your browser",
                "attention required! | cloudflare",
                "g-recaptcha",
                "hcaptcha"
            ]) or response.status_code in (403, 429):
                raise BotProtectionException("The source website requires interactive verification.")

        response.raise_for_status()
        return response.text

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

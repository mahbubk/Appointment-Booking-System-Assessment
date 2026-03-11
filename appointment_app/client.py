"""
Handle HTTP errors: retry on 5xx (max 3 attempts, exponential backoff), raise on 4xx
Handle rate limiting (429 responses) — wait and retry
Handle connection timeouts and network errors
Use requests.Session for connection reuse
Log all API calls (method, URL, status code, response time) using Python logging

"""

import logging
import time
from typing import Optional

import requests
from requests.exceptions import ConnectionError, Timeout

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RATE_LIMIT_WAIT = 30  
REQUEST_TIMEOUT = 30 


class APIError(Exception):


    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"API error {status_code}: {message}")


class BookingSystemClient:
 

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/index.php/api/v1"
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.session.headers.update({"Content-Type": "application/json"})



    def test_connection(self) -> bool:
      
        try:
            response = self._request("GET", "/settings")
            return response.status_code == 200
        except (APIError, ConnectionError, Timeout):
            return False

    def get_providers(self) -> list[dict]:
        return self._get_all("/providers")

    def get_customers(self) -> list[dict]:
        return self._get_all("/customers")

    def get_services(self) -> list[dict]:
        return self._get_all("/services")

    def get_appointments(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> list[dict]:
        """
        Fetch appointments, optionally filtered by date range.
        Date format: YYYY-MM-DD
        """
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self._get_all("/appointments", params=params)


    def _get_all(self, path: str, params: Optional[dict] = None) -> list[dict]:
        """
        GET a resource list. Easy!Appointments returns all records in one shot
        (no cursor pagination), so we just GET and return the list.
        """
        response = self._request("GET", path, params=params)
        data = response.json()

        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("data", data.get("results", []))
        return []

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
    ) -> requests.Response:
    
        url = f"{self.api_base}{path}"

        for attempt in range(MAX_RETRIES + 1):
            start = time.monotonic()
            try:
                response = self.session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    timeout=REQUEST_TIMEOUT,
                )
                elapsed = time.monotonic() - start
                logger.info(
                    "%s %s → %s (%.2fs)",
                    method,
                    url,
                    response.status_code,
                    elapsed,
                )

                if response.status_code == 429:
                    logger.warning("Rate limited (429). Waiting %ss before retry.", RATE_LIMIT_WAIT)
                    time.sleep(RATE_LIMIT_WAIT)
                    continue  
                if 400 <= response.status_code < 500:
                    raise APIError(response.status_code, response.text)

                if response.status_code >= 500:
                    if attempt < MAX_RETRIES:
                        wait = 2 ** attempt
                        logger.warning(
                            "Server error %s on attempt %s/%s. Retrying in %ss.",
                            response.status_code,
                            attempt + 1,
                            MAX_RETRIES,
                            wait,
                        )
                        time.sleep(wait)
                        continue
                    raise APIError(response.status_code, f"Server error after {MAX_RETRIES} retries")

                return response

            except (ConnectionError, Timeout) as exc:
                elapsed = time.monotonic() - start
                logger.warning(
                    "Network error on %s %s (attempt %s/%s, %.2fs): %s",
                    method,
                    url,
                    attempt + 1,
                    MAX_RETRIES,
                    elapsed,
                    exc,
                )
                if attempt >= MAX_RETRIES:
                    raise
                wait = 2 ** attempt
                time.sleep(wait)

     
        raise APIError(0, "Max retries exceeded")
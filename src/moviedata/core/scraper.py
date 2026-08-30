"""
Base modules for web scraping
"""
import time
from abc import ABC
from camoufox.sync_api import Camoufox
from curl_cffi import requests
from bs4 import BeautifulSoup

class scraper(ABC):
    """
    Parent template for all domain scanner classes.
    """

    def __init__(self, domain: str, timeout: int = 10):
        self.domain = domain
        # Normalize domain to ensure valid URL structure
        self.base_url = f"https://{domain}" if not domain.startswith(("http://", "https://")) else domain
        self.timeout = timeout
        # HTTP-Headers
        self.headers: tuple | None = None
        # Session object
        self.session: requests.Session | None = None
        self.soup = None

    def get_headers(self, max_retries: int = 3, wait: float = 1.0):
        """
        Shared method: Fetches HTTP response headers for the domain.
        Inherited by all child classes without rewriting code.
        """
        for i in range(max_retries):
            try:
                print(f"[INFO] ({i+1}/{max_retries}) Trying to obtain headers for {self.base_url}...")
                with Camoufox(headless=True) as browser:
                    page = browser.new_page()

                    print(f"[INFO] Opening {self.base_url}...")
                    # Camoufox uses timeout values in ms, so multiple by 1000
                    page.goto(self.base_url, wait_until="networkidle", timeout=self.timeout*1000)

                    # Export browser session details for curl
                    user_agent = page.evaluate("navigator.userAgent")
                    cookies = page.context.cookies()
                    print("[INFO] Headers obtained successfully!")

                    # Set parameters
                    self.headers = (user_agent, cookies)
                return (user_agent, cookies)
            except Exception as e:
                # If this was the last attempt, raise the actual error immediately with its full traceback
                if i == max_retries - 1:
                    print(f"[ERROR] Max retries ({max_retries}) reached. Failing...")
                    raise e
                
                print(f"[WARNING] Obtaining headers failed! Trying again in {wait}s...")
                time.sleep(wait)

    def set_session(self):
        """
        """
        # Create session object
        self.session = requests.Session(impersonate="chrome124")

        # Get headers if not set already
        if self.headers is None:
            self.get_headers()

        # 1. Update User-Agent
        self.session.headers.update({"User-Agent": self.headers[0]})

        # 2. Add all cookies at once
        for cookie in self.headers[1]:
            self.session.cookies.set(
                name=cookie["name"],
                value=cookie["value"],
                domain=cookie.get("domain"),
                path=cookie.get("path", "/")
            )

        # Return session object
        return self.session

    def get_soup(self, request_url: str, timeout: int = 10, max_retries: int = 3, wait: float = 1.0):
        """
        """
        if self.session is None:
            self.set_session()

        for i in range(max_retries):
            try:
                print(f"[INFO] ({i+1}/{max_retries}) Performing GET request on {request_url}...")
                res = self.session.get(request_url, timeout=timeout)

                if res.status_code == 200:
                    print("[INFO] Request successful! Returning soup...")
                    soup = BeautifulSoup(res.text, "html.parser")
                    self.soup = soup
                    return soup
                else:
                    print(f"[WARNING] Request failed! [{res.status_code}]")
                    raise Exception(res.text)
            except Exception as e:
                # If this was the last attempt, raise the actual error immediately with its full traceback
                if i == max_retries - 1:
                    print(f"[ERROR] Max retries ({max_retries}) reached. Failing...")
                    raise e
                
                print(f"[WARNING] GET request failed! Trying again in {wait}s...")
                time.sleep(wait)

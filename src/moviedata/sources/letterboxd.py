"""
Module specialized for scraping letterboxd data
"""
import io
import zipfile
from camoufox.sync_api import Camoufox
from config.settings import settings

import moviedata.core.tools as tools

class letterboxd:
    """
    Class for letterboxd specific actions
    """
    def __init__(self):
        self.userdata = None
        self.headers = None

    def __repr__(self) -> str:
        """Official representation for debugging & logs."""
        return f"Letterboxd Class"

    def get_headers(self):
        """
        Calls letterboxd and stores headers
        """
        with Camoufox(headless=True) as browser:
            page = browser.new_page()

            print("[INFO] Opening letterboxd...")
            page.goto("https://letterboxd.com/", wait_until="networkidle")

            # Export browser session details for curl
            user_agent = page.evaluate("navigator.userAgent")
            cookies = page.context.cookies()

            # Set parameters
            self.headers = (user_agent, cookies)

    def get_userdata(self):
        """
        Logs into letterboxd using provided user-credentials
        then downloads and returns the userdata zip-file to memory
        as well as headers.
        """
        with Camoufox(headless=True) as browser:
            page = browser.new_page()

            # ----------------------------------------------------------------------
            # Sign in
            print("[INFO] Navigating to Sign-In page...")
            page.goto("https://letterboxd.com/sign-in/", wait_until="networkidle")

            page.fill("input[name='username']", settings.LETTERBOXD_USERNAME)
            page.fill("input[name='password']", settings.LETTERBOXD_PASSWORD)

            # Click the explicit submit button
            page.click("button[type='submit']")
            page.wait_for_timeout(3000)
            
            page.wait_for_url(lambda url: "sign-in" not in url, timeout=10000)
            print("[INFO] Logged in successfully!")
    
            # ----------------------------------------------------------------------
            # Export browser session details for curl
            user_agent = page.evaluate("navigator.userAgent")
            cookies = page.context.cookies()
    
            # ----------------------------------------------------------------------
            # 2. Go to data settings
            print("[INFO] Navigating to Data Settings page...")
            page.goto("https://letterboxd.com/settings/data/", wait_until="networkidle")
            
            # 3. Click initial trigger to open the Colorbox modal
            print("[INFO] Opening Colorbox modal...")
            page.eval_on_selector("a.export-data-link", "el => el.click()")
    
            # ----------------------------------------------------------------------
            # 4. Wait for the modal container to appear and click the inner confirmation button/link
            print("[INFO] Waiting for modal and clicking confirm download...")
            # Colorbox wraps popups inside #colorbox or #cboxLoadedContent
            page.wait_for_selector("#colorbox", state="visible", timeout=10000)
            
            # Capture the file download triggered by clicking the modal's download button
            with page.expect_download(timeout=20000) as download_info:
                # Targets the confirmation button/link inside the open modal
                page.click("#colorbox a, #colorbox button, #cboxLoadedContent a")
            
            # 5. Save ZIP archive
            download = download_info.value
            print("[INFO] Downloaded zip-file successfully!")
    
            # Read the temporary file stream into an in-memory BytesIO buffer
            with open(download.path(), "rb") as f:
                zip_buffer = io.BytesIO(f.read())
    
            # Return buffered data, user_agent and cookies
            self.userdata = zip_buffer
            self.headers = (user_agent, cookies)


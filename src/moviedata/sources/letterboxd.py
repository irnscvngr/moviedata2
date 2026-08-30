"""
Module specialized for scraping letterboxd data
"""
import io
import re
import random
import time
import sys
import asyncio
import zipfile
import pandas as pd
from camoufox.sync_api import Camoufox
from config.settings import settings
from moviedata.core.scraper import scraper
from moviedata.core.database import pg_connect

import moviedata.core.tools as tools

class letterboxd(scraper):
    """
    Class for letterboxd specific actions
    """
    def __init__(self, timeout: int=10):
        super().__init__(domain="https://www.letterboxd.com", timeout=timeout)
        self.userdata = None

    def __repr__(self) -> str:
        """Official representation for debugging & logs."""
        return f"Letterboxd Class"

    def get_userdata(self):
        """
        Logs into letterboxd using provided user-credentials
        then downloads and returns the userdata zip-file to memory
        as well as headers.
        """
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        with Camoufox(headless=True) as browser:
            page = browser.new_page()

            # ----------------------------------------------------------------------
            # Sign in
            print("[INFO] Navigating to Sign-In page...")
            page.goto("https://letterboxd.com/sign-in/", wait_until="networkidle", timeout=self.timeout*1000)

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

    def get_recommended_movies(self):
        """
        Uses view "recommended_movies" to get collection of movies
        that are shows as "similar" to already watched/rated movies.
        Then obtains their letterboxd_uri and stores them to database.
        """
        # Get recommended movies
        pg = pg_connect()
        df = pg.read_df_from_postgres(
            table_name="recommended_movies",
            schema_name="letterboxd",
            limit=None
        )
        # Reformat names such that name and release year are in separate columns
        df['recom_year'] = (
            df['recom_name']
            .str.extract(r"\((\d+)\)")
            .astype(int)
        )
        df['recom_name'] = (
            df['recom_name']
            .str.replace(r"\([0-9]+\)", "", regex=True)
            .str.strip()
        )

        for i, row in df.iterrows():
            print("\n============================================================")
            print(f"[INFO] [{i+1}/{df.shape[0]}] Processing: {row['recom_name']} ({row['recom_year']})")

            soup = self.get_soup(request_url=f"{self.base_url}{row['recom_link']}")

            if soup is None:
                print("[WARNING] Failed to obtain soup! Skipping movie...")
                continue

            # Search the entire raw HTML string for letterboxd_uri
            match = re.search(r"https://boxd\.it/[a-zA-Z0-9]+", str(soup))
            if match:
                letterboxd_uri = match.group(0)
            else:
                print("[WARNING] Failed to find letterboxd_uri! Skipping movie...")
                continue

            # Create dataframe to write to DB
            df_write = pd.DataFrame([{
                'name':row['recom_name'],
                'year':row['recom_year'],
                'letterboxd_uri':letterboxd_uri,
            }])

            # Write results to DB
            pg.write_df_to_postgres(
                df=df_write,
                table_name="lb_recommended_movies",
                schema_name="letterboxd",
                add_timestamp=False
            )

            print("[INFO] Movie processing completed successfully!\n")
            
            # Wait a little bit. Do it randomly be less suspicious
            time.sleep(random.random()*0.5)

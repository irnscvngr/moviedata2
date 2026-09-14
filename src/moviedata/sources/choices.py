"""
Module specialized for scraping data from choices.de
"""

import re
import json
import time
from datetime import datetime
import random
import pandas as pd
import bs4
from bs4 import BeautifulSoup
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from curl_cffi import requests
from unidecode import unidecode
from camoufox.sync_api import Camoufox
from moviedata.core.tools import hsl_to_rgb
from moviedata.core.scraper import scraper
from moviedata.core.database import pg_connect


class choices(scraper):
    """
    """

    def __init__(self, timeout: int=10):
        """
        """
        super().__init__(domain="https://www.choices.de/", timeout=timeout)
        self.userdata = None
        self.url_cinema_search = "https://www.choices.de/alle-kinos"
        self.all_cinemas = None

    def get_all_cinemas(self):
        """
        Goes to "alle-kinos" page of choices.de, and retreives a list of
        cinemas per city with respective links on choices.
        """
        # Get soup of "all-kinos" page on choices
        soup = self.get_soup(request_url=self.url_cinema_search)

        # Initialize some variables
        res = {}
        current_city = None

        # Go through all h3 and p elements on page
        for el in soup.find_all(["h3","p"]):
            # All cities are stored as h3
            if el.name == "h3":
                # Update current city key
                current_city = el.get_text(strip=True)
                res[current_city] = {}

            # Cinemas and respective links are stored as paragraphs
            if el.name == "p" and current_city:
                # Try to find link. If link exists, store cinema name and link to dict
                link = el.find("a")
                if link:
                    cinema = link.get_text(strip=True)
                    res[current_city][cinema] = link.get("href")

        # Store result and return it
        self.all_cinemas = res
        return res

    def _parse_cinema_page(self, soup: BeautifulSoup):
        """
        Receives soup of a cinema page on choices.de
        Returns pandas dataframe of all movie showings.
        """
        # --------------------------------------------------
        # EXTRACT EVENT ITEMS FROM CINEMA PAGE
        movies_el = soup.find_all(class_="event_item")

        def _parse_movie(el: bs4.element.Tag):
            """
            Function to parse movie information from an event item in HTML.
            """
            # ...................................
            # Get movie title
            title = (
                el
                .find("h3")
                .find("a")
                .get_text(strip=True)
            )
            # .................................
            # Get movie link
            link = (
                el
                .find("h3")
                .find('a')
                ['href']
            )
            # .................................
            # Get movie subtext
            subtext = el.find("p").get_text(strip=True)
            # Extract movie year
            match = re.search(pattern=r"\b\d{4}\b", string=subtext)
            year = None
            if match:
                year = match.group()
            # Get current year
            cur_year = datetime.now().year
            # ...................................
            # Get movie times
            # Get all table rows
            tab_rows = el.find_all("tr")

            # Initialize list for showings and process entries
            showtimes = []
            for tr in tab_rows:
                # Check for header
                th = tr.find("th")
                if th is not None:
                    continue

                # Get all table data elements
                td = tr.find_all("td")
                if len(td) == 0:
                    continue

                # Extract text from table data
                td_list = [td_el.get_text(strip=True) for td_el in td]

                # ......................................................................
                # PROCESS TIME INFORMATION
                # Get time-information
                t_str = td_list[1].strip()

                # Pattern groups match:
                # 1. (\d{2}:\d{2})            -> Time (e.g. 14:00)
                # 2. (?:\s*\((.+?)\))?(?:,|$) -> Optional space + parentheses content
                pattern = r"(\d{2}:\d{2})(?:\s*\((.+?)\))?(?:,|$)"

                # SPLIT TIME INFORMATION
                for time, annotation in re.findall(pattern, t_str, flags=re.IGNORECASE):
                    # Time information can contain annotations, like
                    # OV, OmU, OmeU etc.
                    # For "Sonderveranstaltungen" annotations can sometimes also
                    # contain both movie names and version (OV, OmU etc.)
                    pattern = r"(\bov\b|\bom\wu\b|\bomu\b)"
                    annot_split = re.split(pattern, annotation, flags=re.IGNORECASE)

                    # .................................................................
                    # Just use the "basic" annotation and watch out for OV, OmU etc.
                    vers = "DE"
                    match = re.match(r"\bov\b", annotation, flags=re.IGNORECASE)
                    if match:
                        vers = "OV"
                    match = re.match(r"\bom\wu\b", annotation, flags=re.IGNORECASE)
                    if match:
                        vers = "OmU"
                    match = re.match(r"\bomu\b", annotation, flags=re.IGNORECASE)
                    if match:
                        vers = "OmU"

                    # .................................................................
                    # Take the split annotation's first entry and extract
                    # the potential movie name
                    annot = None
                    match = re.search(r"\b[a-zA-Z0-9].+\b", annot_split[0])
                    if match:
                        annot = match.group()

                    # .................................................................
                    # Create timestamp
                    timestamp_dt = None
                    # Extract date from string
                    match = re.search(r"\b[0-9]{2}.[0-9]{2}\b", td_list[0])
                    if match:
                        timestamp = f"{match.group()}.{cur_year} {time}"
                        # timestamp_dt = datetime.fromtimestamp(timestamp)
                        timestamp_dt = datetime.strptime(timestamp, "%d.%m.%Y %H:%M")

                    # .................................................................
                    # Store all extracted information in a dictionary
                    res = {
                        "title":title,
                        "year":year,
                        "timestamp":timestamp_dt,
                        "vers":vers,
                        "annot":annot,
                        "link":link
                    }

                    # Append dictionary to list
                    showtimes.append(res)
            
            return showtimes

        # Write all showings information as list of dictionaries
        movies_parsed = []
        for el in movies_el:
            try:
                movies_parsed += _parse_movie(el.find('table'))
                print("[INFO] Successfully added movie information!")
            except:
                print("[WARNING] Failed to add movie information! Continuing with next entry...")
                continue
        
        try:
            res = pd.DataFrame(movies_parsed)
            print("[INFO] Successfully created dataframe!")
        except:
            res = None
            print("[WARNING] Failed to create dataframe! Returning None...")

        return res

    def get_all_movies(self):
        """
        Get movie presentations for all cinemas
        """

        # -----------------------------------------------------------------------------------------------
        # FILTER FOR SELECTED CINEMAS (function)
        def _parse_cinema(city, cinemas):
            """
            Check if selected cinema is in config file and return
            uniform list of dictionaries.
            """
            if city not in list(CINEMAS_CONFIG.keys()):
                return None

            # Get cinema names from config
            # Use values, not keys, because keys are reference names and values are taken from choices.de
            cinemas_config = set(CINEMAS_CONFIG[city].values())
            # Get cinema names from choices
            cinemas_choices = set(cinemas.keys())

            # Initialize results-list
            res = []
            # Go through all cinemas that are also in config-file
            for cinema in cinemas_choices.intersection(cinemas_config):
                res.append({
                    'city':city,
                    'cinema':cinema,
                    # Subdict contains href-link as value to cinema-key
                    'link':cinemas[cinema]
                })

            return res

        # -----------------------------------------------------------------------------------------------
        # FILTER FOR SELECTED CINEMAS BY CONFIG
        if self.all_cinemas is None:
            self.get_all_cinemas()

        # Import config-file for cinema selection
        filepath = "src/moviedata/sources/configs/choices_config.json"
        with open(filepath, "r", encoding="utf-8") as file:
            CINEMAS_CONFIG = json.load(file)

        # Go through all cities and get cinema name and link
        cinemas_scrape = []
        for city, cinemas in self.all_cinemas.items():
            res = _parse_cinema(city, cinemas)
            if res is not None:
                cinemas_scrape += res

        print(f"[INFO] Selected {len(cinemas_scrape)} cinemas for scraping!")

        # -----------------------------------------------------------------------------------------------
        # GO THROUGH CINEMAS AND GET MOVIES
        for i, cinema in enumerate(cinemas_scrape):
            print(f"[INFO] ({i+1}/{len(cinemas_scrape)}) Processing {cinema}... {cinema['link']}")

            # Get soup for current cinema
            soup = self.get_soup(request_url=cinema['link'])

            # Try and get dataframe of all movie showings of current cinema
            res = self._parse_cinema_page(soup)

            # Skip if no showings could be obtained
            if res is None:
                print(f"[WARNING] Failed to get movie showings for {cinema}! Continuing...")
                continue

            print(res)


            # Wait a little bit. Do it randomly be less suspicious
            time.sleep(random.random()*1.0)

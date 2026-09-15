"""
Module specialized for getting data from The Movie Database (TMDB) API
"""

import re
import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import random
import pandas as pd
import bs4
from bs4 import BeautifulSoup
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from curl_cffi import requests
from unidecode import unidecode
from config.settings import settings
from camoufox.sync_api import Camoufox
from moviedata.core.tools import hsl_to_rgb
from moviedata.core.scraper import scraper
from moviedata.core.database import pg_connect


class tmdb(scraper):
    """
    """

    def __init__(self, timeout: int=10):
        """
        """     
        self.TMDB_API_KEY = settings.TMDB_API_KEY

    def search_movie(self, movie_title, release_year=None, language="en-US"):
        """
        Calls TMDB API to search for a given movie title and optional release year.
        Returns JSON of search results.

        Languages (among others):
        - en-EN
        - en-US
        - de-DE
        """

        url = "https://api.themoviedb.org/3/search/movie"
        params = {
            "api_key": self.TMDB_API_KEY,
            "query": movie_title,
            "language": language,
            "year": release_year
        }

        response = requests.get(url, params=params)

        return response.json()

    def eval_search_res_by_date(self, res_list: list, ref_year: int, reference_title: str):
        """
        Take list of search results from TMDB (list of dicts).
        Get timedelta between release data from TMDB and reference year.
        Select search result with smallest timedelta.
        """
        # Initialize delta_min as a large value
        delta_years_min = 10

        # Initialize selected object
        el_select = {}

        # Initialize list to store elements with zero-year-delta
        zero_delta_elements = []

        # ---------------------------------------------------------------------------
        # GO THROUGH ALL LIST-ELEMENTS
        for el in res_list:
            if el['release_date'] == '':
                # Some movies don't have a release date in dataset -> Skip
                continue
            else:
                # Convert release date from string to datetime
                release_date = datetime.fromisoformat(el['release_date'])
                # Get time delta in years
                delta_years = ref_year - release_date.year

            if delta_years < delta_years_min:
                # Overwrite selected element if current delta is smaller than previous delta
                el_select = el
                # Set new delta min
                delta_years_min = delta_years

            if delta_years == 0:
                zero_delta_elements.append(el)

        if len(zero_delta_elements) == 1:
            print("[INFO] Only 1 zero-delta element found. Selection conclusive!")
            return el_select
        else:
            print(f"[WARNING] More than 1 zero-delta element found (found {len(zero_delta_elements)}). Selecting by name...")
            for el in zero_delta_elements:
                if el['original_title'] == reference_title:
                    print("[INFO] Original title matches reference title! Returning element...")
                    return el
            print("[WARNING] Processed all zero-delta elements but no direct name-match found. Returning None!")
            return None

    def search_movie_smart(self, movie_title: str, release_year: int, language="en-US"):
        """
        Simplified method to perform "search_movie" and "eval_search_res_by_date" in one go.
        """
        if isinstance(release_year, str):
            release_year = int(release_year)

        search_res = self.search_movie(
            movie_title=movie_title,
            release_year=release_year,
            language=language)

        search_res_eval = self.eval_search_res_by_date(
            res_list=search_res['results'],
            ref_year=release_year,
            reference_title=movie_title
        )

        return search_res_eval

    def get_movie_data(
            self,
            movie_id: int|None=None,
            movie_title: str|None=None,
            release_year: int|None=None,
            language="en-US",
            category="details"):
        """
        category:
        - details
        - translations
        - release_dates
        """
        # ---------------------------------------------------------------------------
        # TMDB API needs movie_id for query.
        # If movie_id was not passed, use smart search first
        if movie_id is None:
            if (movie_title is None) and (release_year is None):
                print("[WARNING] Neither movie_id nor movie title and release year were passed. Returning None!")
                return None
            print("[WARNING] Movie-ID was not passed! Using smart search...")
            res = self.search_movie_smart(
                movie_title=movie_title,
                release_year=release_year,
                language=language
            )
            if res is None:
                print("[WARNING] Failed to find movie id. Returning None!")
                return None
            else:
                print(f"[INFO] Found movie id: {res['id']}")
                movie_id = res['id']

        # ---------------------------------------------------------------------------
        # CALL TMDB API

        # API has a dynamic URL:
        if category=="details":
            url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        else:
            url = f"https://api.themoviedb.org/3/movie/{movie_id}/{category}"

        headers = {"accept": "application/json"}

        params = {
            "api_key": self.TMDB_API_KEY,
        }

        print(f"[INFO] Calling TMDB API for movie id {movie_id}...\nurl: {url}")
        response = requests.get(
            url,
            headers=headers,
            params=params
            )

        return response.json()

    
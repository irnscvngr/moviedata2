"""
Module specialized for scraping medimops data
"""
import re
import json
import time
import random
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from curl_cffi import requests
from unidecode import unidecode
from camoufox.sync_api import Camoufox
from moviedata.core.tools import hsl_to_rgb
from moviedata.core.scraper import scraper
from moviedata.core.database import pg_connect

class medimops(scraper):
    """
    """

    def __init__(self, timeout: int=10):
        """
        """
        super().__init__(domain="https://www.medimops.de/", timeout=timeout)
        self.userdata = None
        self.url_bluray_search = "https://www.medimops.de/Blu-ray,/?condition=UsedVeryGood%2CUsedGood%2CNewItem%2CLibriNew?searchparam="

    # -----------------------------------------------------------------------------------------------
    def _parse_blu_ray_search_results(self, soup: BeautifulSoup, movie_title: str) -> pd.DataFrame:
        """
        Take HTML-soup and movie title, the search for all search results.
        Only keep elements that match the movie-query.
        Return dataframe of parsed search results.
        """
        # Get all titles from search
        found_titles = soup.find_all(class_="ProductSearch_container__QteWl")
        print(f"[INFO] Found {len(found_titles)} titles!")

        # Only look at the first 8 results, because the rest wont match anyway...
        found_titles = found_titles[:8]

        # Init some stuff
        search_results_list = []
        search_results = {}

        # Extract price as float from HTML element
        def _get_price(elem):
            txt = (
                elem.text
                .replace("\xa0", " ")
                .replace("€","")
                .replace(",",".")
                .strip()
            )
            return float(txt)

        # Go through all search results
        for rank, search_res in enumerate(found_titles):
            # Product Title
            try:
                product_title = search_res.find(class_="ProductSearch_title__RhpT3").text.strip()
            except:
                print("[WARNING] Failed to parse product title! Skipping search result...")
                continue

            # Get title without any form of "blu ray"
            pattern = r'[\(\[]?\s*blu[\s\-]?ray\s*[\)\]]?'
            product_title_clean = re.sub(pattern, '', product_title, flags=re.IGNORECASE)

            # Check if product title matches query
            s0 = movie_title.lower() in product_title_clean.lower()
            s1 = product_title_clean.lower() in movie_title.lower()

            # Skip entry if product title doesn't match queried movie
            if not s0 and not s1:
                print(f"[WARNING] Search result didn't match query! Skipping...\nQuery: {movie_title}\nSearch result: {product_title}")
                continue

            print(f"[INFO] Search result matches query! Storing {product_title}")
            # Should check not skip iteration, store product title
            search_results['product_title'] = product_title
            # ....................................................................................................
            # Search rank
            search_results['product_rank'] = rank+1
            # ....................................................................................................
            # Product Link
            try:
                search_results['product_link'] = search_res.find("a")['href']
            except:
                print("[WARNING] Failed to parse product link! Storing None...")
                search_results['product_link'] = None
            # ....................................................................................................
            # Product Price Mobile
            try:
                search_results['product_price_mobile'] = _get_price(
                    search_res
                    .find(class_="ProductSearch_price__N58Fa", attrs={"data-testid":"product-price-display-mobile"}))
                # Product Price Desktop
                search_results['product_price_desktop'] = _get_price(
                                search_res
                                .find(class_="ProductSearch_price__N58Fa", attrs={"data-testid":"product-price-display-desktop"}))
            except:
                print("[WARNING] Failed to parse prices! Storing None...")
                search_results['product_price_mobile'] = None
                search_results['product_price_desktop'] = None
            # ....................................................................................................
            # Product Condition
            try:
                search_results['product_condition'] = (
                    search_res
                    .find(class_="ProductSearch_condition__810YM ProductSearch_flexColumn__HBtVh mobile-only")
                    .text.strip())
            except:
                print("[WARNING] Failed to parse condition! Storing None...")
                search_results['product_condition'] = None
            # ....................................................................................................
            # Append search result metadata to list
            search_results_list.append(search_results)

            # START: SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 
            # # Use this code to process product attributes directly from the product page
            # soup2 = self.get_soup(request_url=product_link)

            # prod_attrs = soup2.find_all(class_="ProductAttributes_row__ioma")
            # for prod_attr in prod_attrs:
            #     attr_type = prod_attr.find(class_="ProductAttributes_rowDefinition__8PGyQ").text.strip()
            #     attr_val = prod_attr.find(class_="ProductAttributes_rowValue__fWL3F").text.strip()

            #     if "ISBN" in attr_type:
            #         search_results['product_ISBN'] = attr_val

            #     if "Altersfreigabe" in attr_type:
            #         search_results['product_PG'] = attr_val

            #     if "Eigenschafen" in attr_type:
            #         search_results['product_properties'] = attr_val

            #     if "Format" in attr_type:
            #         search_results['product_format'] = attr_val

            #     if "Medium" in attr_type:
            #         search_results['product_medium'] = attr_val

            #     if "Anzahl" in attr_type:
            #         search_results['product_disc_count'] = attr_val

            #     if "ISBN" in attr_type:
            #         search_results['product_ISBN'] = attr_val
            # END: SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 SOUP2 

        if len(search_results_list)>0:
            df = (
                pd.DataFrame(search_results_list)
                .dropna(subset=['product_title','product_link','product_price_mobile','product_price_desktop'])
            )
            if df.shape[0] == 0:
                print("[WARNING] No usable search results!")
                return None
            else:
                print("[INFO] Product attributes parsed to data frame successfully!")
                return df
        else:
            print("[WARNING] No usable search results!")
            return None


    # -----------------------------------------------------------------------------------------------
    def get_blu_ray_data(self, df_scrape: pd.DataFrame):
        """
        Receives dataframe of movies to scrape on Medimops.
        Employs medimops' search to get results of possible matches.
        Then stores those results and writes to database.
        Further processing is needed to decide if a search-result
        really matches the search-term.
        """

        # Ensure index of DF starts at 0 and movie name is available
        s0 = df_scrape.shape[0]
        df_scrape = (
            df_scrape
            .dropna(subset='name')
            .reset_index(drop=True)
        )
        s1 = df_scrape.shape[0]
        if s1<s0:
            print(f"[WARNING] Dataframe contained missing 'name' values! Dropped rows from {s0} to {s1}!")

        # Initialize pg_connect object for database communication later
        pg = pg_connect()

        
        # -----------------------------------------------------------------------------------------------
        # PROCESS MOVIES
        # Initialize counter to monitor successful search results
        cnt_found = 0
        for i, row in df_scrape.iterrows():
            print("\n============================================================")
            print(f"[INFO] [{i+1}/{df_scrape.shape[0]}] Processing: EN: {row['name']} / DE: {row['title']}")

            movie_title = row['title']

            try:
                # ......................................................................
                # CREATE REQUEST URL
                # Define the new query parameters
                search_params = {
                    "searchparam": f"{movie_title} blu ray",
                    "fcIsSearch": 1,
                }

                # 1. Parse the base URL into components
                parsed_url = urlparse(self.url_bluray_search)

                # 2. Extract existing parameters and merge with new ones
                existing_params = dict(parse_qsl(parsed_url.query))
                existing_params.update(search_params)

                # 3. Re-encode parameters (spaces become '+' signs)
                new_query_string = urlencode(existing_params)

                # 4. Construct the full final URL
                request_url = urlunparse(parsed_url._replace(query=new_query_string))

                # ......................................................................
                print(f"[INFO] GET request for: {request_url}")
                soup = self.get_soup(request_url=request_url)
                df_res = self._parse_blu_ray_search_results(soup, movie_title)
                if df_res is not None:
                    cnt_found += 1
                    print("[INFO] Scrape successful!")
                else:
                    print("[WARNING] Scrape worked but empty results! Skipping movie...")
                    continue
            except Exception as e:
                print(f"[WARNING] Scrape failed! Skipping movie...{e}")
                continue

            # ......................................................................
            # Add master data to DF
            df_res['title'] = row['title']
            df_res['letterboxd_name'] = row['name']
            df_res['letterboxd_uri'] = row['letterboxd_uri']

            # Write results to database
            pg.write_df_to_postgres(
                df=df_res,
                table_name="product_lines",
                schema_name="medimops"
            )

            print("[INFO] Search results successfully written to database!")
            print(f"[INFO] Found {cnt_found}/{df_scrape.shape[0]} movies.")

            # Wait a little bit. Do it randomly be less suspicious
            time.sleep(random.random()*1.0)

        print(f"[INFO] Medimops Blu Ray scraping completed!")
        print(f"[INFO] Found {cnt_found}/{df_scrape.shape[0]} movies total.\n")

"""
Module specialized for scraping rottentomatoes data
"""
import re
import json
import time
import random
import pandas as pd
from bs4 import BeautifulSoup
from unidecode import unidecode
from camoufox.sync_api import Camoufox
from moviedata.core.tools import hsl_to_rgb, parse_name_for_url
from moviedata.core.scraper import scraper
from moviedata.core.database import pg_connect

class rottentomatoes(scraper):
    """
    """

    def __init__(self, timeout: int=10):
        """
        """
        super().__init__(domain="https://www.rottentomatoes.com", timeout=timeout)
        self.userdata = None

    def parse_rt_search_results(self, name:str, year:int) -> str:
        """
        Receives movie name and release year.
        Performs search on rottentomatoes.
        Either finds movie directly or chooses movie within
        threshold distance of time.
        e.g. search for 2026, result shows 2025 -> pick 2025 result
        if search for 2025 shows results for 1972, do not use result.

        Input:
        - name      Movie name
        - year      Movie release year

        Returns:
        - res_url   URL to rottentomatoes page of movie
        """
        year = int(year)
        print(f"\n[INFO] Performing RT search! | {name} ({year})")

        # ============================================================
        # Helper function to query RT for search by URL
        def get_rt_search_results(search_url_parsed):
            """
            Function to call RT with a parsed URL and return list of dictionaries with search results.
            """
            # Perform search on RottenTomatoes
            soup = self.get_soup(request_url=search_url_parsed)
    
            # Store search result HTML to disk
            # with open(f"rotten_searchresults_soup {name} {year}.html", "w", encoding="utf-8") as file:
            #     file.write(soup.prettify())
    
            search_res = soup.find_all(attrs={"data-qa":"search-result"})
            print(f"[INFO] Search returned {len(search_res)} results!")
    
            # Initialize list to store search results
            search_res_parsed = []
    
            # Go through all search results
            for el in search_res:
                # Extract data row from search result
                data_row = el.find(attrs={'data-qa':'data-row'})
    
                # Get release year
                year_rt = data_row.get('release-year')
                if year_rt is not None:
                    year_rt = year_rt.strip()
    
                # Get name and URL
                el_info = data_row.find(attrs={'data-qa':'info-name'})
                name_rt = el_info.text
                url_rt = el_info.get('href')
                if name_rt is not None:
                    name_rt = name_rt.strip()
                if url_rt is not None:
                    url_rt = url_rt.strip()

                # Store results
                res = {
                    'name':name_rt,
                    'year':year_rt,
                    'url':url_rt
                }
                search_res_parsed.append(res)

                # If search is conclusive stop and return True flag
                if (name_rt is not None) and (year_rt is not None):
                    if (name_rt == name) and (int(year_rt) == int(year)):
                        return True, res

            # Return flag for inconclusive search (=False) and list of search results
            return False, search_res_parsed

        # ============================================================
        # Helper function to process the search results returned from RT
        def examine_rt_search_results(search_res_parsed):
            """
            Go through list of search results and find best candidate.
            """
            if len(search_res_parsed) == 1:
                df_search_res = pd.DataFrame(search_res_parsed, index=[0])
            else:
                df_search_res = pd.DataFrame(search_res_parsed)
    
            # Cast year-column as float (includes NaN) to get time difference
            df_search_res['year'] = df_search_res['year'].astype(float)
    
            # Get difference between release-year from RT and release-year from search
            df_search_res['year_dif'] = (df_search_res['year'] - int(year)).abs()

            # Movie lowest time difference to the top
            df_search_res= df_search_res.sort_values('year_dif')
    
            # Sort results by time difference and take top candidate
            best_res = df_search_res.iloc[0,:].to_dict()

            return best_res, df_search_res

        # ============================================================
        # Helper function in case results are not conclusive
        def process_inconclusive_results(df_search_res:pd.DataFrame):
            """
            Some results are inconclusive.
            Check for release-year differences and parse names
            to potentially find a correct result.
            """
            if (df_search_res.loc[0,'name'] == name) and (df_search_res.loc[0,'year_dif'] == 0.0):
                print("[INFO] 🟢 Found conclusive search result!")
                return df_search_res.loc[0,'url']

            if (df_search_res.loc[0,'name'] == name) and (df_search_res.loc[0,'year_dif'] <= 1.0):
                print("[INFO] 🟢 Found search result within one year range!")
                return df_search_res.loc[0,'url']

            # ...............................................................................................
            # Parse names for comparison (in cases like Alien³)
            
            # Init parsed names
            name_parsed = name.lower()
            name_rt_parsed = df_search_res.loc[0,'name'].lower()

            # Check if ampersand and literal "and" appear in both names.
            # If yes - remove it completely to avoid umambiguity
            if ("&" in f"{name_parsed} {name_rt_parsed}") and ("and" in f"{name_parsed} {name_rt_parsed}"):
                name_parsed = name_parsed.replace("&","")
                name_parsed = name_parsed.replace("and","")
                name_rt_parsed = name_rt_parsed.replace("&","")
                name_rt_parsed = name_rt_parsed.replace("and","")

            # Do the same for percent
            if ("%" in f"{name_parsed} {name_rt_parsed}") and ("percent" in f"{name_parsed} {name_rt_parsed}"):
                name_parsed = name_parsed.replace("%","")
                name_parsed = name_parsed.replace("percent","")
                name_rt_parsed = name_rt_parsed.replace("%","")
                name_rt_parsed = name_rt_parsed.replace("percent","")

            # ...............................................................................................
            # Use dedicated function to do the remaining parsing
            name_parsed = parse_name_for_url(
                name_parsed,
                regular_url_parse=False,
                force_ascii_characters=True,
                remove_all_symbols=True,
                remove_whitespace=True
                )
            name_rt_parsed = parse_name_for_url(
                name_rt_parsed,
                regular_url_parse=False,
                force_ascii_characters=True,
                remove_all_symbols=True,
                remove_whitespace=True
                )

            print(f"[WARNING] Failed to find candidate with given names. Now comparing adjusted names: '{name_parsed}' (search) and '{name_rt_parsed}' (RT-return)")
    
            if (name_parsed == name_rt_parsed) and (df_search_res.loc[0,'year_dif'] == 0.0):
                print("[INFO] 🟢 Found conclusive search result with parsed names!")
                return df_search_res.loc[0,'url']
    
            if (name_parsed == name_rt_parsed) and (df_search_res.loc[0,'year_dif'] <= 1.0):
                print("[INFO] 🟢 Found search result with parsed names and within one year range!")
                return df_search_res.loc[0,'url']

            if (set(name_parsed)==set(name_rt_parsed)) and (abs(1 - 1.0*len(name_parsed)/len(name_rt_parsed))<0.2):
                print("[INFO] 🟢 Found search result by name similarity and within one year range!")
                return df_search_res.loc[0,'url']

            # If all fails, return None
            return None
            
        # ===========================================================================
        # PERFORM SEARCH WITH NAME ONLY

        # Build search URL from movie name only (also adjust symbols etc.)
        search_url_parsed = "https://www.rottentomatoes.com/search?search=" + parse_name_for_url(name, regular_url_parse=True)

        # Perform RT-search
        print(f"[INFO] Created search-URL: {search_url_parsed}")        
        conclusive_flag, search_res_parsed = get_rt_search_results(search_url_parsed)

        # If search was conclusive flag is True and search_res_parsed is dictionary for respective search result.
        # Return URL directly
        if conclusive_flag:
            print("[INFO] 🟢 Found conclusive search result!")
            return search_res_parsed['url']

        # ...........................................................................
        # PROCESS INCONCLUSIVE SEARCH RESULTS
        # (Only executes if conclusive_flag was False)

        print("[WARNING] ❌ Search results inconclusive! Examining list...")

        _, df_search_res = examine_rt_search_results(search_res_parsed)

        res_url = process_inconclusive_results(df_search_res)

        if res_url is not None:
            return res_url

        # ===========================================================================
        # PERFORM SEARCH WITH NAME AND YEAR
        print("[WARNING] ❌ Search results still inconclusive! Performing new search with name and year...")

        # Build search URL from movie name and year (also adjust symbols etc.)
        search_url_parsed = "https://www.rottentomatoes.com/search?search=" + parse_name_for_url(f"{name} {year}", regular_url_parse=True)

        # Perform RT-search
        print(f"[INFO] Created search-URL: {search_url_parsed}")        
        conclusive_flag, search_res_parsed = get_rt_search_results(search_url_parsed)

        # If search was conclusive flag is True and search_res_parsed is dictionary for respective search result.
        # Return URL directly
        if conclusive_flag:
            print("[INFO] 🟢 Found conclusive search result!")
            return search_res_parsed['url']

        # ...........................................................................
        # PROCESS INCONCLUSIVE SEARCH RESULTS
        # (Only executes if conclusive_flag was False)

        print("[WARNING] ❌ Search results inconclusive! Examining list...")

        _, df_search_res = examine_rt_search_results(search_res_parsed)

        res_url = process_inconclusive_results(df_search_res)
        
        if res_url is not None:
            return res_url

        # ===========================================================================
        # SEARCH FAILED
        print("[WARNING] ❌ Both search attempts failed! Returning None...")
        return None

    
    def get_movie_data(self, df_scrape: pd.DataFrame):
        """
        Take dataframe as list for scraping.
        Then go through all listed movies and scrape
        rottentomatoes data.

        Input:
        - df_scrape | necessary columns: name, year

        """
        # Set year of DF as integer (sometimes is float)
        df_scrape['year'] = df_scrape['year'].astype(int)

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

        def get_movie_metadata(soup) -> dict:
            """
            Receives soup from rottentomatoes, processes it and returns movie metadata
            """
            # Initialize dict to store rotten tomatoes metadata
            movie_metadata = {}

            # ==============================================================================================================
            # Get mediaHero (=JSON) to get basic movie-metadata (e.g. release-year)
            try:
                rt_film_data = (
                    json.loads(
                        soup
                        .find("script", attrs={"data-json":"rateAndReviewModule"})
                        .text
                    )
                )
            except:
                print("[WARNING] No release date information found in HTML! Returning None")
                return None

            try:
                # Extracts release_date in the original shape (e.g. "Dec 19, 1997")
                release_date = rt_film_data['releaseDate']
                # Converts to standard format (e.g. 19-12-1997)
                release_date = pd.to_datetime(release_date).strftime("%d-%m-%Y")
                # Store release date in result dict
                movie_metadata['release_date'] = release_date
            except Exception:
                print("[WARNING] Failed to parse release_date. Returning None.")
                return None

            # ==============================================================================================================
            # Get media score card (=JSON) that holds most of the critics-related information
            print("[INFO] Get media score card from soup...")
            rt_film_data = (
                json.loads(
                    soup
                    .find("script", attrs={"data-json":"mediaScorecard"})
                    .text
                    )
            )

            print("[INFO] Extract info from media score card...")
            # ==============================================================================================================
            # CERTIFIED FRESH
            try:
                movie_metadata['certified_fresh'] = rt_film_data['audienceScore']['certifiedFresh']
            except Exception:
                print("[WARNING] Failed to parse certified fresh. Returning None.")
                movie_metadata['certified_fresh'] = None

            # --------------------------------------------------------------------------------------------------------------
            # CRITICS
            try:
                movie_metadata['critics_score'] = int(rt_film_data['criticsScore']['score'])
            except Exception:
                print("[WARNING] Failed to parse critics score. Returning None.")
                movie_metadata['critics_score'] = None

            try:
                movie_metadata['critics_avg_rating'] = float(rt_film_data['criticsScore']['averageRating'])
            except Exception:
                print("[WARNING] Failed to parse critics avg rating. Returning None.")
                movie_metadata['critics_avg_rating'] = None

            try:
                movie_metadata['critics_liked_cnt'] = int(rt_film_data['criticsScore']['likedCount'])
            except Exception:
                print("[WARNING] Failed to parse critics liked cnt. Returning None.")
                movie_metadata['critics_liked_cnt'] = None

            try:
                movie_metadata['critics_not_liked_cnt'] = int(rt_film_data['criticsScore']['notLikedCount'])
            except Exception:
                print("[WARNING] Failed to parse critics not liked cnt. Returning None.")
                movie_metadata['critics_not_liked_cnt'] = None

            try:
                movie_metadata['critics_sentiment'] = rt_film_data['criticsScore']['sentiment']
            except Exception:
                print("[WARNING] Failed to parse critics sentiment. Returning None.")
                movie_metadata['critics_sentiment'] = None

            # --------------------------------------------------------------------------------------------------------------
            # AUDIENCE
            try:
                movie_metadata['audience_score'] = int(rt_film_data['audienceScore']['score'])
            except Exception:
                print("[WARNING] Failed to parse audience score. Returning None.")
                movie_metadata['audience_score'] = None

            try:
                movie_metadata['audience_avg_rating'] = float(rt_film_data['audienceScore']['averageRating'])
            except Exception:
                print("[WARNING] Failed to parse audience avg rating. Returning None.")
                movie_metadata['audience_avg_rating'] = None

            try:
                movie_metadata['audience_liked_cnt'] = int(rt_film_data['audienceScore']['likedCount'])
            except Exception:
                print("[WARNING] Failed to parse audience liked cnt. Returning None.")
                movie_metadata['audience_liked_cnt'] = None

            try:
                movie_metadata['audience_not_liked_cnt'] = int(rt_film_data['audienceScore']['notLikedCount'])
            except Exception:
                print("[WARNING] Failed to parse audience not liked cnt. Returning None.")
                movie_metadata['audience_not_liked_cnt'] = None

            try:
                movie_metadata['audience_sentiment'] = rt_film_data['audienceScore']['sentiment']
            except Exception:
                print("[WARNING] Failed to parse audience sentiment. Returning None.")
                movie_metadata['audience_sentiment'] = None

            # --------------------------------------------------------------------------------------------------------------
            # CONSENSUS
            try:
                consensus = (
                    soup
                    .find(class_="consensus")
                    .find("p")
                    .text
                )
                movie_metadata['consensus'] = consensus
            except Exception:
                print("[WARNING] Failed to parse consensus. Returning None.")
                movie_metadata['consensus'] = None

            # --------------------------------------------------------------------------------------------------------------
            # DESCRIPTION
            try:
                movie_metadata['description'] = rt_film_data['description']
            except Exception:
                print("[WARNING] Failed to parse description. Returning None.")
                movie_metadata['description'] = None

            # ==============================================================================================================
            # POSTER IMAGES

            # BIG IMAGE
            print("[INFO] Get media hero block from soup...")
            media_hero = (
                json.loads(
                    soup
                    .find(
                        "script",
                        attrs={"data-json":"mediaHero",
                            "id":"media-hero-json"
                            }
                        )
                    .text
                )
            )

            # Convert average title image color to RGB
            try:
                col_hsl = [float(c.replace('%','')) for c in media_hero['averageColorHsl'].split(',')]
                movie_metadata['img_title_avg_color_rgb'] = hsl_to_rgb(col_hsl)
            except Exception:
                print("[WARNING] Failed to parse avg. title image color. Returning None.")
                movie_metadata['img_title_avg_color_rgb']

            # Title image link
            try:
                movie_metadata['img_title'] = media_hero['content']['primaryVideo']['thumbnail']['url']
            except Exception:
                print("[WARNING] Failed to parse title image link. Returning None.")
                movie_metadata['img_title'] = None

            # Movie poster
            try:
                movie_metadata['img_poster'] = (
                    soup
                    .find("rt-img", attrs={'slot':'poster-image', 'alt':'poster image'})
                    ['src']
                )
            except Exception:
                print("[WARNING] Failed to parse poster image link. Returning None.")
                movie_metadata['img_poster'] = None

            # Trailer IDs
            try:
                mpx_id = media_hero['content']['primaryVideo']['mpxId']
                public_id = media_hero['content']['primaryVideo']['publicId']

                movie_metadata['trailer_theplatform_mpxid'] = mpx_id
                movie_metadata['trailer_theplatform_public_id'] = public_id
            except Exception:
                print("[WARNING] Failed to parse trailer IDs. Returning None.")
                movie_metadata['trailer_theplatform_mpxid'] = None
                movie_metadata['trailer_theplatform_public_id'] = None


            # ==============================================================================================================
            # RECOMMENDATIONS
            print("[INFO] Get carousel slider from content wrap in soup to find recommendations...")
            try:
                content_wraps = soup.find_all(class_="content-wrap")

                # There are multiple content-wraps in soup
                # Go through them and find the one containing a carousel-slider with
                # a "tile-poster-card" -> That's the one containing recommendations
                for cw in content_wraps:
                    cs = cw.find("carousel-slider")
                    try:
                        tpc = cs.find_all("tile-poster-card")
                    except:
                        pass

                    if isinstance(tpc,list):
                        if len(tpc)>0:
                            break

                # Extract necessary information from recommendation-elements
                # in carousel-slider/tile-poster-card
                def _extract_elem_info(el):
                    try:
                        res = {}
                        res['name'] = el.find("sr-text").text
                        res['link'] = el.find("rt-link")['href']
                        res['critics_score'] = (
                            el
                            .find("rt-text", attrs={'slot':'critics-score'})
                            .text
                            .strip()
                            .replace("%","")
                        )
                        res['audience_score'] = (
                                el
                                .find("rt-text", attrs={'slot':'audience-score'})
                                .text
                                .strip()
                                .replace("%","")
                            )
                        return res
                    except:
                        print("[WARNING] Failed to process recommendation element! Returning None.")
                        return None

                # Process all recommendation elements
                recom_processed = [_extract_elem_info(el) for el in tpc[:-1]]
                movie_metadata['recommendations'] = [c for c in recom_processed if c is not None]
            except:
                print("[WARNING] Failed to parse recommendations. Returning None.")
                movie_metadata['recommendations'] = None

            return movie_metadata

        def qa_movie_metadata(movie_metadata):
            """
            Quick QA-function testing the presence
            of vital metadata values.
            
            Returns True if data is OK, else returns False.
            """
            is_ok = True

            if ((movie_metadata['critics_score'] is None) or
                (movie_metadata['audience_score'] is None) or
                (movie_metadata['release_date'] is None)):
                is_ok = False

            return is_ok

        for i, row in df_scrape.iterrows():
            print("\n============================================================")
            print(f"[INFO] [{i+1}/{df_scrape.shape[0]}] Processing: {row['name']} ({row['year']})")

            # ==========================================================================================
            # GET MOVIE URL AND SOUP
            movie_url = self.parse_rt_search_results(name=row['name'], year=row['year'])

            if movie_url is None:
                print("[WARNING] Could not obtain movie URL. Skipping movie...")
                continue
        
            # Get soup of movie page
            print("[INFO] Performing GET request and parsing soup...")
            # Initialize soup as None and error count to zero
            soup = None

            try:
                soup = self.get_soup(request_url=movie_url)
                print("[INFO] Using simple movie name successful - soup obtained!")
            except:
                print("[WARNING] Failed to get soup! Skipping movie...")
                continue

            # ==========================================================================================
            # GET MOVIE METADATA
            print("[INFO] Parsing movie metadata from soup...")

            movie_metadata = get_movie_metadata(soup)

            if movie_metadata is None:
                print("[WARNING] Failed to obtain movie metadata! Skipping movie...")
                continue

            print("............................................................")
            print("[INFO] Metadata parsed successfully!")

            # Validate returned metadata
            if not qa_movie_metadata(movie_metadata):
                print("[WARNING] Movie metadata is missing vital values! Skipping movie...")
                continue
            else:
                print("[INFO] QA of movie data successful!")

            # -----------------------------------------------------------------
            # Add movie title, year and letterboxd uri to metadata dictionary
            print("[INFO] Metadata parsed successfully! Adding base info to dictionary...")
            movie_metadata['name'] = row['name']
            movie_metadata['year_query'] = row['year']
            if 'letterboxd_uri' in row.index:
                movie_metadata['letterboxd_uri'] = row['letterboxd_uri']
            else:
                movie_metadata['letterboxd_uri'] = None
        
            # Add rotten tomatoes URL that was used
            movie_metadata['rottentomatoes_uri'] = movie_url
            print("[INFO] Base info added to metadata dictionary.")

            # -----------------------------------------------------------------
            # Convert movie metadata to pandas DF and write to database
            print("[INFO] Writing to database...")
            df_out = pd.DataFrame([movie_metadata])
            print(f"[INFO] Writing dataframe of shape {df_out.shape} to database...")
            # Write DF to DB
            pg.write_df_to_postgres(
                df=df_out,
                table_name="rotten__all_movies_metadata",
                schema_name="1_bronze",
                add_timestamp=True
            )

            print("[INFO] Movie processing completed successfully!\n")

            # Wait a little bit. Do it randomly be less suspicious
            time.sleep(random.random()*0.5)

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
from moviedata.core.tools import hsl_to_rgb
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
    
    def get_movie_data(self, df_scrape: pd.DataFrame, preprocess_title=True):
        """
        Take dataframe as list for scraping.
        Then go through all listed movies and scrape
        rottentomatoes data.

        Input:
        - df_scrape | necessary columns: name, year, letterboxd_uri

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

        def get_movie_metadata(soup) -> dict:
            """
            Receives soup from rottentomatoes, processes it and returns movie metadata
            """
            # Initialize dict to store rotten tomatoes metadata
            movie_metadata = {}

            # ==============================================================================================================
            # Get media score card that holds most of the information
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
                (movie_metadata['audience_score'] is None)):
                is_ok = False

            return is_ok

        def movie_name_for_rt_url(movie_name):
            """
            Receives a "regular" movie name from Letterboxd
            (natural spelling).
            Then transforms it for usage in rottentomatoes URL.
            """
            # Replace all accents or otherwise non-ASCII characters with regular characters
            # è -> e, ö -> o, ß -> ss
            movie_name = unidecode(movie_name)
            # Replace "&" with written "and"
            movie_name = movie_name.replace("&","and")
            # Replace "%" with written "percent"
            movie_name = movie_name.replace("%","percent")
            # Remove all symbols from the movie name
            movie_name = re.sub(r'[^\w\s]', '', movie_name)
            # Replace empty space with underscores and make all lower chars
            movie_name = (
                movie_name
                .replace(" ","_")
                .lower()
            )
            # Find 2 or more consecutive underscores and replace with a single underscore
            # e.g. Louise__Thelma -> Louise_Thelma
            movie_name = re.sub(r'_{2,}', '_', movie_name)

            return movie_name

        for i, row in df_scrape.iterrows():
            print("\n============================================================")
            print(f"[INFO] [{i+1}/{df_scrape.shape[0]}] Processing: {row['name']} ({row['year']})")

            # Make movie name for URL
            # (Either preprocess or not - depending on DF source)
            if preprocess_title:
                movie_name = movie_name_for_rt_url(row['name'])
            else:
                movie_name = row['name']
            
            print(f"[INFO] Adjusted movie name for URL usage to: {movie_name}")
        
            # Basic movie URL:
            movie_url = f"https://www.rottentomatoes.com/m/{movie_name}"
            print(f"[INFO] URL: {movie_url}")
        
            # ------------------------------------------------------------------------------------------
            # Get soup of movie page
            print("[INFO] Performing GET request and parsing soup...")
            # Initialize soup as None and error count to zero
            soup = None

            # ..........................................................................................
            # Bare movie name:
            if soup is None:
                try:
                    movie_url = f"https://www.rottentomatoes.com/m/{movie_name}"
                    print(f"[INFO] Trying simple movie name for URL... {movie_url}")
                    soup = self.get_soup(request_url=movie_url)
                    print("[INFO] Using simple movie name successful - soup obtained!")
                except:
                    print("[WARNING] Simple movie name for URL failed!")
            # ..........................................................................................
            # Movie name with release year
            if soup is None:
                try:
                    movie_url = f"https://www.rottentomatoes.com/m/{movie_name}_{row['year']}"
                    print(f"[INFO] Trying movie name with added release year... {movie_url}")
                    soup = self.get_soup(request_url=movie_url)
                    print("[INFO] Using movie name and release year successful - soup obtained!")
                except:
                    print("[WARNING] Movie name with added release year failed!")
            # ..........................................................................................
            # Movie name without "the" at the beginning
            if (soup is None) and (movie_name.startswith("the")):
                try:
                    movie_name2 = movie_name[4:].strip() # Start at index 4 because to avoid '_' at the start
                    movie_url = f"https://www.rottentomatoes.com/m/{movie_name2}"
                    print(f"[INFO] Trying movie name without 'the' at the beginning... {movie_url}")
                    soup = self.get_soup(request_url=movie_url)
                    print("[INFO] Using movie name without 'the' successful - soup obtained!")
                except:
                    print("[WARNING] Movie name without 'the' failed!")
            # ..........................................................................................
            # Movie name without "the" at the beginning AND with added release year
            if (soup is None) and (movie_name.startswith("the")):
                try:
                    movie_name2 = movie_name[4:].strip() # Start at index 4 because to avoid '_' at the start
                    movie_url = f"https://www.rottentomatoes.com/m/{movie_name2}_{row['year']}"
                    print(f"[INFO] Trying movie name without 'the' and with added release year... {movie_url}")
                    soup = self.get_soup(request_url=movie_url)
                    print("[INFO] Using movie name without 'the' successful - soup obtained!")
                except:
                    print("[WARNING] Movie name without 'the' and with added release year failed!")
            # ..........................................................................................
            if soup is None:
                print("[WARNING] Failed to parse any soup! Skipping movie...")
                continue

            # ==========================================================================================
            # Get movie metadata
            print("[INFO] Parsing movie metadata from soup...")
            # Some movies, e.g. Prometheus, use the year in the URL of rotten tomatoes:
            # https://www.rottentomatoes.com/m/prometheus_2012
            # Try without year first:
            movie_metadata = get_movie_metadata(soup)
            print("............................................................")
            print("[INFO] Metadata parsed successfully!")

            # Should URL without year return None on critical values
            # try again with year in the URL
            if not qa_movie_metadata(movie_metadata):
                try:
                    print("[WARNING] Movie metadata missing vital values. Trying again with release year in URL...")
                    soup = self.get_soup(request_url=f"{movie_url}_{row['year']}")
        
                    movie_metadata = get_movie_metadata(soup)
                    print("[INFO] New request using release year succesful! Performing QA...")
                except:
                    print("[WARNING] New request using release year in URL failed!")

            # Skip further processing if dictionary still does not fit requirements
            if not qa_movie_metadata(movie_metadata):
                print("[WARNING] Movie metadata is still missing vital values! Skipping movie entirely!")
                continue
            else:
                print("[INFO] Final QA of movie data successful!")

            # -----------------------------------------------------------------
            # Add movie title, year and letterboxd uri to metadata dictionary
            print("[INFO] Metadata parsed successfully! Adding base info to dictionary...")
            movie_metadata['name'] = row['name']
            movie_metadata['year'] = row['year']
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
            # Write DF to DB
            pg.write_df_to_postgres(
                df=df_out,
                table_name="rotten__all_movies_metadata",
                schema_name="1_bronze",
                add_timestamp=False
            )

            print("[INFO] Movie processing completed successfully!\n")

            # Wait a little bit. Do it randomly be less suspicious
            time.sleep(random.random()*0.5)

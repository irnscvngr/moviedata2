"""
Module to update database
"""
from datetime import datetime
import pytz
import json
import time
import re

import pandas as pd

from moviedata.core import tools
from moviedata.core.database import pg_connect
from moviedata.sources.letterboxd import letterboxd
from moviedata.sources.rottentomatoes import rottentomatoes
from moviedata.sources.medimops import medimops
from moviedata.sources.choices import choices
from moviedata.sources.tmdb import tmdb

class updater:
    """
    """
    def __init__(self):
        pg_con = pg_connect()
        self.pg_con = pg_con

    def update_letterboxd(self, table_select=[]):
        """
        Get userdata from letterboxd and update all related database tables.
        Provide explicit list of table-names (from postgres) to only update
        selected tables.
        """
        print("\n==================================================")
        print("[INFO] Letterboxd update pipeline started!")

        # Convert table_select to list if user entered string
        if isinstance(table_select,str):
            table_select = [table_select]

        # Get current letterboxd userdata
        lb = letterboxd()
        lb.get_userdata()

        # Get letterbox import configurations from config file
        letterboxd_config_filepath = "src/moviedata/services/configs/letterboxd_config.json"
        with open(letterboxd_config_filepath, "rb") as f:
            letterboxd_config = json.load(f)

        # If table select is empty, load all tables
        if not table_select:
            table_select = list(letterboxd_config.keys())

        for table, config in letterboxd_config.items():
            if table not in table_select:
                print(f"[INFO] Table {table} not selected! Skipping...")
                continue
            print(f"[INFO] Processing table {table}...")
            file = tools.extract_file_from_zip_io(lb.userdata, config['filepath'])

            # If information is available in config, use explicit column import
            if config['usecols']:
                df = pd.read_csv(file, skiprows=config['skiprows'], usecols=config['usecols'])
            else:
                df = pd.read_csv(file, skiprows=config['skiprows'])

            # If set in config, rename certain columns
            if config['rename_cols']:
                df = df.rename(columns=config['rename_cols'])

            # Add load timestamp with timezone
            tz = pytz.timezone('Europe/Berlin')
            df['load_timestamp'] = datetime.now(tz)

            # Write data to database
            try:
                print(f"[INFO] Overwrite table: {config['overwrite']}")
                self.pg_con.write_df_to_postgres(
                    df,
                    table_name=f"ltboxd__{table}",
                    schema_name="1_bronze",
                    overwrite=config['overwrite']
                )
            except Exception as e:
                print(f"[WARNING] Failed to write table {table} to database! Skipping table...\n{e}")
                continue

        print("\n[INFO] Letterboxd update pipeline finished!\n")


    def update_rottentomatoes(self):
        """
        """
        print("\n==================================================")
        print("[INFO] Rottentomatoes update pipeline started!")

        # 1 - Load view "rt_movies_for_metadata_scraping" from rottentomatoes schema
        df = self.pg_con.read_df_from_postgres(
            table_name="rotten__movies_for_metadata_scraping",
            schema_name="2_silver",
            limit=None
        )

        # 2 - Scrape respective movies and append new data to
        # table "rt_all_movies_metadata"
        rt = rottentomatoes()
        rt.get_movie_data(df_scrape=df, preprocess_title=True)

        print("[INFO] Rottentomatoes update pipeline finished!\n")


    def update_medimops(self):
        """
        """
        print("\n==================================================")
        print("[INFO] Medimops update pipeline started!")

        # 1 - Load view "shop_candidates" from public schema
        df = self.pg_con.read_df_from_postgres(
            table_name="shop_candidates",
            schema_name="3_gold",
            limit=None
        )

        # 2 - Scrape respective movies and append new data to
        # table "rt_all_movies_metadata"
        mm = medimops()
        mm.get_blu_ray_data(df_scrape=df)

        print("[INFO] Medimops update pipeline finished!\n")


    def update_choices_current_screenings(self):
        """
        """
        print("\n==================================================")
        print("[INFO] Choices update - get current screenings - pipeline started!")

        # Get all current movie showings from choices.de and write to database
        cs = choices()
        cs.get_all_movies()

        print("[INFO] Choices update - get current screenings - pipeline finished!\n")


    def update_choices_tmdb_data(self):
        """
        [DEPRECATED]
        Check this function again
        -> First SQL makes no sense
        -> If join criteria is b.title_german, then b.title_german can never be NULL
        """
        print("\n==================================================")
        print("[INFO] Choices update - get TMDB data - pipeline started!")

        df_movie_select = self.pg_con.sql_query(
            """
            SELECT *
            FROM "1_bronze"."choics__current_movies" a
            LEFT JOIN "1_bronze"."tmdb__movie_details" b
            ON a.title = b.title_german
            AND a.year = EXTRACT(year from b.release_date)
            WHERE b.title_german IS NULL;
            """
        )

        tm = tmdb()

        for i,row in df_movie_select.iterrows():
            print("\n--------------------------------------------------")
            print(f"[INFO] ({i+1}/{df_movie_select.shape[0]}) Processing '{row['title']}'")

            # .................................................................
            # GET DATA - DETAILS
            print("[INFO] Receiving details information from TMDB API...")
            res = tm.get_movie_data(
                movie_title=row['title'],
                release_year=row['year'],
                language='de-DE',
                category='details'
            )

            if res is None:
                print("[WARNING] Failed to obtain movie details! Skipping movie...")
                continue

            # Extract movie_id
            movie_id = res['id']
            print(f"[INFO] Found movie on TMDB! Title: '{res['title']}'")

            # Extract necessary parts of API-response
            skip_keys = ['adult','status','video','softcore','belongs_to_collection']
            res_filt = {key:val for key,val in res.items() if not (isinstance(val,dict) or isinstance(val,list)) and key not in skip_keys}

            # Make dataframe from filtered API-response and adjust to write to database
            df_res = (
                pd.DataFrame([res_filt])
                .rename(columns={
                    'id':'tmdb_id',
                    'title':'title_tmdb'
                    })
            )
            # Add german title as well
            df_res['title_german'] = row['title']

            # Write to database
            self.pg_con.write_df_to_postgres(
                df=df_res,
                schema_name="tmdb",
                table_name="movie_details",
                add_timestamp=True
            )
            print("[INFO] Successfully wrote movie details information to database!")

            # .................................................................
            # GET DATA - RELEASE DATES
            print("[INFO] Receiving release dates information from TMDB API...")
            res = tm.get_movie_data(
                movie_id=movie_id,
                category='release_dates'
            )

            if res is None:
                print("[WARNING] Failed to obtain movie release dates! Continuing with next movie...")
                continue

            if "results" not in list(res.keys()):
                print("[WARNING] 'results'-key not found in API-response! Continuing with next movie...")
                continue

            # Extract German release from results
            res_x = None
            for r in res['results']:
                if r['iso_3166_1'] == 'DE':
                    res_x = r['release_dates']

            if res_x is None:
                print("[WARNING] No German release information in API-response! Continuing with next movie...")
                continue

            print("[INFO] Successfully found German release information!")

            # Extract theatrical release from potential multiple release informations
            # (See API-reference: https://developer.themoviedb.org/reference/movie-release-dates)
            res_x_t = None
            if isinstance(res_x, list):
                for r in res_x:
                    if r['type'] == 3:
                        res_x_t = r
            if isinstance(res_x, dict):
                print(f"res_x: {res_x}")
                if res_x['type'] == 3:
                    res_x_t = res_x

            print("[INFO] Specified release information extracted!")

            if res_x_t is None:
                print("[WARNING] No theatrical release information found in API-response! Continuing with next movie...")
                continue

            # Postprocess API-result as it can contain empty strings or empty lists
            for key,val in res_x_t.items():
                if (val == '') or (val == []):
                    res_x_t[key] = None

            # Make dataframe from filtered API-response and adjust to write to database
            df_res = (
                pd.DataFrame([res_x_t])
                [['certification','descriptors','release_date']]
            )
            df_res['tmdb_id'] = movie_id
            df_res['title_german'] = row['title']

            # Write to database
            self.pg_con.write_df_to_postgres(
                df=df_res,
                schema_name="tmdb",
                table_name="movie_release_dates",
                add_timestamp=True
            )
            print("[INFO] Successfully wrote movie release dates information to database!")

            # .................................................................
            # Wait a little bit to not overflow the API
            time.sleep(0.1)

        print("[INFO] Choices update - get TMDB data - pipeline finished!\n")


    def update_tmdb_from_url(self, tmdb_url:str):
        """
        Takes TMDB-URL, extracts movie ID and adds it to TMDB tables.
        """
        # ......................................................................
        # EXTRACT FROM URL WITH REGEX

        # Get movie id
        match = re.search(r"movie\/([0-9]+)", tmdb_url)
        if match is None:
            print("[WARNING] No movie ID found in URL! Returning None!")
            return None
        else:
            movie_id = match.group(1)
            print(f"[INFO] Found movie ID '{movie_id}'!")

        # ......................................................................
        # GET MOVIE DATA

        tm = tmdb()
        # Get english movie data
        res = tm.get_movie_data(
            movie_id=movie_id,
            language='en-US')
        # Make pandas dataframe from english data
        df_res = tm.movie_data_to_dataframe(res)

        # Get German title
        res = tm.get_movie_data(
            movie_id=movie_id,
            language='de-DE')

        # Add German title
        title_german = res['title']
        df_res['title_german'] = title_german

        # .................................................................
        # WRITE TO DATABASE
        self.pg_con.write_df_to_postgres(
            df=df_res,
            schema_name="1_bronze",
            table_name="tmdb__movie_details",
            add_timestamp=True
        )
        print("[INFO] Successfully wrote movie details information to database!")

        # .................................................................
        # GET DATA - RELEASE DATES
        print("[INFO] Receiving release dates information from TMDB API...")
        res = tm.get_movie_data(
            movie_id=movie_id,
            category='release_dates'
        )

        if res is None:
            print("[WARNING] Failed to obtain movie release dates! Returning None!")
            return None

        if "results" not in list(res.keys()):
            print("[WARNING] 'results'-key not found in API-response! Returning None!")
            return None

        # Extract German release from results
        res_x = None
        for r in res['results']:
            if r['iso_3166_1'] == 'DE':
                res_x = r['release_dates']

        if res_x is None:
            print("[WARNING] No German release information in API-response! Returning None!")
            return None

        print("[INFO] Successfully found German release information!")

        # Extract theatrical release from potential multiple release informations
        # (See API-reference: https://developer.themoviedb.org/reference/movie-release-dates)
        res_x_t = None
        if isinstance(res_x, list):
            for r in res_x:
                if r['type'] == 3:
                    res_x_t = r
        if isinstance(res_x, dict):
            print(f"res_x: {res_x}")
            if res_x['type'] == 3:
                res_x_t = res_x

        print("[INFO] Specified release information extracted!")

        if res_x_t is None:
            print("[WARNING] No theatrical release information found in API-response! Returning None!")
            return None

        # Postprocess API-result as it can contain empty strings or empty lists
        for key,val in res_x_t.items():
            if (val == '') or (val == []):
                res_x_t[key] = None

        # Make dataframe from filtered API-response and adjust to write to database
        df_res = (
            pd.DataFrame([res_x_t])
            [['certification','descriptors','release_date']]
        )
        df_res['tmdb_id'] = movie_id
        df_res['title_german'] = title_german
        
        # .................................................................
        # WRITE TO DATABASE
        self.pg_con.write_df_to_postgres(
            df=df_res,
            schema_name="1_bronze",
            table_name="tmdb__movie_release_dates",
            add_timestamp=True
        )
        print("[INFO] Successfully wrote movie release dates information to database!")
        

    def update_tmdb_data(self, df_movies:pd.DataFrame, language='en-US'):
        """
        Updates tmdb__movie_details and tmdb__movie_release_dates table.
        Inputs:
        - df_movies     dataframe containing a 'title' and 'year' column of movies
        - language      language of incoming movie titles, e.g. 'de-DE' or 'en-US'
        Returns:
        No data return - writes data to postgres
        """
        # Init tmdb class
        tm = tmdb()
        # Go through all movies
        for i, row in df_movies.iterrows():
            # Extract movie info from dataframe
            movie_title = row['title']
            release_year = int(row['year'])

            print("\n--------------------------------------------------")
            print(f"[INFO] ({i+1}/{df_movies.shape[0]}) Processing '{movie_title} ({release_year})'")

            # .................................................................
            # GET DATA - DETAILS
            print("[INFO] Receiving details information from TMDB API...")

            # First try with movie title in selected language (e.g. de-DE)
            res = tm.get_movie_data(
                movie_title=movie_title,
                release_year=release_year,
                language=language,
                category="details")

            # Sometimes recent movies are passed with a release year that is 'one year ago'
            # due to e.g. US release being earlier than Germany
            # This leads to fail on search with TMDB -> Try again with current year can work!
            current_year = datetime.now().year
            if (res is None) and ((current_year - release_year) == 1):
                print(f"[WARNING] Could not get results for release in {release_year}! Trying again for {current_year}...")
                res = tm.get_movie_data(
                    movie_title=movie_title,
                    release_year=current_year,
                    language=language,
                    category="details")

            # Try again for English movie title
            if res is None:
                print("[WARNING] Could not get results on first try! Trying again for 'en-US' as language...")
                res = tm.get_movie_data(
                    movie_title=movie_title,
                    release_year=release_year,
                    language="en-US",
                    category="details")
            
            if res is None:
                print("[WARNING] Failed to obtain movie details! Skipping movie...")
                continue

            # Extract movie_id
            movie_id = res['id']
            print(f"[INFO] Found movie on TMDB! Title: '{res['title']}'")

            # .................................................................
            # CONVERT RESPONSE TO DATAFRAME

            # Make dataframe from filtered API-response and adjust to write to database
            df_res = tm.movie_data_to_dataframe(res)

            # Add german title as well
            if language=='de-DE':
                df_res['title_german'] = row['title']

            # .................................................................
            # WRITE TO DATABASE
            self.pg_con.write_df_to_postgres(
                df=df_res,
                schema_name="1_bronze",
                table_name="tmdb__movie_details",
                add_timestamp=True
            )
            print("[INFO] Successfully wrote movie details information to database!")

            # .................................................................
            # GET DATA - RELEASE DATES
            print("[INFO] Receiving release dates information from TMDB API...")
            res = tm.get_movie_data(
                movie_id=movie_id,
                category='release_dates'
            )

            if res is None:
                print("[WARNING] Failed to obtain movie release dates! Continuing with next movie...")
                continue

            if "results" not in list(res.keys()):
                print("[WARNING] 'results'-key not found in API-response! Continuing with next movie...")
                continue

            # Extract German release from results
            res_x = None
            for r in res['results']:
                if r['iso_3166_1'] == 'DE':
                    res_x = r['release_dates']

            if res_x is None:
                print("[WARNING] No German release information in API-response! Continuing with next movie...")
                continue

            print("[INFO] Successfully found German release information!")

            # Extract theatrical release from potential multiple release informations
            # (See API-reference: https://developer.themoviedb.org/reference/movie-release-dates)
            res_x_t = None
            if isinstance(res_x, list):
                for r in res_x:
                    if r['type'] == 3:
                        res_x_t = r
            if isinstance(res_x, dict):
                print(f"res_x: {res_x}")
                if res_x['type'] == 3:
                    res_x_t = res_x

            print("[INFO] Specified release information extracted!")

            if res_x_t is None:
                print("[WARNING] No theatrical release information found in API-response! Continuing with next movie...")
                continue

            # Postprocess API-result as it can contain empty strings or empty lists
            for key,val in res_x_t.items():
                if (val == '') or (val == []):
                    res_x_t[key] = None

            # Make dataframe from filtered API-response and adjust to write to database
            df_res = (
                pd.DataFrame([res_x_t])
                [['certification','descriptors','release_date']]
            )
            df_res['tmdb_id'] = movie_id
            df_res['title_german'] = row['title']

            # .................................................................
            # WRITE TO DATABASE
            self.pg_con.write_df_to_postgres(
                df=df_res,
                schema_name="1_bronze",
                table_name="tmdb__movie_release_dates",
                add_timestamp=True
            )
            print("[INFO] Successfully wrote movie release dates information to database!")

            # .................................................................
            # Wait a little bit to not overflow the API
            time.sleep(0.1)

        print("[INFO] TMDB database update finished!\n")


    def update_tmdb_data_from_choices(self):
        """
        If new movies are found on choices, TMDB data is out of date.
        Check, which movies from choices are not found in tmdb__movie_details.
        Then get details data for the missing movies from TMDB.
        """
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        print("\n=======================================================================")
        print(f"[INFO] {timestamp} TMDB update based on choices data - pipeline started!")

        # Get currently missing movies
        df_movies = self.pg_con.sql_query(
            """
            SELECT
                title,
                year
            FROM "1_bronze"."choics__current_movies"
            EXCEPT
            SELECT
                title_german AS title,
                EXTRACT(year from release_date) AS year
            FROM "1_bronze"."tmdb__movie_details"
            """
        )

        # Get data of missing movies from TMDB and write to database
        self.update_tmdb_data(
            df_movies=df_movies,
            language='de-DE'
        )

        print("[INFO] Choices update - get TMDB data - pipeline finished!\n")
        

            
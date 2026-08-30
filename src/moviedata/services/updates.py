"""
Module to update database
"""
from datetime import datetime
import pytz
import json

import pandas as pd

from moviedata.core import tools
from moviedata.sources.letterboxd import letterboxd
from moviedata.core.database import pg_connect
from moviedata.sources.rottentomatoes import rottentomatoes

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
                self.pg_con.write_df_to_postgres(
                    df,
                    table_name=table,
                    schema_name="letterboxd"
                )
            except:
                print(f"[WARNING] Failed to write table {table} to database! Skipping table...")
                continue

        print("\n[INFO] Letterboxd update pipeline finished!\n")

    
    def update_rottentomatoes(self):
        """
        """
        print("\n==================================================")
        print("[INFO] Rottentomatoes update pipeline started!")

        # 1 - Load view "rt_movies_for_metadata_scraping" from rottentomatoes schema
        df = self.pg_con.read_df_from_postgres(
            table_name="rt_movies_for_metadata_scraping",
            schema_name="rottentomatoes",
            limit=None
        )

        # 2 - Scrape respective movies and append new data to
        # table "rt_all_movies_metadata"
        rt = rottentomatoes()
        rt.get_movie_data(df_scrape=df, preprocess_title=True)

        print("[INFO] Rottentomatoes update pipeline finished!\n")

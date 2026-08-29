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

class updater:
    """
    """
    def __init__(self):
        pg_con = pg_connect()
        pg_con.create_engine()
        self.pg_con = pg_con

    def update_letterboxd(self, table_select=[]):
        """
        Get userdata from letterboxd and update all related database tables.
        Provide explicit list of table-names (from postgres) to only update
        selected tables.
        """
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

    
    def update_rottentomatoes(self):
        pass
        # 1 - Load view "rt_movies_for_metadata_scraping" from rottentomatoes schema
        # 2 - Scrape respective movies
        # 3 - Append new data to table "rt_all_movies_metadata"
import re
import pandas as pd
from moviedata.core.database import pg_connect
from moviedata.sources.letterboxd import letterboxd
from moviedata.sources.rottentomatoes import rottentomatoes
from bs4 import BeautifulSoup


pg = pg_connect()
df = pg.read_df_from_postgres(
    table_name="recommended_movies_for_metadata_scraping",
    schema_name="letterboxd",
    limit=None
)

rt = rottentomatoes()
rt.get_movie_data(df_scrape=df)
import re
import pandas as pd
from moviedata.sources.rottentomatoes import rottentomatoes
from moviedata.services.updates import updater
from datetime import datetime
import bs4
from bs4 import BeautifulSoup


# # Get test reference data
# DF_SCRAPE = pd.read_csv("tests/files/rottentomatoes_test-movies.csv")

# DF_SCRAPE.rename(columns={'year_search':'year'}, inplace=True)

# rt = rottentomatoes()
# rt.get_movie_data(df_scrape=DF_SCRAPE)

ud = updater()
ud.update_rottentomatoes_from_tmdb()
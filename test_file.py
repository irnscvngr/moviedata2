import re
import pandas as pd
from moviedata.sources.rottentomatoes import rottentomatoes
from moviedata.core.tools import parse_name_for_url
import tests.test_rottentomatoes as test_rt
from datetime import datetime
import bs4
from bs4 import BeautifulSoup


# rt = rottentomatoes()
# rt.get_movie_data()

test_rt.test_rottentomatoes_get_movie_data()
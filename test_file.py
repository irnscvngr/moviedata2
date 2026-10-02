import re
import pandas as pd
from moviedata.services.updates import updater
from moviedata.sources.tmdb import tmdb
from datetime import datetime
import bs4
from bs4 import BeautifulSoup

ud = updater()
tmdb_url = "https://www.themoviedb.org/movie/96820-vaterland?language=de"
tmdb_url = "https://www.themoviedb.org/movie/157832-calvary?language=de"
ud.update_tmdb_from_url(tmdb_url=tmdb_url)
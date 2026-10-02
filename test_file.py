import re
import pandas as pd
from moviedata.services.updates import updater
from moviedata.sources.tmdb import tmdb
from datetime import datetime
import bs4
from bs4 import BeautifulSoup

ud = updater()
ud.update_tmdb_data_from_choices()
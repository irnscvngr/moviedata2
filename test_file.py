import re
import pandas as pd
from moviedata.sources.tmdb import tmdb
from moviedata.services.updates import updater
from datetime import datetime
import bs4
from bs4 import BeautifulSoup


ud = updater()
ud.update_tmdb_streaming_providers()

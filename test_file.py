# import re
# import pandas as pd
from moviedata.sources.letterboxd import letterboxd
# from moviedata.services.updates import updater
# from datetime import datetime
# import bs4
# from bs4 import BeautifulSoup


lb = letterboxd(timeout=30)

lb.get_userdata()

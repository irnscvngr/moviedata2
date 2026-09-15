import re
import pandas as pd
from moviedata.services.updates import updater
from moviedata.sources.tmdb import tmdb
from datetime import datetime
import bs4
from bs4 import BeautifulSoup

ud = updater()
ud.update_choices_tmdb_data()

# tm = tmdb()
# res = tm.get_movie_data(
#     movie_title="The Invite",
#     release_year=2026,
#     language="de-DE",
#     category="release_dates")

# res_res = res['results']

# res_x = None
# for r in res_res:
#     if r['iso_3166_1'] == 'DE':
#         res_x = r

# print(res_x['release_dates'])

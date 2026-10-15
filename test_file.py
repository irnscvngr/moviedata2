import re
import pandas as pd
from moviedata.sources.tmdb import tmdb
from moviedata.services.updates import updater
from datetime import datetime
import bs4
from bs4 import BeautifulSoup


# tm = tmdb()

# res = tm.get_movie_data(
#     movie_title='Calvary',
#     release_year=2014,
#     language='de-DE'
# )

# # res = tm.get_movie_data(
# #     movie_title='Am Sonntag bist du tot',
# #     release_year=2014,
# #     language='en-US'
# # )

# print("\nKeys:\n", "\n".join(list(res.keys())))

# df_res = tm.movie_data_to_dataframe(res)

# print(df_res.T)

ud = updater()
ud.update_tmdb_data_from_letterboxd()
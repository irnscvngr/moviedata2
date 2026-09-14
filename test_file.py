import re
import pandas as pd
from moviedata.sources.choices import choices
# import tests.test_choices as tcs
from datetime import datetime
import bs4
from bs4 import BeautifulSoup

cs = choices()

res = cs.get_all_movies()

print(res.columns)
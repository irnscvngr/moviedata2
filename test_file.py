import re
import pandas as pd
# from moviedata.sources.choices import choices
# import tests.test_choices as tcs
from datetime import datetime
import bs4
from bs4 import BeautifulSoup

# cs = choices()
# cs.get_all_movies()

# tcs.test_choices_get_all_movies()

filepath = "tests/files/choices_residenz_soup.html"
# filepath = "tests/files/choices_cinedom_soup.html"
with open(filepath, "r", encoding="utf-8") as file:
    local_soup = BeautifulSoup(file, "html.parser")

# --------------------------------------------------
movies_el = local_soup.find_all(class_="event_item")

def _parse_movie(el: bs4.element.Tag):
    # ...................................
    # Get movie title
    title = (
        el
        .find("h3")
        .find("a")
        .get_text(strip=True)
    )
    # .................................
    # Get movie link
    link = (
        el
        .find("h3")
        .find('a')
        ['href']
    )
    # .................................
    # Get movie subtext
    subtext = el.find("p").get_text(strip=True)
    # Extract movie year
    match = re.search(pattern=r"\b\d{4}\b", string=subtext)
    year = None
    if match:
        year = match.group()
    # Get current year
    cur_year = datetime.now().year
    # ...................................
    # Get movie times
    # Get all table rows
    tab_rows = el.find_all("tr")

    showtimes = []
    for tr in tab_rows:
        # Check for header
        th = tr.find("th")
        if th is not None:
            continue

        # Get all table data elements
        td = tr.find_all("td")
        if len(td) == 0:
            continue

        # Extract text from table data
        td_list = [td_el.get_text(strip=True) for td_el in td]

        # ......................................................................
        # PROCESS TIME INFORMATION
        # Get time-information
        t_str = td_list[1].strip()

        # Pattern groups match:
        # 1. (\d{2}:\d{2})            -> Time (e.g. 14:00)
        # 2. (?:\s*\((.+?)\))?(?:,|$) -> Optional space + parentheses content
        pattern = r"(\d{2}:\d{2})(?:\s*\((.+?)\))?(?:,|$)"

        # SPLIT TIME INFORMATION
        for time, annotation in re.findall(pattern, t_str, flags=re.IGNORECASE):
            # Time information can contain annotations, like
            # OV, OmU, OmeU etc.
            # For "Sonderveranstaltungen" annotations can sometimes also
            # contain both movie names and version (OV, OmU etc.)
            pattern = r"(\bov\b|\bom\wu\b|\bomu\b)"
            annot_split = re.split(pattern, annotation, flags=re.IGNORECASE)

            # .................................................................
            # Just use the "basic" annotation and watch out for OV, OmU etc.
            vers = "DE"
            match = re.match(r"\bov\b", annotation, flags=re.IGNORECASE)
            if match:
                vers = "OV"
            match = re.match(r"\bom\wu\b", annotation, flags=re.IGNORECASE)
            if match:
                vers = "OmU"
            match = re.match(r"\bomu\b", annotation, flags=re.IGNORECASE)
            if match:
                vers = "OmU"

            # .................................................................
            # Take the split annotation's first entry and extract
            # the potential movie name
            annot = None
            match = re.search(r"\b[a-zA-Z0-9].+\b", annot_split[0])
            if match:
                annot = match.group()

            # .................................................................
            # Create timestamp
            timestamp_dt = None
            # Extract date from string
            match = re.search(r"\b[0-9]{2}.[0-9]{2}\b", td_list[0])
            if match:
                timestamp = f"{match.group()}.{cur_year} {time}"
                # timestamp_dt = datetime.fromtimestamp(timestamp)
                timestamp_dt = datetime.strptime(timestamp, "%d.%m.%Y %H:%M")

            # .................................................................
            # Store all extracted information in a dictionary
            res = {
                "title":title,
                "year":year,
                "timestamp":timestamp_dt,
                "vers":vers,
                "annot":annot,
                "link":link
            }

            # Append dictionary to list
            showtimes.append(res)
    
    return showtimes

# movies_parsed = [_parse_movie(el.find('table')) for el in movies_el]
movies_parsed = []
for el in movies_el:
    movies_parsed += _parse_movie(el.find('table'))

print(pd.DataFrame(movies_parsed))

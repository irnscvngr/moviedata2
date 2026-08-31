"""
Tests for the medimops module
"""
import pytest
import io
import pandas as pd
from bs4 import BeautifulSoup
from moviedata.sources.medimops import medimops

def test_letterboxd_init():
    """
    Test if init function works and assigs base parameters.
    """
    mm = medimops()
    assert mm.base_url is not None
    assert mm.url_bluray_search is not None
    assert mm.timeout is not None

def test_medimops_get_headers():
    """
    Test if HTTP headers can be obtained.
    """
    mm = medimops()
    mm.get_headers()

    # Assertions check values instead of manual visual checks
    assert mm.headers is not None
    assert isinstance(mm.headers, tuple)

def test_medimops_parse_blu_ray_search_results():
    """
    Test if HTML is parsed correctly
    """

    filepath = "tests/files/medimops_bluray_search_soup.html"

    with open(filepath, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

    mm = medimops()
    df_res = mm._parse_blu_ray_search_results(soup=soup, movie_title="Inception")

    assert df_res is not None
    assert isinstance(df_res, pd.DataFrame)

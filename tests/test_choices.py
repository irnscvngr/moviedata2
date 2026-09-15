"""
Tests for the choices module
"""
import pytest
import io
import pandas as pd
from bs4 import BeautifulSoup
from unittest.mock import patch
from moviedata.sources.choices import choices

def test_choices_init():
    """
    Test if init function works and assigns base parameters.
    """
    cs = choices()
    assert cs.base_url is not None
    assert cs.timeout is not None


def test_choices_get_all_cinemas():
    """
    Test if all cinemas can be parsed correctly
    """
    
    # Import html-file for testing
    filepath = "tests/files/choices_all_cinemas_soup.html"
    with open(filepath, "r", encoding="utf-8") as file:
        local_soup = BeautifulSoup(file, "html.parser")

    cs = choices()

    # Mock method 'get_soup' to return local_soup instead of making a network call
    with patch.object(cs, "get_soup", return_value=local_soup):
        cs.get_all_cinemas()

    assert cs.all_cinemas is not None
    assert isinstance(cs.all_cinemas, dict)
    assert len(cs.all_cinemas) > 5


def test_choices_parse_cinema_page():
    """
    Test if movies can be obtained correctly from a cinema page on choices.de
    """
    cs = choices()

    # --------------------------------------------------
    # TEST FOR RESIDENZ
    # Import html-file for testing
    filepath = "tests/files/choices_residenz_soup.html"
    with open(filepath, "r", encoding="utf-8") as file:
        local_soup = BeautifulSoup(file, "html.parser")

    # Get results and check them
    res = cs._parse_cinema_page(local_soup)
    assert res is not None
    assert isinstance(res, pd.DataFrame)

    # --------------------------------------------------
    # TEST FOR CINEDOM
    filepath = "tests/files/choices_cinedom_soup.html"
    with open(filepath, "r", encoding="utf-8") as file:
        local_soup = BeautifulSoup(file, "html.parser")

    # Get results and check them
    res = cs._parse_cinema_page(local_soup)
    assert res is not None
    assert isinstance(res, pd.DataFrame)
"""
Tests for the TMDB module
"""
import pytest
import io
import pandas as pd
from bs4 import BeautifulSoup
from unittest.mock import patch
from moviedata.sources.tmdb import tmdb


def test_search_movie_smart():
    """
    Tests the "smart" movie search (and thereby "search_movie" and "eval_search_res_by_date") method.
    """
    
    tm = tmdb()
    res = tm.search_movie_smart(
        movie_title="Up",
        release_year=2009
    )

    assert res is not None
    assert isinstance(res, dict)
    assert res['title'] == "Up"
    assert res['release_date'] == "2009-05-28"

def test_get_movie_details():
    """
    Tests the get_movie_details method
    """
    
    tm = tmdb()
    # ..................................................
    # Test for "Fight Club" (1999)
    test_id = 550
    res = tm.get_movie_data(movie_id=test_id, category="details")

    assert res is not None
    assert isinstance(res, dict)
    assert res['id'] == test_id

    # ..................................................
    # Test for "Up" (2009)
    test_id = 14160
    res = tm.get_movie_data(movie_id=test_id, category="details")

    assert res is not None
    assert isinstance(res, dict)
    assert res['id'] == test_id

    # ..................................................
    # Test for "Up" (2009) without ID
    res = tm.get_movie_data(movie_title="Up", release_year=2009, category="details")

    assert res is not None
    assert isinstance(res, dict)
    assert res['id'] == 14160
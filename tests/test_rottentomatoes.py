"""
Tests for the medimops module
"""
import time
import pytest
import io
import os
import pandas as pd
from bs4 import BeautifulSoup
from moviedata.sources.rottentomatoes import rottentomatoes

def test_rottentomatoes_parse_rt_search_results():
    """
    Test if search results from rotten tomatoes are parsed correctly.
    Some movies might be called with e.g. year 2026 but on rottentomatoes
    they are listed as 2025.

    The function needs to be able to identify those as the same movies
    and return the correct result.
    """
    print("\n------------------------------------------------------------")
    print("[INFO] Testing Rottentomatoes 'parse_rt_search_results'")

    # Get test reference data
    df_scrape = pd.read_csv("tests/files/rottentomatoes_test-movies.csv")

    # Initialize success count
    success_cnt = 0.0

    # Use predefined movies, years and resulting URLs to test function
    rt = rottentomatoes()
    for _, row in df_scrape.iterrows():
        name = row['name']
        year_search = row['year_search']
        ref_url = row['ref_url']

        # Test method with the previously stored HTML as return-value of get_soup()
        res_url = rt.parse_rt_search_results(name=name, year=year_search)

        # Increase success counter if returned URL is correct
        if res_url == ref_url:
            success_cnt += 1

        time.sleep(0.1)

    # Check if success rate is okay.
    # It makes no sense to use a 1:1 comparison, because some movies just fail to return on search in RT
    assert success_cnt/df_scrape.shape[0] > 0.8
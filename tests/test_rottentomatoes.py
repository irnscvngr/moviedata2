"""
Tests for the medimops module
"""
import time
import pytest
import io
import os
from unittest.mock import patch
import pandas as pd
from bs4 import BeautifulSoup
from moviedata.sources.rottentomatoes import rottentomatoes

# Get test reference data
DF_SCRAPE = pd.read_csv("tests/files/rottentomatoes_test-movies.csv")

def test_rottentomatoes_parse_rt_search_results():
    """
    Test if search results from rotten tomatoes are parsed correctly
    (meaning a search by name and year should return the necessary movie URL).
    Some movies might be called with e.g. year 2026 but on rottentomatoes
    they are listed as 2025.

    The function needs to be able to identify those as the same movies
    and return the correct URL on rottentomatoes.

    Uses a CSV file with reference values for testing. Feel free to expand.
    """
    print("\n------------------------------------------------------------")
    print("[INFO] Testing Rottentomatoes 'parse_rt_search_results'")

    # Initialize success count
    success_cnt = 0.0

    # Use predefined movies, years and resulting URLs to test function
    rt = rottentomatoes()
    for _, row in DF_SCRAPE.iterrows():
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
    assert success_cnt/DF_SCRAPE.shape[0] > 0.8

@patch("moviedata.core.database.pg_connect.write_df_to_postgres")
def test_rottentomatoes_get_movie_data(mock_df):
    """
    Test if get_movie_data succeeds to actually retrieve movie data
    from rottentomatoes based on a test-list of movies.
    """
    rt = rottentomatoes()
    rt.get_movie_data(
        df_scrape=DF_SCRAPE.rename(columns={'year_search':'year'})
        )

    # ..........................................................................................
    # Check if method made it at least once to the point of writing to database
    assert mock_df.called

    # ..........................................................................................
    # Compare number of mock up calls to number of test-movies.
    # Should ideally be 1:1 but using threshold because some movies just fail
    assert 1.0*len(mock_df.call_args_list)/DF_SCRAPE.shape[0] >= 0.75

    # ..........................................................................................
    # Extract actual dataframes that would have been written to postgres
    # to find out which movies failed exactly
    df_values = [c.kwargs['df'] for c in mock_df.call_args_list]
    df_combined = pd.concat(df_values, ignore_index=True)

    # Join reference values and return values from RT
    df_compare = (
        DF_SCRAPE[['name','year_search']]
        .rename(columns={'name':'name_ref'})
        .merge(
            df_combined[['name','release_date']]
            .rename(columns={'name':'name_search'})
            how='left',
            left_on='name_ref',
            right_on='name_search'
        )
    )

    # Extract list of failed movies
    failed_movies = df_compare.loc[df_compare['name_search'].isna(), 'name_ref'].to_list()

    print(f"These movies failed on RT-search: {failed_movies}")

    # ..........................................................................................
    # Make sure that movies that were found actually have the same name as the query
    df_compare_filtered = df_compare.dropna()

    assert min(df_compare_filtered['name_ref'] == df_compare_filtered['name_search']) == True

    # Also make sure that the release_dates are all actual values
    assert min(df_compare_filtered['release_date'].isna()) == False
"""
Tests for the letterboxd module
"""
import pytest
import io
import pandas as pd
import moviedata.core.tools as tools

def test_extract_file_from_zip_io():
    """
    Imports example zip-file from letterboxd to
    test unzip function.
    """
    # Load example file
    testfile_path = "tests/test_letterboxd_userdata.zip"
    with open(testfile_path, "rb") as f:
        zip_buffer = io.BytesIO(f.read())

    # Unzip a file and return its bytes buffer
    file = (
        tools
        .extract_file_from_zip_io(
            zip_buffer=zip_buffer,
            filepath="watched.csv"
            )
    )
    assert file is not None
    assert isinstance(file, io.BytesIO)

    # Unzip another file and return its bytes buffer
    file = (
    tools
    .extract_file_from_zip_io(
        zip_buffer=zip_buffer,
        filepath="lists/br-collection.csv"
        )
    )
    assert file is not None
    assert isinstance(file, io.BytesIO)

    # Convert to pandas dataframe
    df = pd.read_csv(file)
    assert isinstance(df, pd.DataFrame)
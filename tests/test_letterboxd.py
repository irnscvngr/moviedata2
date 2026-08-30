"""
Tests for the letterboxd module
"""
import pytest
import io
from moviedata.sources.letterboxd import letterboxd

def test_letterboxd_init():
    """
    Test if init function works and assigs base parameters.
    """
    lb = letterboxd()
    assert lb.base_url is not None
    assert lb.timeout is not None

def test_letterboxd_get_headers():
    """
    Test if HTTP headers can be obtained.
    """
    lb = letterboxd()
    lb.get_headers()

    # Assertions check values instead of manual visual checks
    assert lb.headers is not None
    assert isinstance(lb.headers, tuple)

def test_letterboxd_get_userdata():
    """
    Test if userdata can be obtained
    """
    lb = letterboxd()
    lb.get_userdata()

    # Assertions check values instead of manual visual checks
    assert lb.userdata is not None
    assert isinstance(lb.userdata, io.BytesIO)
    assert lb.headers is not None
    assert isinstance(lb.headers, tuple)
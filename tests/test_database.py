"""
Tests for the database module
"""

import pytest
import sqlalchemy
from moviedata.core.database import pg_connect

def test_pg_connect_create_engine():
    """
    """
    pg = pg_connect()
    pg.create_engine()

    assert pg.engine is not None
    assert isinstance(pg.engine, sqlalchemy.engine.base.Engine)

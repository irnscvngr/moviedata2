"""
Tests for the database module
"""

import pytest
import pandas as pd
import sqlalchemy
from moviedata.core.database import pg_connect

def test_pg_connect_create_engine():
    """
    Test if creating a database engine works
    """
    pg = pg_connect()
    pg.create_engine()

    assert pg.engine is not None
    assert isinstance(pg.engine, sqlalchemy.engine.base.Engine)

def test_pg_connect_read_df_from_postgres():
    """
    Test if connection to database and reading a table as
    pandas dataframe works
    """
    pg = pg_connect()
    pg.create_engine()

    df = pg.read_df_from_postgres(
        table_name="ratings",
        schema_name="letterboxd"
    )

    assert pg.engine is not None
    assert df is not None
    assert df.shape[0] > 0
    assert isinstance(df, pd.DataFrame)
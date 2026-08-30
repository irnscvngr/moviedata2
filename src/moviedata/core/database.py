"""
Module to communicate with database
"""
import json
from config.settings import settings

from datetime import datetime
import pytz

import pandas as pd

import sqlalchemy
from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects.postgresql import insert

class pg_connect:
    """
    """
    def __init__(self):
        self.engine = None

    def create_engine(self):
        """
        Create engine to connect to database.
        """
        self.engine = create_engine(settings.database_url)

    def read_df_from_postgres(self, table_name: str, schema_name: str, limit=500):
        """
        """
        query = f"SELECT * FROM {schema_name}.{table_name}"
        if limit is not None:
            query = f"{query} LIMIT {limit}"

        if self.engine is None:
           self.create_engine() 

        df = pd.read_sql(query, con=self.engine)
        return df

    def sql_query(self, query:str):
        """
        Sends custom SQL-query to database and returns pandas DF
        """
        if self.engine is None:
            self.create_engine() 

        df = pd.read_sql(query, con=self.engine)
        return df

    def write_df_to_postgres(
        self,
        df: pd.DataFrame,
        table_name: str,
        schema_name: str,
        add_timestamp=True,
        primary_keys: list | None = None,  # Optional override
        ):
        """
        Writes pandas dataframe to postgres DB, auto-detecting primary keys if omitted.
        """

        # Create engine if not available
        if self.engine is None:
            self.create_engine()

        # 1. Automatically fetch PKs from DB schema if not provided
        if not primary_keys:
            inspector = inspect(self.engine)
            pk_info = inspector.get_pk_constraint(table_name, schema=schema_name)
            primary_keys = pk_info.get("constrained_columns", [])

            if not primary_keys:
                print(f"[WARNING] No primary keys found on table '{schema_name}.{table_name}'.")

        # 2. Closure for handling PostgreSQL ON CONFLICT DO NOTHING
        def _build_on_conflict_do_nothing(pk_columns: list, target_table: str):
            target_elements = [pk_columns] if isinstance(pk_columns, str) else list(pk_columns)

            def insert_fn(table, conn, keys, data_iter):
                data = [dict(zip(keys, row)) for row in data_iter]
                
                if not data:
                    print(f"[INFO] [{target_table}] No rows provided to insert.")
                    return 0

                # Build PostgreSQL statement with auto-detected primary keys
                stmt = insert(table.table).values(data)
                
                if target_elements:
                    stmt = stmt.on_conflict_do_nothing(index_elements=target_elements)

                result = conn.execute(stmt)
                inserted_count = result.rowcount
                skipped_count = len(data) - inserted_count

                if inserted_count > 0:
                    print(f"[INFO] [{target_table}] Successfully inserted {inserted_count} new row(s).")
                else:
                    print(f"[INFO] [{target_table}] 0 new rows inserted ({skipped_count} row(s) skipped).")

                return inserted_count

            return insert_fn

        # 3. Clean & Prepare DataFrame
        df_write = df.copy()
        df_write.columns = [c.lower().replace(' ', '_') for c in df_write.columns]

        if 'date' in df_write.columns:
            df_write['date'] = pd.to_datetime(df_write['date'])

        # Add load timestamp if requested
        if add_timestamp:
            tz = pytz.timezone('Europe/Berlin')
            df_write['load_timestamp'] = datetime.now(tz)
        
        # Convert any dict columns to JSON-formatted strings
        # to prevent failure upon writing to database
        # (psycopg2 uses raw python types when sending data to DB server, which fails
        # for Python dictionaries. Serialize as JSON first, then it works!)
        check_types = (dict, list, tuple)
        for col in df_write.columns:
            if df_write[col].apply(lambda x: isinstance(x, check_types)).any():
                print(f"[WARNING] Column '{col}' is either type tuple, dict or list. Serializing to JSON...")
                df_write[col] = df_write[col].apply(lambda x: json.dumps(x) if isinstance(x, check_types) else x)

        # 4. Write to PostgreSQL
        df_write.to_sql(
            name=table_name,
            schema=schema_name,
            con=self.engine,
            if_exists="append",
            index=False,
            method=_build_on_conflict_do_nothing(
                pk_columns=primary_keys,
                target_table=table_name
            )
        )
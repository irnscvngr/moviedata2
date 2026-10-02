from datetime import datetime

import streamlit as st
import numpy as np
import pandas as pd
from moviedata.core.database import pg_connect
from components.image_grid import display_centered_images

# Reduce the top margin/padding of the main container
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 0rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)

pg = pg_connect()

# ==========================================================================================
"## Cinema Overview"
st.markdown(
    "<hr style='margin: 4px 0; border: none; border-top: 1px solid #e6e6e6;' />", 
    unsafe_allow_html=True
)

# ==========================================================================================
# SELECT SCREENINGS

# ..........................................................................................
# Get current screenings enriched with runtimes, posters and age certification
df_screenings = (
    pg
    .sql_query("""
        WITH cte AS (
            SELECT
                -- Get basic movie information from screenings
                a.city,
                a.cinema,
                a.title,
                -- Get year from TMDB to join with details later
                b.year_tmdb AS year
            FROM "1_bronze"."choics__current_screenings" a
            LEFT JOIN "2_silver".choics__get_closest_tmdb_movie_by_year b
            ON a.title = b.title
            AND a.year = b.year_choices
        ),
        cte2 AS (
            SELECT
                cte.*,
                -- Get additional information from TMDB details
                b.runtime,
                b.poster_path,
                b.tmdb_id
            FROM cte
            LEFT JOIN "1_bronze"."tmdb__movie_details" b
            ON cte.title = b.title_german
            AND cte.year = EXTRACT(year FROM b.release_date)
        )
        -- Add age certification from TMDB release dates
        SELECT
            lt.*,
            rt.certification
        FROM cte2 lt
        LEFT JOIN "1_bronze"."tmdb__movie_release_dates" rt
        ON lt.tmdb_id = rt.tmdb_id
        -- Order by title and year for data cleaning later
        ORDER BY title, year
        """)
)

# Some movies have '0' runtime -> Set to None to avoid filtering problems
df_screenings.loc[df_screenings['runtime']==0, 'runtime'] = None

# ..........................................................................................
# SELECT CINEMAS

# Create helper dataframe for cinemas
df_cinemas = (
    df_screenings.copy()
    .loc[:,['city','cinema']]
    .groupby(['city','cinema'], as_index=False)
    .first()
)
df_cinemas['str_display'] = df_cinemas['city'] + ' ' + df_cinemas['cinema']

# Select cinemas
cinema_select = st.multiselect(
    label='select cinema',
    options=df_cinemas.index,
    format_func=lambda x: df_cinemas.loc[x,'str_display'],
    default=df_cinemas.index
)
df_screenings['str_cinema'] = df_screenings['city'] + ' ' + df_screenings['cinema']

# ..........................................................................................
# SELECT RUNTIME
c0, c1 = st.columns(2)

# Set max runtime
with c0:
    runtime_max = st.slider(
        label='select max. runtime',
        min_value = int(df_screenings['runtime'].dropna().min()),
        max_value = int(df_screenings['runtime'].dropna().max()),
        value = int(df_screenings['runtime'].dropna().max()),
        step = 10,
    )

# ..........................................................................................
# SELECT AGE

# Select min age
with c1:
    age_max = st.select_slider(
        label='select max. age',
        options=[0,6,12,16,18],
        value=18
    )

# ..........................................................................................
# FINAL SCREENINGS SELECTION
sel = (
    df_screenings['city'].isin(df_cinemas.loc[cinema_select,'city'])
    & df_screenings['cinema'].isin(df_cinemas.loc[cinema_select,'cinema'])
    & ((df_screenings['runtime'] <= runtime_max) | df_screenings['runtime'].isna())
    & ((df_screenings['certification'] <= age_max) | df_screenings['certification'].isna())
)

df_screenings_select = (
    df_screenings.loc[sel,:]
    .groupby(['title','year'], as_index=False)
    .agg(
        title = ('title', 'first'),
        year = ('year', 'first'),
        runtime = ('runtime', 'first'),
        fsk = ('certification', 'first'),
        screening_cnt = ('str_cinema', 'count'),
        cinema_cnt = ('str_cinema', lambda x: len(np.unique(x))),
        poster = ('poster_path', 'first')
    )
)
df_screenings_select['isna'] = df_screenings_select[['runtime','fsk']].isna().min(axis=1)
df_screenings_select = (
    df_screenings_select
    .sort_values(
            by=[
                'isna', 
                'title',
                ],
            )
    .drop(columns='isna')
)

# ..........................................................................................
# SHOW POSTERS OF SELECTED MOVIES

# Poster URL:
# base_url = https://image.tmdb.org/t/p/w500 (select a width, e.g. w500)
# poster_url = /vhv7lBWYM0DUuNU2a0V7Rhq21dD.jpg

f"""
#### {df_screenings_select.shape[0]} movies total
"""

# Just show dataframe for now...
st.dataframe(df_screenings_select)


# ==========================================================================================
# SELECT SINGLE MOVIE

# Get distinct current movie screenings
df_movies = (
    pg
    .sql_query("""
        SELECT * FROM "2_silver"."choics__current_movie_detailed"
        ORDER BY title ASC
        """)
)

movies_years = list(zip(
    df_movies['title'].to_list(),
    df_movies['year'].to_list(),
    df_movies['title'] + ' (' + df_movies['year'].astype(str) + ')'
))

# Select movie
movie_select_index = st.selectbox(
    label = 'Select movie',
    options = range(len(movies_years)),
    format_func = lambda x: movies_years[x][2]
)

# Get current screenings
df_screenings_selected = (
    pg
    .sql_query(f"""
        SELECT
            city,
            cinema,
            title,
            year,
            vers,
            TO_CHAR(timestamp, 'DD.MM.') AS day,
            TO_CHAR(timestamp, 'HH24:MI') AS time,
            link
        FROM "1_bronze"."choics__current_screenings"
        WHERE title = '{movies_years[movie_select_index][0]}'
        AND year = '{movies_years[movie_select_index][1]}'
        ORDER BY day, time
        """)
)

c0, c1 = st.columns([1,2])

# Show poster
with c0:
    base_url = "https://image.tmdb.org/t/p/w200"
    poster_path = df_movies.loc[movie_select_index,'poster_path']

    if poster_path is not None:
        st.image(base_url + poster_path)

# Set date range
with c1:
    vals=list(df_screenings_selected['day'].sort_values().unique())
    if len(vals)==1:
        date_min = date_max = vals[0]
    else:
        date_min, date_max = st.select_slider(
            label='date_range',
            options=vals,
            value=(vals[0],vals[-1])
        )

    # Set time range
    vals = list(df_screenings_selected['time'].sort_values().unique())
    if len(vals)==1:
        time_min = time_max = vals[0]
    else:
        time_min, time_max = st.select_slider(
            label='time_range',
            options=vals,
            value=(vals[-1],vals[0])
        )

# Select OV only
ov_only = st.checkbox(label='Original Version')

# Filter values
sel = df_screenings_selected['day'] >= date_min
sel = sel & (df_screenings_selected['day'] <= date_max)
sel = sel & (df_screenings_selected['time'] >= time_min)
sel = sel & (df_screenings_selected['time'] <= time_max)
if ov_only:
    sel = sel & (df_screenings_selected['vers'].str.lower().str.startswith('o'))

df_screenings_selected_filtered = (
    df_screenings_selected.loc[sel,:]
)

st.dataframe(df_screenings_selected_filtered)
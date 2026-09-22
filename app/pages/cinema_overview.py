from datetime import datetime

import streamlit as st
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

# Get current screenings
df_movies = (
    pg
    .sql_query("""
        SELECT * FROM choices.current_movie_detailed
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
        FROM choices.current_screenings
        WHERE title = '{movies_years[movie_select_index][0]}'
        AND year = '{movies_years[movie_select_index][1]}'
        ORDER BY day, time
        """)
)

# Set date range
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
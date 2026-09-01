import streamlit as st
import plotly.express as px
import pandas as pd
from moviedata.core.database import pg_connect
from components.movie_price_lines_plot import medimops_price_analyzer

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

"## Medimops Tracking"
st.divider()

pg = pg_connect()

movie_titles = pg.sql_query("""
    SELECT DISTINCT letterboxd_name
    FROM medimops.movie_price_lines2
    ORDER BY letterboxd_name ASC
    """
)['letterboxd_name'].tolist()

mpa = medimops_price_analyzer(movie_titles=movie_titles)

# -----------------------------------------------------------------
"#### Lower than average* prices"
"**4 weeks*"

df_cheap_movies = mpa.get_cheap_movies(cnt=6)

df_movie_prices_cheap = (
    mpa
    .get_movie_prices(movie_select=df_cheap_movies['letterboxd_name'].tolist()))

st.plotly_chart(mpa.plot_price_lines())

# -----------------------------------------------------------------
st.divider()
"#### Price development of selected movies"

movie_select = st.multiselect(
    label="movie_select",
    options=movie_titles,
    max_selections=5,
    label_visibility="collapsed")

# -----------------------------------------------------------------
df_movie_prices = mpa.get_movie_prices(movie_select=movie_select)

st.plotly_chart(mpa.plot_price_lines())


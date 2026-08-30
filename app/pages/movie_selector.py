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
"## Movie Selector"
st.divider()

col1, col2 = st.columns(2)

with col1:
    "**Duration in minutes**"
    select_duration = st.slider(
        label='duration',
        value=(80,110),
        min_value = 0,
        max_value = 300,
        label_visibility='collapsed'
        )
    "**Critics score**"
    select_critics_score = st.slider(
        label='audience_score',
        value=(80,100),
        min_value = 0,
        max_value = 100,
        label_visibility='collapsed'
        )
with col2:
    "**Release year**"
    select_year = st.slider(
        label='release_year',
        value=(2010, 2025),
        min_value = 1950,
        max_value = datetime.now().year,
        label_visibility='collapsed'
        )
    "**Audience score**"
    select_audience_score = st.slider(
        label='critics_score',
        value=(80,100),
        min_value = 0,
        max_value = 100,
        label_visibility='collapsed'
        )

# ==========================================================================================
# Get coverage of rottentomatoes data for watchlist
df = pg.sql_query(
    """
    SELECT 
    -- Count matched items divided by total items in watchlist
    COUNT(*)::NUMERIC / NULLIF((SELECT COUNT(*) FROM letterboxd.watchlist), 0) AS coverage_ratio,
    
    -- Absolute numbers for context
    COUNT(*) AS matched_movies,
    (SELECT COUNT(*) FROM letterboxd.watchlist) AS total_watchlist_movies
    FROM rottentomatoes.rt_all_movies_metadata
    WHERE letterboxd_uri IN (SELECT letterboxd_uri FROM letterboxd.watchlist);
    """
).to_dict('records')[0]

f"*Rotten tomatoes coverage of watchlist: {round(100*df['coverage_ratio'])}%*"

df = (
    pg
    .sql_query(f"""
    SELECT
        name,
        year,
        duration,
        (critics_score + audience_score)/2 AS meta_score,
        poster,
        description,
        critics_score,
        audience_score
    FROM public.watchlist_with_scores
    WHERE critics_score >= {select_critics_score[0]}
    AND critics_score <= {select_critics_score[1]}
    -- audience score
    AND audience_score >= {select_audience_score[0]}
    AND audience_score <= {select_audience_score[1]}
    -- duration
    AND duration >= {select_duration[0]}
    AND duration <= {select_duration[1]}
    -- year
    AND year >= {select_year[0]}
    AND year <= {select_year[1]}
    -- drop nulls
    AND critics_score IS NOT NULL
    AND audience_score IS NOT NULL
    --
    ORDER BY meta_score DESC
    LIMIT 50"""
    )
)

# Display images:
display_centered_images(df.iloc[0:3,:], max_images=3, descr_length=200)
display_centered_images(df.iloc[3:6,:], max_images=3, descr_length=200)

# Display dataframe
st.dataframe(
    df.loc[:,['name','year','duration','meta_score']],
    column_config={
        "name":"Movie Name",
        "year":"Release Year",
        "duration":"Duration [min]",
        "meta_score":"Meta Score [%]"
    }
    )
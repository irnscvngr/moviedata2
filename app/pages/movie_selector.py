from datetime import datetime

import streamlit as st
from moviedata.core.database import pg_connect
from components.image_grid import display_centered_images, hover_image_movie_selector

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
st.markdown(
    "<hr style='margin: 4px 0; border: none; border-top: 1px solid #e6e6e6;' />", 
    unsafe_allow_html=True
)

col1, col2 = st.columns(2)

with col2:
    toggle_free_streaming = st.toggle("Free Streaming Only")

# Define filter for streaming
filter_streaming_types = ('free', '')

if toggle_free_streaming:
    # Select distinct genres that are available via free streaming
    sql_query = f"""
        SELECT 
            DISTINCT b.genre
        FROM "1_bronze"."tmdb__movie_streams_complete" a
        LEFT JOIN "1_bronze".ltboxd__movie_genres b
        ON a.title_tmdb = b.name
        AND EXTRACT(year FROM a.release_date) = b.year
        WHERE b.genre IS NOT NULL
        AND a.streaming_type IN {filter_streaming_types}
    """
else:
    # Select distinct genres for all movies
    sql_query = """
        SELECT DISTINCT genre
        FROM "1_bronze"."ltboxd__movie_genres"
    """


# Get available genres
genres = (
    pg
    .sql_query(sql_query)
    ['genre']
    .sort_values()
    .tolist()
)

with col1:
    # Genre-Filter toggle
    toggle_use_genre_filter = st.toggle("Filter Genres")

if toggle_use_genre_filter:
    genre_select = st.multiselect(
        "genre_select",
        genres,
        default=genres,
        label_visibility='collapsed'
    )
else:
    genre_select = genres

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
    -- Create CTE that returns all movies from ltboxd__watchlist after subtracting all matches
    -- from rottentomatoes
    WITH cte
    AS (
        SELECT name, year
        FROM "1_bronze"."ltboxd__watchlist"
        EXCEPT
        SELECT name, year_query AS year
        FROM "1_bronze"."rotten__all_movies_metadata"
    )
    SELECT
        -- Take number of remaining movies, divide it by length of ltboxd__watchlist and subtract
        -- the result from 1 to get the percentage of movies, that are covered by the rottentomatoes list
        1 - COUNT(*)::NUMERIC / NULLIF((SELECT COUNT(*) FROM "1_bronze"."ltboxd__watchlist"), 0) AS coverage_ratio
    FROM cte
    """
).to_dict('records')[0]

f"*Rotten tomatoes coverage of full watchlist: {round(100*df['coverage_ratio'])}%*"

# ==========================================================================================
# GET MOVIES AND STREAM PROVIDERS BASED ON USER SELECTION

# Dynamically build the SQL filter snippet based on the toggle switch
free_stream_filter = f"""
    AND (w.name, w.year) IN (
        SELECT title_tmdb AS name, EXTRACT(year FROM release_date) AS year
        FROM "1_bronze"."tmdb__movie_streams_complete"
        WHERE streaming_type IN {filter_streaming_types}
    )
""" if toggle_free_streaming else ""

# Dynamically build the streaming filter for the join if toggle is active
join_stream_filter = f"""
    AND b.streaming_type IN {filter_streaming_types}
""" if toggle_free_streaming else ""

# Convert selected genre-list to string for use in SQL
formatted_genres = f"({', '.join(repr(g) for g in genre_select)})" if genre_select else "(NULL)"
# Get movies filtered by user-parameters
df_stream_providers = (
    pg
    .sql_query(f"""
    WITH
    cte AS (
        SELECT
            w.name,
            w.year,
            w.duration,
            (w.critics_score + w.audience_score)/2 AS meta_score,
            w.poster,
            w.description,
            w.critics_score,
            w.audience_score
        FROM "3_gold"."watchlist_with_scores" w
        WHERE w.critics_score >= {select_critics_score[0]}
        AND w.critics_score <= {select_critics_score[1]}
        -- audience score
        AND w.audience_score >= {select_audience_score[0]}
        AND w.audience_score <= {select_audience_score[1]}
        -- duration
        AND w.duration >= {select_duration[0]}
        AND w.duration <= {select_duration[1]}
        -- year
        AND w.year >= {select_year[0]}
        AND w.year <= {select_year[1]}
        -- drop nulls
        AND w.critics_score IS NOT NULL
        AND w.audience_score IS NOT NULL
        -- genre filter
        AND EXISTS (
            SELECT 1 
            FROM "1_bronze"."ltboxd__movie_genres" g
            WHERE g.letterboxd_uri = w.letterboxd_uri
            AND g.genre->>0 IN {formatted_genres}
        )
        -- Toggle Filter for free streaming
        {free_stream_filter}
        --
        LIMIT 50
    )
    SELECT
        a.*,
        b.streaming_type,
        b.provider_name
    FROM cte a
    LEFT JOIN "1_bronze"."tmdb__movie_streams_complete" b
    ON a.name = b.title_tmdb
    AND a.year = EXTRACT(year FROM b.release_date)
    {join_stream_filter}
    ORDER BY meta_score DESC
    """
    )
)

# Dedup results to get distinct movies
df = (
    df_stream_providers
    .copy()
    .drop_duplicates(subset=['name','year'])
)

# Display images:
display_centered_images(
    df_in=df,
    max_images_x=4,
    max_images_y=3,
    hover_func=hover_image_movie_selector
    )

# =============================================================================================
# Display dataframe
df_disp = (
    df_stream_providers
    .groupby(['name','year'], as_index=False)
    .agg({
        'name':'first',
        'year':'first',
        'duration':'first',
        'meta_score':'first',
        'provider_name':lambda x: set(x)
        })
)

st.dataframe(
    df_disp,
    column_config={
        "name":"Movie Name",
        "year":"Release Year",
        "duration":"Duration [min]",
        "meta_score":"Meta Score [%]"
    }
)

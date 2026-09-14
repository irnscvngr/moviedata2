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
st.markdown(
    "<hr style='margin: 4px 0; border: none; border-top: 1px solid #e6e6e6;' />", 
    unsafe_allow_html=True
)

pg = pg_connect()

mpa = medimops_price_analyzer()
df_price_compare = mpa.analyze_price_lines()
df_recent_prices = mpa.df_recent_prices

# -----------------------------------------------------------------
# LOW RELATIVE PRICES

# Get titles with at least 4 entries
low_rel_price_link = (
    df_price_compare[df_price_compare['row_count']>=4]
    .sort_values('price_ratio')
)

# Title
c0, c1 = st.columns(2)
with c0:
    "##### Lower than average* prices"
with c1:
    "**4 weeks*"

# Create slider to scroll through movies
stepsize = 6
offset_movies = st.slider(
    label="offset_movies",
    min_value=0,
    max_value=low_rel_price_link.shape[0]-stepsize,
    label_visibility='collapsed'
    )

# Select 6 movie titles at a time with offset
low_rel_price_link = (
    low_rel_price_link
    .iloc[offset_movies:offset_movies+stepsize,:]
    .index
)

# Use selected movie titles as filter and display product prices
st.plotly_chart(
    mpa
    .plot_price_lines(
        df=df_recent_prices[df_recent_prices['product_link']
                         .isin(low_rel_price_link)],
        x='load_timestamp',
        y='product_price_desktop',
        color='product_link',
        hover_data='product_title'
        )
)

st.dataframe(
    df_price_compare[df_price_compare.index.isin(low_rel_price_link)]
    .sort_values('price_ratio')
    .drop(columns=['row_count','letterboxd_name','letterboxd_uri']),
    hide_index=True)

# -----------------------------------------------------------------
# LOW ABSOLUTE PRICES
st.divider()

df_low_abs_price = (
    df_price_compare[df_price_compare['price_latest']<4]
    .sort_values('price_latest')
    .head(20)
    .reset_index()
)
base_url = "https://www.medimops.de"
df_low_abs_price['product_link'] = base_url + df_low_abs_price['product_link']

# Title
"##### Prices < 4€"

# Display dataframe
st.dataframe(
    df_low_abs_price
    .loc[:,['product_title',
            'price_latest',
            'product_link',
            'letterboxd_name',
            'letterboxd_uri'
            ]]
    .rename(columns={
        'product_title':'Product',
        'price_latest':'Latest Price',
        'letterboxd_name':'Movie Query'
    }),
    column_config={
        "product_link": st.column_config.LinkColumn(
            "Link",        # Display header name
            display_text="[Link]",   # Label shown inside the cell (optional)
        ),
        "letterboxd_uri": st.column_config.LinkColumn(
            "Link",        # Display header name
            display_text="[Link]",   # Label shown inside the cell (optional)
        )
    }
)

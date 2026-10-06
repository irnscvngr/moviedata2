import streamlit as st
from moviedata.core.database import pg_connect
from moviedata.services.updates import updater

"### Movie counts"

db_update = updater()

# ==========================================================================================
st.button(
    label="Update Letterboxd Data",
    on_click=db_update.update_letterboxd)

st.button(
    label="Update Rottentomatoes Data",
    on_click=db_update.update_rottentomatoes)

st.button(
    label="Update Medimops Data",
    on_click=db_update.update_medimops)

def update_choices():
    """
    Updates current screenings from choices
    and also related TMDB data
    """
    db_update.update_choices_current_screenings()
    db_update.update_tmdb_data_from_choices()

st.button(
    label="Update Choices Data",
    on_click=update_choices)

# ==========================================================================================
st.divider()
"### Manual database ingest"
"**Add movie to TMDB data from URL**"
tmdb_url = st.text_input(label='tmdb_url', label_visibility='collapsed')
st.button(
    label="Update TMDB from URL",
    on_click=db_update.update_tmdb_from_url(tmdb_url=tmdb_url))

# ==========================================================================================
pg = pg_connect()
db_overview = {
    "1_bronze":{
        "tables":{
            "ltboxd__all_movies_metadata":{
                "display_name":"Letterboxd All Movies Metadata",
                "count":None
            },
            "ltboxd__watched":{
                "display_name":"Letterboxd Watched",
                "count":None
            },
            "ltboxd__ratings":{
                "display_name":"Letterboxd Ratings",
                "count":None
            },
            "ltboxd__watchlist":{
                "display_name":"Letterboxd Watchlist",
                "count":None
            },
            "ltboxd__br_collection":{
                "display_name":"Letterboxd Blu Ray Collection",
                "count":None
            }
        },
        "display_name":"Bronze Layer"
    }
}

for schema, subdict_schema in db_overview.items():
    for table, subdict_table in subdict_schema['tables'].items():
        df = pg.sql_query(f"""SELECT COUNT("letterboxd_uri") FROM "{schema}"."{table}" """)
        subdict_table['count'] = df.iloc[0,0]

# ==========================================================================================
st.divider()

str = ""
for schema, subdict_schema in db_overview.items():
    str += f"### {subdict_schema['display_name']}\n"
    for table, subdict_table in subdict_schema['tables'].items():
        str += f"**{subdict_table['display_name']}**: {subdict_table['count']}\n\n"

st.markdown(str)
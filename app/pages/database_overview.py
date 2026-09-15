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

st.button(
    label="Update Choices Data",
    on_click=db_update.update_choices_current_screenings)

# ==========================================================================================
pg = pg_connect()
db_overview = {
    "letterboxd":{
        "tables":{
            "lb_all_movies_metadata":{
                "display_name":"All Movies Metadata",
                "count":None
            },
            "watched":{
                "display_name":"Watched",
                "count":None
            },
            "ratings":{
                "display_name":"Ratings",
                "count":None
            },
            "watchlist":{
                "display_name":"Watchlist",
                "count":None
            },
            "br_collection":{
                "display_name":"Blu Ray Collection",
                "count":None
            }
        },
        "display_name":"Letterboxd"
    }
}

for schema, subdict_schema in db_overview.items():
    for table, subdict_table in subdict_schema['tables'].items():
        df = pg.sql_query(f"""SELECT COUNT("letterboxd_uri") FROM {schema}.{table}""")
        subdict_table['count'] = df.iloc[0,0]

# ==========================================================================================
st.divider()

str = ""
for schema, subdict_schema in db_overview.items():
    str += f"### {subdict_schema['display_name']}\n"
    for table, subdict_table in subdict_schema['tables'].items():
        str += f"**{subdict_table['display_name']}**: {subdict_table['count']}\n\n"

st.markdown(str)
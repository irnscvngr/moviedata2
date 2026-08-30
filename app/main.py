import streamlit as st

# Define pages using st.Page pointing to python file paths
page_movie_selector = st.Page("pages/movie_selector.py", title="Movie Selector", icon="🏠", default=True)
page_database_overview = st.Page("pages/database_overview.py", title="Database Overview", icon="🏠")
page_medimops_tracking = st.Page("pages/medimops_tracking.py", title="Medimops Tracking", icon="🏠")

# 2. Group pages into sections
pgnav = st.navigation({
    "General": [page_database_overview],
    "Data": [page_movie_selector, page_medimops_tracking],
})

# 3. Configure shared layout elements (like authentication or global sidebars)
st.set_page_config(page_title="Movie Data App")

pgnav.run()
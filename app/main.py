import streamlit as st
import sys
import asyncio

# Fix Playwright/Camoufox subprocess support on Windows under Streamlit
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

pages_general = [
    st.Page("pages/database_overview.py", title="Database Overview"),
]

pages_data = [
    st.Page("pages/movie_selector.py", title="Movie Selector",default=True),
    st.Page("pages/medimops_tracking.py", title="Medimops Tracking"),
    st.Page("pages/cluster_analysis.py", title="Cluster Analysis")
]

# 2. Group pages into sections
pgnav = st.navigation({
    "General": pages_general,
    "Data": pages_data,
})

# 3. Configure shared layout elements (like authentication or global sidebars)
st.set_page_config(page_title="Moviedata App", page_icon="🎬")

pgnav.run()
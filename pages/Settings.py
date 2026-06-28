import streamlit as st
from pathlib import Path
from services.database import DB_PATH

st.set_page_config(page_title="Settings", layout="wide")
st.title("Settings")

st.write("Database path:", str(DB_PATH))
st.write("Database exists:", Path(DB_PATH).exists())

st.subheader("Streamlit Cloud Notes")
st.markdown("""
- This version uses SQLite stored in `data/portfolio.db`.
- On Streamlit Community Cloud, local files can reset after redeploy/reboot.
- For permanent cloud storage, the next sprint can connect to Google Sheets or Supabase.
""")

if st.button("Initialize / repair database"):
    from services.database import init_db, seed_default_data
    init_db()
    seed_default_data()
    st.success("Database initialized.")

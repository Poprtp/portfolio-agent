import streamlit as st
from pathlib import Path
from services.database import DB_PATH, init_db, seed_default_data

st.set_page_config(page_title="Settings", layout="wide")
st.title("Settings")

st.write("Database:", str(DB_PATH))
st.write("Exists:", Path(DB_PATH).exists())

if st.button("Initialize / repair database"):
    init_db()
    seed_default_data()
    st.success("Database initialized.")

st.info("Note: Streamlit Community Cloud storage may reset after redeploy. Keep important records in GitHub/backup for now.")

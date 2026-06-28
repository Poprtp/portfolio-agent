import streamlit as st

st.set_page_config(page_title='Settings', layout='wide')
st.title('Settings')

st.subheader('OpenAI API Key')
st.write('For Streamlit Cloud, add this in Manage app → Settings → Secrets:')
st.code('OPENAI_API_KEY = "your_api_key_here"', language='toml')

st.subheader('Deploy checklist')
st.markdown('''
- `requirements.txt` exists
- `runtime.txt` uses Python 3.11
- Main file path is `app.py`
- Streamlit Cloud branch is `main`
''')

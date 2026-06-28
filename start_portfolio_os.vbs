Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\Portfolio-Agent"
WshShell.Run "cmd /c venv\Scripts\activate && streamlit run app.py --server.headless true", 0, False
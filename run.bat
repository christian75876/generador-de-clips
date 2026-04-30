@echo off
cd /d %~dp0

echo Iniciando Content Pipeline...

.venv\Scripts\python.exe -m streamlit run app.py --server.headless=false

pause

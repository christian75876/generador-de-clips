@echo off
cd /d %~dp0

echo Creando entorno virtual...
python -m venv .venv

echo Instalando dependencias...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo Setup completado.
echo Ahora puedes ejecutar run.bat
pause
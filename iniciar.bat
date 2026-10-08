@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Instalando/atualizando dependencias...
python -m pip install -U -r requirements.txt
echo.
python server.py
pause

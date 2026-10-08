@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Instalando/atualizando dependencias...
python -m pip install -U -r requirements.txt
echo.
where ffmpeg >nul 2>nul || echo [AVISO] ffmpeg nao encontrado. Instale com: winget install Gyan.FFmpeg  (depois feche e abra este arquivo)
python server.py
pause

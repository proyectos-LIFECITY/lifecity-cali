@echo off
title LifeCity - Iniciar (App + IA)
echo Iniciando LifeCity (servidor web + agente de IA)...
REM 1) Backend de IA (Nemotron/LangChain) en http://localhost:8000
start "LifeCity IA (backend :8000)" "%~dp0ai\run.bat"
REM 2) Servidor web local en http://localhost:8123
start "LifeCity Web (:8123)" "%~dp0LifeCity.bat"
REM 3) Abrir el navegador cuando arranquen
timeout /t 4 >nul
start "" "http://localhost:8123/"
exit

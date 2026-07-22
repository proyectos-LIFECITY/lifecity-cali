@echo off
title LifeCity - Agente de masas (IA) en http://localhost:8000
cd /d "G:\Mi unidad\6. REPOS\44. Visor Propiedades Cali\ai"
echo ==================================================
echo   LifeCity - Agente de masas (IA)
echo   Endpoint:  http://localhost:8000/suggest
echo   (deja esta ventana abierta mientras lo usas)
echo ==================================================
echo.
REM Carga tus claves si existe keys.bat  (copia keys.example.bat a keys.bat)
if exist "%~dp0keys.bat" call "%~dp0keys.bat"
if exist "%~dp0keys.bat" echo Claves cargadas desde keys.bat.
if not exist "%~dp0keys.bat" echo Sin keys.bat: la IA usa fallback. Copia keys.example.bat a keys.bat para Nemotron real.
echo.
python -m uvicorn server:app --host 127.0.0.1 --port 8000
echo.
echo El servidor se detuvo. Revisa el error de arriba. Pulsa una tecla para cerrar.
pause >nul

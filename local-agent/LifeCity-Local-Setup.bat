@echo off
REM ============================================================
REM  LifeCity Local · Instalador (doble clic)
REM  Instala el agente local para las funciones GPU del visor:
REM  detector de elementos (PointNet++) y nube de puntos.
REM  Corre en tu PC, en segundo plano, con TUS permisos.
REM  El backend general (catastro, agentes, IA) vive en la nube.
REM ============================================================
title LifeCity Local - Instalador
echo.
echo   Instalando LifeCity Local (funciones GPU en tu PC)...
echo   Se pedira permiso de administrador para registrar el arranque.
echo.
REM Ejecuta install.ps1 saltando la politica de ejecucion, elevando permisos.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','\"%~dp0install.ps1\"'"
echo.
echo   Si se abrio una ventana azul de PowerShell, sigue sus pasos ahi.
pause

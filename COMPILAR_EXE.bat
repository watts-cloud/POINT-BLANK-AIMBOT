@echo off
title Compilador Executavel - Auto Clique Point Blank
color 0B

echo ================================================================
echo      COMPILADOR EXECUTAVEL STANDALONE (PyInstaller)
echo ================================================================
echo.

echo [*] Instalando/atualizando PyInstaller...
py -3 -m pip install --upgrade pyinstaller

echo.
echo [*] Compilando gui.py em executavel unico...
py -3 -m PyInstaller --noconfirm --onedir --windowed --name "PointBlank_AutoClick" --add-data "config.json;." gui.py

if %errorlevel% neq 0 (
    echo.
    color 0C
    echo [ERRO] Ocorreu uma falha durante a compilacao.
    pause
    exit /b 1
)

echo.
echo ================================================================
color 0A
echo [SUCESSO] Executavel gerado na pasta: dist\PointBlank_AutoClick\
echo ================================================================
echo.
pause

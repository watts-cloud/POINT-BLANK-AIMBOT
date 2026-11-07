@echo off
setlocal enabledelayedexpansion
title Instalador - Auto Clique Point Blank
color 0B

echo ================================================================
echo       INSTALADOR AUTOMATICO - AUTO CLIQUE POINT BLANK
echo ================================================================
echo.

:: 1. Verificar instalacao do Python
echo [*] Verificando instalacao do Python no sistema...
where py >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=py -3"
    goto PYTHON_OK
)

where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=python"
    goto PYTHON_OK
)

echo.
color 0C
echo [ERRO] Python nao foi encontrado no seu computador!
echo Baixe e instale o Python em: https://www.python.org/downloads/
echo ATENCAO: No instalador do Python, marque a caixa "Add Python to PATH"!
echo.
pause
exit /b 1

:PYTHON_OK
echo [OK] Python detectado com sucesso!
%PY_CMD% --version
echo.

:: 2. Instalar dependencias
echo [*] Instalando bibliotecas necessarias via pip...
echo.
%PY_CMD% -m pip install --upgrade pip
%PY_CMD% -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    color 0C
    echo [ERRO] Falha ao instalar algumas dependencias. Verifique sua conexao de internet.
    pause
    exit /b 1
)

echo.
echo ================================================================
color 0A
echo [SUCESSO] Todas as dependencias foram instaladas com sucesso!
echo ================================================================
echo.
echo Para abrir o bot, basta dar um duplo clique em:
echo   - INICIAR.bat  (Abre o Painel Grafico)
echo   - RETICULA.bat (Abre apenas o Overlay de Mira)
echo.
pause

@echo off
title Publicador GitHub - Auto Clique Point Blank
color 0B

echo ================================================================
echo       PUBLICAR PROJETO NO GITHUB (watts-cloud)
echo ================================================================
echo.
echo Este script enviara os arquivos para o seu repositorio no GitHub.
echo.
set /p REPO_URL="Digite a URL do repositorio (ou pressione ENTER para https://github.com/watts-cloud/POINT-BLANK-AIMBOT.git): "
if "%REPO_URL%"=="" set REPO_URL=https://github.com/watts-cloud/POINT-BLANK-AIMBOT.git

echo.
echo [*] Conectando ao repositorio: %REPO_URL%
git remote remove origin 2>nul
git remote add origin %REPO_URL%
git branch -M main
echo [*] Enviando arquivos para o GitHub...
git push -u origin main

if %errorlevel% neq 0 (
    echo.
    color 0C
    echo [AVISO] Se o envio falhou, verifique se:
    echo 1. O repositorio foi criado previamente em: https://github.com/new
    echo 2. O Git esta autenticado na sua conta com Personal Access Token ou SSH.
    echo.
    pause
    exit /b 1
)

echo.
color 0A
echo ================================================================
echo [SUCESSO] Projeto publicado com sucesso no seu GitHub!
echo ================================================================
pause

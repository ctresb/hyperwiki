@echo off
setlocal

:: Verifica se o Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Python nao encontrado. Instale o Python e tente novamente.
    pause
    exit /b
)

:: Instala as dependências do requirements.txt
echo Instalando dependencias...
pip install -r requirements.txt

:: Inicia o app
echo Iniciando o app...
python app.py

endlocal
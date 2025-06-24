@echo off
REM Script de inicialização para Windows

echo Iniciando o Sistema de Monitoramento de Amônia...

REM Verifica se o Python está instalado
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Erro: Python não encontrado. Por favor, instale o Python 3.8 ou superior.
    pause
    exit /b 1
)

REM Cria ambiente virtual se não existir
if not exist "venv\" (
    echo Criando ambiente virtual...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo Erro ao criar ambiente virtual.
        pause
        exit /b 1
    )
)

REM Ativa o ambiente virtual e instala as dependências
echo Ativando ambiente virtual e instalando dependências...
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

REM Inicia a aplicação
echo Iniciando a aplicação...
python run.py

REM Mantém o console aberto em caso de erro
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo A aplicação foi encerrada com erro. Pressione qualquer tecla para sair...
    pause >nul
)

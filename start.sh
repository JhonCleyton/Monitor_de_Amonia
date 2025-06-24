#!/bin/bash
# Script de inicialização para Linux/macOS

echo "Iniciando o Sistema de Monitoramento de Amônia..."

# Verifica se o Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "Erro: Python 3 não encontrado. Por favor, instale o Python 3.8 ou superior."
    exit 1
fi

# Cria ambiente virtual se não existir
if [ ! -d "venv" ]; then
    echo "Criando ambiente virtual..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "Erro ao criar ambiente virtual."
        exit 1
    fi
fi

# Ativa o ambiente virtual e instala as dependências
echo "Ativando ambiente virtual e instalando dependências..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Inicia a aplicação
echo "Iniciando a aplicação..."
python3 run.py

# Mantém o terminal aberto em caso de erro
if [ $? -ne 0 ]; then
    echo -e "\nA aplicação foi encerrada com erro. Pressione qualquer tecla para sair..."
    read -n 1 -s
fi

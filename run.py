#!/usr/bin/env python3
"""
Script de inicialização do Sistema de Monitoramento de Amônia.
"""

import os
import sys
import logging
from pathlib import Path

# Adiciona o diretório raiz ao path para importações absolutas
sys.path.insert(0, str(Path(__file__).parent.absolute()))

# Configuração básica de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Verifica se o ambiente está configurado corretamente."""
    try:
        # Verifica se o arquivo .env existe
        if not os.path.exists('.env'):
            logger.warning("Arquivo .env não encontrado. Copiando de .env.example...")
            import shutil
            shutil.copy('.env.example', '.env')
            logger.info("Arquivo .env criado a partir de .env.example")
        
        # Verifica se as pastas necessárias existem
        os.makedirs('data', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao verificar o ambiente: {e}")
        return False

def install_dependencies():
    """Instala as dependências do projeto."""
    try:
        import pip
        logger.info("Instalando dependências...")
        pip.main(['install', '-r', 'requirements.txt'])
        return True
    except Exception as e:
        logger.error(f"Erro ao instalar dependências: {e}")
        return False

def main():
    """Função principal."""
    logger.info("Iniciando o Sistema de Monitoramento de Amônia")
    
    # Verifica o ambiente
    if not check_environment():
        logger.error("Falha na verificação do ambiente.")
        return 1
    
    # Tenta importar as dependências necessárias
    try:
        from src.main import main as app_main
    except ImportError as e:
        logger.error(f"Erro ao importar dependências: {e}")
        if input("Deseja instalar as dependências? (s/n): ").lower() == 's':
            if not install_dependencies():
                return 1
            try:
                from src.main import main as app_main
            except ImportError as e:
                logger.error(f"Falha ao importar após instalação: {e}")
                return 1
        else:
            return 1
    
    # Inicia a aplicação
    try:
        logger.info("Iniciando a aplicação...")
        return app_main()
    except Exception as e:
        logger.critical(f"Erro fatal: {e}", exc_info=True)
        return 1
    finally:
        logger.info("Aplicação encerrada")

if __name__ == "__main__":
    sys.exit(main())

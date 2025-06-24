"""
Módulo de logging para o Sistema de Monitoramento de Amônia.
"""

import os
import logging
import logging.handlers
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any

# Nível de log padrão
DEFAULT_LOG_LEVEL = logging.INFO

# Formato padrão para as mensagens de log
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Dicionário para armazenar os loggers já criados
_loggers = {}

def setup_logger(
    name: str = None,
    log_level: int = None,
    log_file: str = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """Configura e retorna um logger.
    
    Args:
        name: Nome do logger. Se None, retorna o logger raiz.
        log_level: Nível de log. Se None, usa o nível padrão.
        log_file: Caminho para o arquivo de log. Se None, não salva em arquivo.
        max_bytes: Tamanho máximo do arquivo de log em bytes antes de rotacionar.
        backup_count: Número de arquivos de backup a manter.
        
    Returns:
        logging.Logger: Instância do logger configurado.
    """
    # Se não for especificado um nome, usa o logger raiz
    if name is None:
        name = 'root'
    
    # Se o logger já foi criado, retorna a instância existente
    if name in _loggers:
        return _loggers[name]
    
    # Cria o logger
    logger = logging.getLogger(name)
    
    # Define o nível de log
    if log_level is None:
        log_level = DEFAULT_LOG_LEVEL
    logger.setLevel(log_level)
    
    # Cria um formatador
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Configura o handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Se um arquivo de log for especificado, adiciona um handler de arquivo
    if log_file:
        try:
            # Garante que o diretório do arquivo de log existe
            os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
            
            # Cria um handler de rotação de arquivo
            file_handler = RotatingFileHandler(
                filename=log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            logger.error(f"Não foi possível configurar o arquivo de log '{log_file}': {e}")
    
    # Armazena o logger no dicionário
    _loggers[name] = logger
    
    return logger

def get_logger(name: str = None) -> logging.Logger:
    """Obtém um logger pelo nome. Se não existir, cria um novo.
    
    Args:
        name: Nome do logger. Se None, retorna o logger raiz.
        
    Returns:
        logging.Logger: Instância do logger.
    """
    if name is None:
        name = 'root'
    
    if name in _loggers:
        return _loggers[name]
    
    # Se o logger não existe, cria um novo com as configurações padrão
    return setup_logger(name)

def configure_root_logger(
    log_level: int = None,
    log_file: str = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> None:
    """Configura o logger raiz.
    
    Args:
        log_level: Nível de log. Se None, usa o nível padrão.
        log_file: Caminho para o arquivo de log. Se None, não salva em arquivo.
        max_bytes: Tamanho máximo do arquivo de log em bytes antes de rotacionar.
        backup_count: Número de arquivos de backup a manter.
    """
    setup_logger(
        name='root',
        log_level=log_level,
        log_file=log_file,
        max_bytes=max_bytes,
        backup_count=backup_count
    )

# Configura o logger raiz quando o módulo é importado
configure_root_logger()

# Exemplo de uso:
if __name__ == "__main__":
    logger = get_logger(__name__)
    logger.info("Este é um exemplo de mensagem de informação")
    logger.warning("Este é um exemplo de mensagem de aviso")
    logger.error("Este é um exemplo de mensagem de erro")

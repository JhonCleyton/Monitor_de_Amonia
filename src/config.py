"""
Módulo de configuração do sistema de monitoramento de amônia.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Configuração do logger
logger = logging.getLogger(__name__)

# Caminho para o arquivo de configuração
CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.monitor_amonia')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

# Configuração padrão
DEFAULT_CONFIG = {
    "app": {
        "name": "Monitor de Amônia",
        "version": "1.0.0",
        "language": "pt_BR",
        "theme": "dark",
        "auto_start": True,
        "check_updates": True
    },
    "modbus": {
        "port": "COM3",
        "baudrate": 9600,
        "timeout": 1.0,
        "retries": 3,
        "scan_interval": 5000  # ms
    },
    "sensors": {
        "count": 10,
        "addresses": list(range(1, 11)),  # Endereços 1-10
        "min_value": 0.0,
        "max_value": 100.0,
        "warning_threshold": 70.0,
        "alarm_threshold": 90.0,
        "unit": "ppm"
    },
    "alerts": {
        "enabled": True,
        "min_interval": 300,  # segundos entre alertas
        "notify_email": True,
        "notify_sms": True,
        "notify_whatsapp": True,
        "notify_sound": True,
        "notify_popup": True
    },
    "email": {
        "enabled": False,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "use_tls": True,
        "username": "",
        "password": "",
        "sender_name": "Monitor de Amônia",
        "sender_email": "",
        "recipients": []
    },
    "whatsapp": {
        "enabled": False,
        "account_sid": "",
        "auth_token": "",
        "from_number": "",
        "recipients": []
    },
    "database": {
        "path": os.path.join(CONFIG_DIR, "data.db"),
        "backup_enabled": True,
        "backup_path": os.path.join(CONFIG_DIR, "backups"),
        "backup_interval": 86400,  # segundos (1 dia)
        "max_backups": 30
    },
    "ui": {
        "refresh_interval": 1000,  # ms
        "decimal_places": 1,
        "show_grid": True,
        "show_values": True,
        "show_limits": True
    }
}

def create_default_config() -> bool:
    """
    Cria um arquivo de configuração padrão.
    
    Returns:
        bool: True se o arquivo foi criado com sucesso, False caso contrário.
    """
    try:
        # Cria o diretório de configuração se não existir
        os.makedirs(CONFIG_DIR, exist_ok=True)
        
        # Salva a configuração padrão
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Arquivo de configuração padrão criado em {CONFIG_FILE}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao criar arquivo de configuração: {e}")
        return False

def load_config() -> Dict[str, Any]:
    """
    Carrega a configuração do arquivo.
    
    Returns:
        Dict[str, Any]: Dicionário com as configurações.
    """
    try:
        if not os.path.exists(CONFIG_FILE):
            logger.warning(f"Arquivo de configuração não encontrado em {CONFIG_FILE}")
            if create_default_config():
                return DEFAULT_CONFIG
            else:
                logger.error("Não foi possível criar o arquivo de configuração padrão")
                return {}
        
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # Atualiza a configuração com valores padrão para chaves ausentes
        updated = False
        for section, values in DEFAULT_CONFIG.items():
            if section not in config:
                config[section] = values
                updated = True
            else:
                for key, value in values.items():
                    if key not in config[section]:
                        config[section][key] = value
                        updated = True
        
        # Salva a configuração atualizada se necessário
        if updated:
            save_config(config)
            
        return config
        
    except Exception as e:
        logger.error(f"Erro ao carregar configuração: {e}")
        return {}

def save_config(config: Dict[str, Any]) -> bool:
    """
    Salva a configuração no arquivo.
    
    Args:
        config: Dicionário com as configurações.
        
    Returns:
        bool: True se a configuração foi salva com sucesso, False caso contrário.
    """
    try:
        # Cria o diretório de configuração se não existir
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        
        # Salva a configuração
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
            
        logger.info("Configuração salva com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao salvar configuração: {e}")
        return False

def get_config_value(key_path: str, default: Any = None) -> Any:
    """
    Obtém um valor de configuração a partir de um caminho de chave.
    
    Exemplo: get_config_value("modbus.port", "COM1")
    
    Args:
        key_path: Caminho da chave no formato "section.key" ou "section.subsection.key".
        default: Valor padrão a ser retornado se a chave não existir.
        
    Returns:
        O valor da configuração ou o valor padrão se não encontrado.
    """
    config = load_config()
    keys = key_path.split('.')
    
    try:
        value = config
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default

def set_config_value(key_path: str, value: Any) -> bool:
    """
    Define um valor de configuração.
    
    Args:
        key_path: Caminho da chave no formato "section.key" ou "section.subsection.key".
        value: Valor a ser definido.
        
    Returns:
        bool: True se o valor foi definido com sucesso, False caso contrário.
    """
    config = load_config()
    keys = key_path.split('.')
    
    try:
        # Navega até o nível anterior à chave final
        current_level = config
        for key in keys[:-1]:
            if key not in current_level:
                current_level[key] = {}
            current_level = current_level[key]
        
        # Define o valor
        current_level[keys[-1]] = value
        
        # Salva a configuração
        return save_config(config)
        
    except Exception as e:
        logger.error(f"Erro ao definir valor de configuração: {e}")
        return False

# Cria o diretório de configuração na importação do módulo
os.makedirs(CONFIG_DIR, exist_ok=True)

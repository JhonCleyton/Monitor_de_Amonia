"""
Módulo de configuração do Sistema de Monitoramento de Amônia.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

# Caminho para o arquivo de configuração
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

# Configuração padrão
DEFAULT_CONFIG = {
    "app": {
        "name": "Monitor de Amônia",
        "version": "1.0.0",
        "language": "pt_BR",
        "theme": "dark"
    },
    "modbus": {
        "port": "COM3",
        "baudrate": 9600,
        "bytesize": 8,
        "parity": "N",
        "stopbits": 1,
        "timeout": 1.0,
        "retries": 3,
        "debug": False
    },
    "sensors": [
        {
            "id": i,
            "name": f"Sensor {i}",
            "address": i,
            "unit": "ppm",
            "min_value": 0,
            "max_value": 100,
            "warning_threshold": 25,
            "alarm_threshold": 50,
            "enabled": True
        } for i in range(1, 11)  # 10 sensores por padrão
    ],
    "notifications": {
        "email": {
            "enabled": False,
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "use_tls": True,
            "username": "seu_email@example.com",
            "password": "sua_senha",
            "from_email": "monitor_amonia@example.com",
            "to_emails": ["alerta@example.com"],
            "subject_prefix": "[Alerta de Amônia] "
        },
        "whatsapp": {
            "enabled": False,
            "account_sid": "sua_account_sid",
            "auth_token": "seu_auth_token",
            "from_number": "whatsapp:+14155238886",
            "to_numbers": ["whatsapp:+5511999999999"]
        },
        "alarm_sound": {
            "enabled": True,
            "warning_file": "warning.wav",
            "alarm_file": "alarm.wav"
        }
    },
    "database": {
        "type": "sqlite",
        "filename": "monitor_amonia.db",
        "retention_days": 30
    },
    "ui": {
        "refresh_interval_ms": 1000,
        "decimal_places": 2,
        "date_format": "dd/MM/yyyy HH:mm:ss",
        "theme": {
            "primary_color": "#2196F3",
            "secondary_color": "#FF9800",
            "warning_color": "#FFC107",
            "danger_color": "#F44336",
            "success_color": "#4CAF50",
            "background_color": "#1E1E1E",
            "text_color": "#E0E0E0",
            "grid_color": "#333333"
        }
    }
}

def load_config(config_path: str = None) -> Dict[str, Any]:
    """Carrega a configuração a partir de um arquivo JSON.
    
    Args:
        config_path: Caminho para o arquivo de configuração. Se não informado, usa o caminho padrão.
        
    Returns:
        Dicionário com as configurações carregadas.
    """
    if config_path is None:
        config_path = CONFIG_FILE
    
    # Se o arquivo de configuração não existir, cria um com as configurações padrão
    if not os.path.exists(config_path):
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        save_config(DEFAULT_CONFIG, config_path)
        return DEFAULT_CONFIG
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Atualiza a configuração com valores padrão para chaves ausentes
        return _update_config(config, DEFAULT_CONFIG)
    
    except json.JSONDecodeError as e:
        logging.error(f"Erro ao decodificar o arquivo de configuração: {e}")
        return DEFAULT_CONFIG
    except Exception as e:
        logging.error(f"Erro ao carregar o arquivo de configuração: {e}")
        return DEFAULT_CONFIG

def save_config(config: Dict[str, Any], config_path: str = None) -> bool:
    """Salva a configuração em um arquivo JSON.
    
    Args:
        config: Dicionário com as configurações a serem salvas.
        config_path: Caminho para o arquivo de configuração. Se não informado, usa o caminho padrão.
        
    Returns:
        bool: True se o arquivo foi salvo com sucesso, False caso contrário.
    """
    if config_path is None:
        config_path = CONFIG_FILE
    
    try:
        # Garante que o diretório existe
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Salva o arquivo com formatação legível
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar o arquivo de configuração: {e}")
        return False

def _update_config(config: Dict[str, Any], default_config: Dict[str, Any]) -> Dict[str, Any]:
    """Atualiza recursivamente um dicionário de configuração com valores padrão.
    
    Args:
        config: Dicionário de configuração a ser atualizado.
        default_config: Dicionário com os valores padrão.
        
    Returns:
        Dicionário de configuração atualizado.
    """
    if not isinstance(config, dict):
        return default_config
    
    result = default_config.copy()
    
    for key, value in config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _update_config(value, result[key])
        else:
            result[key] = value
    
    return result

def get_setting(config: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Obtém um valor de configuração aninhado usando uma string de chave com notação de ponto.
    
    Exemplo: get_setting(config, "modbus.port", "COM1")
    
    Args:
        config: Dicionário de configuração.
        key: Chave no formato "chave1.chave2.chave3".
        default: Valor padrão a ser retornado se a chave não existir.
        
    Returns:
        O valor da configuração ou o valor padrão se a chave não existir.
    """
    keys = key.split('.')
    value = config
    
    try:
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        return default

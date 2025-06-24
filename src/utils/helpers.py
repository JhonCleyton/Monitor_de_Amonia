"""
Módulo com funções auxiliares para o Sistema de Monitoramento de Amônia.
"""

import os
import re
import sys
import time
import platform
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import pytz
from dateutil import parser

def validate_email(email: str) -> bool:
    """Valida se uma string é um endereço de e-mail válido.
    
    Args:
        email: String contendo o endereço de e-mail a ser validado.
        
    Returns:
        bool: True se o e-mail for válido, False caso contrário.
    """
    if not email or not isinstance(email, str):
        return False
    
    # Expressão regular para validar e-mail
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """Valida se uma string é um número de telefone válido.
    
    Args:
        phone: String contendo o número de telefone a ser validado.
        
    Returns:
        bool: True se o telefone for válido, False caso contrário.
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # Remove caracteres não numéricos
    digits = re.sub(r'\D', '', phone)
    
    # Verifica se tem entre 10 e 15 dígitos (incluindo DDD e código do país)
    return 10 <= len(digits) <= 15

def format_timestamp(
    timestamp: Union[float, int, str, datetime],
    timezone: str = 'America/Sao_Paulo',
    fmt: str = '%d/%m/%Y %H:%M:%S'
) -> str:
    """Formata um timestamp para uma string de data/hora legível.
    
    Args:
        timestamp: Timestamp a ser formatado. Pode ser um timestamp Unix (float/int),
                 uma string de data/hora ou um objeto datetime.
        timezone: Nome do fuso horário (timezone) para conversão.
        fmt: Formato de saída da data/hora.
        
    Returns:
        String formatada com a data/hora.
    """
    if timestamp is None:
        return ""
    
    # Converte para datetime se necessário
    if isinstance(timestamp, (int, float)):
        # Se for um timestamp Unix (segundos desde a época)
        dt = datetime.fromtimestamp(timestamp)
    elif isinstance(timestamp, str):
        # Tenta converter a string para datetime
        try:
            dt = parser.parse(timestamp)
        except (ValueError, TypeError):
            return ""
    elif isinstance(timestamp, datetime):
        dt = timestamp
    else:
        return ""
    
    # Aplica o fuso horário se especificado
    if timezone:
        try:
            tz = pytz.timezone(timezone)
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            dt = dt.astimezone(tz)
        except Exception:
            pass  # Mantém o datetime sem conversão em caso de erro
    
    # Formata a data/hora
    return dt.strftime(fmt)

def calculate_elapsed_time(start_time: float, end_time: float = None) -> str:
    """Calcula o tempo decorrido entre dois timestamps.
    
    Args:
        start_time: Timestamp de início (em segundos desde a época).
        end_time: Timestamp de término. Se None, usa o tempo atual.
        
    Returns:
        String formatada com o tempo decorrido (ex: "2h 30m 15s").
    """
    if end_time is None:
        end_time = time.time()
    
    elapsed_seconds = int(end_time - start_time)
    
    if elapsed_seconds < 0:
        return "0s"
    
    hours, remainder = divmod(elapsed_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or (hours > 0 and seconds > 0):
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    
    return " ".join(parts)

def resource_path(relative_path: str) -> str:
    """Obtém o caminho absoluto para um recurso, funcionando para desenvolvimento e para PyInstaller.
    
    Args:
        relative_path: Caminho relativo para o recurso.
        
    Returns:
        Caminho absoluto para o recurso.
    """
    try:
        # Caminho base para PyInstaller
        base_path = sys._MEIPASS
    except AttributeError:
        # Caminho base para desenvolvimento
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def is_windows() -> bool:
    """Verifica se o sistema operacional é Windows.
    
    Returns:
        bool: True se for Windows, False caso contrário.
    """
    return platform.system().lower() == 'windows'

def is_linux() -> bool:
    """Verifica se o sistema operacional é Linux.
    
    Returns:
        bool: True se for Linux, False caso contrário.
    """
    return platform.system().lower() == 'linux'

def is_macos() -> bool:
    """Verifica se o sistema operacional é macOS.
    
    Returns:
        bool: True se for macOS, False caso contrário.
    """
    return platform.system().lower() == 'darwin'

def get_platform() -> str:
    """Obtém o nome do sistema operacional atual.
    
    Returns:
        str: Nome do sistema operacional (windows, linux, darwin, etc.).
    """
    return platform.system().lower()

def get_app_data_dir(app_name: str = "MonitorAmmonia") -> str:
    """Obtém o diretório de dados do aplicativo.
    
    Args:
        app_name: Nome do aplicativo para criar um subdiretório.
        
    Returns:
        Caminho para o diretório de dados do aplicativo.
    """
    if is_windows():
        app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
        path = os.path.join(app_data, app_name)
    elif is_macos():
        path = os.path.expanduser(f'~/Library/Application Support/{app_name}')
    else:  # Linux e outros
        path = os.path.expanduser(f'~/.local/share/{app_name}')
    
    # Cria o diretório se não existir
    os.makedirs(path, exist_ok=True)
    
    return path

def parse_interval(interval_str: str) -> Optional[timedelta]:
    """Converte uma string de intervalo (ex: '1h 30m') em um objeto timedelta.
    
    Args:
        interval_str: String contendo o intervalo (ex: '1h 30m', '2d 4h 30m 15s').
        
    Returns:
        Objeto timedelta correspondente ao intervalo, ou None se a string for inválida.
    """
    if not interval_str or not isinstance(interval_str, str):
        return None
    
    # Expressão regular para extrair números e unidades
    pattern = r'(?P<value>\d+)(?P<unit>[smhdw]|min)'
    matches = re.finditer(pattern, interval_str.lower())
    
    if not matches:
        return None
    
    # Mapeamento de unidades para segundos
    unit_to_seconds = {
        's': 1,
        'm': 60,
        'min': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800
    }
    
    total_seconds = 0
    
    for match in matches:
        value = int(match.group('value'))
        unit = match.group('unit')
        
        if unit in unit_to_seconds:
            total_seconds += value * unit_to_seconds[unit]
    
    return timedelta(seconds=total_seconds) if total_seconds > 0 else None

def human_readable_size(size_bytes: int) -> str:
    """Converte um tamanho em bytes para uma representação legível.
    
    Args:
        size_bytes: Tamanho em bytes.
        
    Returns:
        String formatada (ex: '1.5 MB', '3.2 GB').
    """
    if size_bytes is None or not isinstance(size_bytes, (int, float)) or size_bytes < 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0 or unit == 'TB':
            break
        size_bytes /= 1024.0
    
    return f"{size_bytes:.1f} {unit}" if unit != 'B' else f"{int(size_bytes)} {unit}"

def sanitize_filename(filename: str) -> str:
    """Remove caracteres inválidos de um nome de arquivo.
    
    Args:
        filename: Nome do arquivo a ser sanitizado.
        
    Returns:
        Nome do arquivo sem caracteres inválidos.
    """
    if not filename:
        return "unnamed"
    
    # Caracteres inválidos em nomes de arquivo
    invalid_chars = '<>:"/\\|?*\0'
    
    # Remove caracteres inválidos
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove espaços em branco no início e no fim
    filename = filename.strip()
    
    # Se o nome ficar vazio, retorna um valor padrão
    if not filename:
        return "unnamed"
    
    return filename

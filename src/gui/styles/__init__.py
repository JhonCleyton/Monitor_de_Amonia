"""
Módulo de estilos para a interface gráfica do sistema de monitoramento de amônia.
"""

import os
from PyQt6.QtCore import QFile, QTextStream
from ...utils.logger import get_logger

logger = get_logger(__name__)

def load_stylesheet() -> str:
    """
    Carrega a folha de estilo da aplicação.
    
    Returns:
        str: Conteúdo da folha de estilo CSS.
    """
    try:
        # Caminho para o arquivo de estilo
        style_path = os.path.join(os.path.dirname(__file__), 'style.qss')
        
        # Verifica se o arquivo existe
        if not os.path.exists(style_path):
            logger.warning(f"Arquivo de estilo não encontrado: {style_path}")
            return ""
        
        # Lê o conteúdo do arquivo
        style_file = QFile(style_path)
        style_file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text)
        stream = QTextStream(style_file)
        style = stream.readAll()
        style_file.close()
        
        logger.info("Estilo carregado com sucesso")
        return style
        
    except Exception as e:
        logger.error(f"Erro ao carregar o estilo: {str(e)}")
        return ""

def apply_stylesheet(app):
    """
    Aplica a folha de estilo à aplicação.
    
    Args:
        app: Instância da aplicação Qt.
    """
    style = load_stylesheet()
    if style:
        app.setStyleSheet(style)

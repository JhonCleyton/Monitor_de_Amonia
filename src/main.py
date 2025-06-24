"""
Ponto de entrada principal do aplicativo de monitoramento de amônia.
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer, Qt

# Adiciona o diretório raiz ao path para importações absolutas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importações locais
from src.gui.main_window import MainWindow
from src.utils.logger import setup_logging
from src.config import load_config, CONFIG_FILE

# Configuração inicial do logging
setup_logging()
logger = logging.getLogger(__name__)

def check_requirements():
    """Verifica se todos os requisitos estão instalados."""
    try:
        import PyQt6
        import minimalmodbus
        import pyserial
        import pandas
        import numpy
        import matplotlib
        import python_dotenv
        import SQLAlchemy
        import pyqtgraph
        import reportlab
        import twilio
        import python_dateutil
        import PyJWT
        return True
    except ImportError as e:
        logger.error(f"Erro ao importar dependência: {e}")
        return False

def main():
    """Função principal da aplicação."""
    # Verifica se o arquivo de configuração existe
    if not os.path.exists(CONFIG_FILE):
        logger.warning(f"Arquivo de configuração não encontrado em {CONFIG_FILE}")
        # Cria um arquivo de configuração padrão
        from src.config import create_default_config
        create_default_config()
        logger.info("Arquivo de configuração padrão criado")
    
    # Carrega a configuração
    config = load_config()
    
    # Cria a aplicação
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Usa o estilo Fusion para uma aparência mais moderna
    
    # Configura o ícone da aplicação
    from PyQt6.QtGui import QIcon
    icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Cria a janela principal
    try:
        main_window = MainWindow()
        main_window.show()
        
        # Configura o tratamento de exceções não capturadas
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
                
            logger.critical("Erro não tratado:", exc_info=(exc_type, exc_value, exc_traceback))
            QMessageBox.critical(
                main_window,
                "Erro não tratado",
                f"Ocorreu um erro inesperado:\n{str(exc_value)}\n\n"
                f"Verifique o arquivo de log para mais detalhes."
            )
        
        # Configura o manipulador de exceções
        sys.excepthook = handle_exception
        
        # Inicia o loop de eventos
        sys.exit(app.exec())
        
    except Exception as e:
        logger.critical(f"Erro ao iniciar a aplicação: {e}", exc_info=True)
        QMessageBox.critical(
            None,
            "Erro na inicialização",
            f"Não foi possível iniciar o aplicativo:\n{str(e)}\n\n"
            "Verifique o arquivo de log para mais detalhes."
        )
        return 1

if __name__ == "__main__":
    # Verifica os requisitos antes de iniciar
    if not check_requirements():
        print("Erro: Algumas dependências não estão instaladas.")
        print("Por favor, instale todas as dependências com o comando:")
        print("pip install -r requirements.txt")
        sys.exit(1)
    
    # Inicia a aplicação
    sys.exit(main())

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from src.gui.main_window import MainWindow
from src.utils.logger import setup_logger

def main():
    # Configuração do logger
    logger = setup_logger()
    logger.info("Iniciando o Sistema de Monitoramento de Amônia")
    
    # Cria a aplicação
    app = QApplication(sys.argv)
    
    # Define o estilo da aplicação
    app.setStyle('Fusion')
    
    # Tenta carregar o ícone
    try:
        icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.png')
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
    except Exception as e:
        logger.warning(f"Não foi possível carregar o ícone: {e}")
    
    # Cria e mostra a janela principal
    try:
        window = MainWindow()
        window.show()
        
        # Executa o loop de eventos
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Erro fatal ao iniciar a aplicação: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()

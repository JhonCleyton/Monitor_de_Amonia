"""
Módulo principal da janela do aplicativo de monitoramento de amônia.
"""

import os
import json
import logging
from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QStatusBar, QVBoxLayout, 
                           QWidget, QMessageBox, QLabel, QSystemTrayIcon, 
                           QMenu, QApplication, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QSize, QPoint, QSettings
from PyQt6.QtGui import QIcon, QAction, QCloseEvent

from ..utils.logger import get_logger
from ..config import load_config, save_config, CONFIG_FILE
from .pages.dashboard import DashboardPage as DashboardTab
from .settings import SettingsTab
from .emergency_test import EmergencyTestTab

class MainWindow(QMainWindow):
    """Janela principal do aplicativo de monitoramento de amônia."""
    
    def __init__(self):
        """Inicializa a janela principal."""
        super().__init__()
        
        # Configurações iniciais
        self.logger = get_logger(__name__)
        self.config = load_config()
        self.tabs = None
        self.settings = QSettings("MonitorAmmonia", "MonitorAmmoniaApp")
        
        # Inicializa a interface do usuário
        self.init_ui()
        
        # Configura o ícone da bandeja do sistema
        self.setup_system_tray()
        
        # Carrega a geometria e o estado da janela
        self.load_window_state()
        
        self.logger.info("Interface do usuário inicializada com sucesso")
    
    def init_ui(self):
        """Configura a interface do usuário."""
        # Configurações da janela principal
        self.setWindowTitle("Sistema de Monitoramento de Amônia")
        self.setMinimumSize(1200, 800)
        
        # Define o estilo da aplicação
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QStatusBar {
                background: #e0e0e0;
                color: #333333;
                border-top: 1px solid #c4c4c4;
            }
        """)
        
        # Remove as margens da janela principal
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal sem margens
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Barra de status
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Label de status
        self.status_label = QLabel("Sistema Inicializado")
        self.status_bar.addPermanentWidget(self.status_label)
        
        # Inicializa o dashboard
        self.init_dashboard()
        
        # Barra de menu
        self.create_menus()
        
        # Atualiza a interface
        self.update_ui()
    
    def init_dashboard(self):
        """Inicializa o dashboard como tela cheia."""
        # Cria o dashboard com a configuração atual
        self.dashboard = DashboardTab(self, config=self.config)
        
        # Adiciona o dashboard ao layout principal
        self.centralWidget().layout().addWidget(self.dashboard)
        
        # Ajusta o tamanho do dashboard para preencher a janela
        self.dashboard.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Expanding
        )
    
    def create_menus(self):
        """Cria a barra de menus."""
        menu_bar = self.menuBar()
        
        # Menu Arquivo
        file_menu = menu_bar.addMenu("&Arquivo")
        
        # Ação para abrir configurações
        settings_action = QAction("&Configurações", self)
        settings_action.triggered.connect(self.show_settings)
        file_menu.addAction(settings_action)
        
        # Separador
        file_menu.addSeparator()
        
        # Ação para sair
        exit_action = QAction("Sai&r", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Menu Exibir
        view_menu = menu_bar.addMenu("&Exibir")
        
        # Ações para mostrar/ocultar barra de status
        self.show_statusbar_action = QAction("Barra de &Status", self, checkable=True)
        self.show_statusbar_action.setChecked(True)
        self.show_statusbar_action.triggered.connect(self.toggle_statusbar)
        view_menu.addAction(self.show_statusbar_action)
        
        # Menu Sensores
        sensor_menu = menu_bar.addMenu("&Sensores")
        
        # Ação Adicionar Sensor
        add_sensor_action = QAction('Adicionar Sensor', self)
        add_sensor_action.triggered.connect(self.dashboard.show_add_sensor_dialog)
        sensor_menu.addAction(add_sensor_action)
        
        # Ação Gerenciar Sensores
        manage_sensors_action = QAction('Gerenciar Sensores', self)
        manage_sensors_action.triggered.connect(self.dashboard.manage_sensors)
        sensor_menu.addAction(manage_sensors_action)
        
        # Menu Monitoramento
        monitor_menu = menu_bar.addMenu("&Monitoramento")
        
        # Ação Iniciar/Parar Monitoramento
        self.monitor_action = QAction('Iniciar Monitoramento', self)
        self.monitor_action.triggered.connect(self.dashboard.toggle_monitoring)
        monitor_menu.addAction(self.monitor_action)
        
        # Ação Testar Alarmes
        test_alarm_action = QAction('Testar Alarmes', self)
        test_alarm_action.triggered.connect(self.dashboard.trigger_test_alarm)
        monitor_menu.addAction(test_alarm_action)
        
        # Menu Ajuda
        help_menu = menu_bar.addMenu("A&juda")
        
        # Ação sobre
        about_action = QAction("&Sobre", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_system_tray(self):
        """Configura o ícone da bandeja do sistema."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.logger.warning("Bandeja do sistema não disponível")
            return
        
        # Cria o ícone da bandeja do sistema
        self.tray_icon = QSystemTrayIcon(self)
        
        # Tenta carregar o ícone
        try:
            icon_path = os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'icon.png')
            if os.path.exists(icon_path):
                self.tray_icon.setIcon(QIcon(icon_path))
        except Exception as e:
            self.logger.warning(f"Não foi possível carregar o ícone: {e}")
        
        # Cria o menu de contexto
        tray_menu = QMenu()
        
        # Ações do menu de contexto
        show_action = QAction("Abrir", self)
        show_action.triggered.connect(self.show_normal)
        tray_menu.addAction(show_action)
        
        exit_action = QAction("Sair", self)
        exit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        # Conecta o clique no ícone
        self.tray_icon.activated.connect(self.tray_icon_activated)
    
    def tray_icon_activated(self, reason):
        """Lidar com cliques no ícone da bandeja do sistema."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_normal()
    
    def show_normal(self):
        """Mostra a janela principal."""
        self.showNormal()
        self.activateWindow()
        self.raise_()
    
    def closeEvent(self, event: QCloseEvent):
        """Evento chamado ao fechar a janela."""
        # Salva o estado da janela
        self.save_window_state()
        
        # Pergunta ao usuário se ele realmente deseja sair
        reply = QMessageBox.question(
            self, 
            'Confirmação',
            'Tem certeza que deseja sair?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Fecha todos os recursos
            self.cleanup()
            event.accept()
        else:
            event.ignore()
    
    def cleanup(self):
        """Limpa os recursos antes de fechar o aplicativo."""
        self.logger.info("Encerrando aplicativo...")
        
        # Para todos os timers
        for timer in self.findChildren(QTimer):
            if timer.isActive():
                timer.stop()
        
        try:
            # Obtém as configurações atuais
            current_config = load_config()
            
            # Verifica se settings_tab existe antes de tentar acessá-lo
            if hasattr(self, 'settings_tab') and hasattr(self.settings_tab, 'get_settings'):
                # Obtém as configurações da interface
                ui_settings = self.settings_tab.get_settings()
                
                # Atualiza as configurações atuais com as configurações da interface
                if "modbus" in ui_settings and "modbus" in current_config:
                    if "port" in ui_settings["modbus"]:
                        current_config["modbus"]["port"] = ui_settings["modbus"]["port"]
                    if "baudrate" in ui_settings["modbus"]:
                        current_config["modbus"]["baudrate"] = ui_settings["modbus"]["baudrate"]
                
                if "notifications" in ui_settings and "email" in ui_settings["notifications"] and "email" in current_config:
                    email_settings = ui_settings["notifications"]["email"]
                    current_config["email"]["enabled"] = email_settings.get("enabled", False)
                    
                    # Adiciona o destinatário à lista de destinatários se não estiver vazio
                    recipient = email_settings.get("recipient", "")
                    if recipient:
                        if "recipients" not in current_config["email"] or not isinstance(current_config["email"]["recipients"], list):
                            current_config["email"]["recipients"] = []
                        
                        if recipient not in current_config["email"]["recipients"]:
                            current_config["email"]["recipients"].append(recipient)
                
                # Salva as configurações atualizadas
                save_config(current_config)
                self.logger.info("Configurações salvas com sucesso ao encerrar o aplicativo.")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar as configurações ao encerrar o aplicativo: {e}", exc_info=True)
        
        # Fecha as conexões com os sensores
        if hasattr(self, 'dashboard_tab') and hasattr(self.dashboard_tab, 'cleanup'):
            self.dashboard_tab.cleanup()
    
    def save_window_state(self):
        """Salva o estado e a geometria da janela."""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("windowSize", self.size())
        self.settings.setValue("windowPosition", self.pos())
    
    def load_window_state(self):
        """Carrega o estado e a geometria da janela."""
        if self.settings.contains("geometry"):
            self.restoreGeometry(self.settings.value("geometry"))
        if self.settings.contains("windowState"):
            self.restoreState(self.settings.value("windowState"))
        
        # Define um tamanho padrão se não houver configurações salvas
        default_size = QSize(1200, 800)
        size = self.settings.value("windowSize", default_size)
        self.resize(size if isinstance(size, QSize) else default_size)
        
        # Define a posição da janela
        if self.settings.contains("windowPosition"):
            self.move(self.settings.value("windowPosition"))
        else:
            # Centraliza a janela na tela
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)
    
    def update_ui(self):
        """Atualiza a interface do usuário."""
        # Atualiza o título da janela com a versão
        self.setWindowTitle(f"{self.config.get('app', {}).get('name', 'Monitor de Amônia')} v{self.config.get('app', {}).get('version', '1.0.0')}")
    
    def show_status_message(self, message: str, timeout: int = 5000):
        """Exibe uma mensagem na barra de status.
        
        Args:
            message: Mensagem a ser exibida
            timeout: Tempo em milissegundos para a mensagem desaparecer
        """
        self.status_bar.showMessage(message, timeout)
    
    def show_settings(self):
        """Exibe a janela de configurações."""
        from .settings import SettingsDialog
        
        dialog = SettingsDialog(self)
        if dialog.exec():
            # Recarregar configurações se necessário
            self.config = load_config()
            # Aqui você pode adicionar lógica para aplicar as configurações
            self.statusBar().showMessage("Configurações salvas com sucesso", 3000)
    
    def toggle_statusbar(self, checked):
        """Alterna a visibilidade da barra de status.
        
        Args:
            checked: Se True, mostra a barra de status; se False, oculta.
        """
        self.statusBar().setVisible(checked)
    
    def show_about(self):
        """Exibe a caixa de diálogo 'Sobre'."""
        about_text = """
        <h2>Sistema de Monitoramento de Amônia</h2>
        <p>Versão: {version}</p>
        <p>Desenvolvido por: Sua Empresa</p>
        <p>Contato: contato@empresa.com</p>
        <p>Copyright {year} - Todos os direitos reservados</p>
        """.format(
            version=self.config.get('app', {}).get('version', '1.0.0'),
            year=2025
        )
        
        QMessageBox.about(self, "Sobre", about_text)
    
    def show_error(self, title: str, message: str):
        """Exibe uma mensagem de erro.
        
        Args:
            title: Título da mensagem
            message: Mensagem de erro
        """
        QMessageBox.critical(self, title, message)
    
    def show_warning(self, title: str, message: str):
        """Exibe uma mensagem de aviso.
        
        Args:
            title: Título da mensagem
            message: Mensagem de aviso
        """
        QMessageBox.warning(self, title, message)
    
    def show_info(self, title: str, message: str):
        """Exibe uma mensagem informativa.
        
        Args:
            title: Título da mensagem
            message: Mensagem informativa
        """
        QMessageBox.information(self, title, message)
    
    def confirm(self, title: str, message: str) -> bool:
        """Exibe uma caixa de diálogo de confirmação.
        
        Args:
            title: Título da mensagem
            message: Mensagem de confirmação
            
        Returns:
            bool: True se o usuário confirmou, False caso contrário
        """
        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

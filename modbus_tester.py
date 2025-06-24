"""
Módulo para testar e configurar sensores Modbus RTU.
"""

import json
import logging
import os
import sys
import time
import traceback
import winsound  # Para tocar som de alarme no Windows
from datetime import datetime, timedelta
from time import sleep
from enum import Enum

import minimalmodbus
import serial

# Importações do PyQt6 organizadas por módulo
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import (
    QColor, QFont, QPalette, QAction, QIcon, QPixmap, 
    QTextCursor, QTextCharFormat, QTextFormat, QActionGroup, QShortcut
)

from PyQt6.QtWidgets import (
    # Widgets básicos
    QApplication, QMainWindow, QWidget, QDialog, QLabel, 
    QPushButton, QLineEdit, QComboBox, QCheckBox, QRadioButton,
    QSpinBox, QDoubleSpinBox, QSlider, QProgressBar, QTextEdit, QPlainTextEdit,
    
    # Layouts
    QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout, QStackedLayout,
    
    # Containers
    QGroupBox, QFrame, QTabWidget, QScrollArea, QSplitter, QToolBox,
    QTabBar, QMdiArea, QMdiSubWindow, QDockWidget, QWizard, QWizardPage,
    
    # Itens de lista/tabela
    QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, 
    QTreeWidgetItemIterator, QTableWidget, QTableWidgetItem, QHeaderView,
    
    # Diálogos
    QDialogButtonBox, QMessageBox, QFileDialog, QColorDialog, 
    QFontDialog, QInputDialog, QProgressDialog,
    
    # Menus e barra de ferramentas
    QMenuBar, QMenu, QToolBar, QToolButton,
    
    # Outros
    QStatusBar, QSystemTrayIcon, QSplashScreen, QWhatsThis,
    QStyle, QStyleFactory, QStyleOption
)

# Importações específicas para acesso direto
from PyQt6.QtCore import pyqtSlot, pyqtSignal, QObject, QThread, QSizeF, QPoint, QRect, QUrl
from PyQt6.QtGui import (
    QPixmap, QImage, QPainter, QPen, QBrush, QLinearGradient, 
    QRadialGradient, QConicalGradient, QFontMetrics, QTextDocument,
    QTextOption, QTextCursor, QTextCharFormat, QTextBlockFormat, 
    QTextListFormat, QTextTableFormat, QTextImageFormat, QTextFormat
)

# Configuração do logger
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f'modbus_tester_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# Configura o logger raiz
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Cria um logger específico para a aplicação
logger = logging.getLogger('ModbusTester')
logger.setLevel(logging.DEBUG)

# Adiciona um FileHandler para salvar logs em arquivo
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Configuração de cores
COLOR_GOOD = "#4CAF50"  # Verde
COLOR_WARNING = "#FFC107"  # Amarelo
COLOR_ERROR = "#F44336"  # Vermelho
COLOR_DISCONNECTED = "#9E9E9E"  # Cinza

class RegisterType(Enum):
    """Tipos de registros Modbus suportados."""
    COIL = 1
    DISCRETE_INPUT = 2
    HOLDING_REGISTER = 3
    INPUT_REGISTER = 4

class ModbusTester(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Monitoramento - Sensores Modbus RTU")
        
        # Configura o tamanho inicial e mínimo da janela
        screen = QApplication.primaryScreen().availableGeometry()
        width = min(1280, int(screen.width() * 0.9))
        height = min(800, int(screen.height() * 0.9))
        self.resize(width, height)
        self.setMinimumSize(1024, 768)
        
        # Configurações iniciais
        self.port = ""
        self.baudrate = 9600
        self.connected = False
        self.instrument = None
        self.devices = []
        self.update_interval = 1000  # 1 segundo
        self.reading_in_progress = False
        self.closing = False
        self.logger = logging.getLogger('ModbusTester')
        self.logger.info('Inicializando Sistema de Monitoramento')
        
        # Estilo da aplicação
        self.setStyle(QStyleFactory.create('Fusion'))
        
        # Configura a paleta de cores
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.Text, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 215))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)
        
        # Timer para atualização automática
        self.update_timer = QTimer()
        self.update_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.update_timer.timeout.connect(self.safe_update_readings)
        
        # Inicializa a interface
        self.init_ui()
        
        # Carrega configurações salvas
        self.load_settings()
        
        # Escaneia portas disponíveis
        self.scan_ports()
        
        # Configura o ícone da janela
        self.setup_ui_styles()
        
        # Configura o fechamento seguro
        self.installEventFilter(self)
    
    def setup_ui_styles(self):
        """Configura os estilos da interface."""
        self.setStyleSheet("""
            /* Estilo geral da aplicação */
            QMainWindow {
                background-color: #f5f5f5;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            /* Estilo das abas */
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                margin: 2px;
                background: white;
            }
            
            QTabBar::tab {
                background: #e0e0e0;
                border: 1px solid #c0c0c0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 100px;
                padding: 8px 16px;
                margin-right: 2px;
            }
            
            QTabBar::tab:selected {
                background: white;
                border-bottom: 2px solid #0078d7;
                font-weight: bold;
            }
            
            /* Estilo dos grupos */
            QGroupBox {
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                margin-top: 20px;
                padding: 12px 10px 10px 10px;
                font-weight: bold;
                color: #333333;
                font-size: 13px;
                background: white;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                margin-top: -20px;
                background: white;
            }
            
            /* Estilo dos botões */
            QPushButton {
                padding: 8px 20px;
                border: 1px solid #0078d7;
                border-radius: 4px;
                background-color: #0078d7;
                color: white;
                font-weight: 500;
                min-width: 100px;
                font-size: 12px;
            }
            
            QPushButton:hover {
                background-color: #106ebe;
                border-color: #005a9e;
            }
            
            QPushButton:pressed {
                background-color: #005a9e;
                border-color: #004b84;
                padding-top: 9px;
                padding-bottom: 7px;
            }
            
            QPushButton:disabled {
                background-color: #e0e0e0;
                border-color: #cccccc;
                color: #a0a0a0;
            }
            
            /* Estilo da tabela */
            QTableWidget {
                border: 1px solid #d0d0d0;
                background-color: white;
                selection-background-color: #e3f2fd;
                selection-color: black;
                gridline-color: #f0f0f0;
                font-size: 12px;
            }
            
            QTableWidget::item {
                padding: 6px;
            }
            
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 8px;
                border: 1px solid #e0e0e0;
                font-weight: bold;
                font-size: 12px;
            }
            
            /* Estilo dos campos de entrada */
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                padding: 6px;
                min-height: 24px;
                background: white;
            }
            
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #0078d7;
            }
            
            /* Barra de status */
            QStatusBar {
                background-color: #f0f0f0;
                color: #505050;
                border-top: 1px solid #d0d0d0;
                font-size: 11px;
            }
            
            /* Estilo para mensagens de erro */
            .error-text {
                color: #d32f2f;
                background-color: #ffebee;
                padding: 2px 6px;
                border-radius: 3px;
            }
            
            /* Estilo para status desconectado */
            .disconnected {
                color: #9e9e9e;
                font-style: italic;
            }
        """)
    
    def init_ui(self):
        """Inicializa a interface do usuário com um design moderno e funcional."""
        try:
            # Configuração da janela principal
            self.setWindowTitle('Monitor de Amônia - Modbus Tester')
            self.setMinimumSize(1280, 800)
            
            # Define o estilo Fusion para uma aparência mais moderna
            QApplication.setStyle(QStyleFactory.create('Fusion'))
            
            # Widget central
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QVBoxLayout(central_widget)
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(10)
            
            # Cabeçalho da aplicação
            header = QHBoxLayout()
            
            # Logo e título
            logo_label = QLabel()
            try:
                # Tenta carregar um ícone de exemplo (substitua pelo seu próprio ícone)
                from PyQt6.QtGui import QPixmap, QIcon
                from PyQt6.QtCore import QSize
                
                # Cria um ícone simples em memória (substitua por um arquivo real)
                pixmap = QPixmap(40, 40)
                pixmap.fill(Qt.GlobalColor.blue)
                logo_label.setPixmap(pixmap)
            except Exception as e:
                self.logger.warning(f"Não foi possível carregar o logo: {str(e)}")
                
            title_label = QLabel('Monitor de Amônia')
            title_font = QFont()
            title_font.setPointSize(16)
            title_font.setBold(True)
            title_label.setFont(title_font)
            
            header.addWidget(logo_label)
            header.addWidget(title_label, 1, Qt.AlignmentFlag.AlignLeft)
            
            # Barra de status do sistema
            self.system_status = QLabel('Sistema Pronto')
            self.system_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.system_status.setStyleSheet('''
                QLabel {
                    background-color: #e8f5e9;
                    color: #2e7d32;
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-weight: bold;
                }
            ''')
            header.addWidget(self.system_status)
            
            main_layout.addLayout(header)
            
            # Barra de ferramentas principal
            self.toolbar = QToolBar('Barra de Ferramentas')
            self.toolbar.setIconSize(QSize(24, 24))
            self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            
            # Ações da barra de ferramentas
            self.connect_action = QAction('Conectar', self)
            self.connect_action.triggered.connect(self.toggle_connection)
            self.toolbar.addAction(self.connect_action)
            
            self.disconnect_action = QAction('Desconectar', self)
            self.disconnect_action.triggered.connect(self.disconnect_modbus)
            self.disconnect_action.setEnabled(False)
            self.toolbar.addAction(self.disconnect_action)
            
            self.toolbar.addSeparator()
            
            self.start_action = QAction('Iniciar Leitura', self)
            self.start_action.triggered.connect(self.start_reading)
            self.toolbar.addAction(self.start_action)
            
            self.stop_action = QAction('Parar Leitura', self)
            self.stop_action.triggered.connect(self.stop_reading)
            self.stop_action.setEnabled(False)
            self.toolbar.addAction(self.stop_action)
            
            self.toolbar.addSeparator()
            
            self.settings_action = QAction('Configurações', self)
            self.settings_action.triggered.connect(self.show_settings)
            self.toolbar.addAction(self.settings_action)
            
            self.help_action = QAction('Ajuda', self)
            self.help_action.triggered.connect(self.show_help)
            self.toolbar.addAction(self.help_action)
            
            main_layout.addWidget(self.toolbar)
            
            # Área de conteúdo com abas
            self.tabs = QTabWidget()
            self.tabs.setDocumentMode(True)  # Estilo mais limpo
            self.tabs.setTabPosition(QTabWidget.TabPosition.North)
            self.tabs.setMovable(False)
            
            # Aba de Conexão
            connection_tab = QWidget()
            self.tabs.addTab(connection_tab, "Conexão")
            self.setup_connection_tab(connection_tab)
            
            # Aba de Dispositivos
            devices_tab = QWidget()
            self.tabs.addTab(devices_tab, "Dispositivos")
            self.setup_devices_tab(devices_tab)
            
            # Aba de Leitura/Visualização
            reading_tab = QWidget()
            self.tabs.addTab(reading_tab, "Leitura")
            self.setup_reading_tab(reading_tab)
            
            # Aba de Logs (será implementada posteriormente)
            # logs_tab = QWidget()
            # self.tabs.addTab(logs_tab, "Logs")
            # self.setup_logs_tab(logs_tab)
            
            main_layout.addWidget(self.tabs, 1)  # O parâmetro 1 faz o widget expandir
            
            # Barra de status na parte inferior
            self.status_bar = QStatusBar()
            self.status_bar.setStyleSheet(''"""
                QStatusBar {
                    background-color: #f0f0f0;
                    color: #333333;
                    border-top: 1px solid #d0d0d0;
                    padding: 2px 8px;
                }
                QStatusBar::item {
                    border: none;
                }
            """)
            
            # Adiciona widgets à barra de status
            self.status_icon = QLabel()
            self.status_icon.setPixmap(QPixmap('icons/info.png').scaled(16, 16, 
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.status_bar.addPermanentWidget(self.status_icon)
            
            self.status_label = QLabel('Pronto')
            self.status_bar.addWidget(self.status_label, 1)  # Expande para preencher o espaço
            
            self.connection_status = QLabel('Desconectado')
            self.connection_status.setStyleSheet('color: #d32f2f; font-weight: bold;')
            self.status_bar.addPermanentWidget(self.connection_status)
            
            self.reading_status = QLabel('Parado')
            self.reading_status.setStyleSheet('color: #1976d2;')
            self.status_bar.addPermanentWidget(self.reading_status)
            
            self.last_update = QLabel('Última atualização: N/A')
            self.status_bar.addPermanentWidget(self.last_update)
            
            self.setStatusBar(self.status_bar)
            
            # Aplica os estilos personalizados
            self.setup_ui_styles()
            
            # Atualiza o status inicial
            self.update_system_status('Pronto para conectar')
            
        except Exception as e:
            QMessageBox.critical(self, 'Erro de Inicialização', 
                              f'Não foi possível inicializar a interface: {str(e)}')
            self.logger.error(f'Erro ao inicializar a interface: {str(e)}', exc_info=True)
    
    def update_system_status(self, message, status_type='info'):
        """Atualiza a mensagem de status do sistema com estilo apropriado.
        
        Args:
            message (str): Mensagem a ser exibida
            status_type (str): Tipo de status ('info', 'warning', 'error', 'success')
        """
        if not hasattr(self, 'system_status'):
            return
            
        status_styles = {
            'info': 'background-color: #e3f2fd; color: #0d47a1;',
            'warning': 'background-color: #fff8e1; color: #ff8f00;',
            'error': 'background-color: #ffebee; color: #c62828;',
            'success': 'background-color: #e8f5e9; color: #2e7d32;'
        }
        
        style = status_styles.get(status_type.lower(), status_styles['info'])
        self.system_status.setStyleSheet(f'QLabel {{ {style} padding: 5px 10px; border-radius: 4px; font-weight: bold; }}')
        self.system_status.setText(message)
        
        # Atualiza o ícone de status
        if hasattr(self, 'status_icon'):
            icon_map = {
                'info': 'info',
                'warning': 'warning',
                'error': 'error',
                'success': 'success'
            }
            icon_name = icon_map.get(status_type.lower(), 'info')
            # Aqui você pode adicionar lógica para definir o ícone apropriado
            # Por enquanto, apenas atualizamos o texto
    
    def start_reading(self):
        """Inicia a leitura contínua dos dispositivos."""
        if not self.connected:
            self.update_system_status("Não é possível iniciar a leitura: não há conexão ativa", 'error')
            return
            
        try:
            self.reading_in_progress = True
            self.start_action.setEnabled(False)
            self.stop_action.setEnabled(True)
            self.connect_action.setEnabled(False)
            self.disconnect_action.setEnabled(False)
            
            # Inicia o timer para leitura contínua
            self.update_timer = QTimer(self)
            self.update_timer.timeout.connect(self.update_readings)
            self.update_timer.start(self.update_interval)
            
            self.reading_status.setText("Em execução")
            self.reading_status.setStyleSheet('color: #388e3c; font-weight: bold;')
            self.update_system_status("Leitura iniciada com sucesso", 'success')
            
            # Força uma primeira leitura imediatamente
            self.update_readings()
            
        except Exception as e:
            self.logger.error(f"Erro ao iniciar leitura: {str(e)}", exc_info=True)
            self.update_system_status(f"Erro ao iniciar leitura: {str(e)}", 'error')
    
    def stop_reading(self):
        """Para a leitura contínua dos dispositivos."""
        try:
            if hasattr(self, 'update_timer') and self.update_timer.isActive():
                self.update_timer.stop()
                
            self.reading_in_progress = False
            self.start_action.setEnabled(True)
            self.stop_action.setEnabled(False)
            self.connect_action.setEnabled(not self.connected)
            self.disconnect_action.setEnabled(self.connected)
            
            self.reading_status.setText("Parado")
            self.reading_status.setStyleSheet('color: #d32f2f;')
            self.update_system_status("Leitura parada", 'info')
            
        except Exception as e:
            self.logger.error(f"Erro ao parar leitura: {str(e)}", exc_info=True)
            self.update_system_status(f"Erro ao parar leitura: {str(e)}", 'error')
    
    def show_settings(self):
        """Exibe a janela de configurações."""
        # Implementação básica - pode ser expandida conforme necessário
        QMessageBox.information(self, "Configurações", "Janela de configurações será implementada em breve.")
    
    def show_help(self):
        """Exibe a janela de ajuda."""
        help_text = """
        <h2>Ajuda - Monitor de Amônia</h2>
        <p>Este aplicativo permite monitorar sensores Modbus RTU.</p>
        
        <h3>Como usar:</h3>
        <ol>
            <li>Conecte-se à porta serial do conversor Modbus</li>
            <li>Adicione os dispositivos que deseja monitorar</li>
            <li>Inicie a leitura para começar a monitorar os valores</li>
        </ol>
        
        <h3>Atalhos:</h3>
        <ul>
            <li><b>F1</b>: Exibir esta ajuda</li>
            <li><b>Ctrl+Q</b>: Sair do aplicativo</li>
            <li><b>F5</b>: Atualizar leitura (quando em modo manual)</li>
        </ul>
        
        <p>Para mais informações, consulte a documentação do sistema.</p>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Ajuda")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(help_text)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
    
    def setup_connection_tab(self, tab):
        """Configura a aba de conexão com um design moderno e funcional."""
        try:
            # Layout principal com margens e espaçamento
            layout = QVBoxLayout(tab)
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(20)
            
            # Card de configuração da conexão
            connection_card = QGroupBox("Configuração da Conexão")
            connection_card.setStyleSheet("""
                QGroupBox {
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 15px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
            """)
            
            port_layout = QVBoxLayout(connection_card)
            port_layout.setSpacing(15)
            
            # Seção de configuração da porta
            port_group = QGroupBox("Configurações da Porta Serial")
            port_group.setStyleSheet("""
                QGroupBox {
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    margin-top: 10px;
                    padding: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
            """)
            
            form_layout = QFormLayout(port_group)
            form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            form_layout.setSpacing(10)
            
            # Campo de seleção de porta
            port_row = QHBoxLayout()
            self.port_combo = QComboBox()
            self.port_combo.setEditable(True)
            self.port_combo.setMinimumWidth(200)
            self.port_combo.setStyleSheet("""
                QComboBox {
                    padding: 5px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    min-width: 200px;
                }
                QComboBox:hover {
                    border: 1px solid #999;
                }
            """)
            
            # Botão para atualizar lista de portas
            refresh_btn = QPushButton()
            refresh_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
            refresh_btn.setToolTip("Atualizar lista de portas")
            refresh_btn.setFixedSize(30, 30)
            refresh_btn.clicked.connect(self.scan_ports)
            
            port_row.addWidget(self.port_combo, 1)
            port_row.addWidget(refresh_btn)
            
            # Configuração de baudrate
            self.baudrate_combo = QComboBox()
            self.baudrate_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
            self.baudrate_combo.setCurrentText(str(self.baudrate))
            self.baudrate_combo.setStyleSheet("""
                QComboBox {
                    padding: 5px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    min-width: 200px;
                }
            """)
            
            # Adiciona linhas ao formulário
            form_layout.addRow("<b>Porta Serial:</b>", port_row)
            form_layout.addRow("<b>Baudrate:</b>", self.baudrate_combo)
            
            # Seção de status da conexão
            status_group = QGroupBox("Status da Conexão")
            status_group.setStyleSheet("""
                QGroupBox {
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    margin-top: 10px;
                    padding: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
            """)
            
            status_layout = QVBoxLayout(status_group)
            
            # Indicador de status
            self.connection_status_indicator = QLabel()
            self.connection_status_indicator.setFixedSize(16, 16)
            self.connection_status_indicator.setStyleSheet(
                "background-color: #e0e0e0; border-radius: 8px;"
            )
            
            self.connection_status_text = QLabel("Desconectado")
            self.connection_status_text.setStyleSheet("color: #757575; font-weight: bold;")
            
            status_row = QHBoxLayout()
            status_row.addWidget(self.connection_status_indicator)
            status_row.addWidget(self.connection_status_text, 1)
            status_row.addStretch()
            
            status_layout.addLayout(status_row)
            
            # Botões de ação
            button_container = QWidget()
            button_layout = QHBoxLayout(button_container)
            button_layout.setContentsMargins(0, 0, 0, 0)
            
            self.connect_btn = QPushButton("Conectar")
            self.connect_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOkButton))
            self.connect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """)
            self.connect_btn.clicked.connect(self.toggle_connection)
            
            self.disconnect_btn = QPushButton("Desconectar")
            self.disconnect_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
            self.disconnect_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """)
            self.disconnect_btn.setEnabled(False)
            self.disconnect_btn.clicked.connect(self.disconnect_modbus)
            
            button_layout.addWidget(self.connect_btn)
            button_layout.addWidget(self.disconnect_btn)
            button_layout.addStretch()
            
            # Adiciona tudo ao layout principal
            port_layout.addWidget(port_group)
            port_layout.addWidget(status_group)
            port_layout.addWidget(button_container)
            port_layout.addStretch()
            
            # Adiciona o card ao layout principal
            layout.addWidget(connection_card)
            
            # Adiciona um widget vazio para ocupar o espaço restante
            layout.addStretch()
            
            # Carrega as portas disponíveis
            self.scan_ports()
            
        except Exception as e:
            self.logger.error(f"Erro ao configurar a aba de conexão: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Erro", f"Não foi possível configurar a aba de conexão: {str(e)}")
    
    def setup_devices_tab(self, tab):
        """Configura a aba de dispositivos."""
        layout = QVBoxLayout(tab)
        
        # Tabela de dispositivos
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(6)
        self.device_table.setHorizontalHeaderLabels(["ID", "Endereço", "Tipo", "Registro", "Valor", "Ações"])
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Botões de controle
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Adicionar Dispositivo")
        add_btn.clicked.connect(self.add_device_dialog)
        
        remove_btn = QPushButton("Remover Selecionado")
        remove_btn.clicked.connect(self.remove_device)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        
        layout.addLayout(btn_layout)
        layout.addWidget(self.device_table)
    
    def setup_reading_tab(self, tab):
        """Configura a aba de leitura."""
        layout = QVBoxLayout(tab)
        
        # Controles de leitura
        control_layout = QHBoxLayout()
        
        # Grupo de botões de controle
        btn_group = QHBoxLayout()
        
        self.start_btn = QPushButton("Iniciar Leitura")
        self.start_btn.clicked.connect(self.toggle_reading)
        
        self.test_alarm_btn = QPushButton("Testar Alarme")
        self.test_alarm_btn.setToolTip("Dispara um alarme de teste para verificação visual")
        self.test_alarm_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffeb3b;
                border: 1px solid #ffc107;
                font-weight: bold;
                padding: 5px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ffc107;
            }
            QPushButton:pressed {
                background-color: #ffa000;
            }
        """)
        self.test_alarm_btn.clicked.connect(self.trigger_test_alarm)
        
        btn_group.addWidget(self.start_btn)
        btn_group.addWidget(self.test_alarm_btn)
        
        # Configuração do intervalo
        interval_layout = QHBoxLayout()
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(100, 10000)
        self.interval_spin.setValue(self.update_interval)
        self.interval_spin.setSuffix(" ms")
        self.interval_spin.valueChanged.connect(self.update_read_interval)
        
        interval_layout.addWidget(QLabel("Intervalo:"))
        interval_layout.addWidget(self.interval_spin)
        
        # Adiciona os layouts ao layout principal
        control_layout.addLayout(interval_layout)
        control_layout.addStretch()
        control_layout.addLayout(btn_group)
        
        # Área de leitura
        self.reading_area = QVBoxLayout()
        
        # Adiciona ao layout principal
        layout.addLayout(control_layout)
        layout.addLayout(self.reading_area)
    
    def toggle_connection(self):
        """Conecta ou desconecta do dispositivo Modbus."""
        if self.connected:
            self.disconnect_modbus()
        else:
            self.connect_modbus()
    
    def connect_modbus(self):
        """Estabelece conexão com o dispositivo Modbus."""
        self.logger.info("Iniciando conexão Modbus...")
        
        # Obtém o valor real da porta (pode conter descrição)
        port_data = self.port_combo.currentData()
        self.port = port_data if port_data else self.port_combo.currentText().split(' - ')[0]
        
        try:
            self.baudrate = int(self.baudrate_combo.currentText())
            self.logger.debug(f"Tentando conectar em {self.port} @ {self.baudrate} baud")
        except ValueError as e:
            error_msg = f"Baudrate inválido: {self.baudrate_combo.currentText()}"
            self.logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "Erro", "Baudrate inválido!")
            return
        
        if not self.port or 'Nenhuma' in self.port or 'Erro' in self.port:
            error_msg = f"Porta serial inválida: {self.port}"
            self.logger.error(error_msg)
            QMessageBox.critical(self, "Erro", "Selecione uma porta serial válida!")
            return
        
        # Desabilita o botão de conectar para evitar múltiplos cliques
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Conectando...")
        self.logger.debug("Botão de conexão desabilitado durante tentativa de conexão")
        
        try:
            # Cria o instrumento Modbus
            self.instrument = minimalmodbus.Instrument(
                port=self.port,
                slaveaddress=1,  # Endereço temporário para teste
                mode=minimalmodbus.MODE_RTU,
                close_port_after_each_call=False
            )
            
            # Configurações da porta serial
            self.instrument.serial.baudrate = self.baudrate
            self.instrument.serial.timeout = 1.0  # Timeout reduzido para testes
            self.instrument.serial.bytesize = 8
            self.instrument.serial.parity = serial.PARITY_NONE
            self.instrument.serial.stopbits = 1
            
            # Tenta ler um registro para testar a conexão
            connection_success = False
            test_addresses = [1, 2, 3, 4, 5]  # Endereços comuns para teste
            
            for addr in test_addresses:
                try:
                    self.instrument.address = addr
                    self.logger.debug(f"Testando conexão com endereço {addr}...")
                    value = self.instrument.read_register(0, functioncode=4)
                    connection_success = True
                    self.logger.info(f"Conexão bem-sucedida com o dispositivo no endereço {addr}. Valor lido: {value}")
                    break
                except Exception as e:
                    self.logger.warning(f"Tentativa de conexão com endereço {addr} falhou: {str(e)}")
                    continue
            
            if not connection_success:
                # Se nenhum endereço respondeu, tenta sem leitura inicial
                self.logger.warning("Nenhum dispositivo respondeu nas tentativas iniciais, continuando...")
                connection_success = True
            
            if connection_success:
                self.connected = True
                self.connect_btn.setText("Desconectar")
                status_msg = f"Conectado a {self.port} @ {self.baudrate} baud"
                self.update_status(status_msg)
                self.logger.info(status_msg)
                
                # Habilita/desabilita controles
                self.scan_btn.setEnabled(False)
                self.port_combo.setEnabled(False)
                self.baudrate_combo.setEnabled(False)
                self.logger.debug("Controles de conexão desabilitados após conexão bem-sucedida")
                
                # Salva as configurações
                self.save_settings()
                self.logger.debug("Configurações salvas após conexão bem-sucedida")
            
        except Exception as e:
            error_msg = f"Não foi possível conectar a {self.port}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar a {self.port}")
            self.update_status("Falha na conexão", error=True)
        finally:
            self.connect_btn.setEnabled(True)
            self.logger.debug("Botão de conexão reabilitado após tentativa de conexão")
    
    def disconnect_modbus(self):
        """Fecha a conexão com o dispositivo Modbus."""
        self.logger.info("Iniciando desconexão do dispositivo Modbus...")
        
        # Para o timer de atualização
        if self.update_timer.isActive():
            self.logger.debug("Parando timer de atualização...")
            self.update_timer.stop()
        
        # Fecha a conexão serial
        try:
            if self.instrument and hasattr(self.instrument, 'serial') and hasattr(self.instrument.serial, 'is_open'):
                if self.instrument.serial.is_open:
                    self.logger.debug("Fechando conexão serial...")
                    self.instrument.serial.close()
                    self.logger.info("Conexão serial fechada com sucesso")
                else:
                    self.logger.debug("Conexão serial já estava fechada")
        except Exception as e:
            error_msg = f"Erro ao fechar a conexão serial: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
        
        # Atualiza o estado da interface
        self.connected = False
        self.connect_btn.setText("Conectar")
        self.update_status("Desconectado")
        self.logger.info("Interface atualizada para estado desconectado")
        
        # Reabilita controles
        self.scan_btn.setEnabled(True)
        self.port_combo.setEnabled(True)
        self.baudrate_combo.setEnabled(True)
        self.logger.debug("Controles de conexão reabilitados")
        
        # Para qualquer leitura em andamento
        if hasattr(self, 'reading_in_progress'):
            if self.reading_in_progress:
                self.logger.debug("Sinalizando parada de leitura em andamento...")
                self.reading_in_progress = False
            else:
                self.logger.debug("Sem leituras em andamento")
    
    def toggle_reading(self):
        """Inicia ou para a leitura automática."""
        self.logger.info("Alternando estado de leitura...")
        
        try:
            if self.update_timer.isActive():
                # Para a leitura
                self.logger.info("Parando leitura automática...")
                self.update_timer.stop()
                self.start_btn.setText("Iniciar Leitura")
                self.start_btn.setStyleSheet("")
                self.update_status("Leitura parada", clear_after=3000)
                self.logger.info("Leitura automática parada com sucesso")
                
                # Atualiza o ícone do botão para refletir o estado parado
                self.start_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            else:
                # Inicia a leitura
                self.logger.info("Iniciando leitura automática...")
                
                # Verificações de pré-requisitos
                if not self.connected or not hasattr(self, 'instrument') or not self.instrument:
                    error_msg = "Não é possível iniciar a leitura: Nenhum dispositivo conectado"
                    self.logger.warning(error_msg)
                    
                    # Feedback visual mais destacado
                    self.start_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #f8d7da;
                            color: #721c24;
                            border: 1px solid #f5c6cb;
                        }
                    """)
                    
                    QMessageBox.warning(
                        self, 
                        "Aviso", 
                        "<b>Nenhum dispositivo conectado</b><br><br>"
                        "Conecte-se a um dispositivo Modbus antes de iniciar a leitura."
                    )
                    return
                    
                if not hasattr(self, 'device_table') or self.device_table.rowCount() == 0:
                    error_msg = "Não é possível iniciar a leitura: Nenhum dispositivo configurado"
                    self.logger.warning(error_msg)
                    
                    # Feedback visual mais destacado
                    self.start_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #fff3cd;
                            color: #856404;
                            border: 1px solid #ffeeba;
                        }
                    """)
                    
                    QMessageBox.warning(
                        self, 
                        "Aviso", 
                        "<b>Nenhum dispositivo configurado</b><br><br>"
                        "Adicione pelo menos um dispositivo na aba 'Dispositivos' antes de iniciar a leitura."
                    )
                    return
                
                try:
                    # Configura o timer com um intervalo mínimo de 100ms
                    interval = max(100, self.update_interval)
                    self.logger.debug(f"Configurando timer de atualização com intervalo de {interval}ms")
                    
                    # Atualiza a interface para refletir o estado de leitura
                    self.start_btn.setText(" Parar Leitura")
                    self.start_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #d4edda;
                            color: #155724;
                            border: 1px solid #c3e6cb;
                        }
                        QPushButton:hover {
                            background-color: #c3e6cb;
                            border-color: #b1dfbb;
                        }
                    """)
                    
                    # Adiciona um ícone de parar ao botão
                    self.start_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
                    
                    self.update_timer.start(interval)
                    self.update_status(f"Lendo dados a cada {interval}ms...", error=False)
                    
                    self.logger.info(f"Leitura automática iniciada com intervalo de {interval}ms")
                    
                    # Primeira leitura imediata em uma thread separada
                    self.logger.debug("Agendando primeira leitura imediata...")
                    QTimer.singleShot(100, self.safe_update_readings)
                    
                except Exception as e:
                    error_msg = f"Erro ao iniciar leitura automática: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    
                    self.update_timer.stop()
                    
                    # Mensagem de erro mais detalhada
                    error_dialog = QMessageBox(self)
                    error_dialog.setIcon(QMessageBox.Icon.Critical)
                    error_dialog.setWindowTitle("Erro na Leitura")
                    error_dialog.setText("<b>Não foi possível iniciar a leitura automática</b>")
                    error_dialog.setInformativeText(
                        f"Ocorreu um erro ao tentar iniciar a leitura automática.\n\n"
                        f"<b>Detalhes:</b> {str(e)}"
                    )
                    error_dialog.setDetailedText(traceback.format_exc())
                    error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
                    error_dialog.exec()
                    
                    self.update_status("Erro ao iniciar leitura", error=True)
                    self.start_btn.setText("Iniciar Leitura")
                    self.start_btn.setStyleSheet("")
                    self.start_btn.setIcon(QIcon())  # Remove o ícone
                    
        except Exception as e:
            error_msg = f"Erro inesperado em toggle_reading: {str(e)}"
            self.logger.critical(error_msg, exc_info=True)
            
            # Mostra mensagem de erro detalhada
            QMessageBox.critical(
                self,
                "Erro Inesperado",
                f"<b>Ocorreu um erro inesperado:</b><br><br>{str(e)}\n\n"
                "Verifique o log para mais detalhes."
            )
            
            # Tenta restaurar o estado da interface
            self.update_timer.stop()
            self.start_btn.setText("Iniciar Leitura")
            self.start_btn.setStyleSheet("")
            self.start_btn.setIcon(QIcon())  # Remove o ícone
            self.update_status("Erro inesperado", error=True)
    
    def mark_device_as_disconnected(self, row, error_msg=None):
        """Marca um dispositivo como desconectado na interface."""
        try:
            # Obtém o item de valor ou cria um novo se não existir
            if self.device_table.item(row, 4) is None:
                value_item = QTableWidgetItem()
                self.device_table.setItem(row, 4, value_item)
            else:
                value_item = self.device_table.item(row, 4)
            
            # Define o texto e estilo para indicar dispositivo desconectado
            value_item.setText("Desconectado")
            value_item.setForeground(QColor(COLOR_DISCONNECTED))
            value_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Normal))
            value_item.setToolTip("O dispositivo não está respondendo" + (f": {error_msg}" if error_msg else ""))
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # Adiciona um estilo CSS personalizado
            value_item.setData(Qt.ItemDataRole.UserRole, "disconnected")
            
            # Atualiza o ícone de status se existir
            if hasattr(self, 'status_icons') and row in self.status_icons:
                self.status_icons[row].setPixmap(self.disconnected_icon.pixmap(16, 16))
            
            self.logger.debug(f"Dispositivo na linha {row + 1} marcado como desconectado" + (f": {error_msg}" if error_msg else ""))
            
        except Exception as e:
            self.logger.error(f"Erro ao marcar dispositivo como desconectado: {str(e)}", exc_info=True)
    
    def update_ui_for_disconnected_state(self):
        """Atualiza a interface para refletir o estado desconectado."""
        self.logger.debug("Atualizando interface para estado desconectado")
        
        # Atualiza todos os dispositivos na tabela
        if hasattr(self, 'device_table'):
            for row in range(self.device_table.rowCount()):
                self.mark_device_as_disconnected(row, "Sem conexão com o dispositivo")
    
    def update_read_interval(self):
        """Atualiza o intervalo de leitura."""
        self.update_interval = self.interval_spin.value()
        if self.update_timer.isActive():
            self.update_timer.setInterval(self.update_interval)
    
    def update_readings(self):
        """Atualiza as leituras dos dispositivos."""
        if not self.connected or not hasattr(self, 'instrument') or not self.instrument:
            self.logger.warning("Tentativa de leitura sem conexão ativa ou instrumento inválido")
            return
        
        # Evita múltiplas leituras simultâneas
        if hasattr(self, 'reading_in_progress') and self.reading_in_progress:
            self.logger.debug("Leitura já em andamento, ignorando chamada")
            return
            
        self.reading_in_progress = True
        self.logger.debug("Iniciando ciclo de leitura dos dispositivos")
        
        try:
            # Verifica se a tabela ainda existe (pode ter sido fechada)
            if not hasattr(self, 'device_table') or not self.device_table:
                self.logger.warning("Tabela de dispositivos não encontrada")
                return
                
            total_devices = self.device_table.rowCount()
            self.logger.debug(f"Iniciando leitura de {total_devices} dispositivos registrados")
            
            for row in range(total_devices):
                try:
                    # Verifica se a janela ainda está aberta
                    if not self.isVisible():
                        self.logger.info("Janela fechada, interrompendo leitura")
                        return
                        
                    # Obtém os dados do dispositivo
                    device_id = self.device_table.item(row, 0).text() if self.device_table.item(row, 0) else "Desconhecido"
                    address_item = self.device_table.item(row, 1)  # Coluna de endereço
                    register_item = self.device_table.item(row, 3)  # Coluna de registro
                    type_item = self.device_table.item(row, 2)      # Coluna de tipo
                    
                    if not all([address_item, register_item, type_item]):
                        self.logger.warning(f"Dispositivo {device_id} na linha {row + 1} com dados incompletos")
                        continue
                        
                    self.logger.debug(f"Processando dispositivo {device_id} (linha {row + 1})")
                        
                    try:
                        address = int(address_item.text())
                        register = int(register_item.text())
                        reg_type = type_item.text()
                        self.logger.debug(f"Endereço: {address}, Registro: {register}, Tipo: {reg_type}")
                    except (ValueError, AttributeError) as e:
                        error_msg = f"Erro ao converter valores para o dispositivo {device_id}: {str(e)}"
                        self.logger.error(error_msg, exc_info=True)
                        continue
                    
                    # Determina a função com base no tipo de registro
                    try:
                        if reg_type == "INPUT_REGISTER":
                            func_code = 4
                        elif reg_type == "HOLDING_REGISTER":
                            func_code = 3
                        elif reg_type == "COIL":
                            func_code = 1
                        elif reg_type == "DISCRETE_INPUT":
                            func_code = 2
                        else:
                            error_msg = f"Tipo de registro inválido para o dispositivo {device_id}: {reg_type}"
                            self.logger.error(error_msg)
                            continue
                            
                        self.logger.debug(f"Função Modbus selecionada: {func_code} para {reg_type}")
                    except Exception as e:
                        error_msg = f"Erro ao determinar função Modbus para {device_id}: {str(e)}"
                        self.logger.error(error_msg, exc_info=True)
                        continue
                    
                    # Lê o registro
                    try:
                        self.instrument.address = address
                        self.logger.debug(f"Lendo registro {register} do dispositivo {address}...")
                        
                        if func_code in (3, 4):  # Registros de 16 bits
                            value = self.instrument.read_register(register, functioncode=func_code)
                            self.logger.debug(f"Valor lido do registro {register}: {value} (16 bits)")
                        else:  # Coils e entradas discretas (1 bit)
                            value = self.instrument.read_bit(register, functioncode=func_code)
                            self.logger.debug(f"Valor lido do bit {register}: {value} (1 bit)")
                        
                        # Atualiza a tabela de forma segura
                        try:
                            if self.device_table.item(row, 4) is None:
                                value_item = QTableWidgetItem()
                                self.device_table.setItem(row, 4, value_item)
                                self.logger.debug("Novo item de valor criado na tabela")
                            else:
                                value_item = self.device_table.item(row, 4)
                            
                            value_item.setText(str(value))
                            value_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            self.logger.debug(f"Valor {value} atualizado na interface")
                            
                        except Exception as e:
                            error_msg = f"Erro ao atualizar interface para o dispositivo {device_id}: {str(e)}"
                            self.logger.error(error_msg, exc_info=True)
                        
                    except Exception as read_error:
                        error_msg = str(read_error)
                        
                        # Mensagens de erro mais amigáveis
                        if "No communication" in error_msg:
                            error_msg = "Sem comunicação"
                        elif "Invalid response" in error_msg:
                            error_msg = "Resposta inválida"
                        elif "Modbus Error" in error_msg:
                            error_msg = f"Erro Modbus: {error_msg}"
                        
                        log_msg = f"Erro ao ler dispositivo {device_id} (endereço {address}, registro {register}): {error_msg}"
                        self.logger.error(log_msg, exc_info=True)
                        
                        try:
                            if self.device_table.item(row, 4) is None:
                                error_item = QTableWidgetItem()
                                self.device_table.setItem(row, 4, error_item)
                            else:
                                error_item = self.device_table.item(row, 4)
                                
                            error_item.setText("Erro")
                            error_item.setForeground(QColor(COLOR_ERROR))
                            error_item.setToolTip(error_msg)
                            error_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                            
                        except Exception as ui_error:
                            self.logger.error(f"Falha ao atualizar interface com erro: {str(ui_error)}", exc_info=True)
                
                except Exception as e:
                    print(f"Erro ao processar dispositivo na linha {row}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Erro na atualização de leituras: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.reading_in_progress = False
    
    def safe_update_readings(self):
        """Método seguro para atualizar leituras, capturando exceções."""
        self.logger.debug("Iniciando atualização segura de leituras...")
        
        try:
            self.logger.debug("Chamando update_readings...")
            self.update_readings()
            self.logger.debug("Atualização de leituras concluída com sucesso")
            
        except Exception as e:
            error_msg = f"Erro ao atualizar leituras: {str(e)}"
            self.logger.critical(error_msg, exc_info=True)
            
            # Tenta atualizar a interface para mostrar o erro
            try:
                self.update_status("Erro nas leituras", error=True)
            except Exception as ui_error:
                self.logger.error(f"Falha ao atualizar status da interface: {str(ui_error)}", exc_info=True)
                
        finally:
            self.reading_in_progress = False
            self.logger.debug("Estado de leitura em andamento definido como False")
    
    def add_device_dialog(self):
        """Exibe diálogo para adicionar um novo dispositivo."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Adicionar Dispositivo")
        layout = QVBoxLayout()
        
        # Formulário
        form = QFormLayout()
        
        # Campos do formulário
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Ex: Sensor de Amônia 1")
        
        address_spin = QSpinBox()
        address_spin.setRange(1, 247)
        address_spin.setValue(1)
        
        type_combo = QComboBox()
        type_combo.addItems(["INPUT_REGISTER", "HOLDING_REGISTER", "COIL", "DISCRETE_INPUT"])
        
        register_spin = QSpinBox()
        register_spin.setRange(0, 65535)
        register_spin.setValue(0)
        
        # Adiciona campos ao formulário
        form.addRow("Nome:", name_edit)
        form.addRow("Endereço:", address_spin)
        form.addRow("Tipo de Registro:", type_combo)
        form.addRow("Número do Registro:", register_spin)
        
        # Botões
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        
        # Layout principal
        layout.addLayout(form)
        layout.addWidget(button_box)
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if not name_edit.text().strip():
                QMessageBox.warning(self, "Aviso", "Por favor, insira um nome para o dispositivo.")
                return
                
            self.add_device(
                name=name_edit.text().strip(),
                address=address_spin.value(),
                reg_type=type_combo.currentText(),
                register=register_spin.value()
            )
    
    def add_device(self, name, address, reg_type, register):
        """Adiciona um novo dispositivo à tabela."""
        row = self.device_table.rowCount()
        self.device_table.insertRow(row)
        
        # ID
        id_item = QTableWidgetItem(str(row + 1))
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Endereço
        addr_item = QTableWidgetItem(str(address))
        addr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Tipo
        type_item = QTableWidgetItem(reg_type)
        type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Registro
        reg_item = QTableWidgetItem(str(register))
        reg_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Valor (inicialmente vazio)
        val_item = QTableWidgetItem("-")
        val_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Ações
        actions_widget = QWidget()
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(5, 2, 5, 2)
        
        read_btn = QPushButton("Ler")
        read_btn.clicked.connect(lambda: self.read_single_device(row))
        
        actions_layout.addWidget(read_btn)
        actions_widget.setLayout(actions_layout)
        
        # Adiciona à tabela
        self.device_table.setItem(row, 0, id_item)
        self.device_table.setItem(row, 1, addr_item)
        self.device_table.setItem(row, 2, type_item)
        self.device_table.setItem(row, 3, reg_item)
        self.device_table.setItem(row, 4, val_item)
        self.device_table.setCellWidget(row, 5, actions_widget)
        
        # Ajusta o tamanho das linhas
        self.device_table.resizeRowsToContents()
    
    def remove_device(self):
        """Remove o dispositivo selecionado."""
        selected = self.device_table.currentRow()
        if selected >= 0:
            self.device_table.removeRow(selected)
            # Atualiza os IDs
            for row in range(selected, self.device_table.rowCount()):
                self.device_table.item(row, 0).setText(str(row + 1))
    
    def read_single_device(self, row):
        """Lê um único dispositivo."""
        if not self.connected:
            QMessageBox.warning(self, "Aviso", "Conecte-se a um dispositivo primeiro!")
            return
            
        try:
            # Obtém os dados do dispositivo
            address_item = self.device_table.item(row, 1)  # Coluna de endereço
            register_item = self.device_table.item(row, 3)  # Coluna de registro
            type_item = self.device_table.item(row, 2)      # Coluna de tipo
            
            if not all([address_item, register_item, type_item]):
                return
                
            address = int(address_item.text())
            register = int(register_item.text())
            reg_type = type_item.text()
            
            # Determina a função com base no tipo de registro
            if reg_type == "INPUT_REGISTER":
                func_code = 4
            elif reg_type == "HOLDING_REGISTER":
                func_code = 3
            elif reg_type == "COIL":
                func_code = 1
            elif reg_type == "DISCRETE_INPUT":
                func_code = 2
            else:
                raise ValueError(f"Tipo de registro inválido: {reg_type}")
            
            # Lê o registro
            self.instrument.address = address
            
            if func_code in (3, 4):  # Registros de 16 bits
                value = self.instrument.read_register(register, functioncode=func_code)
            else:  # Coils e entradas discretas (1 bit)
                value = self.instrument.read_bit(register, functioncode=func_code)
            
            # Atualiza a tabela
            value_item = QTableWidgetItem(str(value))
            value_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.device_table.setItem(row, 4, value_item)
            
            self.update_status(f"Leitura: {value}")
            
        except Exception as e:
            error_item = QTableWidgetItem("Erro")
            error_item.setForeground(QColor(COLOR_ERROR))
            error_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.device_table.setItem(row, 4, error_item)
            self.update_status(f"Erro: {str(e)}", error=True)
    
    def scan_ports(self):
        """Escaneia as portas seriais disponíveis e atualiza a interface."""
        try:
            import serial.tools.list_ports
            
            # Mostra feedback visual de carregamento
            self.port_combo.setEnabled(False)
            self.port_combo.clear()
            self.port_combo.addItem("Escaneando portas...")
            QApplication.processEvents()  # Atualiza a interface
            
            # Obtém a lista de portas disponíveis
            ports = [port.device for port in serial.tools.list_ports.comports()]
            
            # Limpa e preenche a combobox
            self.port_combo.clear()
            
            if not ports:
                self.port_combo.addItem("Nenhuma porta encontrada")
                self.port_combo.setEnabled(False)
                self.update_system_status("Nenhuma porta serial encontrada", 'warning')
                return []
            
            # Adiciona as portas encontradas
            self.port_combo.addItems(ports)
            self.port_combo.setEnabled(True)
            
            # Tenta selecionar a porta padrão ou a primeira disponível
            if self.port and self.port in ports:
                self.port_combo.setCurrentText(self.port)
            elif ports:
                self.port_combo.setCurrentIndex(0)
            
            self.update_system_status(f"{len(ports)} porta(s) serial(is) encontrada(s)", 'success')
            return ports
            
        except Exception as e:
            self.logger.error(f"Erro ao escanear portas: {str(e)}", exc_info=True)
            self.port_combo.clear()
            self.port_combo.addItem("Erro ao escanear portas")
            self.port_combo.setEnabled(False)
            self.update_system_status(f"Erro ao escanear portas: {str(e)}", 'error')
            return []
    
    def toggle_connection(self):
        """Alterna o estado da conexão Modbus."""
        if self.connected:
            self.disconnect_modbus()
        else:
            self.connect_modbus()
    
    def connect_modbus(self):
        """Estabelece a conexão com o dispositivo Modbus."""
        try:
            port = self.port_combo.currentText()
            baudrate = int(self.baudrate_combo.currentText())
            
            if not port or port == "Nenhuma porta encontrada":
                self.update_system_status("Nenhuma porta selecionada", 'error')
                return False
                
            # Atualiza a interface
            self.connect_btn.setEnabled(False)
            self.connect_btn.setText("Conectando...")
            QApplication.processEvents()
            
            # Configura o instrumento Modbus
            self.instrument = minimalmodbus.Instrument(port, 1)  # Endereço 1 por padrão
            self.instrument.serial.baudrate = baudrate
            self.instrument.serial.bytesize = 8
            self.instrument.serial.parity = serial.PARITY_NONE
            self.instrument.serial.stopbits = 1
            self.instrument.serial.timeout = 1.0  # 1 segundo de timeout
            
            # Tenta ler um registro para testar a conexão
            try:
                self.instrument.read_register(0, 1)  # Lê o primeiro registro
                
                # Se chegou aqui, a conexão foi bem-sucedida
                self.connected = True
                self.port = port
                self.baudrate = baudrate
                
                # Atualiza a interface
                self.connect_btn.setEnabled(False)
                self.disconnect_btn.setEnabled(True)
                self.port_combo.setEnabled(False)
                self.baudrate_combo.setEnabled(False)
                
                # Atualiza o status
                self.connection_status_indicator.setStyleSheet(
                    "background-color: #4CAF50; border-radius: 8px;"
                )
                self.connection_status_text.setText("Conectado")
                self.connection_status_text.setStyleSheet("color: #388E3C; font-weight: bold;")
                
                self.update_system_status(f"Conectado a {port} @ {baudrate} baud", 'success')
                
                # Habilita a aba de dispositivos
                self.tabs.setTabEnabled(1, True)  # Habilita a aba de dispositivos
                
                return True
                
            except Exception as e:
                self.instrument = None
                self.update_system_status(f"Falha na conexão: {str(e)}", 'error')
                self.connect_btn.setEnabled(True)
                self.connect_btn.setText("Conectar")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao conectar: {str(e)}", exc_info=True)
            self.update_system_status(f"Erro na conexão: {str(e)}", 'error')
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("Conectar")
            return False
    
    def disconnect_modbus(self):
        """Encerra a conexão com o dispositivo Modbus."""
        try:
            if self.instrument:
                self.instrument.serial.close()
                self.instrument = None
            
            self.connected = False
            
            # Atualiza a interface
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("Conectar")
            self.disconnect_btn.setEnabled(False)
            self.port_combo.setEnabled(True)
            self.baudrate_combo.setEnabled(True)
            
            # Atualiza o status
            self.connection_status_indicator.setStyleSheet(
                "background-color: #e0e0e0; border-radius: 8px;"
            )
            self.connection_status_text.setText("Desconectado")
            self.connection_status_text.setStyleSheet("color: #757575; font-weight: bold;")
            
            self.update_system_status("Desconectado", 'info')
            
            # Desabilita a aba de dispositivos se estiver ativa
            if self.tabs.count() > 1:  # Verifica se existe a aba de dispositivos
                self.tabs.setTabEnabled(1, False)  # Desabilita a aba de dispositivos
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao desconectar: {str(e)}", exc_info=True)
            self.update_system_status(f"Erro ao desconectar: {str(e)}", 'error')
            return False
    
    def update_status(self, message, error=False, clear_after=0):
        """Atualiza a barra de status com uma mensagem.
        
        Args:
            message (str): A mensagem a ser exibida
            error (bool): Se True, exibe a mensagem em vermelho
            clear_after (int): Tempo em milissegundos para limpar a mensagem (0 = não limpar)
        """
        if not hasattr(self, 'status_bar') or not self.status_bar:
            return
            
        try:
            # Aplica o estilo apropriado
            if error:
                self.status_bar.setStyleSheet(
                    "QStatusBar { color: #d32f2f; background-color: #ffebee; padding: 2px 8px; }"
                )
                self.logger.error(f"Status (erro): {message}")
            else:
                self.status_bar.setStyleSheet(
                    "QStatusBar { color: #2e7d32; background-color: #e8f5e9; padding: 2px 8px; }"
                )
                self.logger.info(f"Status: {message}")
            
            # Exibe a mensagem
            self.status_bar.showMessage(message)
            
            # Configura um timer para limpar a mensagem após o tempo especificado
            if clear_after > 0:
                QTimer.singleShot(clear_after, self.clear_status)
                
            self.logger.debug(f"Status definido: {message} (erro={error})")
                
        except Exception as e:
            error_msg = f"Erro ao atualizar status: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
    
    def load_settings(self):
        """Carrega as configurações salvas."""
        try:
            with open('modbus_tester_settings.json', 'r') as f:
                settings = json.load(f)
                
            self.port = settings.get('port', 'COM3')
            self.baudrate = settings.get('baudrate', 9600)
            
            self.port_combo.setCurrentText(self.port)
            self.baudrate_combo.setCurrentText(str(self.baudrate))
            
        except (FileNotFoundError, json.JSONDecodeError):
            # Usar configurações padrão se o arquivo não existir ou for inválido
            pass
    
    def save_settings(self):
        """Salva as configurações."""
        settings = {
            'port': self.port_combo.currentText(),
            'baudrate': int(self.baudrate_combo.currentText())
        }
        
        with open('modbus_tester_settings.json', 'w') as f:
            json.dump(settings, f, indent=4)
    
    def closeEvent(self, event):
        """Evento de fechamento da janela."""
        self.closing = True
        
        try:
            # Para a leitura automática
            if hasattr(self, 'update_timer') and self.update_timer.isActive():
                self.update_timer.stop()
            
            # Aguarda a finalização de qualquer leitura em andamento
            timeout = 10  # 10 segundos de timeout
            while hasattr(self, 'reading_in_progress') and self.reading_in_progress and timeout > 0:
                QApplication.processEvents()
                sleep(0.1)  # Usando sleep diretamente
                timeout -= 0.1
            
            # Desconecta o dispositivo se estiver conectado
            if hasattr(self, 'disconnect_modbus'):
                self.disconnect_modbus()
            
            # Salva as configurações
            if hasattr(self, 'save_settings'):
                self.save_settings()
                
        except Exception as e:
            self.logger.error(f"Erro durante o fechamento: {str(e)}", exc_info=True)
        finally:
            # Garante que a janela será fechada
            event.accept()
    
    def play_alarm_sound(self, duration=3):
        """Toca um som de alarme.
        
        Args:
            duration (int): Duração do som em segundos.
        """
        try:
            # Importa winsound localmente para evitar problemas de escopo
            import winsound
            
            # Frequência e duração do som de alarme
            frequency = 1000  # 1 KHz
            
            # Reproduz o som de alarme
            for _ in range(3):  # Toca 3 bipes
                winsound.Beep(frequency, 500)  # 500ms de duração por beep
                time.sleep(0.2)  # Pequena pausa entre os bipes
                
        except Exception as e:
            self.logger.error(f"Erro ao reproduzir som de alarme: {str(e)}")
            # Tenta uma abordagem alternativa se o Beep não funcionar
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONHAND)
            except Exception as e2:
                self.logger.error(f"Não foi possível reproduzir som de alarme: {str(e2)}")
    
    def activate_physical_alarm(self, activate=True):
        """Ativa ou desativa um alarme físico conectado via Modbus.
        
        Args:
            activate (bool): Se True, ativa o alarme; se False, desativa.
        """
        if not hasattr(self, 'instrument') or self.instrument is None:
            self.logger.warning("Não é possível ativar alarme físico: dispositivo Modbus não conectado")
            return False
            
        try:
            # Endereço do relé ou saída digital que controla o alarme
            # Ajuste estes valores conforme a configuração do seu hardware
            RELAY_ADDRESS = 0  # Endereço do relé
            
            # Configura o endereço do escravo diretamente no instrumento
            # se ainda não estiver configurado
            if not hasattr(self, '_saved_slave_address'):
                self._saved_slave_address = self.instrument.address  # Salva o endereço atual
            
            # Define o endereço do escravo (1 é o padrão para muitos dispositivos)
            self.instrument.address = 1  # Define o endereço do escravo
            
            if activate:
                self.logger.info("Ativando alarme físico...")
                # Liga o relé (valor 1 para ativar, pode variar dependendo do hardware)
                # Usa a função 6 (Write Single Register)
                self.instrument.write_register(RELAY_ADDRESS, 1, functioncode=6)
            else:
                self.logger.info("Desativando alarme físico...")
                # Desliga o relé (valor 0 para desativar)
                self.instrument.write_register(RELAY_ADDRESS, 0, functioncode=6)
                
            # Restaura o endereço do escravo original, se existir
            if hasattr(self, '_saved_slave_address'):
                self.instrument.address = self._saved_slave_address
                
            return True
            
        except Exception as e:
            error_msg = f"Erro ao controlar alarme físico: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.update_status("Erro ao controlar alarme físico", error=True)
            
            # Tenta restaurar o endereço do escravo em caso de erro
            if hasattr(self, '_saved_slave_address'):
                try:
                    self.instrument.address = self._saved_slave_address
                except:
                    pass
                    
            return False
    
    def play_alarm_loop(self, duration=3, stop_event=None):
        """Toca o alarme em loop até que o evento de parada seja definido."""
        import winsound
        try:
            frequency = 1000  # 1 KHz
            while not (stop_event and stop_event.is_set()):
                winsound.Beep(frequency, 500)  # 500ms de duração
                time.sleep(0.5)  # Pausa entre os bipes
        except Exception as e:
            self.logger.error(f"Erro na thread de som: {str(e)}")
            try:
                winsound.MessageBeep(winsound.MB_ICONHAND)
            except Exception as e2:
                self.logger.error(f"Falha ao tocar som de alerta: {str(e2)}")
    
    def trigger_test_alarm(self):
        """Dispara um alarme de teste com feedback sonoro e ativação física."""
        self.logger.info("Iniciando teste de alarme...")
        
        # Cria um evento para controlar a thread de som
        import threading
        stop_sound_event = threading.Event()
        
        # Inicia a thread de som
        sound_thread = threading.Thread(
            target=self.play_alarm_loop,
            args=(3, stop_sound_event),
            daemon=True
        )
        sound_thread.start()
        
        try:
            # Ativar alarme físico, se disponível
            alarm_activated = self.activate_physical_alarm(True)
            
            # Cria a mensagem de diálogo
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Teste de Alarme")
            msg.setText("⚠️ ALARME DE TESTE ⚠️")
            
            # Mensagem informativa baseada no sucesso da ativação física
            if alarm_activated:
                msg.setInformativeText(
                    "Este é um teste do sistema de alarmes.\n\n"
                    "Verifique se os indicadores visuais, sonoros e físicos "
                    "estão funcionando corretamente."
                )
            else:
                msg.setInformativeText(
                    "Este é um teste do sistema de alarmes.\n\n"
                    "Verifique se os indicadores visuais e sonoros "
                    "estão funcionando corretamente.\n"
                    "Aviso: Não foi possível ativar o alarme físico."
                )
                
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setDefaultButton(QMessageBox.StandardButton.Ok)
            
            # Estilização da mensagem de alarme
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #fff3e0;
                    font-family: 'Segoe UI', Arial, sans-serif;
                }
                QLabel {
                    color: #d32f2f;
                    font-size: 14px;
                }
                QPushButton {
                    min-width: 100px;
                    padding: 8px 16px;
                    background-color: #ff5722;
                    border: 1px solid #e64a19;
                    border-radius: 4px;
                    color: white;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #e64a19;
                }
                QPushButton:pressed {
                    background-color: #bf360c;
                }
            """)
            
            # Exibe a mensagem e aguarda o usuário
            self.logger.info("Exibindo caixa de diálogo de teste de alarme...")
            msg.exec()
            
            # Para o som e desativa o alarme físico
            stop_sound_event.set()
            if alarm_activated:
                self.activate_physical_alarm(False)
                
            # Aguarda a thread de som terminar (com timeout para evitar travar)
            sound_thread.join(timeout=1.0)
            
        except Exception as e:
            # Garante que o som seja parado em caso de erro
            stop_sound_event.set()
            if 'alarm_activated' in locals() and alarm_activated:
                self.activate_physical_alarm(False)
            raise  # Re-lança a exceção para ser tratada no bloco externo
            
            # Atualiza a barra de status
            self.logger.info("Teste de alarme concluído pelo usuário")
            self.update_status("Teste de alarme concluído")
            
        except Exception as e:
            error_msg = f"Erro ao disparar alarme de teste: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.update_status("Erro no teste de alarme", error=True)
            
            # Tenta notificar o usuário sobre o erro
            try:
                QMessageBox.critical(
                    self, 
                    "Erro no Teste de Alarme", 
                    f"Ocorreu um erro ao executar o teste de alarme:\n{str(e)}"
                )
            except Exception as ui_error:
                self.logger.error(f"Erro ao exibir mensagem de erro: {str(ui_error)}", exc_info=True)
                # Tenta uma abordagem mais simples em caso de falha
                try:
                    print(f"ERRO: {error_msg}")
                except:
                    pass  # Último recurso, apenas ignora se não for possível fazer nada
    
    def clear_status(self):
        """Limpa a mensagem da barra de status e restaura o estilo padrão."""
        try:
            if hasattr(self, 'status_bar') and self.status_bar:
                # Restaura o estilo padrão
                self.status_bar.setStyleSheet("""
                    QStatusBar {
                        color: #333333;
                        background-color: #f0f0f0;
                        border-top: 1px solid #d0d0d0;
                        padding: 2px 8px;
                    }
                """)
                self.status_bar.clearMessage()
                self.logger.debug("Barra de status limpa")
        except Exception as e:
            self.logger.error(f"Erro ao limpar barra de status: {str(e)}", exc_info=True)
    
    def show_error_message(self, title, message, details=None, parent=None):
        """Exibe uma mensagem de erro estilizada.
        
        Args:
            title (str): Título da mensagem de erro
            message (str): Mensagem principal
            details (str, optional): Detalhes adicionais para exibição
            parent (QWidget, optional): Widget pai para a caixa de diálogo
        """
        try:
            msg_box = QMessageBox(parent or self)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle(title)
            msg_box.setText(f"<b>{message}</b>")
            
            # Adiciona detalhes se fornecidos
            if details:
                msg_box.setInformativeText(details)
            
            # Configura o estilo
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #f8f9fa;
                }
                QLabel {
                    color: #721c24;
                    font-size: 13px;
                }
                QTextEdit {
                    background-color: white;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    padding: 8px;
                    color: #212529;
                    font-family: 'Consolas', 'Monospace';
                    font-size: 11px;
                }
                QPushButton {
                    min-width: 80px;
                    padding: 5px 15px;
                    border-radius: 4px;
                    border: 1px solid #dc3545;
                    background-color: #dc3545;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c82333;
                    border-color: #bd2130;
                }
            """)
            
            # Adiciona botão OK
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # Exibe a mensagem
            msg_box.exec()
            
        except Exception as e:
            self.logger.error(f"Falha ao exibir mensagem de erro: {str(e)}", exc_info=True)
            # Tenta uma abordagem mais simples em caso de falha
            try:
                QMessageBox.critical(parent or self, title, f"{message}\n\nDetalhes: {details or 'Nenhum'}")
            except:
                print(f"ERRO: {title} - {message}\n{details or ''}")
    
    def show_success_message(self, title, message, details=None, parent=None):
        """Exibe uma mensagem de sucesso estilizada.
        
        Args:
            title (str): Título da mensagem
            message (str): Mensagem principal
            details (str, optional): Detalhes adicionais para exibição
            parent (QWidget, optional): Widget pai para a caixa de diálogo
        """
        try:
            msg_box = QMessageBox(parent or self)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle(title)
            msg_box.setText(f"<b>{message}</b>")
            
            # Adiciona detalhes se fornecidos
            if details:
                msg_box.setInformativeText(details)
            
            # Configura o estilo
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #f8f9fa;
                }
                QLabel {
                    color: #155724;
                    font-size: 13px;
                }
                QTextEdit {
                    background-color: white;
                    border: 1px solid #d4edda;
                    border-radius: 4px;
                    padding: 8px;
                    color: #212529;
                    font-family: 'Consolas', 'Monospace';
                    font-size: 11px;
                }
                QPushButton {
                    min-width: 80px;
                    padding: 5px 15px;
                    border-radius: 4px;
                    border: 1px solid #28a745;
                    background-color: #28a745;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #218838;
                    border-color: #1e7e34;
                }
            """)
            
            # Adiciona botão OK
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # Exibe a mensagem
            msg_box.exec()
            
        except Exception as e:
            self.logger.error(f"Falha ao exibir mensagem de sucesso: {str(e)}", exc_info=True)
            # Tenta uma abordagem mais simples em caso de falha
            try:
                QMessageBox.information(parent or self, title, f"{message}\n\n{details or ''}")
            except:
                print(f"SUCESSO: {title} - {message}\n{details or ''}")
    
    def show_warning_message(self, title, message, details=None, parent=None):
        """Exibe uma mensagem de aviso estilizada.
        
        Args:
            title (str): Título da mensagem
            message (str): Mensagem principal
            details (str, optional): Detalhes adicionais para exibição
            parent (QWidget, optional): Widget pai para a caixa de diálogo
        """
        try:
            msg_box = QMessageBox(parent or self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle(title)
            msg_box.setText(f"<b>{message}</b>")
            
            # Adiciona detalhes se fornecidos
            if details:
                msg_box.setInformativeText(details)
            
            # Configura o estilo
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #fff3e0;
                }
                QLabel {
                    color: #856404;
                    font-size: 13px;
                }
                QTextEdit {
                    background-color: white;
                    border: 1px solid #ffeeba;
                    border-radius: 4px;
                    padding: 8px;
                    color: #212529;
                    font-family: 'Consolas', 'Monospace';
                    font-size: 11px;
                }
                QPushButton {
                    min-width: 80px;
                    padding: 5px 15px;
                    border-radius: 4px;
                    border: 1px solid #ffc107;
                    background-color: #ffc107;
                    color: #212529;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e0a800;
                    border-color: #d39e00;
                }
            """)
            
            # Adiciona botão OK
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # Exibe a mensagem
            msg_box.exec()
            
        except Exception as e:
            self.logger.error(f"Falha ao exibir mensagem de aviso: {str(e)}", exc_info=True)
            # Tenta uma abordagem mais simples em caso de falha
            try:
                QMessageBox.warning(parent or self, title, f"{message}\n\n{details or ''}")
            except Exception as e:
                print(f"AVISO: {title} - {message}\n{details or ''}")
                self.logger.warning(f"Falha ao exibir mensagem de aviso (fallback): {str(e)}")
    
    def show_confirm_message(self, title, message, details=None, parent=None):
        """Exibe uma mensagem de confirmação estilizada.
        
        Args:
            title (str): Título da mensagem
            message (str): Mensagem principal
            details (str, optional): Detalhes adicionais para exibição
            parent (QWidget, optional): Widget pai para a caixa de diálogo
            
        Returns:
            bool: True se o usuário confirmou, False caso contrário
        """
        try:
            msg_box = QMessageBox(parent or self)
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setWindowTitle(title)
            msg_box.setText(f"<b>{message}</b>")
            
            # Adiciona detalhes se fornecidos
            if details:
                msg_box.setInformativeText(details)
            
            # Configura o estilo
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #f8f9fa;
                }
                QLabel {
                    color: #0c5460;
                    font-size: 13px;
                }
                QTextEdit {
                    background-color: white;
                    border: 1px solid #d1ecf1;
                    border-radius: 4px;
                    padding: 8px;
                    color: #212529;
                    font-family: 'Consolas', 'Monospace';
                    font-size: 11px;
                }
                QPushButton {
                    min-width: 80px;
                    padding: 5px 15px;
                    border-radius: 4px;
                    margin: 0 5px;
                    font-weight: bold;
                }
                QPushButton[text="Sim"],
                QPushButton[text="Yes"] {
                    border: 1px solid #17a2b8;
                    background-color: #17a2b8;
                    color: white;
                }
                QPushButton[text="Sim"]:hover,
                QPushButton[text="Yes"]:hover {
                    background-color: #138496;
                    border-color: #117a8b;
                }
                QPushButton[text="Não"],
                QPushButton[text="No"] {
                    border: 1px solid #6c757d;
                    background-color: #6c757d;
                    color: white;
                }
                QPushButton[text="Não"]:hover,
                QPushButton[text="No"]:hover {
                    background-color: #5a6268;
                    border-color: #545b62;
                }
            """)
            
            # Configura os botões
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
            
            # Exibe a mensagem e retorna a resposta
            result = msg_box.exec()
            return result == QMessageBox.StandardButton.Yes
            
        except Exception as e:
            self.logger.error(f"Falha ao exibir mensagem de confirmação: {str(e)}", exc_info=True)
            # Tenta uma abordagem mais simples em caso de falha
            try:
                return QMessageBox.question(
                    parent or self, 
                    title, 
                    f"{message}\n\n{details or ''}",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                ) == QMessageBox.StandardButton.Yes
            except Exception as fallback_error:
                self.logger.error(f"Falha no fallback de confirmação: {str(fallback_error)}")
                # Último recurso - assume que o usuário não confirmou
                return False

def main():
    app = QApplication(sys.argv)
    
    # Aplica um estilo consistente
    app.setStyle('Fusion')
    
    # Configura a fonte padrão
    font = QFont()
    font.setPointSize(10)
    app.setFont(font)
    
    window = ModbusTester()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

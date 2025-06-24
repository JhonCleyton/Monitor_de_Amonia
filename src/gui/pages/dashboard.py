"""
Módulo do dashboard principal do sistema de monitoramento de amônia.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QPushButton, QScrollArea, QSizePolicy, QFrame, QSpacerItem,
    QStatusBar, QDialog, QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox, QMessageBox, QInputDialog, QMenu, QMenuBar, QStyle,
    QToolBar, QApplication, QTableWidgetItem
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, pyqtSlot, QThread, QMetaObject, Q_ARG, QEvent
from PyQt6.QtGui import QFont, QColor, QPalette, QAction, QIcon, QDesktopServices
from PyQt6.QtCore import QUrl
import os
import sys
import time
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any

from src.config import load_config
from src.database import get_db
from src.modbus import ModbusRTUClient, ModbusDeviceConfig, RegisterType
from src.utils.logger import get_logger

# Importa o componente de medidor de amônia
try:
    from ..components.ammonia_gauge import AmmoniaGauge
except ImportError:
    # Se o componente personalizado não estiver disponível, cria uma versão simplificada
    class AmmoniaGauge(QLabel):
        def __init__(self, title="Sensor", unit="ppm", parent=None):
            super().__init__(parent)
            self.setMinimumSize(200, 200)
            self.title = title
            self.unit = unit
            self.value = 0.0
            self.min_value = 0
            self.max_value = 100
            self.update_display()
        
        def set_value(self, value):
            self.value = value
            self.update_display()
            
        def setMinimum(self, value):
            self.min_value = value
            
        def setMaximum(self, value):
            self.max_value = value
        
        def update_display(self):
            self.setText(f"{self.title}\n{self.value:.1f} {self.unit}")
            self.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid #3498db;
                    border-radius: 10px;
                    padding: 10px;
                    background-color: #f8f9fa;
                    font-size: 14px;
                    font-weight: bold;
                }
            """)

class DashboardPage(QWidget):
    """Página principal do dashboard com medidores em tempo real."""
    
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        
        # Inicializa o dicionário de configuração
        self.config = config or {}
        
        # Inicializa o dicionário de dados dos sensores
        self.sensor_data = {}
        
        # Configura o layout principal
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Cabeçalho
        self.header = QWidget()
        self.header.setObjectName("header")
        self.header.setFixedHeight(80)
        
        # Layout do cabeçalho
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(25, 10, 25, 10)
        
        # Título e subtítulo
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)
        
        self.title_label = QLabel("PHANTOM 2000 - Monitor de Amônia")
        self.title_label.setObjectName("title")
        
        self.subtitle_label = QLabel("Sistema de Monitoramento em Tempo Real")
        self.subtitle_label.setObjectName("subtitle")
        
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)
        
        # Status da conexão
        self.connection_status = QWidget()
        connection_layout = QHBoxLayout(self.connection_status)
        connection_layout.setContentsMargins(0, 0, 0, 0)
        connection_layout.setSpacing(5)
        
        self.connection_indicator = QLabel()
        self.connection_indicator.setFixedSize(12, 12)
        self.connection_indicator.setObjectName("statusIndicator")
        
        self.connection_label = QLabel("Desconectado")
        self.connection_label.setStyleSheet("color: #95a5a6; font-size: 12px;")
        
        connection_layout.addWidget(self.connection_indicator)
        connection_layout.addWidget(self.connection_label)
        
        # Atualiza o status da conexão após configurar os widgets
        self.update_connection_status(False)
        
        # Adiciona widgets ao cabeçalho
        header_layout.addWidget(title_container, 1)
        header_layout.addStretch()
        header_layout.addWidget(self.connection_status)
        
        # Barra de ferramentas
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setMovable(False)
        
        # Ações da barra de ferramentas
        self.refresh_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "Atualizar", self)
        self.refresh_action.triggered.connect(self.refresh_sensors)
        self.toolbar.addAction(self.refresh_action)
        
        self.toolbar.addSeparator()
        
        self.settings_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon), "Configurações", self)
        self.settings_action.triggered.connect(self.show_settings_dialog)
        self.toolbar.addAction(self.settings_action)
        
        # Área de rolagem para o conteúdo principal
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Widget que contém o conteúdo rolável
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(20, 20, 20, 20)
        self.scroll_layout.setSpacing(20)
        
        # Seção de status
        self.status_section = QWidget()
        self.status_layout = QHBoxLayout(self.status_section)
        self.status_layout.setContentsMargins(0, 0, 0, 0)
        self.status_layout.setSpacing(15)
        
        # Cartões de status
        self.status_cards = {
            'sensors': self.create_status_card("Sensores Ativos", "0", "sensors"),
            'alerts': self.create_status_card("Alertas", "0", "alerts"),
            'uptime': self.create_status_card("Tempo de Atividade", "00:00:00", "uptime")
        }
        
        for card in self.status_cards.values():
            self.status_layout.addWidget(card)
        
        # Seção dos medidores
        self.gauges_section = QWidget()
        self.gauges_layout = QGridLayout(self.gauges_section)
        self.gauges_layout.setContentsMargins(0, 0, 0, 0)
        self.gauges_layout.setSpacing(20)
        
        # Adiciona as seções ao layout rolável
        self.scroll_layout.addWidget(self.status_section)
        self.scroll_layout.addWidget(self.gauges_section)
        self.scroll_layout.addStretch()
        
        # Configura a área de rolagem
        self.scroll_area.setWidget(self.scroll_content)
        
        # Barra de status
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("statusBar")
        
        # Cria o rodapé
        self.footer = self._create_footer()
        
        # Adiciona widgets ao layout principal
        self.layout.addWidget(self.header)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.scroll_area)
        self.layout.addWidget(self.status_bar)
        self.layout.addWidget(self.footer)
        
        # Aplica o estilo
        self.apply_styles()
        
        # Dicionário para armazenar os medidores
        self.gauges = {}
        
        # Configura o caminho do banco de dados
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data')
        self.db_path = os.path.join(data_dir, 'monitor_amonia.db')
        self.logger.info(f"Caminho do banco de dados: {self.db_path}")
        
        # Inicializa o banco de dados
        try:
            self.db = self._init_database()
            if self.db is None:
                raise Exception("Falha ao inicializar o banco de dados: conexão retornou None")
            self.logger.info("Conexão com o banco de dados estabelecida com sucesso")
            
            # Carrega as configurações dos sensores
            self.load_sensor_config()
            
        except Exception as e:
            self.logger.error(f"Erro ao inicializar o dashboard: {str(e)}")
            QMessageBox.critical(
                self, 
                "Erro de Inicialização", 
                f"Não foi possível inicializar o dashboard:\n{str(e)}\n\nVerifique os logs para mais detalhes."
            )
            raise
        
        # Configura o timer para atualização dos dados
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_sensor_data)
        self.update_interval = 5000  # 5 segundos
        self.update_timer.start(self.update_interval)
        
        # Configuração padrão se não existir
        if 'modbus' not in self.config:
            self.config['modbus'] = {
                'port': 'COM3',
                'baudrate': 9600,
                'timeout': 1.0,
                'stopbits': 1,
                'bytesize': 8,
                'parity': 'N'
            }
        
        # Timer para atualização dos dados
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_sensor_data)
        
        # Inicializa a interface do usuário
        self.init_ui()
        
        # Configura a comunicação Modbus
        self.setup_modbus()
        
        # Carrega configurações salvas
        self.load_sensor_config()
    
    def setup_modbus(self):
        """Configura o cliente Modbus para comunicação com os sensores."""
        try:
            if not hasattr(self, 'modbus_client'):
                # Obtém as configurações do Modbus
                modbus_config = self.config.get('modbus', {})
                
                # Cria o cliente Modbus
                self.modbus_client = ModbusRTUClient(
                    port=modbus_config.get('port', 'COM3'),
                    baudrate=modbus_config.get('baudrate', 9600),
                    timeout=modbus_config.get('timeout', 1.0)
                )
                
                # Tenta conectar ao dispositivo Modbus
                if not self.modbus_client.connect():
                    self.logger.error("Falha ao conectar ao dispositivo Modbus")
                    QMessageBox.critical(
                        self,
                        "Erro de Conexão",
                        "Não foi possível conectar ao dispositivo Modbus. Verifique a porta e as configurações."
                    )
                    return False
                
                self.logger.info("Cliente Modbus configurado com sucesso")
                return True
                
        except Exception as e:
            self.logger.error(f"Erro ao configurar o cliente Modbus: {str(e)}")
            QMessageBox.critical(
                self,
                "Erro de Configuração",
                f"Erro ao configurar o cliente Modbus:\n{str(e)}"
            )
            return False
    
    def _init_database(self):
        """Inicializa o banco de dados SQLite."""
        db = None
        try:
            # Cria o diretório de dados se não existir
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            # Define o caminho do banco de dados
            db_path = os.path.join(data_dir, 'monitor_amonia.db')
            self.logger.info(f"Conectando ao banco de dados em: {db_path}")
            
            # Conecta ao banco de dados (será criado se não existir)
            db = sqlite3.connect(db_path)
            cursor = db.cursor()
            
            # Cria a tabela de configuração de sensores se não existir
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensor_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_id TEXT NOT NULL UNIQUE,
                    name TEXT,
                    unit TEXT,
                    min_value REAL,
                    max_value REAL,
                    warning_level REAL,
                    danger_level REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Remove a tabela de leituras se existir para recriá-la
            cursor.execute("DROP TABLE IF EXISTS sensor_readings")
            
            # Recria a tabela de leituras com a estrutura correta
            cursor.execute('''
                CREATE TABLE sensor_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_id TEXT NOT NULL,
                    value REAL NOT NULL,
                    status TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    unit TEXT,
                    FOREIGN KEY (sensor_id) REFERENCES sensor_config(sensor_id)
                )
            ''')
            
            # Cria a tabela de alarmes se não existir
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alarms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_id TEXT,
                    message TEXT NOT NULL,
                    level TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    acknowledged BOOLEAN DEFAULT 0,
                    acknowledged_at DATETIME,
                    FOREIGN KEY (sensor_id) REFERENCES sensor_config(sensor_id)
                )
            ''')
            
            # Cria índices para melhorar o desempenho das consultas
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_readings_sensor_id ON sensor_readings(sensor_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_readings_timestamp ON sensor_readings(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alarms_sensor_id ON alarms(sensor_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alarms_timestamp ON alarms(timestamp)')
            
            db.commit()
            self.logger.info("Banco de dados inicializado com sucesso")
            return db
            
        except sqlite3.Error as e:
            error_msg = f"Erro ao inicializar o banco de dados: {str(e)}"
            self.logger.error(error_msg)
            if db:
                db.close()
            raise Exception(error_msg)
    
    def load_sensor_config(self):
        """Carrega as configurações dos sensores do banco de dados."""
        if not hasattr(self, 'db') or self.db is None:
            self.logger.error("Banco de dados não inicializado")
            return False
            
        try:
            cursor = self.db.cursor()
            cursor.execute("SELECT * FROM sensor_config")
            sensors = cursor.fetchall()
            
            if not sensors:
                self.logger.info("Nenhum sensor configurado no banco de dados")
                if hasattr(self, 'modbus_client') and self.modbus_client:
                    self.logger.info("Tentando detectar dispositivos Modbus automaticamente...")
                    self.detect_modbus_devices()
                return False
                
            self.logger.info(f"Carregando {len(sensors)} sensores do banco de dados")
            
            # Inicializa o dicionário de dados dos sensores se não existir
            if not hasattr(self, 'sensor_data'):
                self.sensor_data = {}
            
            for sensor in sensors:
                try:
                    sensor_id = sensor[1]  # Assumindo que o sensor_id está na posição 1
                    self.sensor_data[sensor_id] = {
                        'name': sensor[2],           # Nome do sensor
                        'unit': sensor[3] or 'ppm',  # Unidade de medida
                        'min_value': float(sensor[4]) if sensor[4] is not None else 0.0,
                        'max_value': float(sensor[5]) if sensor[5] is not None else 100.0,
                        'warning_level': float(sensor[6]) if sensor[6] is not None else 50.0,
                        'danger_level': float(sensor[7]) if sensor[7] is not None else 80.0,
                        'modbus_address': int(sensor[8]) if len(sensor) > 8 and sensor[8] is not None else 1,
                        'register_type': 'holding',  # Valor padrão
                        'scale_factor': 1.0,          # Valor padrão
                        'value': 0,                   # Valor inicial
                        'status': 'disconnected',     # Status inicial
                        'last_update': None           # Última atualização
                    }
                    self.logger.debug(f"Sensor carregado: {sensor_id} = {self.sensor_data[sensor_id]}")
                    
                    # Adiciona o medidor à interface
                    self._add_gauge_to_ui(sensor_id)
                    
                except (IndexError, ValueError, TypeError) as e:
                    self.logger.error(f"Erro ao processar configuração do sensor {sensor}: {str(e)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar configurações: {str(e)}")
            return False
    
    def _add_gauge_to_ui(self, sensor_id):
        """Adiciona um medidor à interface do usuário."""
        if sensor_id not in self.sensor_data:
            self.logger.warning(f"Tentativa de adicionar medidor para sensor não encontrado: {sensor_id}")
            return False
            
        try:
            sensor = self.sensor_data[sensor_id]
            self.logger.debug(f"Criando medidor para o sensor {sensor_id}: {sensor['name']}")
            
            # Cria o medidor
            gauge = AmmoniaGauge(sensor['name'], sensor['unit'])
            gauge.setMinimum(sensor['min_value'])
            gauge.setMaximum(sensor['max_value'])
            gauge.set_value(0)
            
            # Adiciona ao dicionário de medidores
            self.gauges[sensor_id] = gauge
            
            # Garante que o grid layout existe
            if not hasattr(self, 'gauges_layout'):
                self.logger.error("gauges_layout não inicializado")
                return False
            
            # Encontra a próxima posição vazia no grid
            position = self._find_empty_grid_position()
            if position:
                row, col = position
                self.gauges_layout.addWidget(gauge, row, col)
                self.logger.debug(f"Medidor adicionado na posição ({row}, {col})")
                return True
            else:
                self.logger.error("Não foi possível encontrar uma posição vazia no grid")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao adicionar medidor para o sensor {sensor_id}: {str(e)}")
            return False
    
    def _find_empty_grid_position(self):
        """Encontra a próxima posição vazia no grid de medidores."""
        if not hasattr(self, 'gauges_layout'):
            self.logger.error("gauges_layout não inicializado")
            return None
            
        max_cols = 4  # Número máximo de colunas no grid
        
        for row in range(100):  # Número arbitrário grande para linhas
            for col in range(max_cols):
                # Verifica se a posição está vazia
                item = self.gauges_layout.itemAtPosition(row, col)
                if not item or not item.widget():
                    return (row, col)
        
        # Se não encontrou posição vazia, adiciona uma nova linha
        return (self.gauges_layout.rowCount(), 0)
    
    def create_status_card(self, title, value, card_type):
        """Cria um cartão de status para exibir informações resumidas."""
        card = QFrame()
        card.setObjectName("statusCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet("""
            QFrame#statusCard {
                background: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
                padding: 15px;
            }
            QLabel#cardTitle {
                color: #7f8c8d;
                font-size: 14px;
                font-weight: 500;
            }
            QLabel#cardValue {
                color: #2c3e50;
                font-size: 24px;
                font-weight: 700;
                margin: 5px 0;
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        
        value_label = QLabel(value)
        value_label.setObjectName("cardValue")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addStretch()
        
        # Adiciona um indicador de status baseado no tipo
        indicator = QFrame()
        indicator.setFixedHeight(4)
        indicator.setStyleSheet("""
            QFrame {
                background: #3498db;
                border-radius: 2px;
            }
        """)
        
        if card_type == 'alerts':
            indicator.setStyleSheet("""
                QFrame {
                    background: #e74c3c;
                    border-radius: 2px;
                }
            """)
        elif card_type == 'uptime':
            indicator.setStyleSheet("""
                QFrame {
                    background: #2ecc71;
                    border-radius: 2px;
                }
            """)
        
        layout.addWidget(indicator)
        
        return card
    
    def _create_footer(self):
        """Cria o rodapé com o texto de copyright."""
        footer = QWidget()
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 10, 20, 10)
        
        # Texto de copyright centralizado
        copyright_label = QLabel(" 2025 JC Bytes - Todos os direitos reservados")
        copyright_label.setStyleSheet("color: #000000; font-size: 11px;")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Adiciona o texto ao layout do rodapé
        footer_layout.addWidget(copyright_label)
        
        return footer
    
    def apply_styles(self):
        """Aplica os estilos à interface."""
        styles = """
            /* Estilos gerais */
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #2c3e50;
                background: white;
            }
            
            /* Cabeçalho */
            #header {
                background: #2c3e50;
                color: white;
                padding: 15px 25px;
            }
            
            /* Título e subtítulo */
            #title {
                color: white;
                font-size: 20px;
                font-weight: bold;
                margin: 0;
                padding: 0;
            }
            
            #subtitle {
                color: #bdc3c7;
                font-size: 12px;
                margin: 0;
                padding: 0;
            }
            
            /* Barra de ferramentas */
            QToolBar {
                background: #f8f9fa;
                border: none;
                border-bottom: 1px solid #dcdde1;
                padding: 5px 10px;
            }
            
            QToolBar::separator {
                background: #dcdde1;
                width: 1px;
                margin: 4px 2px;
            }
            
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 5px 10px;
                margin: 0 2px;
            }
            
            QToolButton:hover {
                background: rgba(52, 152, 219, 0.1);
                border: 1px solid rgba(52, 152, 219, 0.2);
            }
            
            QToolButton:pressed {
                background: rgba(52, 152, 219, 0.2);
            }
            
            /* Indicadores de status */
            #statusIndicator {
                min-width: 12px;
                max-width: 12px;
                min-height: 12px;
                max-height: 12px;
                border-radius: 6px;
                background-color: #95a5a6;
            }
            
            #statusIndicator.connected {
                background-color: #2ecc71;
                border: 2px solid #27ae60;
            }
            
            #statusIndicator.disconnected {
                background-color: #e74c3c;
                border: 2px solid #c0392b;
            }
            
            #statusIndicator.connecting {
                background-color: #f39c12;
                border: 2px solid #d35400;
            }
            
            /* Tabelas */
            QTableWidget {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 4px;
            }
            
            QTableWidget::item {
                padding: 5px;
            }
            
            QTableWidget::item:alternate {
                background-color: #f8f9fa;
            }
            
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            
            QTableWidget::item:selected {
                background-color: #e1f0fa;
                color: #2c3e50;
            }
            
            /* Abas */
            QTabWidget::pane {
                border: 1px solid #dcdde1;
                border-top: none;
                border-radius: 0 0 4px 4px;
                background: white;
            }
            
            QTabBar::tab {
                background: #f8f9fa;
                border: 1px solid #dcdde1;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                margin-right: 2px;
            }
            
            QTabBar::tab:selected {
                background: white;
                border-bottom: 2px solid #3498db;
                font-weight: bold;
            }
            
            QTabBar::tab:!selected {
                margin-top: 2px;
            }
            
            /* Botões */
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            
            QPushButton:hover {
                background-color: #2980b9;
            }
            
            QPushButton:pressed {
                background-color: #2471a3;
            }
            
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
            
            /* Botão de teste de alarme */
            #testAlarmButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 20px;
                border: none;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            #testAlarmButton:hover {
                background-color: #c0392b;
            }
            
            #testAlarmButton:pressed {
                background-color: #a93226;
            }
            
            /* Barra de status */
            #statusBar {
                background: #2c3e50;
                color: white;
                padding: 8px 15px;
                font-size: 12px;
            }
            
            /* Cartões de status */
            #statusCard {
                background: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
                padding: 15px;
            }
            
            #cardTitle {
                color: #7f8c8d;
                font-size: 14px;
                font-weight: 500;
            }
            
            #cardValue {
                color: #2c3e50;
                font-size: 24px;
                font-weight: bold;
                margin: 5px 0;
            }
            
            /* Cartões de status */
            .status-card {
                background: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
                padding: 15px;
                margin: 5px;
            }
            
            .status-card .title {
                color: #7f8c8d;
                font-size: 14px;
                font-weight: 500;
            }
            
            .status-card .value {
                color: #2c3e50;
                font-size: 24px;
                font-weight: bold;
            }
            
            .status-card.warning {
                border-left: 4px solid #f39c12;
            }
            
            .status-card.danger {
                border-left: 4px solid #e74c3c;
            }
        """
        
        self.setStyleSheet(styles)
    
    def init_ui(self):
        """Configura a interface do usuário do dashboard com um design moderno inspirado no Phantom 2000."""
        # Configuração de estilo global
        self.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #2c3e50;
                background: #f5f7fa;
            }
            QPushButton {
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
                min-width: 100px;
                background-color: #3498db;
                color: white;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #2471a3;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
            QLineEdit, QComboBox {
                padding: 6px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                min-width: 150px;
            }
            QLabel {
                color: #2c3e50;
            }
            QMenuBar {
                background-color: #2c3e50;
                color: white;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 5px 10px;
            }
            QMenuBar::item:selected {
                background-color: #34495e;
            }
            QMenu {
                background-color: white;
                border: 1px solid #bdc3c7;
            }
            QMenu::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # O menu foi movido para MainWindow para evitar duplicação

        # Cabeçalho
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(70)
        header.setStyleSheet("""
            #header {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                         stop:0 #2c3e50, stop:1 #3498db);
                padding: 15px 25px;
                border-bottom: 1px solid #1a252f;
                color: white;
            }
            QLabel#title {
                color: white;
                font-size: 24px;
                font-weight: 600;
                padding: 5px 0;
                margin-right: 20px;
            }
            QLabel#subtitle {
                color: rgba(255, 255, 255, 0.8);
                font-size: 14px;
                margin-top: 2px;
            }
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        # Área do título
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)
        
        # Título principal
        title_label = QLabel("PHANTOM 2000 - Monitor de Amônia")
        title_label.setObjectName("title")
        
        # Subtítulo
        subtitle_label = QLabel("Sistema de Monitoramento em Tempo Real")
        subtitle_label.setObjectName("subtitle")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        
        # Status da conexão
        self.connection_status = QLabel()
        self.connection_status.setFixedSize(12, 12)
        self.connection_status.setStyleSheet("""
            background-color: #95a5a6;
            border-radius: 6px;
        """)
        
        # Layout do status
        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(2)
        
        status_text = QHBoxLayout()
        status_text.addStretch()
        status_text.addWidget(QLabel("Status:"))
        status_text.addWidget(self.connection_status)
        
        self.status_label = QLabel("Desconectado")
        self.status_label.setStyleSheet("color: #ecf0f1; font-size: 11px;")
        
        status_layout.addLayout(status_text)
        status_layout.addWidget(self.status_label)
        
        # Botões de ação
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)
        
        # Botão de teste de alarme
        self.test_alarm_btn = QPushButton("Testar Alarme")
        self.test_alarm_btn.setIcon(self.style().standardIcon(getattr(QStyle.StandardPixmap, 'SP_MessageBoxWarning')))
        self.test_alarm_btn.setToolTip("Dispara um alarme de teste para verificação do sistema")
        self.test_alarm_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
            QPushButton:pressed {
                background-color: #ba4a00;
            }
        """)
        self.test_alarm_btn.clicked.connect(self.trigger_test_alarm)
        
        # Botão de ação principal
        self.action_btn = QPushButton("Iniciar Monitoramento")
        self.action_btn.setIcon(self.style().standardIcon(getattr(QStyle.StandardPixmap, 'SP_MediaPlay')))
        self.action_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: 500;
                min-width: 180px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #219653;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.action_btn.clicked.connect(self.toggle_monitoring)
        
        buttons_layout.addWidget(self.test_alarm_btn)
        buttons_layout.addWidget(self.action_btn)
        
        # Adiciona widgets ao cabeçalho
        header_layout.addWidget(title_container)
        header_layout.addStretch()
        header_layout.addWidget(status_container)
        header_layout.addSpacing(20)
        header_layout.addWidget(buttons_container)
        
        # Área de conteúdo principal
        content = QWidget()
        content.setStyleSheet("""
            background-color: #f5f7fa;
            border-radius: 8px;
            margin: 20px;
            padding: 10px;
        """)
        
        # Layout principal do conteúdo
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Barra de ferramentas
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background: #ecf0f1;
                border: none;
                border-bottom: 1px solid #d5dbdb;
                padding: 5px 10px;
                spacing: 5px;
            }
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 3px 8px;
            }
            QToolButton:hover {
                background: #d6dbdf;
                border: 1px solid #bdc3c7;
            }
            QToolButton:pressed {
                background: #bdc3c7;
            }
        """)
        
        # Ações da barra de ferramentas
        self.refresh_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "Atualizar", self)
        self.refresh_action.triggered.connect(self.refresh_sensors)
        toolbar.addAction(self.refresh_action)
        
        self.export_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Exportar Dados", self)
        self.export_action.triggered.connect(self.export_data)
        toolbar.addAction(self.export_action)
        
        toolbar.addSeparator()
        
        self.view_logs_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), "Visualizar Logs", self)
        self.view_logs_action.triggered.connect(self.view_logs)
        toolbar.addAction(self.view_logs_action)
        
        content_layout.addWidget(toolbar)
        
        # Área de rolagem para os medidores
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #ecf0f1;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #bdc3c7;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Widget que contém os medidores
        gauges_widget = QWidget()
        gauges_widget.setStyleSheet("background: transparent;")
        
        # Layout em grade para os medidores
        self.grid_layout = QGridLayout(gauges_widget)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)
        
        # Adiciona um widget vazio para centralizar quando não houver sensores
        self.no_sensors_label = QLabel("Nenhum sensor configurado. Vá em 'Sensores > Adicionar Sensor' para começar.")
        self.no_sensors_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-style: italic;
                font-size: 14px;
                padding: 30px;
                background: white;
                border: 2px dashed #bdc3c7;
                border-radius: 8px;
            }
        """)
        self.no_sensors_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.grid_layout.addWidget(self.no_sensors_label, 0, 0, 1, 1, Qt.AlignmentFlag.AlignCenter)
        
        scroll_area.setWidget(gauges_widget)
        content_layout.addWidget(scroll_area)
        
        # Barra de status
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: #2c3e50;
                color: #ecf0f1;
                padding: 5px 15px;
                font-size: 11px;
                border-top: 1px solid #1a252f;
            }
            QStatusBar::item {
                border: none;
            }
        """)
        
        # Widgets da barra de status
        self.status_label = QLabel("Sistema pronto")
        self.status_label.setStyleSheet("color: #ecf0f1;")
        
        self.cpu_usage = QLabel("CPU: --%")
        self.memory_usage = QLabel("MEM: --%")
        self.connection_status = QLabel("Desconectado")
        
        # Adiciona widgets à barra de status
        self.status_bar.addWidget(self.status_label, 1)
        self.status_bar.addPermanentWidget(self.cpu_usage)
        self.status_bar.addPermanentWidget(QLabel("|"))
        self.status_bar.addPermanentWidget(self.memory_usage)
        self.status_bar.addPermanentWidget(QLabel("|"))
        self.status_bar.addPermanentWidget(self.connection_status)
        
        # Adiciona widgets ao layout principal
        main_layout.addWidget(header)
        main_layout.addWidget(content, 1)  # O parâmetro 1 faz o conteúdo se expandir
        main_layout.addWidget(self.status_bar)
        
        # Inicializa o monitoramento de recursos do sistema
        self.system_monitor_timer = QTimer(self)
        self.system_monitor_timer.timeout.connect(self.update_system_status)
        self.system_monitor_timer.start(2000)  # Atualiza a cada 2 segundos
        
        # Atualiza o status inicial
        self.update_status("Sistema inicializado e pronto para uso")
        # Botão de teste de alarme
        self.test_alarm_btn = QPushButton("Testar Alarme")
        self.test_alarm_btn.setIcon(self.style().standardIcon(getattr(QStyle.StandardPixmap, 'SP_MessageBoxWarning')))
        self.test_alarm_btn.setToolTip("Dispara um alarme de teste para verificação do sistema")
        self.test_alarm_btn.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
            QPushButton:pressed {
                background-color: #ba4a00;
            }
        """)
        self.test_alarm_btn.clicked.connect(self.trigger_test_alarm)
        
        # Botão de ação principal
        self.action_btn = QPushButton("Iniciar Monitoramento")
        self.action_btn.setIcon(self.style().standardIcon(getattr(QStyle.StandardPixmap, 'SP_MediaPlay')))
        self.action_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: 500;
                min-width: 180px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #219653;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.action_btn.clicked.connect(self.toggle_monitoring)
        
        buttons_layout.addWidget(self.test_alarm_btn)
        buttons_layout.addWidget(self.action_btn)
        
        # Adiciona widgets ao cabeçalho
        header_layout.addWidget(title_container)
        header_layout.addStretch()
        header_layout.addWidget(status_container)
        header_layout.addSpacing(20)
        header_layout.addWidget(buttons_container)
        
        # Área de conteúdo principal
        content = QWidget()
        content.setStyleSheet("""
            QWidget {
                background-color: #f5f7fa;
            }
        """)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
        
        # Área de rolagem para os medidores
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #e0e0e0;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #bdc3c7;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Container dos medidores
        self.gauges_container = QWidget()
        self.grid_layout = QGridLayout(self.gauges_container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        
        # Adiciona medidores de espaço reservado
        self.create_placeholder_gauges()
        
        # Configura a área de rolagem
        scroll.setWidget(self.gauges_container)
        content_layout.addWidget(scroll)
        
        # Barra de status
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: #ecf0f1;
                color: #7f8c8d;
                padding: 8px 15px;
                border-top: 1px solid #d5dbdb;
                font-size: 12px;
            }
        """)
        
        # Adiciona widgets ao layout principal
        main_layout.addWidget(header)
        main_layout.addWidget(content, 1)  # O 1 faz o conteúdo expandir
        main_layout.addWidget(self.status_bar)
        
        # Atualiza o status inicial
        self.update_status("Sistema pronto", error=False)
    
    def toggle_monitoring(self):
        """Alterna entre iniciar e parar o monitoramento."""
        if hasattr(self, 'monitoring_started') and self.monitoring_started:
            self.stop_monitoring()
            self.action_btn.setText("Iniciar Monitoramento")
            self.action_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2ecc71;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #27ae60;
                }
            """)
            self.update_status("Monitoramento parado", alert=True)
        else:
            if self.start_monitoring():
                self.action_btn.setText("Parar Monitoramento")
                self.action_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e74c3c;
                        color: white;
                    }
                    QPushButton:hover {
                        background-color: #c0392b;
                    }
                """)
                self.update_status("Monitoramento iniciado")
            else:
                self.update_status("Falha ao iniciar monitoramento", error=True)
    
    def update_connection_status(self, connected):
        """Atualiza o indicador de status da conexão."""
        if connected:
            self.connection_indicator.setProperty('class', 'connected')
            self.connection_label.setText("Conectado")
            self.connection_label.setStyleSheet("color: #2ecc71; font-size: 12px;")
        else:
            self.connection_indicator.setProperty('class', 'disconnected')
            self.connection_label.setText("Desconectado")
            self.connection_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        
        # Atualiza o estilo
        self.connection_indicator.style().unpolish(self.connection_indicator)
        self.connection_indicator.style().polish(self.connection_indicator)
    
    def update_status(self, message, error=False, alert=False):
        """Atualiza a mensagem na barra de status.
        
        Args:
            message: Mensagem a ser exibida
            error: Se True, exibe como erro
            alert: Se True, exibe como alerta
        """
        if error:
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background: #fde8e8;
                    color: #e74c3c;
                    padding: 8px 15px;
                    border-top: 1px solid #f5b7b1;
                    font-size: 12px;
                }
            """)
        elif alert:
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background: #fff8e8;
                    color: #e67e22;
                    padding: 8px 15px;
                    border-top: 1px solid #f5e5b7;
                    font-size: 12px;
                }
            """)
        else:
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background: #ecf0f1;
                    color: #7f8c8d;
                    padding: 8px 15px;
                    border-top: 1px solid #d5dbdb;
                    font-size: 12px;
                }
            """)
        self.status_bar.showMessage(message)
    
    def create_placeholder_gauges(self):
        """Cria medidores de espaço reservado."""
        for i in range(8):  # Cria 8 medidores de espaço reservado
            gauge = AmmoniaGauge(f"Sensor {i+1}")
            gauge.set_value(0)
            row = i // 4
            col = i % 4
            self.grid_layout.addWidget(gauge, row, col)
            self.gauges[f"sensor_{i+1}"] = gauge
    
    def setup_modbus(self):
        """Configura a comunicação Modbus."""
        try:
            port = self.config.get('modbus', {}).get('port', 'COM3')
            baudrate = self.config.get('modbus', {}).get('baudrate', 9600)
            
            self.update_status(f"Conectando a {port} @ {baudrate} baud...")
            self.logger.info(f"Iniciando conexão Modbus em {port} @ {baudrate} baud...")
            
            self.modbus_client = ModbusRTUClient(port=port, baudrate=baudrate)
            
            # Tenta estabelecer a conexão
            if self.modbus_client.connect():
                self.update_connection_status(True)
                self.update_status(f"Conectado a {port} @ {baudrate} baud")
                self.logger.info(f"Conexão Modbus estabelecida com sucesso em {port}")
                
                # Inicializa os dispositivos Modbus
                self.initialize_modbus_devices()
                
                # Se não houver dispositivos configurados, tenta fazer uma varredura
                if not hasattr(self, 'modbus_devices') or not self.modbus_devices:
                    self.logger.warning("Nenhum dispositivo Modbus configurado. Tentando detectar...")
                    self.detect_modbus_devices()
                
                return True
            else:
                error_msg = f"Falha ao conectar a {port} @ {baudrate} baud"
                self.update_connection_status(False)
                self.update_status(error_msg, error=True)
                self.logger.error(error_msg)
                return False
            
        except Exception as e:
            error_msg = f"Erro na conexão Modbus: {str(e)}"
            self.update_connection_status(False)
            self.update_status(error_msg, error=True)
            self.logger.error(f"{error_msg}. Detalhes: {str(e)}", exc_info=True)
            return False
    
    def detect_modbus_devices(self, start_address=1, end_address=10):
        """Varre a rede em busca de dispositivos Modbus."""
        try:
            if not self.modbus_client or not self.modbus_client.connected:
                self.logger.warning("Cliente Modbus não está conectado")
                return []
            
            self.update_status("Procurando dispositivos Modbus...")
            found_devices = self.modbus_client.scan_devices(start_address, end_address)
            
            if found_devices:
                self.logger.info(f"Dispositivos encontrados: {found_devices}")
                self.update_status(f"Encontrados {len(found_devices)} dispositivos")
                
                # Configura automaticamente os dispositivos encontrados
                self.auto_configure_devices(found_devices)
                
                return found_devices
            else:
                self.logger.warning("Nenhum dispositivo Modbus encontrado")
                self.update_status("Nenhum dispositivo encontrado", error=True)
                return []
                
        except Exception as e:
            error_msg = f"Erro ao escanear dispositivos Modbus: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.update_status("Erro ao escanear dispositivos", error=True)
            return []
    
    def auto_configure_devices(self, device_addresses):
        """Configura automaticamente os dispositivos Modbus encontrados.
        
        Este método configura automaticamente os dispositivos Modbus com base nos endereços fornecidos,
        identificando o tipo de dispositivo com base no endereço e configurando parâmetros apropriados.
        
        Args:
            device_addresses: Lista de endereços de dispositivos Modbus encontrados.
            
        Returns:
            int: Número de dispositivos configurados com sucesso.
            
        Raises:
            ValueError: Se a lista de endereços for vazia ou inválida.
            RuntimeError: Se o cliente Modbus não estiver disponível ou conectado.
        """
        self.logger.info(f"Iniciando configuração automática para {len(device_addresses)} dispositivos")
        
        # Validação dos parâmetros de entrada
        if not device_addresses or not isinstance(device_addresses, (list, tuple)):
            error_msg = "Lista de endereços de dispositivos inválida ou vazia"
            self.logger.warning(error_msg)
            self.update_status("Nenhum dispositivo encontrado para configuração", alert=True)
            return 0
            
        # Inicializa o dicionário de dispositivos se não existir
        if not hasattr(self, 'modbus_devices'):
            self.modbus_devices = {}
            self.logger.debug("Dicionário de dispositivos Modbus inicializado")
            
        # Verifica se o cliente Modbus está disponível e conectado
        if not hasattr(self, 'modbus_client') or not self.modbus_client:
            error_msg = "Cliente Modbus não inicializado"
            self.logger.error(error_msg)
            self.update_status(error_msg, error=True)
            raise RuntimeError(error_msg)
            
        if not self.modbus_client.connected:
            self.logger.warning("Cliente Modbus desconectado. Tentando reconectar...")
            if not self.modbus_client.connect():
                error_msg = "Não foi possível conectar ao dispositivo Modbus"
                self.logger.error(error_msg)
                self.update_status(error_msg, error=True)
                raise RuntimeError(error_msg)
        
        devices_configured = 0
        configuration_errors = 0
        
        # Ordena os endereços para garantir consistência na interface
        device_addresses = sorted(set(device_addresses))  # Remove duplicatas
        
        self.logger.info(f"Configurando dispositivos nos endereços: {device_addresses}")
        
        for addr in device_addresses:
            # Valida o endereço do dispositivo
            if not isinstance(addr, int) or addr < 1 or addr > 247:  # Endereços Modbus válidos: 1-247
                self.logger.warning(f"Endereço de dispositivo inválido: {addr}. Deve estar entre 1 e 247.")
                configuration_errors += 1
                continue
                
            device_id = f"sensor_{addr}"
            
            # Verifica se o dispositivo já está configurado
            if device_id in self.modbus_devices:
                self.logger.debug(f"Dispositivo {device_id} já está configurado")
                devices_configured += 1
                continue
                
            try:
                # Tenta identificar o tipo de dispositivo com base no endereço
                device_info = self._identify_device_type(addr)
                
                if not device_info or len(device_info) < 9:
                    self.logger.warning(f"Não foi possível identificar o tipo do dispositivo no endereço {addr}")
                    configuration_errors += 1
                    continue
                    
                device_name, register, register_type, unit, scale, min_val, max_val, warn_thresh, alarm_thresh = device_info
                
                # Valida os parâmetros do dispositivo
                if not isinstance(register, int) or register < 0 or register > 65535:
                    self.logger.warning(f"Número de registro inválido para o dispositivo {addr}: {register}")
                    configuration_errors += 1
                    continue
                    
                if not isinstance(scale, (int, float)) or scale <= 0:
                    self.logger.warning(f"Fator de escala inválido para o dispositivo {addr}: {scale}")
                    scale = 1.0  # Valor padrão
                
                # Cria a configuração do dispositivo
                device = ModbusDeviceConfig(
                    name=f"{device_name} {addr}",
                    address=addr,
                    register=register,
                    register_type=register_type,
                    unit=unit,
                    scale=scale,
                    offset=0.0,
                    min_value=min_val,
                    max_value=max_val,
                    warning_threshold=warn_thresh,
                    alarm_threshold=alarm_thresh,
                    description=f"Sensor {device_name} (endereço {addr})"
                )
                
                # Adiciona o dispositivo ao cliente Modbus
                self.modbus_client.add_device(device)
                self.modbus_devices[device_id] = device
                
                # Atualiza a interface para mostrar o novo dispositivo
                self._add_device_to_ui(device_id, device)
                
                self.logger.info(f"Dispositivo {device.name} configurado automaticamente no endereço {addr}")
                devices_configured += 1
                
                # Pequeno atraso entre as configurações para evitar sobrecarga
                QApplication.processEvents()
                
            except Exception as e:
                error_msg = f"Erro ao configurar dispositivo {addr}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                self.update_status(error_msg, error=True)
                configuration_errors += 1
        
        # Resumo da operação
        if devices_configured > 0:
            success_msg = f"{devices_configured} dispositivo(s) configurado(s) com sucesso"
            if configuration_errors > 0:
                success_msg += f", {configuration_errors} com erros"
            
            self.update_status(success_msg)
            self.logger.info(success_msg)
            
            # Se for a primeira configuração, inicia o monitoramento
            if not hasattr(self, 'monitoring_started') or not self.monitoring_started:
                self.logger.info("Iniciando monitoramento após configuração dos dispositivos")
                self.start_monitoring()
        else:
            error_msg = "Nenhum dispositivo pôde ser configurado"
            if configuration_errors > 0:
                error_msg += f" - {configuration_errors} erro(s) encontrado(s)"
            self.update_status(error_msg, error=True)
            self.logger.warning(error_msg)
        
        return devices_configured
        
    def _identify_device_type(self, address):
        """Identifica o tipo de dispositivo com base no endereço Modbus.
        
        Este método mapeia endereços Modbus para tipos de sensores específicos, permitindo
        a identificação automática de sensores com base em seus endereços. Cada faixa de
        endereços é associada a um tipo específico de sensor com parâmetros otimizados.
        
        Args:
            address (int): Endereço do dispositivo Modbus (1-247).
            
        Returns:
            tuple: Uma tupla contendo os parâmetros do dispositivo na seguinte ordem:
                - Nome do sensor (str)
                - Número do registro (int)
                - Tipo de registro (RegisterType)
                - Unidade de medida (str)
                - Fator de escala (float)
                - Valor mínimo (float)
                - Valor máximo (float)
                - Limiar de alerta (float)
                - Limiar de alarme (float)
                
        Note:
            As faixas de endereço são configuráveis e podem ser ajustadas conforme necessário.
            Para adicionar um novo tipo de sensor, basta adicionar uma nova entrada no dicionário
            device_types com a faixa de endereços desejada.
        """
        # Valida o endereço
        if not isinstance(address, int) or address < 1 or address > 247:
            self.logger.warning(f"Endereço de dispositivo inválido: {address}. Usando configuração padrão.")
            address = 0  # Usará a configuração padrão
        
        # Configurações para diferentes tipos de sensores
        # Formato: {
        #   range(inicio, fim): (
        #       'nome', registro, tipo_registro, unidade, escala,
        #       min_val, max_val, warn_thresh, alarm_thresh
        #   )
        # }
        device_types = {
            # Sensores de amônia (endereços 1-10)
            range(1, 11): (
                'Amônia',           # Nome
                0,                   # Registro
                RegisterType.INPUT_REGISTER,  # Tipo de registro
                'ppm',               # Unidade
                0.1,                 # Escala (valor_lido * escala)
                0.0,                 # Valor mínimo
                100.0,               # Valor máximo
                70.0,                # Limiar de alerta (70% do máximo)
                90.0                 # Limiar de alarme (90% do máximo)
            ),
            # Sensores de temperatura (endereços 11-20)
            range(11, 21): (
                'Temperatura',
                0,
                RegisterType.INPUT_REGISTER,
                '°C',
                0.1,    # Precisão de 0.1°C
                -10.0,  # Mínimo: -10°C
                50.0,   # Máximo: 50°C
                35.0,   # Alerta acima de 35°C
                40.0    # Alarme acima de 40°C
            ),
            # Sensores de umidade (endereços 21-30)
            range(21, 31): (
                'Umidade',
                0,
                RegisterType.INPUT_REGISTER,
                '%',
                0.1,     # Precisão de 0.1%
                0.0,     # Mínimo: 0%
                100.0,   # Máximo: 100%
                70.0,    # Alerta acima de 70%
                90.0     # Alarme acima de 90%
            ),
            # Sensores de pressão (endereços 31-40)
            range(31, 41): (
                'Pressão',
                0,
                RegisterType.INPUT_REGISTER,
                'hPa',
                0.1,     # Precisão de 0.1 hPa
                800.0,   # Mínimo: 800 hPa
                1200.0,  # Máximo: 1200 hPa
                1100.0,  # Alerta acima de 1100 hPa
                1150.0   # Alarme acima de 1150 hPa
            ),
            # Sensores de CO2 (endereços 41-50)
            range(41, 51): (
                'CO₂',
                0,
                RegisterType.INPUT_REGISTER,
                'ppm',
                1.0,     # Precisão de 1 ppm
                0.0,     # Mínimo: 0 ppm
                5000.0,  # Máximo: 5000 ppm
                1000.0,  # Alerta acima de 1000 ppm
                2000.0   # Alarme acima de 2000 ppm
            ),
            # Sensores de O2 (endereços 51-60)
            range(51, 61): (
                'Oxigênio',
                0,
                RegisterType.INPUT_REGISTER,
                '%',
                0.1,     # Precisão de 0.1%
                0.0,     # Mínimo: 0%
                25.0,    # Máximo: 25% (ar enriquecido)
                23.0,    # Alerta acima de 23%
                24.0     # Alarme acima de 24%
            )
        }
        
        # Tenta encontrar um intervalo que corresponda ao endereço
        for addr_range, params in device_types.items():
            if address in addr_range:
                # Cria uma cópia da tupla como lista para modificar o register_type
                params_list = list(params)
                # Garante que o register_type seja uma instância de RegisterType
                if not isinstance(params_list[2], RegisterType):
                    try:
                        # Tenta converter para RegisterType se for um inteiro
                        if isinstance(params_list[2], int):
                            params_list[2] = RegisterType(params_list[2])
                    except ValueError:
                        # Se falhar, usa INPUT_REGISTER como padrão
                        params_list[2] = RegisterType.INPUT_REGISTER
                self.logger.debug(f"Dispositivo identificado: {params[0]} (endereço {address}), tipo: {params_list[2].name}")
                return tuple(params_list)
        
        # Se chegou aqui, é um endereço não mapeado
        self.logger.warning(f"Endereço {address} não mapeado. Usando configuração padrão.")
        
        # Configuração padrão para dispositivos não identificados
        return (
            f'Sensor {address}',  # Nome genérico com o endereço
            0,                    # Registro padrão
            RegisterType.INPUT_REGISTER,  # Tipo de registro padrão
            'un',                 # Unidade padrão
            1.0,                  # Escala padrão (sem alteração)
            0.0,                  # Valor mínimo padrão
            100.0,                # Valor máximo padrão
            70.0,                 # Limiar de alerta padrão (70% do máximo)
            90.0                  # Limiar de alarme padrão (90% do máximo)
        )
    
    def _add_device_to_ui(self, device_id, device):
        """Adiciona um dispositivo à interface do usuário.
        
        Este método cria e configura um novo medidor na interface para exibir os dados do dispositivo.
        Os medidores são organizados em um grid, preenchendo as posições da esquerda para a direita
        e de cima para baixo. O método também configura as propriedades visuais do medidor com base
        nos parâmetros do dispositivo.
        
        Args:
            device_id (str): Identificador único do dispositivo.
            device (ModbusDeviceConfig): Objeto de configuração do dispositivo contendo parâmetros
                                       como nome, unidade, limites e limiares.
                                       
        Returns:
            bool: True se o dispositivo foi adicionado com sucesso, False caso contrário.
            
        Note:
            - O método tenta encontrar uma posição vazia no grid para adicionar o novo medidor.
            - Se não houver espaço no grid atual, o método retornará False.
            - O tamanho e as cores do medidor são configurados com base nos parâmetros do dispositivo.
        """
        # Validação dos parâmetros de entrada
        if not device_id or not isinstance(device_id, str):
            self.logger.error("ID do dispositivo inválido")
            return False
            
        if not device or not hasattr(device, 'name') or not hasattr(device, 'unit'):
            self.logger.error("Objeto de dispositivo inválido")
            return False
            
        if device_id in self.gauges:
            self.logger.warning(f"Dispositivo {device_id} já existe na interface")
            return False
            
        try:
            self.logger.debug(f"Adicionando dispositivo à interface: {device_id} - {device.name}")
            
            # Cria um novo medidor para o dispositivo
            try:
                gauge = AmmoniaGauge(device.name, device.unit)
                gauge.set_value(0)  # Valor inicial
                
                # Configura as cores com base no tipo de sensor
                if 'amônia' in device.name.lower() or 'amonia' in device.name.lower():
                    gauge.set_gauge_style(
                        fill_color=QColor(100, 150, 200),  # Azul
                        text_color=QColor(255, 255, 255),    # Branco
                        needle_color=QColor(255, 200, 0)     # Amarelo
                    )
                elif 'temperatura' in device.name.lower():
                    gauge.set_gauge_style(
                        fill_color=QColor(200, 100, 100),  # Vermelho
                        text_color=QColor(255, 255, 255),   # Branco
                        needle_color=QColor(255, 100, 100)  # Vermelho claro
                    )
                elif 'umidade' in device.name.lower():
                    gauge.set_gauge_style(
                        fill_color=QColor(100, 200, 100),  # Verde
                        text_color=QColor(0, 0, 0),         # Preto
                        needle_color=QColor(0, 150, 0)       # Verde escuro
                    )
                else:
                    # Configuração padrão para outros tipos de sensores
                    gauge.set_gauge_style(
                        fill_color=QColor(200, 200, 200),  # Cinza
                        text_color=QColor(0, 0, 0),         # Preto
                        needle_color=QColor(100, 100, 100)   # Cinza escuro
                    )
                
                # Define os limites do medidor
                gauge.set_limits(device.min_value, device.max_value)
                
                # Define os limiares de alerta e alarme
                if hasattr(device, 'warning_threshold') and hasattr(device, 'alarm_threshold'):
                    gauge.set_thresholds(device.warning_threshold, device.alarm_threshold)
                
            except Exception as e:
                self.logger.error(f"Erro ao criar medidor para {device_id}: {str(e)}", exc_info=True)
                return False
            
            # Encontra a primeira posição vazia no grid (4 colunas)
            max_attempts = 100  # Número máximo de tentativas
            grid_cols = 4       # Número de colunas no grid
            added = False
            
            for i in range(max_attempts):
                row = i // grid_cols
                col = i % grid_cols
                
                # Verifica se a posição está vazia
                if self.grid_layout.itemAtPosition(row, col) is None:
                    try:
                        # Adiciona o medidor ao layout
                        self.grid_layout.addWidget(gauge, row, col)
                        self.gauges[device_id] = gauge
                        
                        # Configura o tamanho e o comportamento do medidor
                        gauge.setMinimumSize(200, 200)
                        gauge.setSizePolicy(
                            QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Expanding
                        )
                        
                        # Habilita o tooltip com informações detalhadas
                        tooltip = (
                            f"<b>{device.name}</b><br>"
                            f"Endereço: {device.address}<br>"
                            f"Registro: {device.register}<br>"
                            f"Unidade: {device.unit}<br>"
                            f"Escala: {getattr(device, 'scale', 1.0)}<br>"
                            f"Faixa: {getattr(device, 'min_value', 0.0)} a {getattr(device, 'max_value', 100.0)} {device.unit}"
                        )
                        gauge.setToolTip(tooltip)
                        
                        # Força a atualização do layout
                        gauge.setVisible(True)
                        gauge.update()
                        gauge.repaint()
                        
                        # Atualiza o layout principal
                        self.grid_layout.update()
                        self.update()
                        
                        self.logger.debug(f"Dispositivo {device_id} adicionado à interface na posição ({row}, {col})")
                        added = True
                        break
                        
                    except Exception as e:
                        self.logger.error(f"Erro ao adicionar medidor à interface: {str(e)}", exc_info=True)
                        # Tenta a próxima posição
                        continue
            
            if not added:
                error_msg = f"Não foi possível encontrar espaço disponível no grid para o dispositivo {device_id}"
                self.logger.error(error_msg)
                gauge.deleteLater()
                return False
                
            return True
            
        except Exception as e:
            error_msg = f"Erro ao adicionar dispositivo {device_id} à interface: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.update_status(error_msg, error=True)
            return False
    
    def start_monitoring(self):
        """Inicia o monitoramento dos sensores.
        
        Returns:
            bool: True se o monitoramento foi iniciado com sucesso, False caso contrário.
        """
        try:
            # Verifica se o cliente Modbus está disponível
            if not hasattr(self, 'modbus_client') or not self.modbus_client:
                error_msg = "Não foi possível iniciar o monitoramento: cliente Modbus não inicializado"
                self.logger.error(error_msg)
                self.update_status(error_msg, error=True)
                self.update_connection_status(False)
                return False
                
            # Verifica se o cliente Modbus está conectado
            if not self.modbus_client.connected:
                self.logger.warning("Tentando reconectar o cliente Modbus...")
                self.update_status("Conectando ao dispositivo Modbus...", alert=True)
                
                if not self.modbus_client.connect():
                    error_msg = "Não foi possível conectar ao dispositivo Modbus"
                    self.logger.error(error_msg)
                    self.update_connection_status(False)
                    self.update_status(error_msg, error=True)
                    return False
                
                self.update_connection_status(True)
                self.update_status("Conexão Modbus estabelecida")
            
            # Obtém o intervalo de varredura da configuração
            interval = self.config.get('modbus', {}).get('scan_interval', 5000)
            
            # Verifica se o intervalo é válido
            if not isinstance(interval, (int, float)) or interval < 100:
                self.logger.warning(f"Intervalo de varredura inválido: {interval}ms. Usando valor padrão de 5000ms")
                interval = 5000
            
            # Para o timer se já estiver ativo
            if self.update_timer.isActive():
                self.update_timer.stop()
            
            # Inicia o timer
            self.update_timer.setInterval(int(interval))
            self.update_timer.start()
            self.monitoring_started = True
            
            # Atualiza a interface
            status_msg = f"Monitoramento ativo (atualização a cada {interval/1000:.1f}s)"
            self.update_status(status_msg)
            self.logger.info(f"Monitoramento iniciado com intervalo de {interval}ms")
            
            # Atualiza o botão de ação
            self.action_btn.setEnabled(True)
            
            # Força uma leitura imediata
            QTimer.singleShot(100, self.update_sensor_data)
            
            return True
            
        except Exception as e:
            error_msg = f"Erro ao iniciar o monitoramento: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.update_status(error_msg, error=True)
            self.update_connection_status(False)
            
            # Desativa o botão de monitoramento em caso de erro
            self.action_btn.setEnabled(True)
            
            return False
    
    def stop_monitoring(self):
        """Para o monitoramento dos sensores e libera recursos.
        
        Returns:
            bool: True se o monitoramento foi parado com sucesso, False caso contrário.
        """
        try:
            # Para o timer de atualização
            if hasattr(self, 'update_timer') and self.update_timer.isActive():
                self.update_timer.stop()
                self.logger.debug("Timer de atualização parado")
            
            # Atualiza o estado
            self.monitoring_started = False
            
            # Atualiza a interface
            self.update_status("Monitoramento parado", alert=True)
            self.logger.info("Monitoramento parado")
            
            # Atualiza o botão de ação
            self.action_btn.setEnabled(True)
            
            # Não limpa os medidores para manter os valores visíveis
            # self._clear_gauges()
            
            return True
            
        except Exception as e:
            error_msg = f"Erro ao parar o monitoramento: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.update_status(error_msg, error=True)
            
            # Garante que o botão seja reativado mesmo em caso de erro
            self.action_btn.setEnabled(True)
            
            return False
            
    def _clear_gauges(self):
        """Limpa todos os medidores da interface."""
        try:
            if hasattr(self, 'gauges'):
                # Remove os widgets do layout
                for gauge in self.gauges.values():
                    if gauge and gauge.parent():
                        self.grid_layout.removeWidget(gauge)
                        gauge.setParent(None)
                        gauge.deleteLater()
                
                # Limpa o dicionário de medidores
                self.gauges.clear()
                self.logger.debug("Medidores removidos da interface")
                
        except Exception as e:
            self.logger.error(f"Erro ao limpar medidores: {str(e)}", exc_info=True)
    
    @pyqtSlot()
    def update_sensor_data(self):
        """Atualiza os dados dos sensores a partir do Modbus."""
        # Verifica se o cliente Modbus está disponível
        if not hasattr(self, 'modbus_client') or not self.modbus_client:
            error_msg = "Erro: Cliente Modbus não inicializado"
            self.update_status(error_msg, error=True)
            self.logger.error(error_msg)
            self.update_connection_status(False)
            return False
            
        # Verifica se o cliente Modbus está conectado
        if not self.modbus_client.connected:
            self.logger.warning("Cliente Modbus desconectado. Tentando reconectar...")
            self.update_connection_status(False)
            self.update_status("Reconectando ao dispositivo Modbus...", alert=True)
            
            try:
                if not self.modbus_client.connect():
                    error_msg = "Erro: Não foi possível reconectar ao dispositivo Modbus"
                    self.update_status(error_msg, error=True)
                    self.update_connection_status(False)
                    self.logger.error(error_msg)
                    # Desativa o botão de monitoramento se estiver ativo
                    if hasattr(self, 'monitoring_started') and self.monitoring_started:
                        self.toggle_monitoring()
                    # Espera 5 segundos antes de tentar novamente
                    QTimer.singleShot(5000, self.update_sensor_data)
                    return False
                else:
                    self.update_connection_status(True)
                    self.update_status("Conexão Modbus restabelecida")
            except Exception as e:
                self.update_connection_status(False)
                self.update_status(f"Erro na reconexão: {str(e)}", error=True)
                self.logger.error(f"Erro na reconexão Modbus: {str(e)}")
                QTimer.singleShot(5000, self.update_sensor_data)
                return False
        
        try:
            # Verifica se temos dispositivos configurados
            if not hasattr(self, 'modbus_devices') or not self.modbus_devices:
                self.logger.info("Nenhum dispositivo Modbus configurado. Inicializando...")
                if not self.initialize_modbus_devices():
                    error_msg = "Falha ao inicializar dispositivos Modbus"
                    self.update_status(error_msg, error=True)
                    self.logger.error(error_msg)
                    return False
            
            # Log dos dispositivos configurados
            device_count = len(self.modbus_devices)
            self.logger.debug(f"Iniciando leitura de {device_count} dispositivos Modbus")
            
            # Contadores para estatísticas
            success_count = 0
            error_count = 0
            
            # Lê todos os sensores configurados
            for sensor_id, device in self.modbus_devices.items():
                try:
                    self.logger.debug(f"Lendo sensor {sensor_id} (endereço: {device.address}, registro: {device.register})")
                    
                    # Lê o valor do sensor com um timeout curto para evitar travar a interface
                    value = None
                    read_success = False
                    
                    try:
                        value = self.modbus_client.read_device(device)
                        read_success = True
                    except Exception as read_error:
                        self.logger.error(f"Erro ao ler sensor {sensor_id}: {str(read_error)}", exc_info=True)
                    
                    if read_success and value is not None:
                        try:
                            # Converte para float e aplica limites
                            value = float(value)
                            value = max(device.min_value, min(value, device.max_value))
                            
                            self.logger.debug(f"Valor lido do sensor {sensor_id}: {value} {device.unit}")
                            
                            # Atualiza a interface de forma assíncrona
                            QTimer.singleShot(0, lambda v=value, sid=sensor_id: self._update_gauge(sid, v))
                            
                            # Registra no banco de dados em uma thread separada para não travar a interface
                            self._log_sensor_reading(sensor_id, value, device.unit)
                            
                            # Verifica alertas
                            self.check_alerts(sensor_id, value)
                            
                            success_count += 1
                            
                        except (ValueError, TypeError) as conv_error:
                            error_msg = f"Valor inválido do sensor {sensor_id}: {value}"
                            self.logger.error(error_msg, exc_info=True)
                            self.update_status(error_msg, error=True)
                            error_count += 1
                            
                    else:
                        error_msg = f"Falha ao ler o sensor {sensor_id} (endereço: {device.address}, registro: {device.register})"
                        self.logger.warning(error_msg)
                        self.update_status(error_msg, alert=True)
                        error_count += 1
                        
                except Exception as e:
                    error_msg = f"Erro ao processar sensor {sensor_id}: {str(e)}"
                    self.logger.error(error_msg, exc_info=True)
                    self.update_status(error_msg, error=True)
                    error_count += 1
            
            # Atualiza a barra de status com o resultado da leitura
            if device_count > 0:
                status_msg = f"Leitura concluída: {success_count} de {device_count} sensores lidos com sucesso"
                if error_count > 0:
                    status_msg += f" ({error_count} com erros)"
                self.update_status(status_msg)
                self.logger.info(status_msg)
                
                # Se todos os sensores falharem, tenta reiniciar a conexão
                if success_count == 0 and error_count > 0:
                    self.logger.warning("Todos os sensores falharam. Tentando reiniciar a conexão...")
                    self.stop_monitoring()
                    QTimer.singleShot(1000, self.start_monitoring)
            
            return success_count > 0
            
        except Exception as e:
            error_msg = f"Erro inesperado ao atualizar dados: {str(e)}"
            self.update_status(error_msg, error=True)
            self.logger.error(error_msg, exc_info=True)
            return False
    
    def _update_gauge(self, sensor_id, value):
        """Atualiza o medidor na interface do usuário.
        
        Este método é responsável por atualizar o valor exibido em um medidor específico
        na interface do usuário. Ele inclui tratamento de erros robusto e validação
        de entrada para garantir uma operação segura.
        
        Args:
            sensor_id (str): Identificador único do sensor cujo medidor será atualizado.
            value (float): Novo valor a ser exibido no medidor.
            
        Returns:
            bool: True se a atualização foi bem-sucedida, False caso contrário.
        """
        try:
            # Validação dos parâmetros de entrada
            if not isinstance(sensor_id, str) or not sensor_id:
                self.logger.error("ID do sensor inválido para atualização do medidor")
                return False
                
            # Verifica se o sensor_id existe no dicionário de medidores
            if sensor_id not in self.gauges:
                self.logger.warning(f"Tentativa de atualizar medidor não encontrado: {sensor_id}")
                # Tenta adicionar o medidor se não existir
                if hasattr(self, 'modbus_devices') and sensor_id in self.modbus_devices:
                    device = self.modbus_devices[sensor_id]
                    self.logger.info(f"Tentando recriar medidor para {sensor_id}")
                    if not self._add_device_to_ui(sensor_id, device):
                        self.logger.error(f"Falha ao recriar medidor para {sensor_id}")
                        return False
                    else:
                        self.logger.info(f"Medidor {sensor_id} recriado com sucesso")
                else:
                    self.logger.error(f"Não foi possível recriar medidor {sensor_id}: dispositivo não encontrado")
                    return False
            
            # Valida se o valor é numérico
            try:
                value = float(value)
            except (ValueError, TypeError):
                self.logger.error(f"Valor inválido para o medidor {sensor_id}: {value}")
                return False
            
            # Obtém a referência para o medidor
            gauge = self.gauges.get(sensor_id)
            
            # Verifica se o medidor ainda está válido
            if not gauge or not hasattr(gauge, 'set_value'):
                self.logger.error(f"Medidor {sensor_id} inválido ou corrompido")
                # Tenta remover e recriar o medidor na próxima atualização
                if sensor_id in self.gauges:
                    del self.gauges[sensor_id]
                return False
            
            try:
                # Atualiza o valor do medidor na thread da interface
                if QThread.currentThread() != self.thread():
                    # Se não estiver na thread da interface, usa QMetaObject.invokeMethod
                    QMetaObject.invokeMethod(
                        gauge, 
                        'set_value', 
                        Qt.ConnectionType.QueuedConnection,
                        Q_ARG(float, float(value))
                    )
                else:
                    # Se já estiver na thread da interface, atualiza diretamente
                    gauge.set_value(value)
                
                # Log de depuração (com nível apropriado para não sobrecarregar)
                if hasattr(self, 'logger') and self.logger.isEnabledFor(10):  # DEBUG level
                    self.logger.debug(f"Medidor {sensor_id} atualizado para {value}")
                    
                return True
                
            except RuntimeError as e:
                # Trata erros de referência a objetos Qt inválidos
                if 'wrapped C/C++ object' in str(e):
                    self.logger.warning(f"Referência a objeto Qt inválida ao atualizar medidor {sensor_id}")
                    # Remove a referência inválida
                    if sensor_id in self.gauges:
                        del self.gauges[sensor_id]
                else:
                    self.logger.error(f"Erro ao atualizar medidor {sensor_id}: {str(e)}", exc_info=True)
                return False
                
            except Exception as e:
                self.logger.error(f"Erro inesperado ao atualizar medidor {sensor_id}: {str(e)}", exc_info=True)
                return False
                
        except Exception as e:
            # Captura qualquer outra exceção inesperada
            self.logger.error(f"Erro crítico em _update_gauge para {sensor_id}: {str(e)}", exc_info=True)
            return False
    
    def _ensure_sensor_exists(self, sensor_id, name=None, unit='ppm'):
        """Garante que um sensor exista no banco de dados.
        
        Args:
            sensor_id: ID do sensor.
            name: Nome do sensor (opcional).
            unit: Unidade de medida (padrão: 'ppm').
            
        Returns:
            bool: True se o sensor existe ou foi criado, False em caso de erro.
        """
        try:
            cursor = self.db.cursor()
            
            # Verifica se o sensor já existe
            cursor.execute("SELECT 1 FROM sensor_config WHERE sensor_id = ?", (sensor_id,))
            if not cursor.fetchone():
                # Se não existir, cria um novo sensor
                cursor.execute(
                    """
                    INSERT INTO sensor_config 
                    (sensor_id, name, unit, min_value, max_value, warning_level, danger_level)
                    VALUES (?, ?, ?, 0, 100, 70, 90)
                    """,
                    (sensor_id, name or f"Sensor {sensor_id}", unit)
                )
                self.db.commit()
                self.logger.info(f"Novo sensor adicionado: {sensor_id}")
                
                # Atualiza o dicionário de sensores
                if sensor_id not in self.sensor_data:
                    self.sensor_data[sensor_id] = {
                        'name': name or f"Sensor {sensor_id}",
                        'unit': unit,
                        'min_value': 0,
                        'max_value': 100,
                        'warning_level': 70,
                        'danger_level': 90,
                        'value': 0,
                        'status': 'disconnected',
                        'last_update': None
                    }
                    # Adiciona o medidor à interface
                    self._add_gauge_to_ui(sensor_id)
                    
            return True
            
        except sqlite3.Error as e:
            self.logger.error(f"Erro ao verificar/criar sensor {sensor_id}: {str(e)}")
            self.db.rollback()
            return False
    
    def _log_sensor_reading(self, sensor_id, value, unit='ppm'):
        """Registra a leitura do sensor no banco de dados.
        
        Args:
            sensor_id: ID do sensor.
            value: Valor lido.
            unit: Unidade de medida.
            
        Returns:
            bool: True se a leitura foi registrada com sucesso, False caso contrário.
        """
        try:
            # Garante que o sensor existe no banco de dados
            if not self._ensure_sensor_exists(sensor_id, unit=unit):
                self.logger.error(f"Não foi possível garantir a existência do sensor {sensor_id}")
                return False
                
            cursor = self.db.cursor()
            cursor.execute(
                """
                INSERT INTO sensor_readings (sensor_id, value, unit, timestamp)
                VALUES (?, ?, ?, datetime('now'))
                """,
                (sensor_id, float(value), unit)
            )
            self.db.commit()
            return True
            
        except sqlite3.Error as e:
            self.logger.error(f"Erro ao registrar leitura do sensor {sensor_id}: {str(e)}")
            self.db.rollback()
            return False
    
    def initialize_modbus_devices(self):
        """Inicializa os dispositivos Modbus com base na configuração.
        
        Returns:
            bool: True se a inicialização foi bem-sucedida, False caso contrário.
        """
        if not hasattr(self, 'modbus_client') or not self.modbus_client or not self.modbus_client.connected:
            self.logger.warning("Cliente Modbus não está conectado")
            return False
            
        self.logger.info("Inicializando dispositivos Modbus...")
        
        # Se já tivermos dispositivos configurados, não precisamos fazer nada
        if hasattr(self, 'modbus_devices') and self.modbus_devices:
            self.logger.info("Dispositivos já inicializados")
            return True
        
        # Configuração padrão dos sensores
        # Nota: Ajuste estes valores conforme a especificação do seu sensor
        sensor_configs = [
            {
                'id': 'sensor_1',
                'name': 'Sensor de Amônia',
                'address': 2,  # Endereço Modbus do dispositivo (ajustado para 2)
                'register': 0,  # Registro a ser lido (ajuste conforme o manual do sensor)
                'register_type': RegisterType.INPUT_REGISTER,  # 4x registros
                'unit': 'ppm',
                'scale': 0.1,   # Fator de escala (ajuste conforme o manual do sensor)
                'offset': 0.0,  # Offset (ajuste conforme necessário)
                'min_value': 0.0,
                'max_value': 100.0,
                'warning_threshold': 70.0,
                'alarm_threshold': 90.0,
                'description': 'Sensor de concentração de amônia',
                'decimal_places': 1  # Casas decimais para exibição
            },
            # Exemplo de configuração para um segundo sensor:
            # {
            #     'id': 'sensor_2',
            #     'name': 'Sensor de Temperatura',
            #     'address': 2,
            #     'register': 0,
            #     'register_type': RegisterType.INPUT_REGISTER,
            #     'unit': '°C',
            #     'scale': 0.1,
            #     'offset': 0.0,
            #     'min_value': -10.0,
            #     'max_value': 50.0,
            #     'warning_threshold': 35.0,
            #     'alarm_threshold': 40.0,
            #     'description': 'Sensor de temperatura ambiente',
            #     'decimal_places': 1
            # },
        ]
        
        self.modbus_devices = {}
        devices_added = 0
        
        # Cria e adiciona os dispositivos ao cliente Modbus
        for config in sensor_configs:
            try:
                self.logger.info(f"Configurando sensor {config['id']} (endereço: {config['address']}, registro: {config['register']})")
                
                device = ModbusDeviceConfig(
                    name=config['name'],
                    address=config['address'],
                    register=config['register'],
                    register_type=config['register_type'],
                    unit=config['unit'],
                    scale=config['scale'],
                    offset=config.get('offset', 0.0),
                    description=config.get('description', ''),
                    min_value=config.get('min_value', 0.0),
                    max_value=config.get('max_value', 100.0),
                    warning_threshold=config.get('warning_threshold', 70.0),
                    alarm_threshold=config.get('alarm_threshold', 90.0)
                )
                
                self.modbus_client.add_device(device)
                self.modbus_devices[config['id']] = device
                self.logger.info(f"Dispositivo {config['name']} configurado no endereço {config['address']}")
                
            except Exception as e:
                self.logger.error(f"Erro ao configurar dispositivo {config.get('name', 'desconhecido')}: {str(e)}")
    
    def check_alerts(self, sensor_id, value):
        """Verifica se o valor do sensor acionou algum alerta."""
        try:
            warning_threshold = self.config.get('sensors', {}).get('warning_threshold', 70)
            alarm_threshold = self.config.get('sensors', {}).get('alarm_threshold', 90)
            
            if value >= alarm_threshold:
                self.trigger_alert(sensor_id, value, "CRÍTICO", self.palette().color(QPalette.ColorRole.Highlight).red())
            elif value >= warning_threshold:
                self.trigger_alert(sensor_id, value, "ALERTA", self.palette().color(QPalette.ColorRole.Highlight).yellow())
                
        except Exception as e:
            self.logger.error(f"Erro ao verificar alertas: {str(e)}")
    
    def trigger_alert(self, sensor_id, value, level, color):
        """Aciona um alerta."""
        message = f"{level}: Sensor {sensor_id} = {value:.1f} ppm"
        self.update_status(message, alert=True)
        
        # Em uma implementação real, aqui você poderia:
        # 1. Tocar um som de alerta
        # 2. Enviar notificação por e-mail/SMS
        # 3. Registrar o alerta no banco de dados
        self.logger.warning(message)
    
    def update_status(self, message, error=False, alert=False):
        """Atualiza a mensagem na barra de status.
        
        Args:
            message: Mensagem a ser exibida
            error: Se True, exibe como erro
            alert: Se True, exibe como alerta
        """
        if error:
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background: #fde8e8;
                    color: #e74c3c;
                    padding: 8px 15px;
                    border-top: 1px solid #f5b7b1;
                    font-size: 12px;
                }
            """)
        elif alert:
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background: #fff8e8;
                    color: #e67e22;
                    padding: 8px 15px;
                    border-top: 1px solid #f5e5b7;
                    font-size: 12px;
                }
            """)
        else:
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background: #ecf0f1;
                    color: #7f8c8d;
                    padding: 8px 15px;
                    border-top: 1px solid #d5dbdb;
                    font-size: 12px;
                }
            """)
        self.status_bar.showMessage(message)
    
    def trigger_test_alarm(self):
        """
        Dispara um alarme de teste para verificação do sistema.
        Envia um comando de teste de alarme para o dispositivo Modbus.
        """
        from PyQt6.QtWidgets import QMessageBox, QInputDialog
        
        # Verifica se o cliente Modbus está configurado
        if not hasattr(self, 'modbus_client') or not self.modbus_client:
            QMessageBox.warning(
                self,
                "Aviso",
                "Cliente Modbus não configurado. Verifique as configurações de conexão."
            )
            return
        
        # Pergunta ao usuário por quanto tempo (em segundos) o alarme deve tocar
        duration, ok = QInputDialog.getInt(
            self,
            "Duração do Alarme",
            "Digite a duração do alarme (segundos):",
            5,  # Valor padrão
            1,   # Valor mínimo
            60,  # Valor máximo
            1    # Incremento
        )
        
        if not ok:
            return  # Usuário cancelou
        
        try:
            # Endereço do registro de controle do alarme (ajuste conforme o manual do dispositivo)
            ALARM_REGISTER = 0x0000
            
            # Endereço do dispositivo Modbus (geralmente 1 por padrão, mas pode variar)
            device_address = 1  # Ajuste este valor para o endereço correto do seu dispositivo
            
            # Log dos parâmetros que serão usados
            self.logger.info(f"Enviando comando de teste de alarme para o dispositivo {device_address}, registro {ALARM_REGISTER}")
            
            # Envia o comando de teste de alarme
            success = self.modbus_client.write_register(
                address=device_address,
                register=ALARM_REGISTER,
                value=1,  # Valor para ativar o alarme
                register_type=RegisterType.HOLDING_REGISTER  # Ajuste para COIL se necessário
            )
            
            if success:
                self.logger.info(f"Comando de teste de alarme enviado com sucesso (duração: {duration}s)")
                
                # Agenda o desligamento do alarme após a duração especificada
                QTimer.singleShot(duration * 1000, self._turn_off_alarm)
                
                QMessageBox.information(
                    self,
                    "Sucesso",
                    f"Alarme de teste ativado por {duration} segundos."
                )
            else:
                raise Exception("Falha ao enviar comando para o dispositivo")
                
        except Exception as e:
            self.logger.error(f"Erro ao ativar alarme de teste: {str(e)}", exc_info=True)
            QMessageBox.critical(
                self,
                "Erro",
                f"Falha ao ativar o alarme de teste.\nVerifique se o endereço do dispositivo e o registro estão corretos.\n\nDetalhes: {str(e)}"
            )
    
    def _turn_off_alarm(self):
        """Desativa o alarme de teste."""
        try:
            if hasattr(self, 'modbus_client') and self.modbus_client:
                ALARM_REGISTER = 0x0000  # Mesmo registro usado para ativar
                device_address = 1  # Mesmo endereço usado para ativar
                
                self.logger.info(f"Desativando alarme de teste no dispositivo {device_address}, registro {ALARM_REGISTER}")
                
                success = self.modbus_client.write_register(
                    address=device_address,
                    register=ALARM_REGISTER,
                    value=0,  # Valor para desativar o alarme
                    register_type=RegisterType.HOLDING_REGISTER  # Ajuste para COIL se necessário
                )
                
                if success:
                    self.logger.info("Alarme de teste desativado com sucesso")
                else:
                    self.logger.error("Falha ao desativar o alarme de teste")
                    
        except Exception as e:
            self.logger.error(f"Erro ao desativar alarme de teste: {str(e)}", exc_info=True)
            # Tenta reconectar se houver erro de comunicação
            if hasattr(self, 'modbus_client') and self.modbus_client:
                self.modbus_client.connect()
    
    def manage_sensors(self):
        """Exibe a janela de gerenciamento de sensores."""
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
                                   QPushButton, QHBoxLayout, QHeaderView, QMessageBox,
                                   QAbstractItemView, QLabel)
        
        # Cria o diálogo
        dialog = QDialog(self)
        dialog.setWindowTitle("Gerenciar Sensores")
        dialog.setMinimumSize(800, 500)
        
        # Layout principal
        layout = QVBoxLayout(dialog)
        
        # Título
        title_label = QLabel("Sensores Cadastrados")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px 0;
            }
        """)
        layout.addWidget(title_label)
        
        # Tabela de sensores
        self.sensors_table = QTableWidget()
        self.sensors_table.setColumnCount(6)
        self.sensors_table.setHorizontalHeaderLabels(["ID", "Nome", "Endereço", "Registro", "Tipo", "Ações"])
        self.sensors_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sensors_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.sensors_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        
        # Estilização da tabela
        self.sensors_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 4px;
                gridline-color: #dcdde1;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #dcdde1;
            }
            QTableWidget::item:selected {
                background-color: #e1f0fa;
                color: #2c3e50;
            }
        """)
        
        # Botões de ação
        button_layout = QHBoxLayout()
        
        add_button = QPushButton("Adicionar Sensor")
        add_button.clicked.connect(self.show_add_sensor_dialog)
        add_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        
        edit_button = QPushButton("Editar")
        edit_button.setEnabled(False)
        edit_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
            QPushButton:hover:enabled {
                background-color: #2980b9;
            }
        """)
        
        remove_button = QPushButton("Remover")
        remove_button.setEnabled(False)
        remove_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
            QPushButton:hover:enabled {
                background-color: #c0392b;
            }
        """)
        
        close_button = QPushButton("Fechar")
        close_button.clicked.connect(dialog.reject)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        
        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(remove_button)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        
        # Adiciona widgets ao layout principal
        layout.addWidget(self.sensors_table)
        layout.addLayout(button_layout)
        
        # Carrega os sensores na tabela
        self.load_sensors_to_table()
        
        # Exibe o diálogo
        dialog.exec()
    
    def update_system_status(self):
        """Atualiza as informações de status do sistema (CPU, memória, etc.)."""
        try:
            import psutil
            
            # Obtém o uso de CPU
            cpu_percent = psutil.cpu_percent(interval=0.5)
            
            # Obtém o uso de memória
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used / (1024 * 1024)  # Em MB
            memory_total = memory.total / (1024 * 1024)  # Em MB
            
            # Atualiza os labels
            self.cpu_usage.setText(f"CPU: {cpu_percent:.1f}%")
            self.memory_usage.setText(f"Memória: {memory_percent:.1f}% ({memory_used:.0f}/{memory_total:.0f} MB)")
            
            # Muda a cor com base no uso
            self.update_status_color(self.cpu_usage, cpu_percent)
            self.update_status_color(self.memory_usage, memory_percent)
            
            # Atualiza o status da conexão Modbus
            if hasattr(self, 'modbus_client') and self.modbus_client:
                self.connection_status.setStyleSheet("""
                    QLabel {
                        color: #27ae60;
                        font-weight: bold;
                    }
                """)
                self.connection_status.setText("Modbus: Conectado")
            else:
                self.connection_status.setStyleSheet("""
                    QLabel {
                        color: #e74c3c;
                        font-weight: bold;
                    }
                """)
                self.connection_status.setText("Modbus: Desconectado")
                
        except ImportError:
            # Se o psutil não estiver instalado, mostra mensagem de erro
            self.cpu_usage.setText("CPU: N/A (instale 'psutil')")
            self.memory_usage.setText("Memória: N/A (instale 'psutil')")
            self.connection_status.setText("Modbus: N/A")
            
            # Para de tentar atualizar se não tiver o psutil
            if hasattr(self, 'system_monitor_timer'):
                self.system_monitor_timer.stop()
                
        except Exception as e:
            self.logger.error(f"Erro ao atualizar status do sistema: {str(e)}")
    
    def update_status_color(self, label, percent):
        """Atualiza a cor do texto com base no percentual de uso."""
        if percent > 80:
            color = "#e74c3c"  # Vermelho para uso alto
        elif percent > 60:
            color = "#f39c12"  # Laranja para uso médio-alto
        else:
            color = "#27ae60"  # Verde para uso normal
            
        label.setStyleSheet(f"color: {color}; font-weight: bold;")
    
    def view_logs(self):
        """Exibe uma janela simples com os logs do sistema."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
        import os
        
        # Cria o diálogo
        dialog = QDialog(self)
        dialog.setWindowTitle("Visualizador de Logs")
        dialog.setMinimumSize(800, 600)
        
        # Layout principal
        layout = QVBoxLayout(dialog)
        
        # Área de texto para exibir os logs
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        
        # Tenta carregar o arquivo de log
        log_file = os.path.join('logs', 'monitor_amonia.log')
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                log_text.setPlainText(log_content)
            else:
                log_text.setPlainText("Arquivo de log não encontrado.")
        except Exception as e:
            log_text.setPlainText(f"Erro ao carregar logs: {str(e)}")
        
        # Botão Fechar
        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(dialog.accept)
        
        # Adiciona widgets ao layout
        layout.addWidget(log_text)
        layout.addWidget(close_btn)
        
        # Exibe o diálogo
        dialog.exec()
    
    def export_data(self):
        """Exporta os dados dos sensores para um arquivo."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        import csv
        from datetime import datetime
        import os
        
        try:
            # Abre diálogo para selecionar local de salvamento
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "Exportar Dados",
                f"dados_sensores_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "Arquivos CSV (*.csv);;Todos os arquivos (*)"
            )
            
            if not file_name:
                return  # Usuário cancelou
                
            # Garante a extensão .csv
            if not file_name.lower().endswith('.csv'):
                file_name += '.csv'
            
            # Prepara os dados para exportação
            headers = ["ID", "Nome", "Endereço", "Registro", "Tipo", "Unidade", "Valor", "Data/Hora"]
            rows = []
            
            # Obtém os dados atuais dos sensores
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Se houver medidores na interface, usa seus valores
            if hasattr(self, 'gauges') and self.gauges:
                for sensor_id, gauge in self.gauges.items():
                    # Tenta obter informações adicionais do sensor
                    sensor_info = next((s for s in self.sensor_data.get('sensors', []) 
                                     if str(s.get('id')) == str(sensor_id)), {})
                    
                    rows.append([
                        sensor_id,
                        sensor_info.get('name', f'Sensor {sensor_id}'),
                        sensor_info.get('address', ''),
                        sensor_info.get('register', ''),
                        sensor_info.get('register_type', ''),
                        sensor_info.get('unit', ''),
                        gauge.value(),
                        current_time
                    ])
            
            # Se não houver medidores, tenta usar os dados da tabela
            elif hasattr(self, 'sensors_table') and self.sensors_table:
                for row in range(self.sensors_table.rowCount()):
                    rows.append([
                        self.sensors_table.item(row, 0).text(),  # ID
                        self.sensors_table.item(row, 1).text(),  # Nome
                        self.sensors_table.item(row, 2).text(),  # Endereço
                        self.sensors_table.item(row, 3).text(),  # Registro
                        self.sensors_table.item(row, 4).text(),  # Tipo
                        '',  # Unidade não disponível na tabela
                        'N/A',  # Valor não disponível
                        current_time
                    ])
            
            # Se não houver dados para exportar
            if not rows:
                QMessageBox.information(
                    self,
                    "Nenhum Dado",
                    "Não há dados de sensores disponíveis para exportação."
                )
                return
            
            # Escreve os dados no arquivo CSV
            with open(file_name, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(headers)
                writer.writerows(rows)
            
            # Mensagem de sucesso
            QMessageBox.information(
                self,
                "Exportação Concluída",
                f"Dados exportados com sucesso para:\n{file_name}"
            )
            
            self.update_status(f"Dados exportados para {os.path.basename(file_name)}")
            self.logger.info(f"Dados exportados para {file_name}")
            
        except Exception as e:
            error_msg = f"Erro ao exportar dados: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            QMessageBox.critical(
                self,
                "Erro na Exportação",
                f"Ocorreu um erro ao exportar os dados:\n{str(e)}"
            )
            self.update_status(error_msg, error=True)
    
    def refresh_sensors(self):
        """Atualiza os dados dos sensores."""
        try:
            self.logger.info("Atualizando dados dos sensores...")
            
            # Atualiza o status
            self.update_status("Atualizando sensores...")
            
            # Aqui você implementaria a lógica para buscar os dados mais recentes dos sensores
            # Por enquanto, vamos apenas simular uma atualização
            
            # Simula um atraso para a operação
            import time
            time.sleep(1)  # Simula o tempo de leitura dos sensores
            
            # Atualiza a interface
            if hasattr(self, 'sensors_table') and self.sensors_table:
                self.load_sensors_to_table()
            
            # Atualiza os medidores se necessário
            if hasattr(self, 'gauges') and self.gauges:
                for sensor_id, gauge in self.gauges.items():
                    # Simula uma nova leitura
                    # Em uma implementação real, você buscaria o valor real do sensor
                    gauge.set_value(0)  # Usa set_value em vez de setValue
            
            self.update_status("Sensores atualizados com sucesso!")
            self.logger.info("Dados dos sensores atualizados")
            
        except Exception as e:
            error_msg = f"Erro ao atualizar sensores: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.update_status(error_msg, error=True)
    
    def load_sensors_to_table(self):
        """Carrega os sensores na tabela de gerenciamento."""
        # Limpa a tabela
        if not hasattr(self, 'sensors_table') or not self.sensors_table:
            return
            
        self.sensors_table.setRowCount(0)
        
        # Tenta carregar os sensores do banco de dados
        try:
            # Aqui você implementaria a lógica para buscar os sensores do banco de dados
            # Por enquanto, vamos simular alguns dados de exemplo
            example_sensors = [
                {"id": 1, "name": "Sensor de Amônia 1", "address": 1, "register": 0, "register_type": "Holding Register", "unit": "ppm"},
                {"id": 2, "name": "Sensor de Temperatura", "address": 2, "register": 1, "register_type": "Input Register", "unit": "°C"},
            ]
            
            # Se houver sensores configurados, use-os
            if hasattr(self, 'sensor_config') and self.sensor_config:
                sensors = self.sensor_config
            else:
                sensors = example_sensors
        except Exception as e:
            self.logger.error(f"Erro ao carregar sensores: {str(e)}")
            sensors = []
        
        for sensor in example_sensors:
            row = self.sensors_table.rowCount()
            self.sensors_table.insertRow(row)
            
            # Adiciona os itens da linha
            self.sensors_table.setItem(row, 0, QTableWidgetItem(str(sensor['id'])))
            self.sensors_table.setItem(row, 1, QTableWidgetItem(sensor['name']))
            self.sensors_table.setItem(row, 2, QTableWidgetItem(str(sensor['address'])))
            self.sensors_table.setItem(row, 3, QTableWidgetItem(str(sensor['register'])))
            self.sensors_table.setItem(row, 4, QTableWidgetItem(sensor['register_type']))
            
            # Adiciona botões de ação
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 2, 5, 2)
            
            edit_btn = QPushButton("Editar")
            edit_btn.setProperty('sensor_id', sensor['id'])
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    padding: 5px 10px;
                    border: none;
                    border-radius: 3px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            
            remove_btn = QPushButton("Remover")
            remove_btn.setProperty('sensor_id', sensor['id'])
            remove_btn.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    padding: 5px 10px;
                    border: none;
                    border-radius: 3px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            
            action_layout.addWidget(edit_btn)
            action_layout.addWidget(remove_btn)
            action_layout.addStretch()
            
            self.sensors_table.setCellWidget(row, 5, action_widget)
        
        # Ajusta as colunas
        self.sensors_table.resizeColumnsToContents()
    
    def show_add_sensor_dialog(self):
        """Exibe a caixa de diálogo para adicionar um novo sensor."""
        from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                                   QComboBox, QDialogButtonBox, QMessageBox)
        
        # Cria o diálogo
        dialog = QDialog(self)
        dialog.setWindowTitle("Adicionar Novo Sensor")
        dialog.setMinimumWidth(400)
        
        # Layout principal
        layout = QVBoxLayout(dialog)
        
        # Formulário
        form_layout = QFormLayout()
        
        # Campos do formulário
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Ex.: Sensor de Amônia 1")
        
        address_edit = QLineEdit()
        address_edit.setPlaceholderText("1-247")
        
        register_edit = QLineEdit()
        register_edit.setPlaceholderText("0-65535")
        
        register_type_combo = QComboBox()
        register_type_combo.addItems(["Holding Register", "Input Register", "Coil", "Discrete Input"])
        
        unit_edit = QLineEdit()
        unit_edit.setPlaceholderText("Ex.: ppm, °C, %")
        
        # Adiciona campos ao formulário
        form_layout.addRow("Nome do Sensor:", name_edit)
        form_layout.addRow("Endereço Modbus:", address_edit)
        form_layout.addRow("Número do Registro:", register_edit)
        form_layout.addRow("Tipo de Registro:", register_type_combo)
        form_layout.addRow("Unidade de Medida:", unit_edit)
        
        # Botões do diálogo
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        
        # Adiciona widgets ao layout principal
        layout.addLayout(form_layout)
        layout.addWidget(button_box)
        
        # Estilização
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #2c3e50;
                font-size: 13px;
            }
            QLineEdit, QComboBox {
                padding: 6px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton {
                min-width: 80px;
                padding: 6px 15px;
                margin: 5px;
                border: none;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:enabled {
                background-color: #3498db;
                color: white;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
            QPushButton:hover:enabled {
                background-color: #2980b9;
            }
        """)
        
        # Exibe o diálogo
        result = dialog.exec()
        
        # Processa o resultado
        if result == QDialog.DialogCode.Accepted:
            # Valida os campos
            if not all([name_edit.text().strip(), 
                       address_edit.text().strip(), 
                       register_edit.text().strip(),
                       unit_edit.text().strip()]):
                QMessageBox.warning(
                    self, 
                    "Campos Obrigatórios",
                    "Por favor, preencha todos os campos obrigatórios."
                )
                return
                
            try:
                # Aqui você adicionaria a lógica para salvar o novo sensor
                sensor_data = {
                    'name': name_edit.text().strip(),
                    'address': int(address_edit.text().strip()),
                    'register': int(register_edit.text().strip()),
                    'register_type': register_type_combo.currentText(),
                    'unit': unit_edit.text().strip(),
                }
                
                # Log
                self.logger.info(f"Novo sensor adicionado: {sensor_data}")
                
                # Atualiza a interface
                self.update_status(f"Sensor '{sensor_data['name']}' adicionado com sucesso!")
                
                # Aqui você chamaria o método para adicionar o sensor à interface
                # self.add_sensor_to_ui(sensor_data)
                
            except ValueError as e:
                QMessageBox.critical(
                    self,
                    "Erro de Formato",
                    f"Por favor, verifique os valores informados. Erro: {str(e)}"
                )
    
    def show_settings_dialog(self):
        """Exibe a caixa de diálogo de configurações."""
        from PyQt6.QtWidgets import QMessageBox
        
        # Cria uma mensagem simples por enquanto
        # Em uma implementação real, você pode criar um diálogo personalizado
        # com as configurações do sistema
        msg = QMessageBox(self)
        msg.setWindowTitle("Configurações")
        msg.setText("Configurações do Sistema")
        msg.setInformativeText("Aqui serão exibidas as configurações do sistema.")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Estiliza a mensagem
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #2c3e50;
                font-size: 14px;
            }
            QPushButton {
                min-width: 80px;
                padding: 5px 15px;
                background-color: #3498db;
                border: 1px solid #2980b9;
                border-radius: 4px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        # Exibe a mensagem
        msg.exec()
        
        # Log
        self.logger.info("Diálogo de configurações exibido")
    
    def closeEvent(self, event):
        """Método chamado quando a janela é fechada.
        
        Args:
            event: Evento de fechamento
        """
        try:
            self.logger.info("Fechando o dashboard...")
            
            # Para o monitoramento se estiver ativo
            if hasattr(self, 'monitoring_started') and self.monitoring_started:
                self.stop_monitoring()
            
            # Para o timer se estiver ativo
            if hasattr(self, 'update_timer') and self.update_timer.isActive():
                self.update_timer.stop()
            
            # Desativa qualquer alarme ativo
            if hasattr(self, '_turn_off_alarm'):
                self._turn_off_alarm()
            
            # Fecha a conexão com o banco de dados
            if hasattr(self, 'db'):
                self.db.close()
            
            # Fecha a conexão Modbus se existir
            if hasattr(self, 'modbus_client') and self.modbus_client:
                self.logger.debug("Fechando conexão Modbus...")
                if hasattr(self.modbus_client, 'disconnect'):
                    self.modbus_client.disconnect()
                elif hasattr(self.modbus_client, 'close'):
                    self.modbus_client.close()
            
            self.logger.info("Dashboard fechado com sucesso")
            event.accept()
            
        except Exception as e:
            error_msg = f"Erro ao fechar o dashboard: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            # Mesmo em caso de erro, aceita o evento para fechar a janela
            event.accept()

# Para teste independente
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Configuração básica para teste
    import os
    os.makedirs("config", exist_ok=True)
    
    dashboard = DashboardPage()
    dashboard.setWindowTitle("Dashboard de Teste")
    dashboard.resize(1024, 768)
    dashboard.show()
    
    sys.exit(app.exec())

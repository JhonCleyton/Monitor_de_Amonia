"""
Módulo de configurações da interface gráfica do sistema de monitoramento de amônia.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFormLayout, QLineEdit, 
                           QSpinBox, QComboBox, QCheckBox, QPushButton, QApplication,
                           QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt

from ..config import get_config_value, set_config_value, save_config

class SettingsTab(QWidget):
    """Aba de configurações do aplicativo."""
    
    def __init__(self, parent=None):
        """Inicializa a aba de configurações."""
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Configura a interface do usuário da aba de configurações."""
        layout = QVBoxLayout(self)
        
        # Título
        title = QLabel("Configurações")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Formulário de configurações
        form_layout = QFormLayout()
        
        # Configurações de conexão Modbus
        self.modbus_port = QLineEdit()
        self.modbus_port.setText(get_config_value("modbus.port", "COM3"))
        form_layout.addRow("Porta Modbus:", self.modbus_port)
        
        self.modbus_baudrate = QSpinBox()
        self.modbus_baudrate.setRange(1200, 115200)
        self.modbus_baudrate.setValue(int(get_config_value("modbus.baudrate", 9600)))
        form_layout.addRow("Taxa de transmissão (baud):", self.modbus_baudrate)
        
        # Botão para testar a conexão Modbus
        self.test_connection_btn = QPushButton("Testar Conexão")
        self.test_connection_btn.clicked.connect(self.test_modbus_connection)
        form_layout.addRow("", self.test_connection_btn)
        
        # Status da conexão
        self.connection_status = QLabel("")
        self.connection_status.setStyleSheet("color: #666; font-style: italic;")
        form_layout.addRow("Status:", self.connection_status)
        
        # Configurações de notificação
        self.notify_email = QCheckBox("Ativar notificações por e-mail")
        self.notify_email.setChecked(get_config_value("notifications.email.enabled", False))
        form_layout.addRow("", self.notify_email)
        
        self.email_recipient = QLineEdit()
        self.email_recipient.setText(get_config_value("notifications.email.recipient", ""))
        form_layout.addRow("E-mail para notificações:", self.email_recipient)
        
        # Botão de salvar
        save_btn = QPushButton("Salvar Configurações")
        save_btn.clicked.connect(self.save_settings)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignRight)
    
    def get_settings(self):
        """Retorna as configurações atuais como um dicionário.
        
        Returns:
            dict: Dicionário com as configurações atuais
        """
        return {
            "modbus": {
                "port": self.modbus_port.text(),
                "baudrate": self.modbus_baudrate.value()
            },
            "notifications": {
                "email": {
                    "enabled": self.notify_email.isChecked(),
                    "recipient": self.email_recipient.text()
                }
            }
        }
    
    def test_modbus_connection(self):
        """Testa a conexão com o dispositivo Modbus."""
        from src.modbus.modbus_client import ModbusRTUClient
        import serial.tools.list_ports
        
        port = self.modbus_port.text()
        baudrate = self.modbus_baudrate.value()
        
        # Verifica se a porta existe
        available_ports = [p.device for p in serial.tools.list_ports.comports()]
        if port not in available_ports:
            self.connection_status.setText(f"Porta {port} não encontrada")
            self.connection_status.setStyleSheet("color: red; font-style: italic;")
            return False
        
        self.connection_status.setText("Conectando...")
        self.connection_status.setStyleSheet("color: #666; font-style: italic;")
        self.test_connection_btn.setEnabled(False)
        
        # Atualiza a interface
        QApplication.processEvents()
        
        try:
            # Cria e configura o cliente Modbus
            client = ModbusRTUClient(port=port, baudrate=baudrate)
            
            # Tenta conectar
            if client.connect():
                # Tenta ler um dispositivo (endereço 1 por padrão)
                try:
                    # Tenta ler o primeiro registro do dispositivo 1
                    from src.modbus.modbus_client import RegisterType
                    result = client.read_register(1, 0, RegisterType.INPUT_REGISTER)
                    self.connection_status.setText("Conexão bem-sucedida!")
                    self.connection_status.setStyleSheet("color: green; font-style: italic;")
                    return True
                except Exception as e:
                    self.connection_status.setText("Erro ao ler dispositivo: verifique o endereço")
                    self.connection_status.setStyleSheet("color: orange; font-style: italic;")
                    return False
                finally:
                    client.disconnect()
            else:
                self.connection_status.setText("Falha na conexão: verifique os parâmetros")
                self.connection_status.setStyleSheet("color: red; font-style: italic;")
                return False
                
        except Exception as e:
            self.connection_status.setText(f"Erro: {str(e)}")
            self.connection_status.setStyleSheet("color: red; font-style: italic;")
            return False
            
        finally:
            self.test_connection_btn.setEnabled(True)
    
    def save_settings(self):
        """Salva as configurações atuais."""
        try:
            # Obtém as configurações atuais
            config = self.get_settings()
            
            # Salva as configurações no arquivo
            if save_config(config):
                # Testa a conexão Modbus ao salvar
                if self.test_modbus_connection():
                    self.connection_status.setText("Configurações salvas e conexão testada com sucesso!")
                    self.connection_status.setStyleSheet("color: green; font-style: italic;")
                
                # Emite um sinal ou mostra uma mensagem de sucesso
                if self.parent() and hasattr(self.parent(), 'show_status_message'):
                    self.parent().show_status_message("Configurações salvas com sucesso!")
                return True
            else:
                error_msg = "Erro ao salvar configurações"
                self.connection_status.setText(error_msg)
                self.connection_status.setStyleSheet("color: red; font-style: italic;")
                
                if self.parent() and hasattr(self.parent(), 'show_error_message'):
                    self.parent().show_error_message(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Erro: {str(e)}"
            self.connection_status.setText(error_msg)
            self.connection_status.setStyleSheet("color: red; font-style: italic;")
            
            if self.parent() and hasattr(self.parent(), 'show_error_message'):
                self.parent().show_error_message(error_msg)
            return False


class SettingsDialog(QDialog):
    """Janela de diálogo para configurações do sistema."""
    
    def __init__(self, parent=None):
        """Inicializa a janela de configurações."""
        super().__init__(parent)
        self.setWindowTitle("Configurações")
        self.setMinimumWidth(500)
        
        # Cria a aba de configurações
        self.settings_tab = SettingsTab(self)
        
        # Botões de OK e Cancelar
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        # Layout principal
        layout = QVBoxLayout(self)
        layout.addWidget(self.settings_tab)
        layout.addWidget(self.button_box)
    
    def get_settings(self):
        """Retorna as configurações atuais."""
        return self.settings_tab.get_settings()
    
    def accept(self):
        """Salva as configurações e fecha o diálogo."""
        if self.settings_tab.save_settings():
            super().accept()

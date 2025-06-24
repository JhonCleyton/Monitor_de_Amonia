"""
Módulo para teste de emergência do sistema de monitoramento de amônia.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt6.QtCore import Qt

from ..config import get_config_value
from ..utils.logger import get_logger

class EmergencyTestTab(QWidget):
    """Aba para teste de emergência do sistema."""
    
    def __init__(self, parent=None):
        """Inicializa a aba de teste de emergência."""
        super().__init__(parent)
        self.logger = get_logger(__name__)
        self.setup_ui()
    
    def setup_ui(self):
        """Configura a interface do usuário da aba de teste de emergência."""
        layout = QVBoxLayout(self)
        
        # Título
        title = QLabel("Teste de Emergência")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Descrição
        description = QLabel(
            "Esta ferramenta permite testar os procedimentos de emergência "
            "e notificações do sistema."
        )
        description.setWordWrap(True)
        description.setStyleSheet("margin: 10px;")
        layout.addWidget(description)
        
        # Botão de teste de alarme
        self.test_alarm_btn = QPushButton("Testar Alarme de Emergência")
        self.test_alarm_btn.setStyleSheet(
            "QPushButton { background-color: #e74c3c; color: white; font-weight: bold; padding: 10px; }"
            "QPushButton:hover { background-color: #c0392b; }"
        )
        self.test_alarm_btn.clicked.connect(self.test_emergency_alarm)
        layout.addWidget(self.test_alarm_btn)
        
        # Botão de teste de notificação
        self.test_notification_btn = QPushButton("Testar Notificação de Emergência")
        self.test_notification_btn.setStyleSheet(
            "QPushButton { background-color: #f39c12; color: white; font-weight: bold; padding: 10px; }"
            "QPushButton:hover { background-color: #d35400; }"
        )
        self.test_notification_btn.clicked.connect(self.test_emergency_notification)
        layout.addWidget(self.test_notification_btn)
        
        # Espaçador
        layout.addStretch()
    
    def test_emergency_alarm(self):
        """Testa o alarme de emergência."""
        self.logger.warning("Teste de alarme de emergência iniciado")
        
        # Aqui você pode adicionar o código para ativar o alarme sonoro/visual
        # Por enquanto, apenas mostramos uma mensagem
        QMessageBox.critical(
            self,
            "Teste de Alarme de Emergência",
            "ALERTA DE EMERGÊNCIA!\n\n"
            "Este é um teste do sistema de alarme de emergência. "
            "Em uma situação real, um alarme sonoro e visual seria ativado.",
            QMessageBox.StandardButton.Ok
        )
        
        self.logger.info("Teste de alarme de emergência concluído")
    
    def test_emergency_notification(self):
        """Testa o envio de notificações de emergência."""
        self.logger.warning("Teste de notificação de emergência iniciado")
        
        # Verifica se as notificações por e-mail estão habilitadas
        if get_config_value("notifications.email.enabled", False):
            email_recipient = get_config_value("notifications.email.recipient", "")
            if email_recipient:
                # Aqui você pode adicionar o código para enviar um e-mail de teste
                # Por enquanto, apenas mostramos uma mensagem
                QMessageBox.information(
                    self,
                    "Teste de Notificação de Emergência",
                    f"Uma notificação de emergência de teste foi enviada para:\n{email_recipient}\n\n"
                    "Verifique sua caixa de entrada (e pasta de spam) para confirmar o recebimento.",
                    QMessageBox.StandardButton.Ok
                )
            else:
                QMessageBox.warning(
                    self,
                    "Teste de Notificação de Emergência",
                    "Nenhum destinatário de e-mail configurado. "
                    "Por favor, configure um endereço de e-mail nas configurações.",
                    QMessageBox.StandardButton.Ok
                )
        else:
            QMessageBox.information(
                self,
                "Teste de Notificação de Emergência",
                "As notificações por e-mail estão desabilitadas. "
                "Habilite-as nas configurações para testar.",
                QMessageBox.StandardButton.Ok
            )
        
        self.logger.info("Teste de notificação de emergência concluído")

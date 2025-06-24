    def update_status(self, message, error=False, alert=False):
        """Atualiza a mensagem na barra de status.
        
        Args:
            message: Mensagem a ser exibida
            error: Se True, exibe como erro
            alert: Se True, exibe como alerta
        """
        from PyQt6.QtCore import QDateTime, Qt
        from PyQt6.QtWidgets import QLabel
        
        # Adiciona timestamp à mensagem
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        status_text = f"[{timestamp}] {message}"
        
        # Atualiza o log apropriado
        if error:
            self.logger.error(message)
        elif alert:
            self.logger.warning(message)
        else:
            self.logger.info(message)
        
        # Atualiza o estilo da barra de status
        if error:
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background: #fde8e8;
                    color: #e74c3c;
                    padding: 8px 15px;
                    border-top: 1px solid #f5b7b1;
                    font-size: 12px;
                    font-weight: bold;
                }
                QStatusBar::item {
                    border: none;
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
                    font-weight: 500;
                }
                QStatusBar::item {
                    border: none;
                }
            """)
        else:
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background: #ecf0f1;
                    color: #2c3e50;
                    padding: 8px 15px;
                    border-top: 1px solid #d5dbdb;
                    font-size: 12px;
                }
                QStatusBar::item {
                    border: none;
                }
            """)
        
        # Exibe a mensagem com timestamp
        self.status_bar.showMessage(status_text)
        
        # Torna o texto selecionável
        for child in self.status_bar.findChildren(QLabel):
            child.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

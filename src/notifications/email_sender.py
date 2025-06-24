"""
Módulo para envio de notificações por e-mail.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass
from pathlib import Path
import jinja2

# Configuração do logger
logger = logging.getLogger(__name__)

@dataclass
class EmailConfig:
    """Configurações do servidor de e-mail."""
    smtp_server: str = 'smtp.gmail.com'
    smtp_port: int = 587
    username: str = ''
    password: str = ''
    use_tls: bool = True
    sender_name: str = 'Monitor de Amônia'
    sender_email: str = ''

class EmailSender:
    """Classe para envio de e-mails."""
    
    def __init__(self, config: EmailConfig, template_dir: str = None):
        self.config = config
        self.template_env = None
        if template_dir:
            self._setup_jinja_environment(template_dir)
    
    def _setup_jinja_environment(self, template_dir: str):
        """Configura o ambiente de templates Jinja2."""
        template_path = Path(template_dir)
        if not template_path.exists() or not template_path.is_dir():
            logger.warning(f"Diretório de templates não encontrado: {template_dir}")
            return
            
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=True
        )
    
    def connect(self) -> Optional[smtplib.SMTP]:
        """Estabelece conexão com o servidor SMTP."""
        try:
            server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
            if self.config.use_tls:
                context = ssl.create_default_context()
                server.starttls(context=context)
            if self.config.username and self.config.password:
                server.login(self.config.username, self.config.password)
            logger.info("Conexão SMTP estabelecida com sucesso")
            return server
        except Exception as e:
            logger.error(f"Erro ao conectar ao servidor SMTP: {e}")
            return None
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        is_html: bool = False,
        cc_emails: List[str] = None,
        bcc_emails: List[str] = None
    ) -> bool:
        """Envia um e-mail."""
        if not to_emails:
            logger.warning("Nenhum destinatário especificado para o e-mail")
            return False
        
        msg = MIMEMultipart()
        msg['From'] = f"{self.config.sender_name} <{self.config.sender_email}>"
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        
        if cc_emails:
            msg['Cc'] = ', '.join(cc_emails)
        
        msg.attach(MIMEText(body, 'html' if is_html else 'plain'))
        
        server = None
        try:
            server = self.connect()
            if not server:
                return False
            
            all_recipients = to_emails.copy()
            if cc_emails:
                all_recipients.extend(cc_emails)
            if bcc_emails:
                all_recipients.extend(bcc_emails)
            
            server.send_message(msg)
            logger.info(f"E-mail enviado para {', '.join(all_recipients)}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail: {e}")
            return False
            
        finally:
            if server:
                try:
                    server.quit()
                except Exception as e:
                    logger.warning(f"Erro ao encerrar conexão SMTP: {e}")
    
    def send_template_email(
        self,
        template_name: str,
        to_emails: List[str],
        context: Dict[str, Any],
        subject: str = None,
        **kwargs
    ) -> bool:
        """Envia um e-mail usando um template."""
        if not self.template_env:
            logger.error("Ambiente de templates não configurado")
            return False
            
        try:
            template = self.template_env.get_template(template_name)
            body = template.render(**context)
            email_subject = subject or context.get('subject', 'Notificação do Sistema')
            
            return self.send_email(
                to_emails=to_emails,
                subject=email_subject,
                body=body,
                is_html=True,
                **kwargs
            )
            
        except Exception as e:
            logger.error(f"Erro ao processar template de e-mail: {e}")
            return False

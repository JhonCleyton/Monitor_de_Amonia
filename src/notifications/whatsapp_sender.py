"""
Módulo para envio de notificações por WhatsApp usando a API do Twilio.
"""

from twilio.rest import Client
from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass
import os
from pathlib import Path
import json

# Configuração do logger
logger = logging.getLogger(__name__)

@dataclass
class TwilioConfig:
    """Configurações da conta Twilio."""
    account_sid: str = ''
    auth_token: str = ''
    whatsapp_from: str = ''  # Número Twilio no formato 'whatsapp:+14155238886'

class WhatsAppSender:
    """Classe para envio de mensagens pelo WhatsApp usando Twilio."""
    
    def __init__(self, config: TwilioConfig):
        """Inicializa o cliente do Twilio."""
        self.config = config
        self.client = None
        
        if config.account_sid and config.auth_token:
            self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa o cliente Twilio."""
        try:
            self.client = Client(self.config.account_sid, self.config.auth_token)
            logger.info("Cliente Twilio inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar o cliente Twilio: {e}")
            self.client = None
    
    def send_message(
        self,
        to_number: str,
        message: str,
        media_url: str = None
    ) -> bool:
        """
        Envia uma mensagem pelo WhatsApp.
        
        Args:
            to_number: Número de telefone do destinatário no formato 'whatsapp:+5511999999999'.
            message: Mensagem de texto a ser enviada.
            media_url: URL de mídia opcional (imagem, PDF, etc.).
            
        Returns:
            True se a mensagem foi enviada com sucesso, False caso contrário.
        """
        if not self.client:
            logger.error("Cliente Twilio não inicializado")
            return False
            
        if not to_number.startswith('whatsapp:'):
            to_number = f'whatsapp:{to_number}'
            
        try:
            message_kwargs = {
                'from_': self.config.whatsapp_from,
                'body': message,
                'to': to_number
            }
            
            if media_url:
                message_kwargs['media_url'] = media_url
            
            message = self.client.messages.create(**message_kwargs)
            logger.info(f"Mensagem enviada para {to_number}. SID: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para {to_number}: {e}")
            return False
    
    def send_template_message(
        self,
        to_number: str,
        template_name: str,
        context: Dict[str, Any],
        media_url: str = None
    ) -> bool:
        """
        Envia uma mensagem usando um template.
        
        Args:
            to_number: Número de telefone do destinatário.
            template_name: Nome do template a ser usado.
            context: Dicionário com as variáveis do template.
            media_url: URL de mídia opcional.
            
        Returns:
            True se a mensagem foi enviada com sucesso, False caso contrário.
        """
        try:
            # Carrega o template
            template_path = Path(__file__).parent / 'templates' / f"{template_name}.txt"
            
            if not template_path.exists():
                logger.error(f"Template não encontrado: {template_name}")
                return False
                
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Aplica as variáveis ao template (substituição simples)
            message = template_content.format(**context)
            
            # Envia a mensagem
            return self.send_message(
                to_number=to_number,
                message=message,
                media_url=media_url
            )
            
        except Exception as e:
            logger.error(f"Erro ao processar template de mensagem: {e}")
            return False
    
    def broadcast_message(
        self,
        to_numbers: List[str],
        message: str,
        media_url: str = None
    ) -> Dict[str, bool]:
        """
        Envia uma mensagem para múltiplos números.
        
        Args:
            to_numbers: Lista de números de telefone.
            message: Mensagem a ser enviada.
            media_url: URL de mídia opcional.
            
        Returns:
            Dicionário com o status de envio para cada número.
        """
        results = {}
        for number in to_numbers:
            success = self.send_message(
                to_number=number,
                message=message,
                media_url=media_url
            )
            results[number] = success
        return results


# Exemplo de uso
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # Carrega variáveis de ambiente
    load_dotenv()
    
    # Configuração do logger
    logging.basicConfig(level=logging.INFO)
    
    # Configuração do Twilio
    config = TwilioConfig(
        account_sid=os.getenv('TWILIO_ACCOUNT_SID', ''),
        auth_token=os.getenv('TWILIO_AUTH_TOKEN', ''),
        whatsapp_from=os.getenv('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')
    )
    
    # Cria o cliente
    whatsapp = WhatsAppSender(config)
    
    # Envia uma mensagem de teste
    to_number = os.getenv('WHATSAPP_TO', 'whatsapp:+5511999999999')
    
    # Mensagem simples
    whatsapp.send_message(
        to_number=to_number,
        message="*ALERTA DE AMÔNIA*\n\nNível de amônia acima do limite permitido!\nSensor: Tanque 1\nValor: 45.2 ppm\nLimite: 40.0 ppm"
    )
    
    # Cria o diretório de templates se não existir
    template_dir = Path(__file__).parent / 'templates'
    template_dir.mkdir(exist_ok=True)
    
    # Cria um template de exemplo
    template_path = template_dir / 'alerta.txt'
    if not template_path.exists():
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write("""
            *ALERTA DE AMÔNIA*\n\n
            🚨 *ATENÇÃO* 🚨\n\n
            O sistema de monitoramento de amônia detectou um nível fora do normal.\n\n
            *Detalhes do Alerta:*\n            • *Sensor:* {sensor_name}\n
            • *Valor Atual:* {current_value} {unit}\n
            • *Limite de Alerta:* {threshold} {unit}\n
            • *Data/Hora:* {timestamp}\n\n
            *Ação Recomendada:*\n            Verificar o sistema imediatamente e tomar as devidas providências.\n\n
            _Esta é uma mensagem automática, por favor não responda._""")

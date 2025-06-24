"""
Módulo de notificações do sistema de monitoramento de amônia.

Este módulo fornece funcionalidades para envio de notificações por diversos canais,
como e-mail e WhatsApp, além de gerenciar templates e configurações de notificação.
"""

from .email_sender import EmailSender, EmailConfig
from .whatsapp_sender import WhatsAppSender, TwilioConfig

__all__ = [
    'EmailSender',
    'EmailConfig',
    'WhatsAppSender',
    'TwilioConfig'
]

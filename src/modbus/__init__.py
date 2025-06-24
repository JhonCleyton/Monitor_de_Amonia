"""
Módulo para comunicação com dispositivos Modbus RTU.

Este módulo fornece uma interface para comunicação com sensores industriais
usando o protocolo Modbus RTU através de um conversor USB-i485 Novus.
"""

from .modbus_client import (
    ModbusRTUClient,
    ModbusDeviceConfig,
    ModbusException,
    RegisterType
)

__all__ = [
    'ModbusRTUClient',
    'ModbusDeviceConfig',
    'ModbusException',
    'RegisterType'
]

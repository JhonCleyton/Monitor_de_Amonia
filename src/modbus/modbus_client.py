"""
Módulo para comunicação com sensores Modbus RTU via conversor USB-i485 Novus.
"""

import time
import minimalmodbus
import serial
from typing import List, Dict, Optional, Tuple, Union
import logging
from dataclasses import dataclass
from enum import Enum

# Configuração do logger
logger = logging.getLogger(__name__)


class ModbusException(Exception):
    """Exceção para erros específicos do Modbus."""
    pass


class RegisterType(Enum):
    """Tipos de registros Modbus suportados."""
    COIL = 1
    DISCRETE_INPUT = 2
    HOLDING_REGISTER = 3
    INPUT_REGISTER = 4


@dataclass
class ModbusDeviceConfig:
    """Configuração de um dispositivo Modbus."""
    name: str
    address: int
    register: int
    register_type: RegisterType
    unit: str = 'ppm'
    scale: float = 1.0
    offset: float = 0.0
    description: str = ''
    min_value: float = 0.0
    max_value: float = 100.0
    warning_threshold: float = 70.0
    alarm_threshold: float = 90.0


class ModbusRTUClient:
    """Cliente para comunicação com dispositivos Modbus RTU."""
    
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        """Inicializa o cliente Modbus RTU.
        
        Args:
            port: Porta serial (ex: 'COM3' no Windows, '/dev/ttyUSB0' no Linux).
            baudrate: Taxa de transmissão em bauds (padrão: 9600).
            timeout: Timeout em segundos (padrão: 1.0).
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.instrument = None
        self.connected = False
        self.devices: Dict[int, ModbusDeviceConfig] = {}
        
        # Configuração padrão do conversor USB-i485 Novus
        self.default_settings = {
            'bytesize': 8,
            'parity': serial.PARITY_NONE,
            'stopbits': 1,
            'close_port_after_each_call': False
        }
    
    def disconnect(self) -> None:
        """Fecha a conexão com o dispositivo Modbus."""
        if hasattr(self, 'instrument') and self.instrument is not None:
            try:
                if hasattr(self.instrument, 'serial') and self.instrument.serial.is_open:
                    self.instrument.serial.close()
                    logger.info("Conexão Modbus RTU encerrada")
            except Exception as e:
                logger.error(f"Erro ao fechar a conexão Modbus: {e}")
            finally:
                self.instrument = None
                self.connected = False
                
    def write_register(self, address: int, register: int, value: Union[int, bool], 
                       register_type: RegisterType = RegisterType.HOLDING_REGISTER) -> bool:
        """
        Escreve um valor em um registro Modbus.
        
        Args:
            address: Endereço do dispositivo Modbus (1-247).
            register: Número do registro a ser escrito.
            value: Valor a ser escrito (inteiro ou booleano).
            register_type: Tipo de registro (HOLDING_REGISTER ou COIL).
            
        Returns:
            bool: True se a escrita foi bem-sucedida, False caso contrário.
        """
        try:
            if not self.connected and not self.connect():
                logger.error("Não foi possível conectar ao dispositivo Modbus")
                return False
                
            # Configura o endereço do dispositivo
            self.instrument.address = address
            
            # Escreve no registro de acordo com o tipo
            if register_type == RegisterType.HOLDING_REGISTER:
                if not isinstance(value, int):
                    raise ValueError("O valor para HOLDING_REGISTER deve ser um inteiro")
                self.instrument.write_register(register, value, functioncode=6)
                logger.info(f"Escrito valor {value} no registro de holding {register} do dispositivo {address}")
                
            elif register_type == RegisterType.COIL:
                if not isinstance(value, bool):
                    raise ValueError("O valor para COIL deve ser um booleano")
                self.instrument.write_bit(register, value, functioncode=5)
                logger.info(f"Escrito valor {value} na bobina {register} do dispositivo {address}")
                
            else:
                raise ValueError(f"Tipo de registro não suportado para escrita: {register_type}")
                
            return True
            
        except Exception as e:
            logger.error(f"Erro ao escrever no registro {register} do dispositivo {address}: {str(e)}")
            self.connected = False
            return False

    def connect(self) -> bool:
        """Estabelece conexão com o conversor Modbus.
        
        Returns:
            bool: True se a conexão foi bem-sucedida, False caso contrário.
        """
        if self.connected and self.instrument is not None:
            return True
            
        try:
            logger.info(f"Tentando conectar à porta {self.port} @ {self.baudrate} baud")
            
            # Fecha a conexão existente se houver
            self.disconnect()
            
            # Cria o instrumento com configuração básica
            self.instrument = minimalmodbus.Instrument(
                port=self.port,
                slaveaddress=1,  # Endereço temporário para teste
                mode=minimalmodbus.MODE_RTU,
                close_port_after_each_call=self.default_settings['close_port_after_each_call']
            )
            
            # Configurações da porta serial
            self.instrument.serial.baudrate = self.baudrate
            self.instrument.serial.timeout = 1.0  # Timeout reduzido para testes
            self.instrument.serial.bytesize = self.default_settings['bytesize']
            self.instrument.serial.parity = self.default_settings['parity']
            self.instrument.serial.stopbits = self.default_settings['stopbits']
            
            # Tenta ler um registro para testar a conexão em diferentes endereços
            test_addresses = [1, 2, 3, 4, 5]  # Endereços comuns para teste
            
            for addr in test_addresses:
                try:
                    self.instrument.address = addr
                    logger.debug(f"Testando conexão com endereço {addr}...")
                    self.instrument.read_register(0, functioncode=4)
                    logger.info(f"Conexão bem-sucedida com o dispositivo no endereço {addr}")
                    self.connected = True
                    return True
                except Exception as e:
                    logger.debug(f"Falha ao conectar no endereço {addr}: {str(e)}")
                    continue
            
            # Se nenhum endereço respondeu, tenta continuar mesmo assim
            logger.warning("Nenhum dispositivo respondeu, mas continuando...")
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"Erro ao conectar ao dispositivo Modbus em {self.port}: {e}", exc_info=True)
            self.connected = False
            return False
    
    def disconnect(self):
        """Fecha a conexão com o dispositivo Modbus."""
        if self.instrument and hasattr(self.instrument.serial, 'close'):
            self.instrument.serial.close()
            self.connected = False
            logger.info("Conexão Modbus RTU encerrada")
    
    def add_device(self, device: ModbusDeviceConfig):
        """Adiciona um dispositivo à lista de dispositivos gerenciados.
        
        Args:
            device: Configuração do dispositivo Modbus.
        """
        self.devices[device.address] = device
        logger.debug(f"Dispositivo adicionado: {device.name} (endereço: {device.address})")
    
    def read_register(self, address: int, register: int, register_type: RegisterType, **kwargs) -> Optional[float]:
        """Lê um registro Modbus.
        
        Args:
            address: Endereço do dispositivo escravo.
            register: Número do registro a ser lido.
            register_type: Tipo de registro (INPUT_REGISTER, HOLDING_REGISTER, COIL, DISCRETE_INPUT).
            **kwargs: Argumentos adicionais para a leitura.
            
        Returns:
            O valor lido ou None em caso de erro.
        """
        if not self.connected or self.instrument is None:
            logger.warning("Tentando reconectar ao dispositivo Modbus...")
            if not self.connect():
                logger.error("Não foi possível reconectar ao dispositivo Modbus")
                return None
        
        if not isinstance(register_type, RegisterType):
            register_type = RegisterType(register_type)
            
        self.instrument.address = address
        
        try:
            # Salva o timeout atual
            original_timeout = self.instrument.serial.timeout
            self.instrument.serial.timeout = 1.0  # Timeout reduzido para leitura
            
            # Garante que o parâmetro de decimais está no formato correto
            if 'numberOfDecimals' in kwargs:
                kwargs['number_of_decimals'] = kwargs.pop('numberOfDecimals')
            
            if register_type == RegisterType.COIL:
                value = self.instrument.read_bit(register, functioncode=1)
            elif register_type == RegisterType.DISCRETE_INPUT:
                value = self.instrument.read_bit(register, functioncode=2)
            elif register_type in (RegisterType.HOLDING_REGISTER, RegisterType.INPUT_REGISTER):
                functioncode = 3 if register_type == RegisterType.HOLDING_REGISTER else 4
                value = self.instrument.read_register(register, functioncode=functioncode, **kwargs)
            else:
                logger.error(f"Tipo de registro inválido: {register_type}")
                
            # Se chegou até aqui, a leitura foi bem-sucedida
            return float(value)
            
        except minimalmodbus.NoResponseError as e:
            logger.error(f"Sem resposta do dispositivo {address} (registro {register}): {str(e)}")
            self.connected = False
            return None
            
        except minimalmodbus.InvalidResponseError as e:
            logger.error(f"Resposta inválida do dispositivo {address} (registro {register}): {str(e)}")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao ler registro {register} do dispositivo {address}: {str(e)}")
            self.connected = False
            return None
            
        finally:
            # Restaura o timeout original
            if hasattr(self, 'instrument') and hasattr(self.instrument, 'serial'):
                self.instrument.serial.timeout = original_timeout
                
    
    def read_device(self, device: ModbusDeviceConfig) -> Optional[float]:
        """Lê o valor de um dispositivo específico.
        
        Args:
            device: Configuração do dispositivo a ser lido.
            
        Returns:
            Valor lido (já aplicados scale e offset) ou None em caso de erro.
        """
        try:
            if not hasattr(device, 'register_type') or device.register_type is None:
                logger.error(f"Dispositivo {device.name} não tem um register_type definido")
                return None
                
            logger.debug(f"Lendo dispositivo {device.name} (endereço: {device.address}, "
                         f"registro: {device.register}, tipo: {getattr(device.register_type, 'name', 'N/A')})")
            
            # Prepara os argumentos para a leitura do registro
            read_kwargs = {}
            
            # Adiciona o número de casas decimais apenas para registros de entrada e holding
            if hasattr(device, 'register_type') and device.register_type in (RegisterType.INPUT_REGISTER, RegisterType.HOLDING_REGISTER):
                read_kwargs['number_of_decimals'] = 2
            
            # Lê o valor bruto do registro
            raw_value = self.read_register(
                address=getattr(device, 'address', 1),
                register=getattr(device, 'register', 0),
                register_type=device.register_type,
                **read_kwargs
            )
            
            if raw_value is not None:
                try:
                    # Aplica escala e offset
                    scaled_value = (float(raw_value) * float(device.scale)) + float(device.offset)
                    rounded_value = round(scaled_value, 2)
                    
                    # Verifica se o valor está dentro dos limites esperados
                    if hasattr(device, 'min_value') and hasattr(device, 'max_value'):
                        if not (device.min_value <= rounded_value <= device.max_value):
                            logger.warning(
                                f"Valor fora dos limites esperados para {device.name}: "
                                f"{rounded_value} {device.unit} (mín: {device.min_value}, máx: {device.max_value})"
                            )
                    
                    logger.debug(f"Valor processado para {device.name}: {rounded_value} {device.unit}")
                    return rounded_value
                    
                except (ValueError, TypeError) as e:
                    logger.error(f"Erro ao processar valor do dispositivo {device.name}: {str(e)}", exc_info=True)
                    return None
                except Exception as e:
                    logger.error(f"Erro inesperado ao processar valor do dispositivo {device.name}: {str(e)}", exc_info=True)
                    return None
            else:
                logger.warning(f"Falha ao ler valor do dispositivo {device.name} (endereço: {device.address}, registro: {device.register})")
                return None
                
        except Exception as e:
            logger.error(f"Erro inesperado ao ler dispositivo {getattr(device, 'name', 'desconhecido')}: {str(e)}", exc_info=True)
            return None
    
    def read_all_devices(self) -> Dict[int, Dict[str, Union[float, str, None]]]:
        """Lê todos os dispositivos registrados.
        
        Returns:
            Dicionário com os valores lidos de todos os dispositivos.
        """
        results = {}
        
        for addr, device in self.devices.items():
            value = self.read_device(device)
            results[addr] = {
                'name': device.name,
                'value': value,
                'unit': device.unit,
                'status': self._get_status(device, value) if value is not None else 'erro',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        
        return results
    
    def write_register(self, address: int, register: int, value: int, register_type: RegisterType = RegisterType.HOLDING_REGISTER) -> bool:
        """Escreve um valor em um registro Modbus.
        
        Args:
            address: Endereço do dispositivo escravo.
            register: Número do registro a ser escrito.
            value: Valor a ser escrito.
            register_type: Tipo de registro (HOLDING_REGISTER ou COIL).
            
        Returns:
            bool: True se a escrita foi bem-sucedida, False caso contrário.
        """
        if not self.connected or self.instrument is None:
            logger.warning("Tentando reconectar ao dispositivo Modbus...")
            if not self.connect():
                logger.error("Não foi possível reconectar ao dispositivo Modbus")
                return False
        
        if not isinstance(register_type, RegisterType):
            register_type = RegisterType(register_type)
            
        self.instrument.address = address
        
        try:
            # Salva o timeout atual
            original_timeout = self.instrument.serial.timeout
            self.instrument.serial.timeout = 1.0  # Timeout reduzido para escrita
            
            if register_type == RegisterType.COIL:
                # Para coils, o valor deve ser True/False ou 0/1
                self.instrument.write_bit(register, bool(value), functioncode=5)
            elif register_type == RegisterType.HOLDING_REGISTER:
                # Para registros de holding, o valor é um inteiro
                self.instrument.write_register(register, int(value), functioncode=6)
            else:
                logger.error(f"Tipo de registro não suportado para escrita: {register_type}")
                return False
                
            logger.debug(f"Escrita bem-sucedida no endereço {address}, registro {register}: {value}")
            return True
            
        except minimalmodbus.NoResponseError as e:
            logger.error(f"Sem resposta do dispositivo {address} (registro {register}): {str(e)}")
            self.connected = False
            return False
            
        except minimalmodbus.InvalidResponseError as e:
            logger.error(f"Resposta inválida do dispositivo {address} (registro {register}): {str(e)}")
            return False
            
        except Exception as e:
            logger.error(f"Erro ao escrever no registro {register} do dispositivo {address}: {str(e)}")
            self.connected = False
            return False
            
        finally:
            # Restaura o timeout original
            if hasattr(self, 'instrument') and hasattr(self.instrument, 'serial'):
                self.instrument.serial.timeout = original_timeout
                
    def _get_status(self, device: ModbusDeviceConfig, value: float) -> str:
        """Determina o status com base no valor lido e nos limiares.
        
        Args:
            device: Configuração do dispositivo.
            value: Valor lido.
            
        Returns:
            Status: 'normal', 'alerta' ou 'alarme'.
        """
        if value >= device.alarm_threshold:
            return 'alarme'
        elif value >= device.warning_threshold:
            return 'alerta'
        return 'normal'
    
    def scan_devices(self, start_address: int = 1, end_address: int = 10) -> List[int]:
        """Varre a rede em busca de dispositivos Modbus.
        
        Args:
            start_address: Endereço inicial da varredura (padrão: 1).
            end_address: Endereço final da varredura (padrão: 10).
            
        Returns:
            Lista de endereços de dispositivos encontrados.
            
        Raises:
            ModbusException: Se ocorrer um erro durante a varredura.
        """
        if not self.connected:
            error_msg = "Não é possível varrer dispositivos: cliente Modbus não conectado"
            logger.error(error_msg)
            raise ModbusException(error_msg)
        
        if not (1 <= start_address <= 247):
            error_msg = f"Endereço inicial inválido: {start_address}. Deve estar entre 1 e 247."
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not (1 <= end_address <= 247):
            error_msg = f"Endereço final inválido: {end_address}. Deve estar entre 1 e 247."
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if start_address > end_address:
            error_msg = f"Endereço inicial ({start_address}) deve ser menor ou igual ao endereço final ({end_address})"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        found_devices = []
        original_timeout = self.instrument.serial.timeout
        
        try:
            # Configura um timeout mais curto para a varredura
            self.instrument.serial.timeout = 0.2  # 200ms por tentativa
            
            logger.info(f"Iniciando varredura de dispositivos Modbus (endereços {start_address} a {end_address})...")
            
            for addr in range(start_address, end_address + 1):
                try:
                    # Tenta ler um registro (endereço 0, função 4 - Input Register)
                    self.instrument.address = addr
                    logger.debug(f"Verificando endereço {addr}...")
                    
                    # Tenta ler o registro 0 (input register)
                    value = self.instrument.read_register(0, functioncode=4)
                    
                    # Se chegou aqui, o dispositivo respondeu
                    found_devices.append(addr)
                    logger.info(f"Dispositivo encontrado no endereço {addr} (valor lido: {value})")
                    
                except minimalmodbus.NoResponseError:
                    # Nenhuma resposta do dispositivo, continua para o próximo
                    continue
                    
                except minimalmodbus.InvalidResponseError as e:
                    # Resposta inválida, mas pode ser um dispositivo Modbus com formato diferente
                    logger.warning(f"Resposta inválida do endereço {addr}: {str(e)}")
                    found_devices.append(addr)
                    
                except Exception as e:
                    logger.warning(f"Erro ao verificar endereço {addr}: {str(e)}")
                    continue
            
            logger.info(f"Varredura concluída. {len(found_devices)} dispositivos encontrados.")
            return found_devices
            
        except Exception as e:
            error_msg = f"Erro durante a varredura de dispositivos: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ModbusException(error_msg) from e
            
        finally:
            # Restaura o timeout original
            self.instrument.serial.timeout = original_timeout


# Exemplo de uso
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Configuração do cliente
    PORT = 'COM3'  # Ajustar para a porta correta
    client = ModbusRTUClient(port=PORT, baudrate=9600)
    
    try:
        if client.connect():
            # Exemplo: adicionar sensores
            sensor1 = ModbusDeviceConfig(
                name="Sensor 1",
                address=1,
                register=0,
                register_type=RegisterType.INPUT_REGISTER,
                unit='ppm',
                scale=0.1,
                offset=0.0,
                min_value=0.0,
                max_value=100.0,
                warning_threshold=70.0,
                alarm_threshold=90.0
            )
            
            client.add_device(sensor1)
            
            # Ler todos os sensores
            while True:
                try:
                    readings = client.read_all_devices()
                    for addr, data in readings.items():
                        print(f"{data['name']}: {data['value']} {data['unit']} [{data['status']}]")
                    time.sleep(1)
                except KeyboardInterrupt:
                    break
                    
    finally:
        client.disconnect()

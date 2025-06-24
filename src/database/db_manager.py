"""
Módulo de gerenciamento do banco de dados SQLite para o Sistema de Monitoramento de Amônia.
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path

# Configuração do logger
logger = logging.getLogger(__name__)

# Caminho para o banco de dados
DB_FILENAME = "monitor_amonia.db"
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', DB_FILENAME)

# Garante que o diretório de dados existe
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Versão do esquema do banco de dados
SCHEMA_VERSION = 1

class DatabaseManager:
    """Classe para gerenciar o banco de dados SQLite."""
    
    def __init__(self, db_path: str = None):
        """Inicializa o gerenciador do banco de dados.
        
        Args:
            db_path: Caminho para o arquivo do banco de dados. Se None, usa o caminho padrão.
        """
        self.db_path = db_path or DB_PATH
        self.conn = None
        self.cursor = None
        self._connect()
        self._initialize_database()
    
    def _connect(self):
        """Estabelece conexão com o banco de dados."""
        try:
            # Cria o diretório do banco de dados se não existir
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Conecta ao banco de dados
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Permite acesso aos campos por nome
            self.cursor = self.conn.cursor()
            
            # Ativa chaves estrangeiras
            self.cursor.execute("PRAGMA foreign_keys = ON")
            
            # Otimizações de desempenho
            self.cursor.execute("PRAGMA journal_mode = WAL")  # Melhora a concorrência
            self.cursor.execute("PRAGMA synchronous = NORMAL")  # Bom equilíbrio entre segurança e desempenho
            
            logger.info(f"Conectado ao banco de dados: {self.db_path}")
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao conectar ao banco de dados: {e}")
            raise
    
    def _initialize_database(self):
        """Inicializa o banco de dados com as tabelas necessárias."""
        try:
            # Tabela de metadados para controle de versão
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            
            # Verifica a versão do esquema
            self.cursor.execute("SELECT value FROM metadata WHERE key = 'schema_version'")
            result = self.cursor.fetchone()
            
            if result is None:
                # Banco de dados novo, cria todas as tabelas
                self._create_tables()
                self._update_schema_version(SCHEMA_VERSION)
            else:
                # Banco de dados existente, verifica se precisa de atualização
                current_version = int(result['value'])
                if current_version < SCHEMA_VERSION:
                    self._upgrade_database(current_version, SCHEMA_VERSION)
            
            self.conn.commit()
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao inicializar o banco de dados: {e}")
            self.conn.rollback()
            raise
    
    def _create_tables(self):
        """Cria as tabelas do banco de dados."""
        try:
            # Tabela de sensores
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS sensors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    address INTEGER NOT NULL,
                    unit TEXT NOT NULL,
                    min_value REAL NOT NULL,
                    max_value REAL NOT NULL,
                    warning_threshold REAL NOT NULL,
                    alarm_threshold REAL NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(address)
                )
            """)
            
            # Tabela de leituras dos sensores
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_id INTEGER NOT NULL,
                    value REAL NOT NULL,
                    status TEXT NOT NULL,  -- 'normal', 'warning', 'alarm', 'error'
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sensor_id) REFERENCES sensors (id) ON DELETE CASCADE
                )
            """)
            
            # Tabela de alertas
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_id INTEGER,
                    alert_type TEXT NOT NULL,  -- 'warning', 'alarm', 'error', 'recovery'
                    message TEXT NOT NULL,
                    value REAL,
                    threshold REAL,
                    acknowledged BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    acknowledged_at TIMESTAMP,
                    acknowledged_by TEXT,
                    FOREIGN KEY (sensor_id) REFERENCES sensors (id) ON DELETE SET NULL
                )
            """)
            
            # Tabela de notificações
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id INTEGER,
                    notification_type TEXT NOT NULL,  -- 'email', 'whatsapp', 'sms', 'sound', 'popup'
                    status TEXT NOT NULL,  -- 'pending', 'sent', 'failed'
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP,
                    FOREIGN KEY (alert_id) REFERENCES alerts (id) ON DELETE CASCADE
                )
            """)
            
            # Tabela de configurações
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Cria índices para melhorar o desempenho
            self._create_indexes()
            
            # Insere configurações padrão
            self._insert_default_settings()
            
            # Insere sensores padrão
            self._insert_default_sensors()
            
            logger.info("Tabelas do banco de dados criadas com sucesso")
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao criar tabelas: {e}")
            raise
    
    def _create_indexes(self):
        """Cria índices para melhorar o desempenho das consultas."""
        try:
            # Índices para a tabela sensor_readings
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sensor_readings_sensor_id 
                ON sensor_readings(sensor_id)
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sensor_readings_timestamp 
                ON sensor_readings(timestamp)
            """)
            
            # Índices para a tabela alerts
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_sensor_id 
                ON alerts(sensor_id)
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_created_at 
                ON alerts(created_at)
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged 
                ON alerts(acknowledged)
            """)
            
            # Índices para a tabela notifications
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_alert_id 
                ON notifications(alert_id)
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_created_at 
                ON notifications(created_at)
            """)
            
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_status 
                ON notifications(status)
            """)
            
            logger.info("Índices criados com sucesso")
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao criar índices: {e}")
            raise
    
    def _insert_default_settings(self):
        """Insere as configurações padrão no banco de dados."""
        try:
            # Verifica se já existem configurações
            self.cursor.execute("SELECT COUNT(*) as count FROM settings")
            if self.cursor.fetchone()['count'] > 0:
                return
            
            # Configurações padrão
            default_settings = [
                ('app_name', 'Monitor de Amônia', 'Nome da aplicação'),
                ('app_version', '1.0.0', 'Versão da aplicação'),
                ('data_retention_days', '30', 'Dias de retenção de dados'),
                ('modbus_port', 'COM3', 'Porta serial do conversor USB-RS485'),
                ('modbus_baudrate', '9600', 'Taxa de transmissão do Modbus'),
                ('modbus_timeout', '1.0', 'Tempo limite de resposta do Modbus (segundos)'),
                ('modbus_retries', '3', 'Número de tentativas de leitura'),
                ('smtp_server', '', 'Servidor SMTP para envio de e-mails'),
                ('smtp_port', '587', 'Porta do servidor SMTP'),
                ('smtp_username', '', 'Usuário do servidor SMTP'),
                ('smtp_password', '', 'Senha do servidor SMTP'),
                ('smtp_from', '', 'E-mail remetente'),
                ('smtp_to', '', 'E-mails destinatários (separados por vírgula)'),
                ('twilio_account_sid', '', 'SID da conta Twilio'),
                ('twilio_auth_token', '', 'Token de autenticação Twilio'),
                ('twilio_from_number', '', 'Número de telefone Twilio'),
                ('notification_phone_numbers', '', 'Números de telefone para notificação (separados por vírgula)'),
                ('enable_email_notifications', '0', 'Habilitar notificações por e-mail (0/1)'),
                ('enable_sms_notifications', '0', 'Habilitar notificações por SMS (0/1)'),
                ('enable_whatsapp_notifications', '0', 'Habilitar notificações por WhatsApp (0/1)'),
                ('enable_sound_notifications', '1', 'Habilitar notificações sonoras (0/1)'),
                ('enable_popup_notifications', '1', 'Habilitar notificações popup (0/1)'),
                ('check_interval', '60', 'Intervalo de verificação dos sensores (segundos)'),
                ('alert_cooldown', '300', 'Tempo mínimo entre alertas do mesmo tipo (segundos)'),
                ('theme', 'dark', 'Tema da interface (dark/light)'),
                ('language', 'pt_BR', 'Idioma da interface')
            ]
            
            # Insere as configurações
            self.cursor.executemany(
                """
                INSERT INTO settings (key, value, description)
                VALUES (?, ?, ?)
                """,
                default_settings
            )
            
            logger.info("Configurações padrão inseridas com sucesso")
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao inserir configurações padrão: {e}")
            raise
    
    def _insert_default_sensors(self):
        """Insere sensores padrão no banco de dados."""
        try:
            # Verifica se já existem sensores
            self.cursor.execute("SELECT COUNT(*) as count FROM sensors")
            if self.cursor.fetchone()['count'] > 0:
                return
            
            # Sensores padrão (10 sensores)
            default_sensors = [
                (f"Sensor {i+1}", i+1, "ppm", 0.0, 100.0, 25.0, 50.0, 1)
                for i in range(10)
            ]
            
            # Insere os sensores
            self.cursor.executemany(
                """
                INSERT INTO sensors (
                    name, address, unit, min_value, max_value, 
                    warning_threshold, alarm_threshold, enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                default_sensors
            )
            
            logger.info("Sensores padrão inseridos com sucesso")
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao inserir sensores padrão: {e}")
            raise
    
    def _upgrade_database(self, current_version: int, target_version: int):
        """Atualiza o esquema do banco de dados.
        
        Args:
            current_version: Versão atual do esquema.
            target_version: Versão alvo do esquema.
        """
        logger.info(f"Atualizando banco de dados da versão {current_version} para {target_version}")
        
        try:
            # Atualizações incrementais baseadas na versão
            if current_version < 1:
                # Atualizações para a versão 1 (já aplicadas na criação inicial)
                pass
                
            # Adicione mais atualizações conforme necessário para versões futuras
            # elif current_version < 2:
            #     # Atualizações para a versão 2
            #     pass
            
            # Atualiza a versão do esquema
            self._update_schema_version(target_version)
            
            logger.info("Banco de dados atualizado com sucesso")
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao atualizar o banco de dados: {e}")
            raise
    
    def _update_schema_version(self, version: int):
        """Atualiza a versão do esquema no banco de dados.
        
        Args:
            version: Número da versão do esquema.
        """
        self.cursor.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ('schema_version', str(version))
        )
    
    def close(self):
        """Fecha a conexão com o banco de dados."""
        if self.conn:
            self.conn.close()
            logger.info("Conexão com o banco de dados fechada")
    
    def __enter__(self):
        """Suporte para gerenciador de contexto."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Garante que a conexão seja fechada ao sair do contexto."""
        self.close()
    
    # ===== MÉTODOS PARA ALERTAS =====
    
    def add_alert(
        self,
        sensor_id: Optional[int],
        alert_type: str,
        message: str,
        value: Optional[float] = None,
        threshold: Optional[float] = None
    ) -> Optional[int]:
        """Adiciona um novo alerta ao banco de dados.
        
        Args:
            sensor_id: ID do sensor relacionado (opcional).
            alert_type: Tipo do alerta ('warning', 'alarm', 'error', 'recovery').
            message: Mensagem descritiva do alerta.
            value: Valor que disparou o alerta (opcional).
            threshold: Limite que foi ultrapassado (opcional).
            
        Returns:
            ID do alerta criado ou None em caso de erro.
        """
        try:
            self.cursor.execute(
                """
                INSERT INTO alerts (
                    sensor_id, alert_type, message, value, threshold
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (sensor_id, alert_type, message, value, threshold)
            )
            
            alert_id = self.cursor.lastrowid
            self.conn.commit()
            logger.info(f"Alerta {alert_id} adicionado: {message}")
            return alert_id
            
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Erro ao adicionar alerta: {e}")
            return None
    
    def get_alerts(
        self,
        sensor_id: Optional[int] = None,
        alert_type: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Obtém alertas com base nos filtros fornecidos.
        
        Args:
            sensor_id: ID do sensor (opcional).
            alert_type: Tipo de alerta (opcional).
            acknowledged: Se o alerta foi reconhecido (opcional).
            start_time: Data/hora de início (opcional).
            end_time: Data/hora de fim (opcional).
            limit: Número máximo de alertas a retornar.
            
        Returns:
            Lista de dicionários com os alertas.
        """
        try:
            query = """
                SELECT a.*, s.name as sensor_name, s.unit
                FROM alerts a
                LEFT JOIN sensors s ON a.sensor_id = s.id
                WHERE 1=1
            """
            
            params = []
            
            if sensor_id is not None:
                query += " AND a.sensor_id = ?"
                params.append(sensor_id)
                
            if alert_type is not None:
                query += " AND a.alert_type = ?"
                params.append(alert_type)
                
            if acknowledged is not None:
                query += " AND a.acknowledged = ?"
                params.append(1 if acknowledged else 0)
                
            if start_time is not None:
                query += " AND a.created_at >= ?"
                params.append(start_time)
                
            if end_time is not None:
                query += " AND a.created_at <= ?"
                params.append(end_time)
            
            query += " ORDER BY a.created_at DESC"
            
            if limit > 0:
                query += " LIMIT ?"
                params.append(limit)
            
            self.cursor.execute(query, params)
            return [dict(row) for row in self.cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao obter alertas: {e}")
            return []
    
    def get_alert(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """Obtém um alerta pelo seu ID.
        
        Args:
            alert_id: ID do alerta.
            
        Returns:
            Dicionário com os dados do alerta ou None se não encontrado.
        """
        try:
            self.cursor.execute(
                """
                SELECT a.*, s.name as sensor_name, s.unit
                FROM alerts a
                LEFT JOIN sensors s ON a.sensor_id = s.id
                WHERE a.id = ?
                """,
                (alert_id,)
            )
            
            row = self.cursor.fetchone()
            return dict(row) if row else None
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao obter alerta {alert_id}: {e}")
            return None
    
    def acknowledge_alert(self, alert_id: int, acknowledged_by: str = None) -> bool:
        """Marca um alerta como reconhecido.
        
        Args:
            alert_id: ID do alerta.
            acknowledged_by: Nome do usuário que reconheceu o alerta (opcional).
            
        Returns:
            True se o alerta foi atualizado com sucesso, False caso contrário.
        """
        try:
            self.cursor.execute(
                """
                UPDATE alerts 
                SET acknowledged = 1, 
                    acknowledged_at = CURRENT_TIMESTAMP,
                    acknowledged_by = ?
                WHERE id = ? AND acknowledged = 0
                """,
                (acknowledged_by, alert_id)
            )
            
            if self.cursor.rowcount == 0:
                logger.warning(f"Alerta {alert_id} não encontrado ou já reconhecido")
                return False
                
            self.conn.commit()
            logger.info(f"Alerta {alert_id} reconhecido por {acknowledged_by or 'sistema'}")
            return True
            
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Erro ao reconhecer alerta {alert_id}: {e}")
            return False
    
    def get_unacknowledged_alerts_count(self) -> int:
        """Obtém o número de alertas não reconhecidos.
        
        Returns:
            Número de alertas não reconhecidos.
        """
        try:
            self.cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE acknowledged = 0")
            result = self.cursor.fetchone()
            return result['count'] if result else 0
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao contar alertas não reconhecidos: {e}")
            return 0
    
    # ===== MÉTODOS PARA NOTIFICAÇÕES =====
    
    def add_notification(
        self,
        alert_id: int,
        notification_type: str,
        status: str = 'pending',
        error_message: Optional[str] = None
    ) -> Optional[int]:
        """Adiciona um registro de notificação.
        
        Args:
            alert_id: ID do alerta relacionado.
            notification_type: Tipo de notificação ('email', 'whatsapp', 'sms', 'sound', 'popup').
            status: Status da notificação ('pending', 'sent', 'failed').
            error_message: Mensagem de erro, se aplicável.
            
        Returns:
            ID da notificação criada ou None em caso de erro.
        """
        try:
            self.cursor.execute(
                """
                INSERT INTO notifications (
                    alert_id, notification_type, status, error_message
                ) VALUES (?, ?, ?, ?)
                """,
                (alert_id, notification_type, status, error_message)
            )
            
            notification_id = self.cursor.lastrowid
            
            if status == 'sent':
                self.cursor.execute(
                    """
                    UPDATE notifications 
                    SET sent_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                    """,
                    (notification_id,)
                )
            
            self.conn.commit()
            logger.debug(f"Notificação {notification_id} adicionada para alerta {alert_id}")
            return notification_id
            
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Erro ao adicionar notificação para alerta {alert_id}: {e}")
            return None
    
    def update_notification(
        self,
        notification_id: int,
        status: str = None,
        error_message: str = None,
        sent: bool = None
    ) -> bool:
        """Atualiza o status de uma notificação.
        
        Args:
            notification_id: ID da notificação.
            status: Novo status da notificação (opcional).
            error_message: Nova mensagem de erro (opcional).
            sent: Se a notificação foi enviada (define sent_at).
            
        Returns:
            True se a atualização foi bem-sucedida, False caso contrário.
        """
        if status is None and error_message is None and sent is None:
            return False
            
        try:
            updates = []
            params = []
            
            if status is not None:
                updates.append("status = ?")
                params.append(status)
                
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)
                
            if sent is not None:
                updates.append("sent_at = ?")
                params.append(datetime.now() if sent else None)
            
            query = f"UPDATE notifications SET {', '.join(updates)} WHERE id = ?"
            params.append(notification_id)
            
            self.cursor.execute(query, params)
            
            if self.cursor.rowcount == 0:
                logger.warning(f"Notificação {notification_id} não encontrada para atualização")
                return False
                
            self.conn.commit()
            logger.debug(f"Notificação {notification_id} atualizada: status={status}, sent={sent}")
            return True
            
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Erro ao atualizar notificação {notification_id}: {e}")
            return False
    
    def get_notifications(
        self,
        alert_id: Optional[int] = None,
        notification_type: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Obtém notificações com base nos filtros fornecidos.
        
        Args:
            alert_id: ID do alerta relacionado (opcional).
            notification_type: Tipo de notificação (opcional).
            status: Status da notificação (opcional).
            start_time: Data/hora de início (opcional).
            end_time: Data/hora de fim (opcional).
            limit: Número máximo de notificações a retornar.
            
        Returns:
            Lista de dicionários com as notificações.
        """
        try:
            query = """
                SELECT n.*, a.alert_type, a.message, a.sensor_id, s.name as sensor_name
                FROM notifications n
                LEFT JOIN alerts a ON n.alert_id = a.id
                LEFT JOIN sensors s ON a.sensor_id = s.id
                WHERE 1=1
            """
            
            params = []
            
            if alert_id is not None:
                query += " AND n.alert_id = ?"
                params.append(alert_id)
                
            if notification_type is not None:
                query += " AND n.notification_type = ?"
                params.append(notification_type)
                
            if status is not None:
                query += " AND n.status = ?"
                params.append(status)
                
            if start_time is not None:
                query += " AND n.created_at >= ?"
                params.append(start_time)
                
            if end_time is not None:
                query += " AND n.created_at <= ?"
                params.append(end_time)
            
            query += " ORDER BY n.created_at DESC"
            
            if limit > 0:
                query += " LIMIT ?"
                params.append(limit)
            
            self.cursor.execute(query, params)
            return [dict(row) for row in self.cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao obter notificações: {e}")
            return []
    
    def get_pending_notifications(self, notification_type: str = None) -> List[Dict[str, Any]]:
        """Obtém notificações pendentes.
        
        Args:
            notification_type: Tipo de notificação (opcional).
            
        Returns:
            Lista de dicionários com as notificações pendentes.
        """
        return self.get_notifications(
            status='pending',
            notification_type=notification_type,
            limit=0  # Sem limite para notificações pendentes
        )
    
    # ===== MÉTODOS PARA CONFIGURAÇÕES =====
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Obtém o valor de uma configuração.
        
        Args:
            key: Chave da configuração.
            default: Valor padrão a retornar se a chave não existir.
            
        Returns:
            Valor da configuração ou o valor padrão.
        """
        try:
            self.cursor.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,)
            )
            
            result = self.cursor.fetchone()
            return result['value'] if result else default
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao obter configuração '{key}': {e}")
            return default
    
    def get_settings(self) -> Dict[str, str]:
        """Obtém todas as configurações.
        
        Returns:
            Dicionário com todas as configurações.
        """
        try:
            self.cursor.execute("SELECT key, value FROM settings")
            return {row['key']: row['value'] for row in self.cursor.fetchall()}
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao obter configurações: {e}")
            return {}
    
    def set_setting(self, key: str, value: Any, description: str = None) -> bool:
        """Define o valor de uma configuração.
        
        Args:
            key: Chave da configuração.
            value: Valor a ser definido.
            description: Descrição da configuração (opcional, apenas na criação).
            
        Returns:
            True se a operação foi bem-sucedida, False caso contrário.
        """
        try:
            # Converte o valor para string, se não for None
            str_value = str(value) if value is not None else None
            
            # Verifica se a chave já existe
            self.cursor.execute("SELECT 1 FROM settings WHERE key = ?", (key,))
            exists = self.cursor.fetchone() is not None
            
            if exists:
                # Atualiza a configuração existente
                if description is not None:
                    self.cursor.execute(
                        """
                        UPDATE settings 
                        SET value = ?, description = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE key = ?
                        """,
                        (str_value, description, key)
                    )
                else:
                    self.cursor.execute(
                        """
                        UPDATE settings 
                        SET value = ?, updated_at = CURRENT_TIMESTAMP 
                        WHERE key = ?
                        """,
                        (str_value, key)
                    )
            else:
                # Insere uma nova configuração
                if description is None:
                    description = f"Configuração {key}"
                    
                self.cursor.execute(
                    """
                    INSERT INTO settings (key, value, description)
                    VALUES (?, ?, ?)
                    """,
                    (key, str_value, description)
                )
            
            self.conn.commit()
            logger.debug(f"Configuração '{key}' atualizada para: {value}")
            return True
            
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Erro ao definir configuração '{key}': {e}")
            return False
    
    def delete_setting(self, key: str) -> bool:
        """Remove uma configuração.
        
        Args:
            key: Chave da configuração a ser removida.
            
        Returns:
            True se a remoção foi bem-sucedida, False caso contrário.
        """
        try:
            self.cursor.execute("DELETE FROM settings WHERE key = ?", (key,))
            
            if self.cursor.rowcount == 0:
                logger.warning(f"Configuração '{key}' não encontrada para remoção")
                return False
                
            self.conn.commit()
            logger.info(f"Configuração '{key}' removida com sucesso")
            return True
            
        except sqlite3.Error as e:
            self.conn.rollback()
            logger.error(f"Erro ao remover configuração '{key}': {e}")
            return False
    
    # ===== MÉTODOS DE MANUTENÇÃO =====
    
    def vacuum(self) -> bool:
        """Executa o comando VACUUM no banco de dados para otimizar o espaço em disco.
        
        Returns:
            True se o comando foi executado com sucesso, False caso contrário.
        """
        try:
            # Fecha o cursor e a conexão atuais
            if self.cursor:
                self.cursor.close()
            
            if self.conn:
                self.conn.close()
            
            # Reconecta com o banco de dados
            self._connect()
            
            # Executa o VACUUM
            self.cursor.execute("VACUUM")
            self.conn.commit()
            
            logger.info("Otimização do banco de dados concluída com sucesso")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Erro ao otimizar o banco de dados: {e}")
            return False
    
    def backup_database(self, backup_path: str) -> bool:
        """Cria uma cópia de segurança do banco de dados.
        
        Args:
            backup_path: Caminho completo para salvar o backup.
            
        Returns:
            True se o backup foi criado com sucesso, False caso contrário.
        """
        try:
            # Garante que o diretório de destino existe
            os.makedirs(os.path.dirname(os.path.abspath(backup_path)), exist_ok=True)
            
            # Fecha a conexão atual para garantir que todos os dados foram gravados
            if self.conn:
                self.conn.close()
            
            # Copia o arquivo do banco de dados
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
            # Reconecta ao banco de dados
            self._connect()
            
            logger.info(f"Backup do banco de dados criado em: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao criar backup do banco de dados: {e}")
            # Tenta reconectar em caso de erro
            self._connect()
            return False

    def add_reading(self, sensor_id: str, value: float, unit: str = "ppm"):
        """Adiciona uma nova leitura de sensor ao banco de dados.
        
        Args:
            sensor_id: ID do sensor que fez a leitura.
            value: Valor da leitura.
            unit: Unidade de medida (padrão: "ppm").
            
        Returns:
            ID da leitura inserida ou None em caso de erro.
        """
        try:
            # Determina o status com base no valor
            if value is None:
                status = "error"
            else:
                # Aqui você pode adicionar lógica para determinar warning/alarm
                # com base em valores de configuração
                status = "normal"
            
            self.cursor.execute(
                """
                INSERT INTO sensor_readings (sensor_id, value, status)
                VALUES (?, ?, ?)
                """,
                (sensor_id, float(value), status)
            )
            self.conn.commit()
            return self.cursor.lastrowid
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Erro ao adicionar leitura do sensor {sensor_id}: {str(e)}")
            return None

# Funções auxiliares para uso com gerenciador de contexto
def init_database(db_path: str = None) -> DatabaseManager:
    """Inicializa o banco de dados e retorna uma instância do gerenciador.
    
    Args:
        db_path: Caminho para o arquivo do banco de dados.
        
    Returns:
        Instância do DatabaseManager.
    """
    return DatabaseManager(db_path)

def get_database() -> DatabaseManager:
    """Retorna uma instância do gerenciador de banco de dados.
    
    Returns:
        Instância do DatabaseManager.
    """
    return DatabaseManager()

# Cria uma instância global do banco de dados
_db = None

def get_db() -> DatabaseManager:
    """Retorna uma instância global do banco de dados.
    
    Returns:
        Instância do DatabaseManager.
    """
    global _db
    if _db is None:
        _db = DatabaseManager()
    return _db

# Inicializa o banco de dados quando o módulo é importado
if __name__ != "__main__":
    db = get_db()

"""
Módulo da interface gráfica do Sistema de Monitoramento de Amônia.
"""

# Importações dos componentes da interface
from .main_window import MainWindow
from .pages.dashboard import DashboardPage as DashboardTab
from .settings import SettingsTab
from .emergency_test import EmergencyTestTab
from .styles import apply_stylesheet, load_stylesheet

__all__ = [
    'MainWindow', 
    'DashboardTab', 
    'SettingsTab', 
    'EmergencyTestTab',
    'DashboardPage',
    'apply_stylesheet',
    'load_stylesheet'
]

"""
Componente personalizado para exibição de medidor de amônia.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QRectF, QProperty, Property
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics, QBrush, QLinearGradient

class AmmoniaGauge(QWidget):
    """
    Widget personalizado para exibição de um medidor de amônia estilizado.
    """
    
    # Sinal emitido quando o valor do medidor é alterado
    valueChanged = pyqtSignal(float)
    
    def __init__(self, title="Sensor", unit="ppm", min_value=0.0, max_value=100.0, parent=None):
        """
        Inicializa o medidor de amônia.
        
        Args:
            title: Título do medidor.
            unit: Unidade de medida (ex: ppm, %).
            min_value: Valor mínimo do medidor.
            max_value: Valor máximo do medidor.
            parent: Widget pai.
        """
        super().__init__(parent)
        
        # Configurações iniciais
        self._title = title
        self._unit = unit
        self._min_value = min_value
        self._max_value = max_value
        self._value = min_value
        self._target_value = min_value
        self._animation = None
        
        # Cores personalizáveis
        self._bg_color = QColor(240, 240, 240)
        self._border_color = QColor(200, 200, 200)
        self._title_color = QColor(70, 70, 70)
        self._value_color = QColor(50, 50, 50)
        self._unit_color = QColor(100, 100, 100)
        self._arc_bg_color = QColor(230, 230, 230)
        self._arc_color = QColor(65, 105, 225)  # Azul royal
        self._arc_warning_color = QColor(255, 165, 0)  # Laranja
        self._arc_danger_color = QColor(220, 20, 60)  # Vermelho
        
        # Configuração do widget
        self.setMinimumSize(200, 250)
        self.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding
        )
        
        # Configura a animação
        self.animation = QPropertyAnimation(self, b"value")
        self.animation.setDuration(1000)  # 1 segundo de duração
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def setValue(self, value, animated=True):
        """
        Define o valor do medidor.
        
        Args:
            value: Novo valor a ser exibido.
            animated: Se True, anima a transição para o novo valor.
        """
        # Garante que o valor está dentro dos limites
        value = max(self._min_value, min(float(value), self._max_value))
        
        if value == self._value:
            return
        
        self._target_value = value
        
        if animated:
            # Para qualquer animação em andamento
            if self.animation.state() == QPropertyAnimation.State.Running:
                self.animation.stop()
            
            # Configura a animação
            self.animation.setStartValue(self._value)
            self.animation.setEndValue(value)
            self.animation.start()
        else:
            self.value = value  # Usa a propriedade para definir o valor
    
    def get_value(self):
        """Retorna o valor atual do medidor."""
        return self._value
    
    def set_value(self, value):
        """Define o valor diretamente (usado pela animação)."""
        if value != self._value:
            self._value = float(value)
            self.update()
            self.valueChanged.emit(self._value)
    
    # Define a propriedade 'value' para uso com QPropertyAnimation
    value = Property(float, fget=get_value, fset=set_value)
    
    def paintEvent(self, event):
        """Renderiza o medidor."""
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Obtém as dimensões do widget
            width = self.width()
            height = self.height()
            
            # Desenha o fundo
            self.drawBackground(painter, width, height)
            
            # Desenha o arco do medidor
            self.drawArc(painter, width, height)
            
            # Desenha o valor e a unidade
            self.drawValue(painter, width, height)
            
            # Desenha o título
            self.drawTitle(painter, width, height)
        except Exception as e:
            print(f"Erro ao desenhar o medidor: {str(e)}")
        finally:
            # Garante que o QPainter seja finalizado corretamente
            painter.end()
    
    def drawBackground(self, painter, width, height):
        """Desenha o fundo do medidor."""
        # Salva o estado do painter
        painter.save()
        
        try:
            # Retângulo arredondado para o fundo
            rect = self.rect().adjusted(1, 1, -1, -1)
            
            # Configura a caneta e o pincel
            pen = QPen(self._border_color, 1)
            painter.setPen(pen)
            painter.setBrush(self._bg_color)
            
            # Desenha o retângulo arredondado
            painter.drawRoundedRect(rect, 10, 10)
        except Exception as e:
            print(f"Erro ao desenhar o fundo: {str(e)}")
        finally:
            # Restaura o estado do painter
            painter.restore()
    
    def drawArc(self, painter, width, height):
        """Desenha o arco do medidor."""
        # Salva o estado do painter
        painter.save()
        
        try:
            # Tamanho do arco
            margin = 20
            arc_rect = QRectF(
                margin,
                margin,
                width - 2 * margin,
                (width - 2 * margin) * 0.8
            )
            
            # Ângulos para o arco (em graus * 16)
            start_angle = 45 * 16
            span_angle = 270 * 16
            
            # Desenha o fundo do arco
            pen = QPen(self._arc_bg_color, 15, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(arc_rect, start_angle, span_angle)
            
            # Calcula a porcentagem do valor atual
            value_range = self._max_value - self._min_value
            if value_range > 0:
                percentage = (self._value - self._min_value) / value_range
                percentage = max(0.0, min(1.0, percentage))  # Garante que está entre 0 e 1
            else:
                percentage = 0.0
            
            # Define a cor do arco com base no valor
            if percentage > 0.7:
                arc_color = self._arc_danger_color
            elif percentage > 0.4:
                arc_color = self._arc_warning_color
            else:
                arc_color = self._arc_color
            
            # Desenha o arco de preenchimento
            if percentage > 0:
                pen = QPen(arc_color, 15, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawArc(arc_rect, start_angle, int(span_angle * percentage))
            
            # Desenha o marcador de valor
            self.drawValueMarker(painter, arc_rect, start_angle, span_angle, percentage)
        except Exception as e:
            print(f"Erro ao desenhar o arco: {str(e)}")
        finally:
            # Restaura o estado do painter
            painter.restore()
    
    def drawValueMarker(self, painter, arc_rect, start_angle, span_angle, percentage):
        """Desenha o marcador de valor no arco."""
        # Importa math para funções trigonométricas
        import math
        
        # Calcula a posição do marcador
        angle = start_angle + int(span_angle * percentage)
        angle_rad = math.radians(angle / 16.0)
        
        # Raio do arco
        radius = arc_rect.width() / 2
        
        # Centro do arco
        center_x = arc_rect.center().x()
        center_y = arc_rect.center().y()
        
        # Posição do marcador (ajustada para ângulos do Qt)
        marker_size = 10
        marker_radius = radius - marker_size / 2
        
        # Ajusta o ângulo para o sistema de coordenadas do Qt (0° em cima, sentido horário)
        adjusted_angle = angle_rad - math.pi / 2
        
        # Calcula as coordenadas x e y do marcador
        marker_x = center_x + marker_radius * math.cos(adjusted_angle)
        marker_y = center_y + marker_radius * math.sin(adjusted_angle)
        
        # Salva o estado do painter
        painter.save()
        
        try:
            # Desenha o marcador
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255))
            painter.drawEllipse(marker_x - marker_size / 2, marker_y - marker_size / 2, 
                              marker_size, marker_size)
            
            # Borda do marcador
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(marker_x - marker_size / 2, marker_y - marker_size / 2, 
                              marker_size, marker_size)
        finally:
            # Restaura o estado do painter
            painter.restore()
    
    def drawValue(self, painter, width, height):
        """Desenha o valor e a unidade."""
        # Configura a fonte para o valor
        value_font = QFont()
        value_font.setPointSize(24)
        value_font.setBold(True)
        painter.setFont(value_font)
        painter.setPen(self._value_color)
        
        # Texto do valor
        value_text = f"{self._value:.1f}"
        value_rect = painter.fontMetrics().boundingRect(value_text)
        
        # Posiciona o valor no centro do widget
        value_x = (width - value_rect.width()) / 2
        value_y = height * 0.6
        
        painter.drawText(int(value_x), int(value_y), value_text)
        
        # Configura a fonte para a unidade
        unit_font = QFont()
        unit_font.setPointSize(12)
        painter.setFont(unit_font)
        painter.setPen(self._unit_color)
        
        # Texto da unidade
        unit_text = self._unit
        unit_rect = painter.fontMetrics().boundingRect(unit_text)
        
        # Posiciona a unidade ao lado do valor
        unit_x = value_x + value_rect.width() + 5
        unit_y = value_y - (value_rect.height() - unit_rect.height()) / 2
        
        painter.drawText(int(unit_x), int(unit_y), unit_text)
    
    def drawTitle(self, painter, width, height):
        """Desenha o título do medidor."""
        # Configura a fonte para o título
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(self._title_color)
        
        # Texto do título
        title_text = self._title
        title_rect = painter.fontMetrics().boundingRect(title_text)
        
        # Posiciona o título na parte inferior do widget
        title_x = (width - title_rect.width()) / 2
        title_y = height - 15
        
        painter.drawText(int(title_x), int(title_y), title_text)

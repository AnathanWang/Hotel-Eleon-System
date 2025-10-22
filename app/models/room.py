"""
Модель номеров отеля
Автор модуля: Солянов А.А.
"""
from enum import Enum
from app import db


class RoomType(Enum):
    # Типы номеров
    STANDARD = ('standard', 'Стандарт', 3000)
    DELUXE = ('deluxe', 'Делюкс', 5000)
    SUITE = ('suite', 'Люкс', 8000)
    FAMILY = ('family', 'Семейный', 6000)
    
    def __init__(self, code, name, base_price):
        self.code = code
        self.display_name = name
        self.base_price = base_price


class Room(db.Model):
    """
    Модель номера отеля
    
    Реализует принципы ООП:
    - Инкапсуляция: скрывает внутреннюю структуру данных
    - Абстракция: представляет номер как объект с ключевыми свойствами
    """
    __tablename__ = 'rooms'
    
    # поля таблицы
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(10), unique=True, nullable=False, index=True) # Номер команты
    room_type = db.Column(db.String(20), nullable=False) # тип номера
    floor = db.Column(db.Integer, nullable=False) # этаж
    capacity = db.Column(db.Integer, nullable=False)  # Вместимость (человек)
    price_per_night = db.Column(db.Float, nullable=False) # прайс
    description = db.Column(db.Text) # описание
    is_available = db.Column(db.Boolean, default=True) # флаг доступности
    
    # Связь с бронированиями (one-to-many)
    bookings = db.relationship('Booking', backref='room', lazy='dynamic', 
                               cascade='all, delete-orphan')
    
    def __init__(self, number, room_type, floor, capacity, description=''):
        """Инициализация номера с автоматическим расчетом цены"""
        self.number = number
        self.room_type = room_type
        self.floor = floor
        self.capacity = capacity
        self.description = description
        self.is_available = True
        
        # Автоматический расчет цены на основе типа номера
        self._set_price_by_type()
    
    def _set_price_by_type(self):
        """Приватный метод для установки цены (инкапсуляция)"""
        for room_type in RoomType:
            if room_type.code == self.room_type:
                self.price_per_night = room_type.base_price
                break
        else:
            self.price_per_night = 3000  # Цена по умолчанию
    
    def get_type_display(self):
        """Получить отображаемое название типа номера"""
        for room_type in RoomType:
            if room_type.code == self.room_type:
                return room_type.display_name
        return self.room_type
    
    def is_available_for_period(self, check_in, check_out):
        """
        Проверка доступности номера на период
        
        Args:
            check_in (date): Дата заезда
            check_out (date): Дата выезда
        
        Returns:
            bool: True если номер свободен
        """
        from app.models.booking import BookingStatus
        #првоерка пересечения дат
        overlapping_bookings = self.bookings.filter(
            db.and_(
                Booking.status.in_([BookingStatus.CONFIRMED.value, BookingStatus.CHECKED_IN.value]),
                db.or_(
                    db.and_(Booking.check_in <= check_in, Booking.check_out > check_in),
                    db.and_(Booking.check_in < check_out, Booking.check_out >= check_out),
                    db.and_(Booking.check_in >= check_in, Booking.check_out <= check_out)
                )
            )
        ).first()
        
        return overlapping_bookings is None
    
    def calculate_total_price(self, nights):
        """Рассчитать общую стоимость за период"""
        return self.price_per_night * nights
    
    def to_dict(self):
        """Преобразование в словарь для JSON"""
        return {
            'id': self.id,
            'number': self.number,
            'type': self.room_type,
            'type_display': self.get_type_display(),
            'floor': self.floor,
            'capacity': self.capacity,
            'price_per_night': self.price_per_night,
            'description': self.description,
            'is_available': self.is_available
        }
    
    def __repr__(self):
        return f'<Room {self.number} ({self.get_type_display()})>'

"""
Модель бронирования
Автор модуля: Солянов А.А.
"""
from enum import Enum
from datetime import datetime
from app import db
from sqlalchemy.orm import relationship


class BookingStatus(Enum):
    """Статусы бронирования"""
    PENDING = ('pending', 'В ожидании')
    CONFIRMED = ('confirmed', 'Подтверждено')
    CHECKED_IN = ('checked_in', 'Заселен')
    CHECKED_OUT = ('checked_out', 'Выселен')
    CANCELLED = ('cancelled', 'Отменено')
    
    def __init__(self, code, name):
        self.code = code
        self.display_name = name


class Booking(db.Model):
    """
    Модель бронирования номера
    
    Реализует принципы ООП:
    - Инкапсуляция: управление статусами и расчетами
    - Абстракция: представляет бронь как бизнес-объект
    """
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Связь с номером (many-to-one)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    
    # Информация о госте (упрощенная, без отдельной таблицы для модуля Солянова)
    guest_name = db.Column(db.String(100), nullable=False)
    guest_phone = db.Column(db.String(20), nullable=False)
    guest_email = db.Column(db.String(100))

    guest_id = db.Column(db.Integer, db.ForeignKey("guests.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Даты бронирования
    check_in = db.Column(db.Date, nullable=False, index=True)
    check_out = db.Column(db.Date, nullable=False, index=True)
    
    # Финансовая информация
    total_price = db.Column(db.Float, nullable=False)
    
    # Статус бронирования
    status = db.Column(db.String(20), nullable=False, default='pending')
    
    # Дополнительная информация
    special_requests = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Временные метки
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    guest = relationship("Guest", back_populates="bookings")
    visit = relationship("GuestVisit", back_populates="booking", uselist=False)
    
    def __init__(self, room_id, guest_name, guest_phone, check_in, check_out,
                 guest_email='', special_requests='', notes=''):
        """Инициализация бронирования с автоматическим расчетом цены"""
        self.room_id = room_id
        self.guest_name = guest_name
        self.guest_phone = guest_phone
        self.guest_email = guest_email
        self.check_in = check_in
        self.check_out = check_out
        self.special_requests = special_requests
        self.notes = notes
        self.status = BookingStatus.PENDING.value
        
        # Автоматический расчет общей стоимости
        self._calculate_total_price()
    
    def _calculate_total_price(self):
        """Приватный метод для расчета общей стоимости (инкапсуляция)"""
        nights = (self.check_out - self.check_in).days
        if nights <= 0:
            nights = 1
        
        # Получаем цену номера
        room = db.session.get(Room, self.room_id)
        if room:
            self.total_price = room.price_per_night * nights
        else:
            self.total_price = 0
    
    def get_nights_count(self):
        """Получить количество ночей"""
        return (self.check_out - self.check_in).days
    
    def get_status_display(self):
        """Получить отображаемое название статуса"""
        for status in BookingStatus:
            if status.value == self.status:
                return status.display_name
        return self.status
    
    def confirm(self):
        """Подтвердить бронирование"""
        if self.status == BookingStatus.PENDING.value:
            self.status = BookingStatus.CONFIRMED.value
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def check_in_guest(self):
        """Заселить гостя"""
        if self.status == BookingStatus.CONFIRMED.value:
            self.status = BookingStatus.CHECKED_IN.value
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def check_out_guest(self):
        """Выселить гостя"""
        if self.status == BookingStatus.CHECKED_IN.value:
            self.status = BookingStatus.CHECKED_OUT.value
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def cancel(self):
        """Отменить бронирование"""
        if self.status not in [BookingStatus.CHECKED_OUT.value, BookingStatus.CANCELLED.value]:
            self.status = BookingStatus.CANCELLED.value
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def to_dict(self):
        """Преобразование в словарь для JSON"""
        return {
            'id': self.id,
            'room_id': self.room_id,
            'room_number': self.room.number if self.room else None,
            'guest_name': self.guest_name,
            'guest_phone': self.guest_phone,
            'guest_email': self.guest_email,
            'check_in': self.check_in.strftime('%Y-%m-%d'),
            'check_out': self.check_out.strftime('%Y-%m-%d'),
            'nights': self.get_nights_count(),
            'total_price': self.total_price,
            'status': self.status,
            'status_display': self.get_status_display(),
            'special_requests': self.special_requests,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def can_checkin(self) -> bool:
        # Разрешаем заселение только из confirmed и в пределах дат
        if self.status != "confirmed":
            return False
        # Предполагаем, что есть поля start_date/end_date
        from datetime import date
        return self.start_date is not None and date.today() >= self.start_date

    def can_checkout(self) -> bool:
        # Выселение — только если уже заселён
        return self.status == "checked_in"
    
    def __repr__(self):
        return f'<Booking {self.id}: {self.guest_name} ({self.check_in} - {self.check_out})>'


# Импорт Room для использования в Booking
from app.models.room import Room

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.orm import relationship

from app import db  

# класс модель гостя
# хранение персональных данных и связи с бронированиями и посещениями
class Guest(db.Model):

    __tablename__ = "guests"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)   # Имя
    last_name = db.Column(db.String(80), nullable=False)    # Фамилия
    phone = db.Column(db.String(32), nullable=True, index=True)  # Телефон
    email = db.Column(db.String(120), nullable=True, index=True, unique=False)  # Почта (не делаем уникальной — бывают дубли)
    doc_number = db.Column(db.String(64), nullable=True, index=True)  # Паспорт/удостоверение
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # История проживаний (визиты) и бронирования (ожидаем наличие модели Booking)
    visits = relationship("GuestVisit", back_populates="guest", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="guest", lazy="selectin", foreign_keys="Booking.guest_id")

    def full_name(self) -> str:
        # Полное имя для отображения
        return f"{self.last_name} {self.first_name}"

    def to_dict(self) -> dict:
        # Сериализация в JSON (для API)
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "email": self.email,
            "doc_number": self.doc_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

# класс модель визита, фаткическое проживание
# создается при заселении и закрываеися при выселении
# класс привязан к бронирование и номеру
class GuestVisit(db.Model):

    __tablename__ = "guest_visits"

    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey("guests.id", ondelete="CASCADE"), nullable=False, index=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, unique=True)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True)
    checkin_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)   # Время фактического заселения
    checkout_at = db.Column(db.DateTime, nullable=True)                             # Время фактического выселения
    base_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)          # Базовая стоимость проживания (из бронирования)
    services_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)      # Стоимость услуг
    total_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)         # Итог к оплате (фиксируется при check-out)

    # Связи
    guest = relationship("Guest", back_populates="visits")
    booking = relationship("Booking", back_populates="visit", uselist=False)
    room = relationship("Room")
    service_orders = relationship("ServiceOrder", back_populates="visit", cascade="all, delete-orphan")

    # пересчет итогов по услугам
    def recalc_totals(self):
        self.services_amount = (db.session.query(func.coalesce(func.sum(
            db.text("quantity * unit_price")  # умножение на уровне БД
        ), 0))
         .select_from(ServiceOrder)
         .filter(ServiceOrder.visit_id == self.id, ServiceOrder.status == "completed")
         .scalar() or 0)

        self.total_amount = (self.base_amount or 0) + (self.services_amount or 0)

from app.models.service import ServiceOrder  # noqa: E402
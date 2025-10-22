from datetime import datetime
from app import db  
from sqlalchemy.orm import relationship

# класс со справочником
class Service(db.Model):
    """
    Справочник услуг (RoomService, Spa, Laundry, Transfer и т.д.)
    """
    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)   # Уникальный код услуги (e.g. SPA, ROOM_SERVICE)
    title = db.Column(db.String(120), nullable=False)                           # Название
    base_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)       # Базовая цена за единицу
    is_active = db.Column(db.Boolean, nullable=False, default=True)            # Признак активности в прайсе
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    orders = relationship("ServiceOrder", back_populates="service")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "title": self.title,
            "base_price": float(self.base_price or 0),
            "is_active": self.is_active,
        }

# класс с заказом услуг 
class ServiceOrder(db.Model):
    """
    Заказ услуги в рамках визита (проживания).
    """
    __tablename__ = "service_orders"

    id = db.Column(db.Integer, primary_key=True)
    visit_id = db.Column(db.Integer, db.ForeignKey("guest_visits.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id = db.Column(db.Integer, db.ForeignKey("services.id", ondelete="RESTRICT"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)                 # Количество
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)        # Цена за единицу (зафиксированная на момент заказа)
    status = db.Column(db.String(20), nullable=False, default="pending")        # pending/completed/canceled
    note = db.Column(db.String(255), nullable=True)                             # Комментарий
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    service = relationship("Service", back_populates="orders")
    visit = relationship("GuestVisit", back_populates="service_orders")

    def subtotal(self) -> float:
        # Подитог по заказу
        q = self.quantity or 0
        p = float(self.unit_price or 0)
        return round(q * p, 2)
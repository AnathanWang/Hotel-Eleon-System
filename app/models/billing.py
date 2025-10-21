# Модели биллинга
from enum import Enum
from datetime import datetime
import json
from app import db


class BillStatus(Enum):
    OPEN = ('open', 'Открыт')
    PARTIALLY_PAID = ('partially_paid', 'Частично оплачен')
    PAID = ('paid', 'Оплачен')
    CANCELLED = ('cancelled', 'Отменён')
    REFUNDED = ('refunded', 'Возвращён')
    
    def __init__(self, code, name):
        self.code = code
        self.display_name = name


class PaymentMethod(Enum):
    CASH = ('cash', 'Наличные')
    CARD = ('card', 'Банковская карта')
    ONLINE = ('online', 'Онлайн-оплата')
    TRANSFER = ('transfer', 'Банковский перевод')
    REFUND = ('refund', 'Возврат')
    
    def __init__(self, code, name):
        self.code = code
        self.display_name = name


class Bill(db.Model):
    __tablename__ = 'bills'
    
    id = db.Column(db.Integer, primary_key=True)
    
    guest_name = db.Column(db.String(100), nullable=False)
    guest_contact = db.Column(db.String(100), nullable=False)
    
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=True)
    booking = db.relationship('Booking', backref='bills')
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    
    items_json = db.Column(db.Text, nullable=False, default='[]')
    
    subtotal = db.Column(db.Float, nullable=False, default=0.0)
    tax = db.Column(db.Float, nullable=False, default=0.0)
    discount = db.Column(db.Float, nullable=False, default=0.0)
    total = db.Column(db.Float, nullable=False, default=0.0)
    paid_amount = db.Column(db.Float, nullable=False, default=0.0)
    
    status = db.Column(db.String(20), nullable=False, default='open')
    
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    payments = db.relationship('Payment', backref='bill', lazy='dynamic',
                              cascade='all, delete-orphan')
    
    def __init__(self, guest_name, guest_contact, created_by_id, 
                 booking_id=None, notes=''):
        self.guest_name = guest_name
        self.guest_contact = guest_contact
        self.created_by_id = created_by_id
        self.booking_id = booking_id
        self.notes = notes
        self.status = BillStatus.OPEN.code
        self.items_json = '[]'
        self.subtotal = 0.0
        self.tax = 0.0
        self.discount = 0.0
        self.total = 0.0
        self.paid_amount = 0.0
    
    @property
    def items(self):
        try:
            return json.loads(self.items_json)
        except (json.JSONDecodeError, TypeError):
            return []
    
    @items.setter
    def items(self, value):
        self.items_json = json.dumps(value, ensure_ascii=False)
    
    def add_item(self, description, quantity, unit_price):
        items = self.items
        item_total = quantity * unit_price
        
        items.append({
            'description': description,
            'quantity': quantity,
            'unit_price': unit_price,
            'total': item_total
        })
        
        self.items = items
        self.updated_at = datetime.utcnow()
    
    def remove_item(self, index):
        items = self.items
        if 0 <= index < len(items):
            items.pop(index)
            self.items = items
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def recalc_totals(self, tax_percent=None, discount_amount=None):
        from flask import current_app
        
        items = self.items
        self.subtotal = sum(item.get('total', 0) for item in items)
        
        if tax_percent is None:
            tax_percent = current_app.config.get('TAX_PERCENT', 0)
        self.tax = self.subtotal * (tax_percent / 100.0)
        
        if discount_amount is not None:
            self.discount = discount_amount
        
        self.total = self.subtotal + self.tax - self.discount
        
        self._update_status()
        self.updated_at = datetime.utcnow()
    
    def apply_payment(self, payment):
        self.paid_amount += payment.amount
        self._update_status()
        self.updated_at = datetime.utcnow()
    
    def _update_status(self):
        if self.status == BillStatus.CANCELLED.code:
            return
        
        if self.paid_amount <= 0:
            self.status = BillStatus.OPEN.code
        elif self.paid_amount < self.total:
            self.status = BillStatus.PARTIALLY_PAID.code
        elif self.paid_amount >= self.total:
            self.status = BillStatus.PAID.code
    
    def get_balance(self):
        return max(0, self.total - self.paid_amount)
    
    def cancel(self):
        if self.status not in [BillStatus.PAID.code, BillStatus.REFUNDED.code]:
            self.status = BillStatus.CANCELLED.code
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    def get_status_display(self):
        for status in BillStatus:
            if status.code == self.status:
                return status.display_name
        return self.status
    
    def to_dict(self):
        """Преобразование в словарь для JSON"""
        return {
            'id': self.id,
            'guest_name': self.guest_name,
            'guest_contact': self.guest_contact,
            'booking_id': self.booking_id,
            'created_by': self.creator.full_name() if self.creator else None,
            'items': self.items,
            'subtotal': self.subtotal,
            'tax': self.tax,
            'discount': self.discount,
            'total': self.total,
            'paid_amount': self.paid_amount,
            'balance': self.get_balance(),
            'status': self.status,
            'status_display': self.get_status_display(),
            'notes': self.notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def __repr__(self):
        return f'<Bill {self.id}: {self.guest_name} - {self.total} руб. ({self.get_status_display()})>'


class Payment(db.Model):
    """
    Модель платежа
    
    Реализует принципы ООП:
    - Инкапсуляция: хранение данных о платеже
    - Абстракция: представляет платёж как транзакцию
    """
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Связь со счётом
    bill_id = db.Column(db.Integer, db.ForeignKey('bills.id'), nullable=False)
    
    # Сумма платежа (может быть отрицательной для возвратов)
    amount = db.Column(db.Float, nullable=False)
    
    # Способ оплаты
    method = db.Column(db.String(20), nullable=False, default='cash')
    
    # Кто принял платёж
    received_by_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    
    # Референс платежа (номер транзакции, чека и т.д.)
    reference = db.Column(db.String(100))
    
    # Примечания
    notes = db.Column(db.Text)
    
    # Временная метка
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __init__(self, bill_id, amount, method, received_by_id, 
                 reference='', notes=''):
        """Инициализация платежа"""
        self.bill_id = bill_id
        self.amount = amount
        self.method = method
        self.received_by_id = received_by_id
        self.reference = reference
        self.notes = notes
    
    def get_method_display(self):
        """Получить отображаемое название способа оплаты"""
        for payment_method in PaymentMethod:
            if payment_method.code == self.method:
                return payment_method.display_name
        return self.method
    
    def is_refund(self):
        """Является ли платёж возвратом"""
        return self.amount < 0
    
    def to_dict(self):
        """Преобразование в словарь для JSON"""
        return {
            'id': self.id,
            'bill_id': self.bill_id,
            'amount': self.amount,
            'method': self.method,
            'method_display': self.get_method_display(),
            'received_by': self.receiver.full_name() if self.receiver else None,
            'reference': self.reference,
            'notes': self.notes,
            'is_refund': self.is_refund(),
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def __repr__(self):
        return f'<Payment {self.id}: {self.amount} руб. ({self.get_method_display()})>'

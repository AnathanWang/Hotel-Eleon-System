# Модели персонала
from enum import Enum
from datetime import datetime
from app import db


class StaffRole(Enum):
    """Роли персонала"""
    STAFF = ('staff', 'Персонал')
    RECEPTIONIST = ('receptionist', 'Администратор')
    MANAGER = ('manager', 'Менеджер')
    
    def __init__(self, code, name):
        self.code = code
        self.display_name = name


class Staff(db.Model):
    __tablename__ = 'staff'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Личная информация
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    
    # Роль и статус
    role = db.Column(db.String(20), nullable=False, default='staff')
    is_active = db.Column(db.Boolean, default=True)
    
    # Даты
    hire_date = db.Column(db.Date, nullable=False)
    termination_date = db.Column(db.Date, nullable=True)
    
    # Дополнительно
    notes = db.Column(db.Text)
    
    # Временные метки
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи с биллингом (один сотрудник может создать много счетов)
    created_bills = db.relationship('Bill', foreign_keys='Bill.created_by_id',
                                   backref='creator', lazy='dynamic')
    received_payments = db.relationship('Payment', foreign_keys='Payment.received_by_id',
                                       backref='receiver', lazy='dynamic')
    
    # Полиморфизм через тип
    __mapper_args__ = {
        'polymorphic_identity': 'staff',
        'polymorphic_on': role
    }
    
    def __init__(self, first_name, last_name, email, phone, hire_date, 
                 role='staff', notes=''):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phone = phone
        self.hire_date = hire_date
        self.role = role
        self.notes = notes
        self.is_active = True
    
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def can_manage_bill(self, bill):
        return False
    
    def can_approve_refund(self, amount):
        return False
    
    def get_role_display(self):
        for staff_role in StaffRole:
            if staff_role.code == self.role:
                return staff_role.display_name
        return self.role
    
    def deactivate(self, termination_date=None):
        self.is_active = False
        self.termination_date = termination_date or datetime.utcnow().date()
        self.updated_at = datetime.utcnow()
    
    def activate(self):
        self.is_active = True
        self.termination_date = None
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name(),
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'role_display': self.get_role_display(),
            'is_active': self.is_active,
            'hire_date': self.hire_date.strftime('%Y-%m-%d'),
            'termination_date': self.termination_date.strftime('%Y-%m-%d') if self.termination_date else None,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<Staff {self.id}: {self.full_name()} ({self.get_role_display()})>'


class Manager(Staff):
    __mapper_args__ = {
        'polymorphic_identity': 'manager',
    }
    
    def __init__(self, first_name, last_name, email, phone, hire_date, notes=''):
        super().__init__(first_name, last_name, email, phone, hire_date, 
                        role='manager', notes=notes)
    
    def can_manage_bill(self, bill):
        return True
    
    def can_approve_refund(self, amount):
        return True
    
    def generate_report(self, start_date, end_date):
        from app.models.billing import Bill, Payment, BillStatus
        from app.models.booking import Booking, BookingStatus
        
        # Счета за период
        bills = Bill.query.filter(
            Bill.created_at >= start_date,
            Bill.created_at <= end_date
        ).all()
        
        total_bills = len(bills)
        total_revenue = sum(b.total for b in bills if b.status == BillStatus.PAID.code)
        paid_bills = sum(1 for b in bills if b.status == BillStatus.PAID.code)
        pending_bills = sum(1 for b in bills if b.status == BillStatus.OPEN.code)
        
        # Статистика по платежам
        payments = Payment.query.filter(
            Payment.created_at >= start_date,
            Payment.created_at <= end_date
        ).all()
        
        total_payments = len(payments)
        total_payment_amount = sum(p.amount for p in payments)
        
        payment_methods = {}
        for p in payments:
            payment_methods[p.method] = payment_methods.get(p.method, 0) + p.amount
        
        bookings = Booking.query.filter(
            Booking.created_at >= start_date,
            Booking.created_at <= end_date
        ).all()
        
        total_bookings = len(bookings)
        confirmed_bookings = sum(1 for b in bookings 
                                if b.status == BookingStatus.CONFIRMED.value)
        checked_in = sum(1 for b in bookings 
                        if b.status == BookingStatus.CHECKED_IN.value)
        checked_out = sum(1 for b in bookings 
                         if b.status == BookingStatus.CHECKED_OUT.value)
        
        return {
            'period': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'billing': {
                'total_bills': total_bills,
                'paid_bills': paid_bills,
                'pending_bills': pending_bills,
                'total_revenue': total_revenue,
                'total_payments': total_payments,
                'total_payment_amount': total_payment_amount,
                'payment_methods': payment_methods
            },
            'bookings': {
                'total': total_bookings,
                'confirmed': confirmed_bookings,
                'checked_in': checked_in,
                'checked_out': checked_out
            }
        }
    
    def approve_refund(self, bill, amount, note=''):
        from app.models.billing import Payment
        
        if not self.can_approve_refund(amount):
            return None
        
        if amount <= 0 or amount > bill.paid_amount:
            return None
        
        refund = Payment(
            bill_id=bill.id,
            amount=-amount,
            method='refund',
            received_by_id=self.id,
            reference=f'Refund approved by {self.full_name()}',
            notes=note
        )
        
        db.session.add(refund)
        bill.apply_payment(refund)
        
        return refund


class Receptionist(Staff):
    __mapper_args__ = {
        'polymorphic_identity': 'receptionist',
    }
    
    def __init__(self, first_name, last_name, email, phone, hire_date, notes=''):
        super().__init__(first_name, last_name, email, phone, hire_date,
                        role='receptionist', notes=notes)
    
    def can_manage_bill(self, bill):
        return bill.created_by_id == self.id or bill.status != 'paid'
    
    def create_bill_for_booking(self, booking, additional_items=None, auto_from_booking=True):
        from app.models.billing import Bill
        
        bill = Bill(
            guest_name=booking.guest_name,
            guest_contact=booking.guest_phone,
            booking_id=booking.id,
            created_by_id=self.id
        )
        
        if auto_from_booking:
            nights = booking.get_nights_count()
            bill.add_item(
                description=f'Проживание в номере {booking.room.number}',
                quantity=nights,
                unit_price=booking.room.price_per_night
            )
        
        if additional_items:
            for item in additional_items:
                bill.add_item(
                    description=item.get('desc', ''),
                    quantity=item.get('qty', 1),
                    unit_price=item.get('unit_price', 0)
                )
        
        bill.recalc_totals()
        db.session.add(bill)
        
        return bill
    
    def record_payment(self, bill, amount, method='cash', reference='', notes=''):
        from app.models.billing import Payment
        
        payment = Payment(
            bill_id=bill.id,
            amount=amount,
            method=method,
            received_by_id=self.id,
            reference=reference,
            notes=notes
        )
        
        db.session.add(payment)
        bill.apply_payment(payment)
        
        return payment
    
    def check_in_guest(self, booking, create_bill=True, additional_items=None):
        success = booking.check_in_guest()
        
        if success and create_bill:
            bill = self.create_bill_for_booking(booking, additional_items)
            return True, bill
        
        return success, None

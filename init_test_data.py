"""
Скрипт инициализации тестовых данных
"""
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import *
from datetime import date, timedelta

app = create_app()

with app.app_context():
    # Проверяем, есть ли уже данные
    if Room.query.first():
        print('База данных уже содержит данные! Очистка...')
        db.drop_all()
        db.create_all()
    
    print('Добавление тестовых номеров...')
    
    # Создаем номера
    rooms_data = [
        # Стандарт
        ('101', 'standard', 1, 2, 'Стандартный номер с двуспальной кроватью'),
        ('102', 'standard', 1, 2, 'Стандартный номер с двумя односпальными кроватями'),
        ('103', 'standard', 1, 2, 'Стандартный номер с видом на парк'),
        
        # Делюкс
        ('201', 'deluxe', 2, 2, 'Делюкс с балконом и видом на город'),
        ('202', 'deluxe', 2, 2, 'Делюкс с джакузи'),
        ('203', 'deluxe', 2, 3, 'Делюкс с дополнительным диваном'),
        
        # Люкс
        ('301', 'suite', 3, 3, 'Люкс с гостиной и спальней'),
        ('302', 'suite', 3, 4, 'Президентский люкс с панорамным видом'),
        
        # Семейный
        ('401', 'family', 4, 4, 'Семейный номер с двумя спальнями'),
        ('402', 'family', 4, 5, 'Семейный номер с детской комнатой'),
    ]
    
    for room_data in rooms_data:
        room = Room(
            number=room_data[0],
            room_type=room_data[1],
            floor=room_data[2],
            capacity=room_data[3],
            description=room_data[4]
        )
        db.session.add(room)
    
    db.session.commit()
    print(f'Добавлено {len(rooms_data)} номеров')
    
    # Создаем тестовое бронирование
    print('Добавление тестового бронирования...')
    room = Room.query.filter_by(number='101').first()
    if room:
        booking = Booking(
            room_id=room.id,
            guest_name='Иван Иванов',
            guest_phone='+7 999 123-45-67',
            guest_email='ivan@example.com',
            check_in=date.today() + timedelta(days=2),
            check_out=date.today() + timedelta(days=5),
            special_requests='Ранний заезд, если возможно'
        )
        booking.confirm()
        db.session.add(booking)
        db.session.commit()
        print('Тестовое бронирование создано')
    
    # Создаем тестовый персонал
    print('Добавление тестового персонала...')
    
    # Менеджер
    manager = Manager(
        first_name='Анна',
        last_name='Менеджерова',
        email='manager@hotel-eleon.ru',
        phone='+7 999 111-22-33',
        hire_date=date(2023, 1, 15),
        notes='Главный менеджер отеля'
    )
    db.session.add(manager)
    
    # Администраторы
    receptionist1 = Receptionist(
        first_name='Мария',
        last_name='Администраторова',
        email='reception1@hotel-eleon.ru',
        phone='+7 999 222-33-44',
        hire_date=date(2023, 3, 1),
        notes='Администратор утренней смены'
    )
    db.session.add(receptionist1)
    
    receptionist2 = Receptionist(
        first_name='Пётр',
        last_name='Петров',
        email='reception2@hotel-eleon.ru',
        phone='+7 999 333-44-55',
        hire_date=date(2023, 6, 10),
        notes='Администратор вечерней смены'
    )
    db.session.add(receptionist2)
    
    # Обычный персонал
    staff1 = Staff(
        first_name='Иван',
        last_name='Техников',
        email='tech@hotel-eleon.ru',
        phone='+7 999 444-55-66',
        hire_date=date(2024, 1, 20),
        role='staff',
        notes='Технический персонал'
    )
    db.session.add(staff1)
    
    db.session.commit()
    print(f'Добавлено 4 сотрудника')
    
    # Создаем тестовый счёт
    print('Создание тестового счёта...')
    booking = Booking.query.filter_by(guest_name='Иван Иванов').first()
    if booking:
        # Создаём счёт через администратора
        bill = receptionist1.create_bill_for_booking(
            booking,
            additional_items=[
                {'desc': 'Мини-бар', 'qty': 1, 'unit_price': 500},
                {'desc': 'Завтрак', 'qty': 3, 'unit_price': 350}
            ],
            auto_from_booking=True
        )
        
        # Сохраняем счёт чтобы получить ID
        db.session.commit()
        
        # Добавляем частичную оплату
        payment = receptionist1.record_payment(
            bill,
            amount=5000,
            method='card',
            reference='CARD-12345',
            notes='Предоплата картой'
        )
        
        db.session.commit()
        print(f'Тестовый счёт создан: {bill.total} руб., оплачено: {bill.paid_amount} руб.')
    
    print('База данных инициализирована успешно!')

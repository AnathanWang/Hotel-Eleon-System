#!/usr/bin/env python3
"""
Скрипт инициализации базы данных
"""
import os
import sys

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.room import Room, RoomType
from app.models.booking import Booking
from datetime import date, timedelta

def init_database():
    """Инициализация базы данных с тестовыми данными"""
    app = create_app()
    
    with app.app_context():
        print('Создание таблиц базы данных...')
        db.create_all()
        
        # Проверяем, есть ли уже данные
        if Room.query.first():
            print('База данных уже содержит данные!')
            return
        
        print('Добавление тестовых номеров...')
        
        # Создаем номера
        rooms_data = [
            # Стандарт
            ('101', RoomType.STANDARD.code, 1, 2, 'Стандартный номер с двуспальной кроватью'),
            ('102', RoomType.STANDARD.code, 1, 2, 'Стандартный номер с двумя односпальными кроватями'),
            ('103', RoomType.STANDARD.code, 1, 2, 'Стандартный номер с видом на парк'),
            
            # Делюкс
            ('201', RoomType.DELUXE.code, 2, 2, 'Делюкс с балконом и видом на город'),
            ('202', RoomType.DELUXE.code, 2, 2, 'Делюкс с джакузи'),
            ('203', RoomType.DELUXE.code, 2, 3, 'Делюкс с дополнительным диваном'),
            
            # Люкс
            ('301', RoomType.SUITE.code, 3, 3, 'Люкс с гостиной и спальней'),
            ('302', RoomType.SUITE.code, 3, 4, 'Президентский люкс с панорамным видом'),
            
            # Семейный
            ('401', RoomType.FAMILY.code, 4, 4, 'Семейный номер с двумя спальнями'),
            ('402', RoomType.FAMILY.code, 4, 5, 'Семейный номер с детской комнатой'),
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
        
        print('\n✅ База данных инициализирована успешно!')
        print(f'📁 Файл базы данных: hotel_eleon.db')
        print(f'🏨 Создано номеров: {Room.query.count()}')
        print(f'📅 Создано бронирований: {Booking.query.count()}')

if __name__ == '__main__':
    init_database()

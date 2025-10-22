"""
Главное приложение Hotel Eleon System
Точка входа в систему управления отелем
"""
import os
from app import create_app, db
from app.models import Room, RoomType, Booking, BookingStatus
from datetime import date, timedelta

# Создаем приложение
app = create_app(os.getenv('FLASK_CONFIG') or 'default')


@app.route('/')
def index():
    """Главная страница системы"""
    from flask import render_template
    
    # Статистика для главной страницы
    total_rooms = Room.query.count()
    available_rooms = Room.query.filter_by(is_available=True).count()
    total_bookings = Booking.query.count()
    
    # Активные бронирования (сегодня и в будущем)
    today = date.today()
    active_bookings = Booking.query.filter(
        Booking.status.in_([
            BookingStatus.CONFIRMED.value,
            BookingStatus.CHECKED_IN.value
        ]),
        Booking.check_out >= today
    ).count()
    
    # Ближайшие заезды
    upcoming_checkins = Booking.query.filter(
        Booking.status == BookingStatus.CONFIRMED.value,
        Booking.check_in >= today,
        Booking.check_in <= today + timedelta(days=7)
    ).order_by(Booking.check_in).limit(5).all()
    
    return render_template('index.html',
                         total_rooms=total_rooms,
                         available_rooms=available_rooms,
                         total_bookings=total_bookings,
                         active_bookings=active_bookings,
                         upcoming_checkins=upcoming_checkins)


@app.cli.command()
def init_db():
    """Инициализация базы данных с тестовыми данными"""
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
    
    # Создание тестовонр бронирования
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
    
    print('База данных инициализирована успешно!')

# очистка бд
@app.cli.command()
def clear_db():
    """Очистка базы данных"""
    if input('Вы уверены? Все данные будут удалены (yes/no): ') == 'yes':
        db.drop_all()
        print('База данных очищена!')
    else:
        print('Отменено')


if __name__ == '__main__':
    app.run(debug=True)

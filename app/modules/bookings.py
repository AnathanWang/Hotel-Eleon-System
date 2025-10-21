"""
Модуль бронирования номеров
Автор: Солянов А.А.

Функционал:
- Создание бронирований
- Поиск свободных номеров по датам
- Управление бронированиями
- Календарь загруженности
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models.room import Room, RoomType
from app.models.booking import Booking, BookingStatus
from datetime import datetime, date, timedelta
from sqlalchemy import and_, or_

bp = Blueprint('bookings', __name__, url_prefix='/bookings')


@bp.route('/')
def index():
    """
    Главная страница бронирований
    Отображает список всех бронирований с фильтрацией по статусу
    """
    status_filter = request.args.get('status', '')
    
    # Базовый запрос
    query = Booking.query
    
    # Фильтр по статусу
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    # Получаем бронирования, отсортированные по дате заезда
    bookings = query.order_by(Booking.check_in.desc()).all()
    
    return render_template('bookings/index.html',
                         bookings=bookings,
                         booking_statuses=BookingStatus,
                         current_status=status_filter)


@bp.route('/search', methods=['GET', 'POST'])
def search():
    """
    Поиск свободных номеров по датам
    Реализует основную бизнес-логику модуля
    """
    if request.method == 'POST':
        try:
            # Получаем данные из формы
            check_in_str = request.form.get('check_in')
            check_out_str = request.form.get('check_out')
            room_type = request.form.get('room_type', '')
            capacity = request.form.get('capacity', 0)
            
            # Парсим даты
            check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
            
            # Валидация дат
            if check_in < date.today():
                flash('Дата заезда не может быть в прошлом!', 'warning')
                return redirect(url_for('bookings.search'))
            
            if check_out <= check_in:
                flash('Дата выезда должна быть позже даты заезда!', 'warning')
                return redirect(url_for('bookings.search'))
            
            # Поиск доступных номеров
            available_rooms = find_available_rooms(check_in, check_out, room_type, capacity)
            
            # Расчет количества ночей
            nights = (check_out - check_in).days
            
            return render_template('bookings/search_results.html',
                                 rooms=available_rooms,
                                 check_in=check_in,
                                 check_out=check_out,
                                 nights=nights,
                                 room_types=RoomType)
            
        except ValueError:
            flash('Неверный формат данных!', 'danger')
            return redirect(url_for('bookings.search'))
    
    # GET запрос - показываем форму поиска
    return render_template('bookings/search.html', room_types=RoomType)


def find_available_rooms(check_in, check_out, room_type='', min_capacity=0):
    """
    Вспомогательная функция для поиска доступных номеров
    
    Алгоритм:
    1. Получаем все номера по фильтрам (тип, вместимость)
    2. Для каждого номера проверяем наличие пересекающихся бронирований
    3. Возвращаем только свободные номера
    """
    # Базовый запрос
    query = Room.query.filter_by(is_available=True)
    
    # Применяем фильтры
    if room_type:
        query = query.filter_by(room_type=room_type)
    if min_capacity:
        query = query.filter(Room.capacity >= int(min_capacity))
    
    all_rooms = query.all()
    
    # Фильтруем номера, проверяя доступность на период
    available_rooms = []
    for room in all_rooms:
        if room.is_available_for_period(check_in, check_out):
            available_rooms.append(room)
    
    return available_rooms


@bp.route('/create', methods=['GET', 'POST'])
def create():
    """
    Создание бронирования
    Может быть вызвано из результатов поиска или напрямую
    """
    if request.method == 'POST':
        try:
            # Получаем данные из формы
            room_id = int(request.form.get('room_id'))
            guest_name = request.form.get('guest_name')
            guest_phone = request.form.get('guest_phone')
            guest_email = request.form.get('guest_email', '')
            check_in_str = request.form.get('check_in')
            check_out_str = request.form.get('check_out')
            special_requests = request.form.get('special_requests', '')
            
            # Парсим даты
            check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
            
            # Проверяем, что номер существует
            room = db.session.get(Room, room_id)
            if not room:
                flash('Номер не найден!', 'danger')
                return redirect(url_for('bookings.search'))
            
            # Проверяем доступность номера на период
            if not room.is_available_for_period(check_in, check_out):
                flash('Номер уже забронирован на выбранные даты!', 'danger')
                return redirect(url_for('bookings.search'))
            
            # Создаем бронирование (цена рассчитается автоматически)
            booking = Booking(
                room_id=room_id,
                guest_name=guest_name,
                guest_phone=guest_phone,
                guest_email=guest_email,
                check_in=check_in,
                check_out=check_out,
                special_requests=special_requests
            )
            
            db.session.add(booking)
            db.session.commit()
            
            flash(f'Бронирование успешно создано! Номер: {room.number}', 'success')
            return redirect(url_for('bookings.detail', booking_id=booking.id))
            
        except ValueError:
            flash('Ошибка в данных формы!', 'danger')
            return redirect(url_for('bookings.create'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании бронирования: {str(e)}', 'danger')
            return redirect(url_for('bookings.create'))
    
    # GET запрос - показываем форму
    # Получаем параметры из URL (если пришли из поиска)
    room_id = request.args.get('room_id')
    check_in = request.args.get('check_in')
    check_out = request.args.get('check_out')
    
    room = None
    if room_id:
        room = db.session.get(Room, int(room_id))
    
    return render_template('bookings/create.html',
                         room=room,
                         check_in=check_in,
                         check_out=check_out)


@bp.route('/<int:booking_id>')
def detail(booking_id):
    """
    Детальная информация о бронировании
    """
    booking = db.session.get(Booking, booking_id)
    if not booking:
        flash('Бронирование не найдено!', 'danger')
        return redirect(url_for('bookings.index'))
    
    return render_template('bookings/detail.html', booking=booking)


@bp.route('/<int:booking_id>/confirm', methods=['POST'])
def confirm(booking_id):
    """Подтверждение бронирования"""
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return jsonify({'success': False, 'message': 'Бронирование не найдено'}), 404
    
    try:
        if booking.confirm():
            db.session.commit()
            flash(f'Бронирование #{booking_id} подтверждено!', 'success')
            return jsonify({'success': True, 'status': booking.status})
        else:
            return jsonify({'success': False, 'message': 'Невозможно подтвердить'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/<int:booking_id>/checkin', methods=['POST'])
def checkin(booking_id):
    """Заселение гостя"""
    booking = db.session.get(Booking, booking_id)
    if not booking:
        flash('Бронирование не найдено!', 'danger')
        return redirect(url_for('bookings.index'))
    
    try:
        if booking.check_in_guest():
            db.session.commit()
            flash(f'Гость {booking.guest_name} успешно заселен!', 'success')
        else:
            flash('Невозможно заселить гостя. Проверьте статус бронирования.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при заселении: {str(e)}', 'danger')
    
    return redirect(url_for('bookings.detail', booking_id=booking_id))


@bp.route('/<int:booking_id>/checkout', methods=['POST'])
def checkout(booking_id):
    """Выселение гостя"""
    booking = db.session.get(Booking, booking_id)
    if not booking:
        flash('Бронирование не найдено!', 'danger')
        return redirect(url_for('bookings.index'))
    
    try:
        if booking.check_out_guest():
            db.session.commit()
            flash(f'Гость {booking.guest_name} успешно выселен!', 'success')
        else:
            flash('Невозможно выселить гостя. Проверьте статус бронирования.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при выселении: {str(e)}', 'danger')
    
    return redirect(url_for('bookings.detail', booking_id=booking_id))


@bp.route('/<int:booking_id>/cancel', methods=['POST'])
def cancel(booking_id):
    """Отмена бронирования"""
    booking = db.session.get(Booking, booking_id)
    if not booking:
        flash('Бронирование не найдено!', 'danger')
        return redirect(url_for('bookings.index'))
    
    try:
        if booking.cancel():
            db.session.commit()
            flash(f'Бронирование #{booking_id} отменено!', 'info')
        else:
            flash('Невозможно отменить бронирование.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при отмене: {str(e)}', 'danger')
    
    return redirect(url_for('bookings.detail', booking_id=booking_id))


@bp.route('/calendar')
def calendar():
    """
    Календарь загруженности отеля
    Визуализирует занятость номеров на ближайший месяц
    """
    # Получаем параметры или используем текущую дату
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    
    # Первый и последний день месяца
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    # Получаем все номера
    rooms = Room.query.order_by(Room.floor, Room.number).all()
    
    # Получаем все активные бронирования за период
    bookings = Booking.query.filter(
        and_(
            Booking.status.in_([
                BookingStatus.CONFIRMED.value,
                BookingStatus.CHECKED_IN.value
            ]),
            or_(
                and_(Booking.check_in <= last_day, Booking.check_out > first_day)
            )
        )
    ).all()
    
    # Создаем матрицу занятости
    # {room_id: {date: booking}}
    occupancy_matrix = {}
    for room in rooms:
        occupancy_matrix[room.id] = {}
        
        # Находим бронирования для этого номера
        room_bookings = [b for b in bookings if b.room_id == room.id]
        
        # Заполняем даты
        current_date = first_day
        while current_date <= last_day:
            for booking in room_bookings:
                if booking.check_in <= current_date < booking.check_out:
                    occupancy_matrix[room.id][current_date] = booking
                    break
            current_date += timedelta(days=1)
    
    # Создаем список дней месяца
    days = []
    current_date = first_day
    while current_date <= last_day:
        days.append(current_date)
        current_date += timedelta(days=1)
    
    # Навигация по месяцам
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    return render_template('bookings/calendar.html',
                         rooms=rooms,
                         days=days,
                         occupancy_matrix=occupancy_matrix,
                         current_month=month,
                         current_year=year,
                         prev_month=prev_month,
                         prev_year=prev_year,
                         next_month=next_month,
                         next_year=next_year)

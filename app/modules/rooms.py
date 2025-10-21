"""
Модуль управления номерами отеля
Автор: Солянов А.А.

Функционал:
- CRUD операции с номерами
- Просмотр списка номеров с фильтрацией
- Управление статусами номеров
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models.room import Room, RoomType
from datetime import datetime

bp = Blueprint('rooms', __name__, url_prefix='/rooms')


@bp.route('/')
def index():
    """
    Главная страница модуля номеров
    Отображает список всех номеров с возможностью фильтрации
    """
    # Получаем параметры фильтрации
    room_type = request.args.get('type', '')
    floor = request.args.get('floor', '')
    available_only = request.args.get('available', '')
    
    # Базовый запрос
    query = Room.query
    
    # Применяем фильтры
    if room_type:
        query = query.filter_by(room_type=room_type)
    if floor:
        query = query.filter_by(floor=int(floor))
    if available_only:
        query = query.filter_by(is_available=True)
    
    # Получаем отсортированный список
    rooms = query.order_by(Room.floor, Room.number).all()
    
    # Получаем уникальные этажи для фильтра
    floors = db.session.query(Room.floor).distinct().order_by(Room.floor).all()
    floors = [f[0] for f in floors]
    
    return render_template('rooms/index.html',
                         rooms=rooms,
                         room_types=RoomType,
                         floors=floors,
                         current_type=room_type,
                         current_floor=floor,
                         available_only=available_only)


@bp.route('/create', methods=['GET', 'POST'])
def create():
    """
    Создание нового номера
    GET: отображает форму создания
    POST: обрабатывает данные формы и создает номер
    """
    if request.method == 'POST':
        try:
            # Получаем данные из формы
            number = request.form.get('number')
            room_type = request.form.get('room_type')
            floor = int(request.form.get('floor'))
            capacity = int(request.form.get('capacity'))
            description = request.form.get('description', '')
            
            # Проверяем уникальность номера
            existing_room = Room.query.filter_by(number=number).first()
            if existing_room:
                flash('Номер с таким номером уже существует!', 'danger')
                return redirect(url_for('rooms.create'))
            
            # Создаем новый номер (цена установится автоматически)
            room = Room(
                number=number,
                room_type=room_type,
                floor=floor,
                capacity=capacity,
                description=description
            )
            
            db.session.add(room)
            db.session.commit()
            
            flash(f'Номер {number} успешно создан!', 'success')
            return redirect(url_for('rooms.index'))
            
        except ValueError as e:
            flash('Ошибка в данных формы. Проверьте корректность введенных значений.', 'danger')
            return redirect(url_for('rooms.create'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании номера: {str(e)}', 'danger')
            return redirect(url_for('rooms.create'))
    
    # GET запрос - показываем форму
    return render_template('rooms/create.html', room_types=RoomType)


@bp.route('/<int:room_id>')
def detail(room_id):
    """
    Детальная информация о номере
    Показывает все данные номера и историю бронирований
    """
    room = db.session.get(Room, room_id)
    if not room:
        flash('Номер не найден!', 'danger')
        return redirect(url_for('rooms.index'))
    
    # Получаем активные бронирования
    from app.models.booking import BookingStatus
    active_bookings = room.bookings.filter(
        Booking.status.in_([
            BookingStatus.PENDING.code,
            BookingStatus.CONFIRMED.code,
            BookingStatus.CHECKED_IN.code
        ])
    ).order_by(Booking.check_in).all()
    
    return render_template('rooms/detail.html', room=room, active_bookings=active_bookings)


@bp.route('/<int:room_id>/edit', methods=['GET', 'POST'])
def edit(room_id):
    """
    Редактирование номера
    GET: отображает форму редактирования
    POST: сохраняет изменения
    """
    room = db.session.get(Room, room_id)
    if not room:
        flash('Номер не найден!', 'danger')
        return redirect(url_for('rooms.index'))
    
    if request.method == 'POST':
        try:
            # Обновляем данные
            new_number = request.form.get('number')
            
            # Проверяем уникальность номера (если изменился)
            if new_number != room.number:
                existing_room = Room.query.filter_by(number=new_number).first()
                if existing_room:
                    flash('Номер с таким номером уже существует!', 'danger')
                    return redirect(url_for('rooms.edit', room_id=room_id))
                room.number = new_number
            
            room.room_type = request.form.get('room_type')
            room.floor = int(request.form.get('floor'))
            room.capacity = int(request.form.get('capacity'))
            room.description = request.form.get('description', '')
            room.is_available = request.form.get('is_available') == 'on'
            
            # Обновляем цену при изменении типа
            room._set_price_by_type()
            
            db.session.commit()
            
            flash(f'Номер {room.number} успешно обновлен!', 'success')
            return redirect(url_for('rooms.detail', room_id=room_id))
            
        except ValueError:
            flash('Ошибка в данных формы. Проверьте корректность введенных значений.', 'danger')
            return redirect(url_for('rooms.edit', room_id=room_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении номера: {str(e)}', 'danger')
            return redirect(url_for('rooms.edit', room_id=room_id))
    
    # GET запрос - показываем форму
    return render_template('rooms/edit.html', room=room, room_types=RoomType)


@bp.route('/<int:room_id>/delete', methods=['POST'])
def delete(room_id):
    """
    Удаление номера
    Удаляет номер и все связанные бронирования (cascade)
    """
    room = db.session.get(Room, room_id)
    if not room:
        flash('Номер не найден!', 'danger')
        return redirect(url_for('rooms.index'))
    
    try:
        room_number = room.number
        db.session.delete(room)
        db.session.commit()
        flash(f'Номер {room_number} успешно удален!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении номера: {str(e)}', 'danger')
    
    return redirect(url_for('rooms.index'))


@bp.route('/<int:room_id>/toggle_availability', methods=['POST'])
def toggle_availability(room_id):
    """
    Переключение статуса доступности номера
    AJAX endpoint
    """
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({'success': False, 'message': 'Номер не найден'}), 404
    
    try:
        room.is_available = not room.is_available
        db.session.commit()
        return jsonify({
            'success': True,
            'is_available': room.is_available,
            'message': f'Статус номера {room.number} изменен'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# Импорт Booking для использования в функциях
from app.models.booking import Booking

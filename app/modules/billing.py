# Биллинг: счета и платежи
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models.billing import Bill, Payment, BillStatus, PaymentMethod
from app.models.booking import Booking
from app.models.staff import Staff, Receptionist, Manager
from datetime import datetime
import json

bp = Blueprint('billing', __name__, url_prefix='/billing')


@bp.route('/')
def index():
    """
    Главная страница биллинга
    Отображает список всех счетов
    """
    status_filter = request.args.get('status', '')
    
    # Базовый запрос
    query = Bill.query
    
    # Фильтр по статусу
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    # Получаем счета
    bills = query.order_by(Bill.created_at.desc()).all()
    
    return render_template('billing/index.html',
                         bills=bills,
                         bill_statuses=BillStatus,
                         current_status=status_filter)


@bp.route('/create', methods=['GET', 'POST'])
def create():
    """
    Создание нового счёта
    Может быть создан вручную или на основе бронирования
    """
    if request.method == 'POST':
        try:
            # Получаем данные
            guest_name = request.form.get('guest_name')
            guest_contact = request.form.get('guest_contact')
            booking_id = request.form.get('booking_id')
            created_by_id = int(request.form.get('created_by_id'))
            notes = request.form.get('notes', '')
            
            # Проверяем сотрудника
            staff_member = db.session.get(Staff, created_by_id)
            if not staff_member:
                flash('Сотрудник не найден!', 'danger')
                return redirect(url_for('billing.create'))
            
            # Создаём счёт
            bill = Bill(
                guest_name=guest_name,
                guest_contact=guest_contact,
                created_by_id=created_by_id,
                booking_id=int(booking_id) if booking_id else None,
                notes=notes
            )
            
            # Если есть бронирование, добавляем автоматически
            if booking_id:
                booking = db.session.get(Booking, int(booking_id))
                if booking and isinstance(staff_member, Receptionist):
                    receptionist = staff_member
                    # Используем метод администратора для создания счёта
                    bill = receptionist.create_bill_for_booking(
                        booking, 
                        auto_from_booking=True
                    )
            
            # Получаем позиции из формы (JSON)
            items_json = request.form.get('items', '[]')
            try:
                items = json.loads(items_json)
                for item in items:
                    bill.add_item(
                        description=item.get('description', ''),
                        quantity=float(item.get('quantity', 1)),
                        unit_price=float(item.get('unit_price', 0))
                    )
            except json.JSONDecodeError:
                pass
            
            # Пересчитываем
            bill.recalc_totals()
            
            db.session.add(bill)
            db.session.commit()
            
            flash(f'Счёт #{bill.id} успешно создан!', 'success')
            return redirect(url_for('billing.detail', bill_id=bill.id))
            
        except ValueError as e:
            flash(f'Ошибка в данных формы: {str(e)}', 'danger')
            return redirect(url_for('billing.create'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании счёта: {str(e)}', 'danger')
            return redirect(url_for('billing.create'))
    
    # GET запрос - показываем форму
    booking_id = request.args.get('booking_id')
    booking = None
    if booking_id:
        booking = db.session.get(Booking, int(booking_id))
    
    # Получаем активный персонал
    staff_list = Staff.query.filter_by(is_active=True).all()
    
    return render_template('billing/create.html',
                         booking=booking,
                         staff_list=staff_list)


@bp.route('/<int:bill_id>')
def detail(bill_id):
    """
    Детальная информация о счёте
    """
    bill = db.session.get(Bill, bill_id)
    if not bill:
        flash('Счёт не найден!', 'danger')
        return redirect(url_for('billing.index'))
    
    # Получаем все платежи
    payments = bill.payments.order_by(Payment.created_at.desc()).all()
    
    return render_template('billing/detail.html',
                         bill=bill,
                         payments=payments,
                         payment_methods=PaymentMethod)


@bp.route('/<int:bill_id>/add_payment', methods=['POST'])
def add_payment(bill_id):
    """
    Добавление платежа к счёту
    """
    bill = db.session.get(Bill, bill_id)
    if not bill:
        flash('Счёт не найден!', 'danger')
        return redirect(url_for('billing.index'))
    
    try:
        # Получаем данные
        amount = float(request.form.get('amount'))
        method = request.form.get('method')
        received_by_id = int(request.form.get('received_by_id'))
        reference = request.form.get('reference', '')
        notes = request.form.get('notes', '')
        
        # Проверяем сотрудника
        staff_member = db.session.get(Staff, received_by_id)
        if not staff_member:
            flash('Сотрудник не найден!', 'danger')
            return redirect(url_for('billing.detail', bill_id=bill_id))
        
        # Создаём платёж
        if isinstance(staff_member, Receptionist):
            payment = staff_member.record_payment(
                bill, amount, method, reference, notes
            )
        else:
            payment = Payment(
                bill_id=bill.id,
                amount=amount,
                method=method,
                received_by_id=received_by_id,
                reference=reference,
                notes=notes
            )
            db.session.add(payment)
            bill.apply_payment(payment)
        
        db.session.commit()
        
        flash(f'Платёж на сумму {amount} руб. успешно добавлен!', 'success')
        
    except ValueError:
        flash('Ошибка в данных формы!', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при добавлении платежа: {str(e)}', 'danger')
    
    return redirect(url_for('billing.detail', bill_id=bill_id))


@bp.route('/<int:bill_id>/add_item', methods=['POST'])
def add_item(bill_id):
    """
    Добавление позиции к счёту
    """
    bill = db.session.get(Bill, bill_id)
    if not bill:
        return jsonify({'success': False, 'message': 'Счёт не найден'}), 404
    
    try:
        description = request.form.get('description')
        quantity = float(request.form.get('quantity'))
        unit_price = float(request.form.get('unit_price'))
        
        bill.add_item(description, quantity, unit_price)
        bill.recalc_totals()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'items': bill.items,
            'total': bill.total
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/<int:bill_id>/remove_item/<int:item_index>', methods=['POST'])
def remove_item(bill_id, item_index):
    """
    Удаление позиции из счёта
    """
    bill = db.session.get(Bill, bill_id)
    if not bill:
        return jsonify({'success': False, 'message': 'Счёт не найден'}), 404
    
    try:
        if bill.remove_item(item_index):
            bill.recalc_totals()
            db.session.commit()
            return jsonify({
                'success': True,
                'items': bill.items,
                'total': bill.total
            })
        else:
            return jsonify({'success': False, 'message': 'Позиция не найдена'}), 404
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/<int:bill_id>/cancel', methods=['POST'])
def cancel(bill_id):
    """
    Отмена счёта
    """
    bill = db.session.get(Bill, bill_id)
    if not bill:
        flash('Счёт не найден!', 'danger')
        return redirect(url_for('billing.index'))
    
    try:
        if bill.cancel():
            db.session.commit()
            flash(f'Счёт #{bill_id} отменён!', 'info')
        else:
            flash('Невозможно отменить счёт!', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при отмене: {str(e)}', 'danger')
    
    return redirect(url_for('billing.detail', bill_id=bill_id))


@bp.route('/<int:bill_id>/refund', methods=['POST'])
def refund(bill_id):
    """
    Возврат средств по счёту (только для менеджеров)
    """
    bill = db.session.get(Bill, bill_id)
    if not bill:
        flash('Счёт не найден!', 'danger')
        return redirect(url_for('billing.index'))
    
    try:
        amount = float(request.form.get('amount'))
        manager_id = int(request.form.get('manager_id'))
        note = request.form.get('note', '')
        
        # Проверяем менеджера
        manager = db.session.get(Manager, manager_id)
        if not manager or manager.role != 'manager':
            flash('Возврат может одобрить только менеджер!', 'danger')
            return redirect(url_for('billing.detail', bill_id=bill_id))
        
        # Одобряем возврат
        refund = manager.approve_refund(bill, amount, note)
        
        if refund:
            db.session.commit()
            flash(f'Возврат на сумму {amount} руб. одобрен!', 'success')
        else:
            flash('Ошибка при одобрении возврата!', 'danger')
            
    except ValueError:
        flash('Ошибка в данных формы!', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при возврате: {str(e)}', 'danger')
    
    return redirect(url_for('billing.detail', bill_id=bill_id))


@bp.route('/from_booking/<int:booking_id>')
def from_booking(booking_id):
    """
    Быстрое создание счёта из бронирования
    """
    booking = db.session.get(Booking, booking_id)
    if not booking:
        flash('Бронирование не найдено!', 'danger')
        return redirect(url_for('bookings.index'))
    
    # Проверяем, нет ли уже счёта для этого бронирования
    existing_bill = Bill.query.filter_by(booking_id=booking_id).first()
    if existing_bill:
        flash('Для этого бронирования уже существует счёт!', 'info')
        return redirect(url_for('billing.detail', bill_id=existing_bill.id))
    
    # Перенаправляем на форму создания с параметром
    return redirect(url_for('billing.create', booking_id=booking_id))

# Управление персоналом
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.models.staff import Staff, Manager, Receptionist, StaffRole
from datetime import datetime, date

bp = Blueprint('staff', __name__, url_prefix='/staff')


@bp.route('/')
def index():
    """
    Главная страница персонала
    Отображает список всех сотрудников с фильтрацией
    """
    role_filter = request.args.get('role', '')
    active_only = request.args.get('active', '')
    
    # Базовый запрос
    query = Staff.query
    
    # Фильтры
    if role_filter:
        query = query.filter_by(role=role_filter)
    if active_only:
        query = query.filter_by(is_active=True)
    
    # Получаем сотрудников
    staff_list = query.order_by(Staff.last_name, Staff.first_name).all()
    
    return render_template('staff/index.html',
                         staff_list=staff_list,
                         staff_roles=StaffRole,
                         current_role=role_filter,
                         active_only=active_only)


@bp.route('/create', methods=['GET', 'POST'])
def create():
    """
    Создание нового сотрудника
    """
    if request.method == 'POST':
        try:
            # Получаем данные из формы
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            role = request.form.get('role')
            hire_date_str = request.form.get('hire_date')
            notes = request.form.get('notes', '')
            
            # Парсим дату
            hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date()
            
            # Проверяем уникальность email
            existing_staff = Staff.query.filter_by(email=email).first()
            if existing_staff:
                flash('Сотрудник с таким email уже существует!', 'danger')
                return redirect(url_for('staff.create'))
            
            # Создаем сотрудника в зависимости от роли
            if role == 'manager':
                staff_member = Manager(first_name, last_name, email, phone, 
                                     hire_date, notes)
            elif role == 'receptionist':
                staff_member = Receptionist(first_name, last_name, email, phone,
                                          hire_date, notes)
            else:
                staff_member = Staff(first_name, last_name, email, phone,
                                   hire_date, role, notes)
            
            db.session.add(staff_member)
            db.session.commit()
            
            flash(f'Сотрудник {staff_member.full_name()} успешно добавлен!', 'success')
            return redirect(url_for('staff.index'))
            
        except ValueError:
            flash('Ошибка в данных формы!', 'danger')
            return redirect(url_for('staff.create'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании сотрудника: {str(e)}', 'danger')
            return redirect(url_for('staff.create'))
    
    # GET запрос - показываем форму
    return render_template('staff/create.html', staff_roles=StaffRole)


@bp.route('/<int:staff_id>')
def detail(staff_id):
    """
    Детальная информация о сотруднике
    """
    staff_member = db.session.get(Staff, staff_id)
    if not staff_member:
        flash('Сотрудник не найден!', 'danger')
        return redirect(url_for('staff.index'))
    
    # Статистика по счетам
    bills_created = staff_member.created_bills.count()
    payments_received = staff_member.received_payments.count()
    
    return render_template('staff/detail.html',
                         staff=staff_member,
                         bills_created=bills_created,
                         payments_received=payments_received)


@bp.route('/<int:staff_id>/edit', methods=['GET', 'POST'])
def edit(staff_id):
    """
    Редактирование сотрудника
    """
    staff_member = db.session.get(Staff, staff_id)
    if not staff_member:
        flash('Сотрудник не найден!', 'danger')
        return redirect(url_for('staff.index'))
    
    if request.method == 'POST':
        try:
            # Обновляем данные
            new_email = request.form.get('email')
            
            # Проверяем уникальность email (если изменился)
            if new_email != staff_member.email:
                existing_staff = Staff.query.filter_by(email=new_email).first()
                if existing_staff:
                    flash('Сотрудник с таким email уже существует!', 'danger')
                    return redirect(url_for('staff.edit', staff_id=staff_id))
                staff_member.email = new_email
            
            staff_member.first_name = request.form.get('first_name')
            staff_member.last_name = request.form.get('last_name')
            staff_member.phone = request.form.get('phone')
            staff_member.notes = request.form.get('notes', '')
            
            db.session.commit()
            
            flash(f'Данные сотрудника {staff_member.full_name()} обновлены!', 'success')
            return redirect(url_for('staff.detail', staff_id=staff_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении: {str(e)}', 'danger')
            return redirect(url_for('staff.edit', staff_id=staff_id))
    
    # GET запрос - показываем форму
    return render_template('staff/edit.html', staff=staff_member)


@bp.route('/<int:staff_id>/deactivate', methods=['POST'])
def deactivate(staff_id):
    """
    Деактивация сотрудника
    """
    staff_member = db.session.get(Staff, staff_id)
    if not staff_member:
        flash('Сотрудник не найден!', 'danger')
        return redirect(url_for('staff.index'))
    
    try:
        termination_date_str = request.form.get('termination_date')
        termination_date = None
        if termination_date_str:
            termination_date = datetime.strptime(termination_date_str, '%Y-%m-%d').date()
        
        staff_member.deactivate(termination_date)
        db.session.commit()
        
        flash(f'Сотрудник {staff_member.full_name()} деактивирован!', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при деактивации: {str(e)}', 'danger')
    
    return redirect(url_for('staff.detail', staff_id=staff_id))


@bp.route('/<int:staff_id>/activate', methods=['POST'])
def activate(staff_id):
    """
    Активация сотрудника
    """
    staff_member = db.session.get(Staff, staff_id)
    if not staff_member:
        flash('Сотрудник не найден!', 'danger')
        return redirect(url_for('staff.index'))
    
    try:
        staff_member.activate()
        db.session.commit()
        
        flash(f'Сотрудник {staff_member.full_name()} активирован!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при активации: {str(e)}', 'danger')
    
    return redirect(url_for('staff.detail', staff_id=staff_id))


@bp.route('/report', methods=['GET', 'POST'])
def report():
    """
    Генерация отчётов (доступно только менеджерам)
    """
    if request.method == 'POST':
        try:
            # Получаем ID менеджера и даты
            manager_id = int(request.form.get('manager_id'))
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')
            
            # Парсим даты
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            # Получаем менеджера
            manager = db.session.get(Manager, manager_id)
            if not manager or manager.role != 'manager':
                flash('Выбран неверный менеджер!', 'danger')
                return redirect(url_for('staff.report'))
            
            # Генерируем отчёт
            report_data = manager.generate_report(start_date, end_date)
            
            return render_template('staff/report_result.html',
                                 manager=manager,
                                 report=report_data)
            
        except ValueError:
            flash('Ошибка в данных формы!', 'danger')
            return redirect(url_for('staff.report'))
        except Exception as e:
            flash(f'Ошибка при генерации отчёта: {str(e)}', 'danger')
            return redirect(url_for('staff.report'))
    
    # GET запрос - показываем форму
    managers = Manager.query.filter_by(is_active=True, role='manager').all()
    
    # Если менеджеров нет, показываем предупреждение
    if not managers:
        flash('В системе нет активных менеджеров для генерации отчётов!', 'warning')
    
    return render_template('staff/report.html', managers=managers)

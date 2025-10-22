from datetime import datetime, timezone
from flask import Blueprint, jsonify, abort
from app import db 
from app.models.guests import Guest, GuestVisit
from app.models.service import ServiceOrder
from app.models.booking import Booking 

bp = Blueprint("stays", __name__, url_prefix="/stays")

# эндпоинт заселения
@stays_bp.post("/checkin/<int:booking_id>")
def checkin(booking_id: int):
    """
    Заселение гостя по брони:
    - проверяем статус/даты
    - создаём GuestVisit
    - переводим бронь в checked_in
    """
    booking = Booking.query.get_or_404(booking_id)

    # должен быть гость
    if not booking.guest_id:
        abort(400, "У бронирования не указан гость (guest_id)")

    if not booking.can_checkin():
        abort(400, "Бронь нельзя заселить (не подтверждена или дата ещё не наступила)")

    # Если уже есть визит — не дублируем
    if booking.visit:
        abort(400, "Визит по этой брони уже существует")

    # Базовая сумма проживания (берём из брони, предполагаем наличие total_price/amount)
    base_amount = float(getattr(booking, "total_price", 0) or getattr(booking, "amount", 0) or 0)

    # создание новой записи о фактическом проживании
    visit = GuestVisit(
        guest_id=booking.guest_id,
        booking_id=booking.id,
        room_id=booking.room_id,
        checkin_at=datetime.now(timezone.utc),
        base_amount=base_amount,
    )
    db.session.add(visit)

    booking.status = "checked_in"
    db.session.commit()

    # Возврат JSON-ответ с подтверждением и ключевыми данными
    return jsonify({
        "ok": True,
        "visit_id": visit.id,
        "booking_id": booking.id,
        "status": booking.status
    })

@bp.post("/checkout/<int:booking_id>")
def checkout(booking_id: int):
    """
    Выселение гостя:
    - проверяем статус
    - завершаем визит, пересчитываем суммы
    - переводим бронь в checked_out
    """
    booking = Booking.query.get_or_404(booking_id)
    if not booking.can_checkout():
        abort(400, "Выселение невозможно (бронь не в статусе 'checked_in')")

    if not booking.visit:
        abort(400, "Нет активного визита по данной брони")

    visit = booking.visit
    if visit.checkout_at:
        abort(400, "Визит уже закрыт")

    # Пересчёт итогов (услуги уже должны быть в статусе completed)
    visit.recalc_totals()
    visit.checkout_at = datetime.now(timezone.utc)

    booking.status = "checked_out"
    db.session.commit()

    return jsonify({
        "ok": True,
        "visit_id": visit.id,
        "booking_id": booking.id,
        "total_amount": float(visit.total_amount or 0),
        "services_amount": float(visit.services_amount or 0),
        "base_amount": float(visit.base_amount or 0),
        "status": booking.status
    })
from flask import Blueprint, request, jsonify, abort
from app import db  # type: ignore
from app.models.service import Service, ServiceOrder
from app.models.guests import GuestVisit

bp = Blueprint("services", __name__, url_prefix="/services")

@bp.get("/")
def list_services():
    # Прайс услуг (активные)
    items = Service.query.filter_by(is_active=True).order_by(Service.title.asc()).all()
    return jsonify([s.to_dict() for s in items])

@bp.post("/")
def create_service():
    # Создание/редактирование справочника услуг (админка на будущее)
    data = request.get_json(force=True, silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    title = (data.get("title") or "").strip()
    price = data.get("base_price", 0)

    if not code or not title:
        abort(400, "code и title обязательны")

    svc = Service(code=code, title=title, base_price=price, is_active=bool(data.get("is_active", True)))
    db.session.add(svc)
    db.session.commit()
    return jsonify(svc.to_dict()), 201

@bp.post("/orders")
def create_service_order():
    # Создание заказа услуги на визит
    data = request.get_json(force=True, silent=True) or {}
    visit_id = data.get("visit_id")
    service_id = data.get("service_id")
    quantity = int(data.get("quantity") or 1)
    note = (data.get("note") or "").strip()

    if not visit_id or not service_id:
        abort(400, "visit_id и service_id обязательны")

    visit = GuestVisit.query.get_or_404(int(visit_id))
    service = Service.query.get_or_404(int(service_id))

    order = ServiceOrder(
        visit_id=visit.id,
        service_id=service.id,
        quantity=max(1, quantity),
        unit_price=service.base_price,  # фиксируем цену на момент заказа
        status="pending",
        note=note or None,
    )
    db.session.add(order)
    db.session.commit()

    return jsonify({
        "id": order.id,
        "visit_id": order.visit_id,
        "service": service.to_dict(),
        "quantity": order.quantity,
        "unit_price": float(order.unit_price or 0),
        "status": order.status,
        "subtotal": order.subtotal(),
    }), 201

@bp.post("/orders/<int:order_id>/complete")
def complete_service_order(order_id: int):
    # Закрыть заказ (выполнено)
    order = ServiceOrder.query.get_or_404(order_id)
    order.status = "completed"
    db.session.commit()

    # Пересчитать итоги визита после выполнения услуги
    order.visit.recalc_totals()
    db.session.commit()

    return jsonify({"ok": True, "subtotal": order.subtotal()})

@bp.post("/orders/<int:order_id>/cancel")
def cancel_service_order(order_id: int):
    # Отмена заказа (если ещё не выполнен)
    order = ServiceOrder.query.get_or_404(order_id)
    if order.status == "completed":
        abort(400, "Нельзя отменить уже выполненный заказ")
    order.status = "canceled"
    db.session.commit()
    return jsonify({"ok": True})

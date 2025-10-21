# app/modules/guests.py
# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify, abort
from sqlalchemy.exc import IntegrityError
from app import db  # type: ignore
from app.models.guests import Guest, GuestVisit

guests_bp = Blueprint("guests", __name__, url_prefix="/guests")

@guests_bp.get("/")
def list_guests():
    # Список гостей с фильтрами (поиск по имени/телефону/почте)
    q = request.args.get("q", "", type=str).strip()
    query = Guest.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Guest.first_name.ilike(like),
                Guest.last_name.ilike(like),
                Guest.phone.ilike(like),
                Guest.email.ilike(like),
                Guest.doc_number.ilike(like),
            )
        )
    items = query.order_by(Guest.created_at.desc()).limit(200).all()
    return jsonify([g.to_dict() for g in items])

@guests_bp.get("/<int:guest_id>")
def get_guest(guest_id: int):
    # Карточка гостя с историей визитов
    guest = Guest.query.get_or_404(guest_id)
    visits = [{
        "visit_id": v.id,
        "booking_id": v.booking_id,
        "room_id": v.room_id,
        "checkin_at": v.checkin_at.isoformat() if v.checkin_at else None,
        "checkout_at": v.checkout_at.isoformat() if v.checkout_at else None,
        "base_amount": float(v.base_amount or 0),
        "services_amount": float(v.services_amount or 0),
        "total_amount": float(v.total_amount or 0),
    } for v in sorted(guest.visits, key=lambda x: x.checkin_at or x.created_at)]
    data = guest.to_dict()
    data["visits"] = visits
    return jsonify(data)

@guests_bp.post("/")
def create_guest():
    # Создание гостя
    data = request.get_json(force=True, silent=True) or {}
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    if not first_name or not last_name:
        abort(400, "first_name и last_name обязательны")

    guest = Guest(
        first_name=first_name,
        last_name=last_name,
        phone=(data.get("phone") or "").strip() or None,
        email=(data.get("email") or "").strip() or None,
        doc_number=(data.get("doc_number") or "").strip() or None,
    )
    db.session.add(guest)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, "Конфликт данных (возможно, дублирующийся email/doc_number)")

    return jsonify(guest.to_dict()), 201

@guests_bp.put("/<int:guest_id>")
def update_guest(guest_id: int):
    # Редактирование гостя
    guest = Guest.query.get_or_404(guest_id)
    data = request.get_json(force=True, silent=True) or {}

    for field in ("first_name", "last_name", "phone", "email", "doc_number"):
        if field in data and data[field] is not None:
            setattr(guest, field, str(data[field]).strip())

    db.session.commit()
    return jsonify(guest.to_dict())

@guests_bp.delete("/<int:guest_id>")
def delete_guest(guest_id: int):
    # Удаление гостя (каскадно удалит визиты и заказы услуг)
    guest = Guest.query.get_or_404(guest_id)
    db.session.delete(guest)
    db.session.commit()
    return jsonify({"ok": True})
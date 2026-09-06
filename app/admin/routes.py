from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models import Restaurant, MenuItem, Order, ORDER_STATUSES, User
from app.security import role_required

admin_bp = Blueprint("admin", __name__)


def _admin_restaurant(user_id):
    """A restaurant admin manages the single restaurant they're assigned to at signup/seed time."""
    user = db.session.get(User, user_id)
    if not user.restaurant_id:
        abort(403, "This admin account is not linked to a restaurant.")
    return Restaurant.query.get_or_404(user.restaurant_id)


@admin_bp.route("/")
@role_required("admin")
def dashboard():
    user_id = int(get_jwt_identity())
    restaurant = _admin_restaurant(user_id)

    orders = Order.query.filter_by(restaurant_id=restaurant.id).order_by(Order.created_at.desc()).all()
    pending = [o for o in orders if o.status in ("placed", "preparing", "out_for_delivery")]
    revenue = sum((o.total_amount for o in orders if o.status != "cancelled"), Decimal("0.00"))

    stats = {
        "total_orders": len(orders),
        "pending_orders": len(pending),
        "revenue": revenue,
        "menu_item_count": MenuItem.query.filter_by(restaurant_id=restaurant.id).count(),
    }
    return render_template(
        "admin/dashboard.html", restaurant=restaurant, stats=stats, recent_orders=orders[:8]
    )


@admin_bp.route("/menu", methods=["GET", "POST"])
@role_required("admin")
def menu():
    user_id = int(get_jwt_identity())
    restaurant = _admin_restaurant(user_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "Main").strip() or "Main"
        icon = request.form.get("icon", "🍔").strip() or "🍔"
        try:
            price = Decimal(request.form.get("price", "0"))
        except InvalidOperation:
            price = Decimal("0")

        if not name or price <= 0:
            flash("Please provide a valid item name and price.", "error")
        else:
            db.session.add(
                MenuItem(
                    restaurant_id=restaurant.id,
                    name=name,
                    description=description,
                    category=category,
                    icon=icon,
                    price=price,
                )
            )
            db.session.commit()
            flash(f"Added {name} to the menu.", "success")
        return redirect(url_for("admin.menu"))

    items = MenuItem.query.filter_by(restaurant_id=restaurant.id).order_by(MenuItem.category, MenuItem.name).all()
    return render_template("admin/menu.html", restaurant=restaurant, items=items)


@admin_bp.route("/menu/<int:item_id>/toggle", methods=["POST"])
@role_required("admin")
def toggle_menu_item(item_id):
    user_id = int(get_jwt_identity())
    restaurant = _admin_restaurant(user_id)
    item = MenuItem.query.filter_by(id=item_id, restaurant_id=restaurant.id).first_or_404()
    item.is_available = not item.is_available
    db.session.commit()
    return redirect(url_for("admin.menu"))


@admin_bp.route("/menu/<int:item_id>/delete", methods=["POST"])
@role_required("admin")
def delete_menu_item(item_id):
    user_id = int(get_jwt_identity())
    restaurant = _admin_restaurant(user_id)
    item = MenuItem.query.filter_by(id=item_id, restaurant_id=restaurant.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Menu item removed.", "success")
    return redirect(url_for("admin.menu"))


@admin_bp.route("/orders")
@role_required("admin")
def orders():
    user_id = int(get_jwt_identity())
    restaurant = _admin_restaurant(user_id)
    all_orders = Order.query.filter_by(restaurant_id=restaurant.id).order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", restaurant=restaurant, orders=all_orders, statuses=ORDER_STATUSES)


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@role_required("admin")
def update_order_status(order_id):
    user_id = int(get_jwt_identity())
    restaurant = _admin_restaurant(user_id)
    order = Order.query.filter_by(id=order_id, restaurant_id=restaurant.id).first_or_404()

    new_status = request.form.get("status")
    if new_status in ORDER_STATUSES:
        order.status = new_status
        db.session.commit()
        flash(f"Order #{order.id} marked as {new_status.replace('_', ' ')}.", "success")
    return redirect(url_for("admin.orders"))

from decimal import Decimal

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_jwt_extended import get_jwt_identity, get_jwt

from app.extensions import db, limiter
from app.models import Restaurant, MenuItem, CartItem, Order, OrderItem
from app.security import login_required

customer_bp = Blueprint("customer", __name__)


@customer_bp.route("/")
def index():
    return redirect(url_for("customer.restaurants"))


@customer_bp.route("/restaurants")
def restaurants():
    all_restaurants = Restaurant.query.filter_by(is_active=True).order_by(Restaurant.name).all()
    return render_template("customer/restaurants.html", restaurants=all_restaurants)


@customer_bp.route("/restaurants/<int:restaurant_id>/menu")
def menu(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    items = MenuItem.query.filter_by(restaurant_id=restaurant.id, is_available=True).order_by(MenuItem.category).all()
    return render_template("customer/menu.html", restaurant=restaurant, items=items)


def _cart_for_user(user_id):
    return (
        CartItem.query.filter_by(user_id=user_id)
        .join(MenuItem)
        .order_by(CartItem.created_at)
        .all()
    )


@customer_bp.route("/cart")
@login_required
def cart():
    user_id = int(get_jwt_identity())
    items = _cart_for_user(user_id)
    total = sum((item.menu_item.price * item.quantity for item in items), Decimal("0.00"))
    return render_template("customer/cart.html", items=items, total=total)


@customer_bp.route("/cart/add/<int:menu_item_id>", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def add_to_cart(menu_item_id):
    user_id = int(get_jwt_identity())
    menu_item = MenuItem.query.get_or_404(menu_item_id)
    if not menu_item.is_available:
        abort(400)

    existing = CartItem.query.filter_by(user_id=user_id, menu_item_id=menu_item_id).first()
    if existing:
        existing.quantity += 1
    else:
        db.session.add(CartItem(user_id=user_id, menu_item_id=menu_item_id, quantity=1))
    db.session.commit()
    flash(f"Added {menu_item.name} to your cart.", "success")
    return redirect(url_for("customer.menu", restaurant_id=menu_item.restaurant_id))


@customer_bp.route("/cart/update/<int:cart_item_id>", methods=["POST"])
@login_required
def update_cart(cart_item_id):
    user_id = int(get_jwt_identity())
    item = CartItem.query.filter_by(id=cart_item_id, user_id=user_id).first_or_404()
    try:
        quantity = int(request.form.get("quantity", 1))
    except ValueError:
        quantity = 1

    if quantity <= 0:
        db.session.delete(item)
    else:
        item.quantity = min(quantity, 20)
    db.session.commit()
    return redirect(url_for("customer.cart"))


@customer_bp.route("/cart/remove/<int:cart_item_id>", methods=["POST"])
@login_required
def remove_from_cart(cart_item_id):
    user_id = int(get_jwt_identity())
    item = CartItem.query.filter_by(id=cart_item_id, user_id=user_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Item removed from cart.", "success")
    return redirect(url_for("customer.cart"))


@customer_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    user_id = int(get_jwt_identity())
    items = _cart_for_user(user_id)
    if not items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("customer.restaurants"))

    restaurant_ids = {item.menu_item.restaurant_id for item in items}
    if len(restaurant_ids) > 1:
        flash("You can only order from one restaurant at a time.", "error")
        return redirect(url_for("customer.cart"))

    total = sum((item.menu_item.price * item.quantity for item in items), Decimal("0.00"))

    if request.method == "POST":
        address = request.form.get("delivery_address", "").strip()
        if not address:
            flash("Please provide a delivery address.", "error")
            return render_template("customer/checkout.html", items=items, total=total)

        order = Order(
            user_id=user_id,
            restaurant_id=restaurant_ids.pop(),
            status="placed",
            total_amount=total,
            delivery_address=address,
        )
        for item in items:
            order.items.append(
                OrderItem(
                    menu_item_id=item.menu_item.id,
                    name_snapshot=item.menu_item.name,
                    price_snapshot=item.menu_item.price,
                    quantity=item.quantity,
                )
            )
            db.session.delete(item)

        db.session.add(order)
        db.session.commit()
        flash("Order placed successfully!", "success")
        return redirect(url_for("customer.order_detail", order_id=order.id))

    return render_template("customer/checkout.html", items=items, total=total)


@customer_bp.route("/orders")
@login_required
def orders():
    user_id = int(get_jwt_identity())
    user_orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    return render_template("customer/orders.html", orders=user_orders)


@customer_bp.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    user_id = int(get_jwt_identity())
    order = Order.query.filter_by(id=order_id, user_id=user_id).first_or_404()
    return render_template("customer/order_detail.html", order=order)

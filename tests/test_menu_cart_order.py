from tests.conftest import login
from app.models import Restaurant, MenuItem, Order


def test_browse_restaurants_and_menu(client):
    resp = client.get("/restaurants")
    assert resp.status_code == 200
    assert b"Bella Italia" in resp.data

    restaurant = Restaurant.query.filter_by(name="Bella Italia").first()
    resp = client.get(f"/restaurants/{restaurant.id}/menu")
    assert b"Margherita Pizza" in resp.data


def test_add_to_cart_requires_login(client):
    item = MenuItem.query.filter_by(name="Margherita Pizza").first()
    resp = client.post(f"/cart/add/{item.id}", follow_redirects=True)
    assert b"Login to your account" in resp.data


def test_full_order_flow(client, app):
    login(client, "customer@foodies.com", "Customer123!")

    item = MenuItem.query.filter_by(name="Margherita Pizza").first()
    client.post(f"/cart/add/{item.id}", follow_redirects=True)

    resp = client.get("/cart")
    assert b"Margherita Pizza" in resp.data

    resp = client.post("/checkout", data={"delivery_address": "221B Baker Street"}, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        order = Order.query.first()
        assert order is not None
        assert str(order.total_amount) == str(item.price)
        assert order.status == "placed"


def test_sql_injection_style_input_is_safe(client):
    """A classic SQLi payload must never authenticate; it's rejected by validation or the
    ORM's parameterized lookup returns no match either way, never a raw-query error/bypass."""
    resp = client.post(
        "/auth/login",
        data={"email": "' OR 1=1 --", "password": "anything"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Login to your account" in resp.data

    # Confirm no session was actually established.
    orders_resp = client.get("/orders", follow_redirects=True)
    assert b"Login to your account" in orders_resp.data

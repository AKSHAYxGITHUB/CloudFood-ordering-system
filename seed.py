"""Seeds sample restaurants, menu items, and a restaurant-admin + demo customer account.

Run via `flask --app wsgi init-db` (wraps this in an app context and calls db.create_all() first).
Admin accounts are intentionally not created through public signup, since only the customer
role is exposed there.
"""
import os

from app.extensions import db
from app.models import User, Restaurant, MenuItem


SAMPLE_RESTAURANTS = [
    {
        "name": "Bella Italia",
        "description": "Wood-fired pizza and fresh handmade pasta.",
        "cuisine": "Italian",
        "icon": "🍕",
        "menu": [
            ("Margherita Pizza", "Tomato, mozzarella, fresh basil", "Pizza", 9.99, "🍕"),
            ("Pepperoni Pizza", "Classic pepperoni with mozzarella", "Pizza", 11.49, "🍕"),
            ("Spaghetti Carbonara", "Egg, pancetta, parmesan, black pepper", "Pasta", 12.99, "🍝"),
            ("Tiramisu", "Espresso-soaked ladyfingers, mascarpone", "Dessert", 6.5, "🍰"),
        ],
    },
    {
        "name": "Spice Route",
        "description": "Authentic North Indian curries and tandoori grills.",
        "cuisine": "Indian",
        "icon": "🍛",
        "menu": [
            ("Butter Chicken", "Creamy tomato curry with tandoori chicken", "Main", 13.99, "🍛"),
            ("Paneer Tikka", "Chargrilled cottage cheese skewers", "Starter", 8.99, "🧆"),
            ("Garlic Naan", "Tandoor-baked flatbread with garlic butter", "Bread", 3.5, "🫓"),
            ("Gulab Jamun", "Warm milk-solid dumplings in sugar syrup", "Dessert", 4.5, "🍮"),
        ],
    },
    {
        "name": "Dragon Wok",
        "description": "Wok-fired Chinese favorites, made fast and fresh.",
        "cuisine": "Chinese",
        "icon": "🥡",
        "menu": [
            ("Kung Pao Chicken", "Spicy stir-fry with peanuts and chili", "Main", 11.99, "🥡"),
            ("Vegetable Spring Rolls", "Crispy rolls with sweet chili dip", "Starter", 5.99, "🥟"),
            ("Egg Fried Rice", "Wok-tossed rice with egg and scallions", "Rice", 6.99, "🍚"),
        ],
    },
]


def run_seed():
    if Restaurant.query.first():
        print("Seed data already present, skipping.")
        return

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@foodies.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")

    first_restaurant = None
    for r in SAMPLE_RESTAURANTS:
        restaurant = Restaurant(
            name=r["name"], description=r["description"], cuisine=r["cuisine"], icon=r["icon"]
        )
        db.session.add(restaurant)
        db.session.flush()  # get restaurant.id
        if first_restaurant is None:
            first_restaurant = restaurant

        for name, desc, category, price, icon in r["menu"]:
            db.session.add(
                MenuItem(
                    restaurant_id=restaurant.id,
                    name=name,
                    description=desc,
                    category=category,
                    price=price,
                    icon=icon,
                )
            )

    admin = User(name="Restaurant Admin", email=admin_email, role="admin", restaurant_id=first_restaurant.id)
    admin.set_password(admin_password)
    db.session.add(admin)

    demo_customer = User(name="Demo Customer", email="customer@foodies.com", role="customer")
    demo_customer.set_password("Customer123!")
    db.session.add(demo_customer)

    db.session.commit()
    print(f"Seeded {len(SAMPLE_RESTAURANTS)} restaurants, admin '{admin_email}', and a demo customer.")

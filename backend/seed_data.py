"""Generate 90 days of realistic cafe mock data."""

import random
import sys
from datetime import date, datetime, timedelta
from typing import Dict, List, Set
from zoneinfo import ZoneInfo

from sqlalchemy import text

from database import SessionLocal, init_db
from models import (
    Customer,
    DailySummary,
    InventorySnapshot,
    MenuItem,
    Order,
    OrderItem,
    PurchaseOrder,
    Restaurant,
)

IST = ZoneInfo("Asia/Kolkata")
random.seed(42)

# -- Menu catalog --
MENU_ITEMS = [
    # (name, category, base_price_inr, cost_price_inr, item_type)
    ("Espresso", "Coffee", 180, 45, "veg"),
    ("Americano", "Coffee", 220, 50, "veg"),
    ("Cappuccino", "Coffee", 260, 60, "veg"),
    ("Latte", "Coffee", 280, 65, "veg"),
    ("Mocha", "Coffee", 320, 80, "veg"),
    ("Cold Brew", "Coffee", 300, 55, "veg"),
    ("Iced Latte", "Coffee", 300, 65, "veg"),
    ("Matcha Latte", "Specialty", 340, 90, "veg"),
    ("Chai Latte", "Specialty", 240, 50, "veg"),
    ("Hot Chocolate", "Specialty", 280, 70, "veg"),
    ("Fresh Juice", "Beverages", 220, 60, "veg"),
    ("Smoothie Bowl", "Beverages", 380, 110, "veg"),
    ("Iced Tea", "Beverages", 200, 40, "veg"),
    ("Club Sandwich", "Sandwiches", 320, 100, "non_veg"),
    ("Grilled Panini", "Sandwiches", 350, 110, "veg"),
    ("Avocado Toast", "Sandwiches", 380, 120, "veg"),
    ("Chicken Wrap", "Sandwiches", 340, 115, "non_veg"),
    ("Caesar Salad", "Salads", 360, 100, "non_veg"),
    ("Greek Salad", "Salads", 320, 90, "veg"),
    ("Quinoa Bowl", "Salads", 400, 130, "veg"),
    ("Margherita Pizza", "Pizza", 450, 140, "veg"),
    ("Pepperoni Pizza", "Pizza", 520, 170, "non_veg"),
    ("Pasta Alfredo", "Pasta", 420, 130, "veg"),
    ("Penne Arrabbiata", "Pasta", 380, 110, "veg"),
    ("Chocolate Cake", "Desserts", 280, 80, "egg"),
    ("Cheesecake", "Desserts", 320, 95, "egg"),
    ("Brownie", "Desserts", 220, 60, "egg"),
    ("Tiramisu", "Desserts", 360, 100, "egg"),
    ("Croissant", "Bakery", 180, 50, "egg"),
    ("Muffin", "Bakery", 160, 40, "egg"),
    ("Banana Bread", "Bakery", 200, 55, "egg"),
    ("Scone", "Bakery", 180, 45, "egg"),
    ("Eggs Benedict", "Breakfast", 420, 140, "egg"),
    ("Pancakes", "Breakfast", 360, 100, "egg"),
    ("French Toast", "Breakfast", 340, 95, "egg"),
    ("Granola Bowl", "Breakfast", 300, 80, "veg"),
    ("Garlic Bread", "Sides", 180, 45, "veg"),
    ("Fries", "Sides", 200, 50, "veg"),
    ("Soup of the Day", "Sides", 240, 60, "veg"),
    ("Bruschetta", "Sides", 260, 70, "veg"),
]

PLATFORMS = ["direct", "swiggy", "zomato"]
PLATFORM_WEIGHTS = [0.50, 0.30, 0.20]
ORDER_TYPES = {"direct": "dine_in", "swiggy": "delivery", "zomato": "delivery"}
PAYMENT_MODES = ["cash", "card", "upi", "online"]
PAYMENT_WEIGHTS = [0.15, 0.20, 0.40, 0.25]
STAFF = ["Rahul", "Priya", "Amit", "Sneha", "Vikram"]
TABLES = [f"T{i}" for i in range(1, 16)]

VENDORS = ["FreshFarms", "Metro Wholesale", "Daily Dairy", "Spice World", "BakeMaster"]
INVENTORY_ITEMS = [
    ("Coffee Beans", "kg"), ("Milk", "litre"), ("Sugar", "kg"),
    ("Flour", "kg"), ("Butter", "kg"), ("Cheese", "kg"),
    ("Chicken", "kg"), ("Vegetables", "kg"), ("Bread", "loaf"),
    ("Eggs", "dozen"), ("Cream", "litre"), ("Chocolate", "kg"),
    ("Pasta", "kg"), ("Rice", "kg"), ("Oil", "litre"),
    ("Tomatoes", "kg"), ("Onions", "kg"), ("Potatoes", "kg"),
    ("Tea Leaves", "kg"), ("Ice Cream", "litre"),
]


def _hour_weight(hour: int, is_weekend: bool) -> float:
    """Weight for order probability by hour — models real cafe traffic."""
    base = {
        8: 0.3, 9: 0.7, 10: 0.5, 11: 0.6, 12: 1.0, 13: 1.0,
        14: 0.6, 15: 0.5, 16: 0.7, 17: 0.8, 18: 0.9, 19: 1.0,
        20: 0.8, 21: 0.5, 22: 0.2,
    }.get(hour, 0.1)
    return base * (1.3 if is_weekend else 1.0)


def seed() -> None:
    """Run the full seed process."""
    init_db()
    db = SessionLocal()

    try:
        # Clear existing data
        for tbl in [
            "order_items", "orders", "daily_summaries", "inventory_snapshots",
            "purchase_orders", "customers", "menu_items", "restaurants",
        ]:
            db.execute(text(f"DELETE FROM {tbl}"))
        db.commit()

        # 1. Create demo restaurant
        restaurant = Restaurant(
            name="YoursTruly Cafe",
            slug="yourstruly-cafe",
            timezone="Asia/Kolkata",
            notification_emails="owner@yourstruly.in",
        )
        db.add(restaurant)
        db.flush()
        rid = restaurant.id
        print(f"Created restaurant: {restaurant.name} (id={rid})")

        # 2. Seed menu items
        menu_map: Dict[str, MenuItem] = {}
        for name, cat, price, cost, itype in MENU_ITEMS:
            mi = MenuItem(
                restaurant_id=rid, name=name, category=cat,
                base_price=price * 100, cost_price=cost * 100, item_type=itype,
            )
            db.add(mi)
            menu_map[name] = mi
        db.flush()
        print(f"Seeded {len(MENU_ITEMS)} menu items")

        # 3. Seed customers (power law distribution)
        customers: List[Customer] = []
        for i in range(200):
            cust = Customer(
                restaurant_id=rid,
                phone=f"98{random.randint(10000000, 99999999)}",
                name=f"Customer {i + 1}",
                first_visit=date.today() - timedelta(days=random.randint(1, 180)),
                total_visits=0,
                total_spend=0,
                loyalty_tier="new",
            )
            db.add(cust)
            customers.append(cust)
        db.flush()
        print(f"Seeded {len(customers)} customers")

        # 4. Generate 90 days of orders
        end_date = date.today()
        start_date = end_date - timedelta(days=89)
        total_orders = 0
        total_items = 0

        current = start_date
        while current <= end_date:
            is_weekend = current.weekday() >= 5
            day_orders = 0
            day_revenue = 0
            day_tax = 0
            day_discounts = 0
            day_commissions = 0
            day_cancel = 0
            platform_rev: Dict[str, int] = {}
            payment_rev: Dict[str, int] = {}
            cust_set: Set[int] = set()

            # Generate orders hour by hour
            for hour in range(8, 23):
                weight = _hour_weight(hour, is_weekend)
                num_orders = int(random.gauss(7 * weight, 2))
                num_orders = max(0, num_orders)

                for _ in range(num_orders):
                    minute = random.randint(0, 59)
                    ordered_at = datetime(
                        current.year, current.month, current.day,
                        hour, minute, random.randint(0, 59), tzinfo=IST,
                    )

                    platform = random.choices(PLATFORMS, PLATFORM_WEIGHTS)[0]
                    order_type = ORDER_TYPES[platform]
                    if platform == "direct" and random.random() < 0.3:
                        order_type = "takeaway"

                    payment = random.choices(PAYMENT_MODES, PAYMENT_WEIGHTS)[0]
                    if platform != "direct":
                        payment = "online"

                    # Pick customer (power law — first 30 are regulars)
                    if random.random() < 0.4:
                        cust = random.choice(customers[:30])
                    else:
                        cust = random.choice(customers)

                    is_cancelled = random.random() < 0.03
                    cancel_reason = random.choice([
                        "customer_request", "out_of_stock", "kitchen_delay",
                    ]) if is_cancelled else None

                    # Build order items (2-4 items)
                    num_items = random.choices([1, 2, 3, 4], [0.15, 0.40, 0.30, 0.15])[0]
                    chosen_items = random.sample(list(menu_map.keys()), min(num_items, len(menu_map)))

                    subtotal = 0
                    order_items: List[OrderItem] = []
                    for item_name in chosen_items:
                        mi = menu_map[item_name]
                        qty = random.choices([1, 2], [0.8, 0.2])[0]
                        item_total = mi.base_price * qty
                        subtotal += item_total
                        oi = OrderItem(
                            restaurant_id=rid, item_name=item_name,
                            category=mi.category, quantity=qty,
                            unit_price=mi.base_price, total_price=item_total,
                            cost_price=mi.cost_price * qty,
                            menu_item_id=mi.id,
                        )
                        order_items.append(oi)

                    # Void simulation for leakage module — ~5% of non-cancelled orders
                    if not is_cancelled and random.random() < 0.05:
                        void_target = random.choice(order_items)
                        void_target.is_void = True
                        void_target.void_reason = random.choice([
                            "wrong_item", "quality_issue",
                            "customer_changed_mind", "kitchen_error",
                        ])

                    tax = int(subtotal * 0.05)  # 5% GST
                    discount = int(subtotal * random.choice([0, 0, 0, 0.05, 0.1, 0.15])) if not is_cancelled else 0
                    commission = int(subtotal * 0.22) if platform == "swiggy" else (
                        int(subtotal * 0.18) if platform == "zomato" else 0
                    )
                    total = subtotal + tax - discount
                    net = total - commission

                    order = Order(
                        restaurant_id=rid, order_type=order_type,
                        platform=platform, payment_mode=payment,
                        status="cancelled" if is_cancelled else "completed",
                        customer_id=cust.id,
                        subtotal=subtotal, tax_amount=tax,
                        discount_amount=discount, platform_commission=commission,
                        total_amount=total, net_amount=net,
                        item_count=len(order_items),
                        table_number=random.choice(TABLES) if order_type == "dine_in" else None,
                        staff_name=random.choice(STAFF),
                        is_cancelled=is_cancelled, cancel_reason=cancel_reason,
                        preparation_minutes=None if is_cancelled else max(5, int(random.gauss(20, 8))),
                        ordered_at=ordered_at,
                    )
                    db.add(order)
                    db.flush()

                    for oi in order_items:
                        oi.order_id = order.id
                        db.add(oi)

                    if not is_cancelled:
                        day_revenue += total
                        day_tax += tax
                        day_discounts += discount
                        day_commissions += commission
                        platform_rev[platform] = platform_rev.get(platform, 0) + total
                        payment_rev[payment] = payment_rev.get(payment, 0) + total
                        cust_set.add(cust.id)
                        cust.total_visits += 1
                        cust.total_spend += total
                        cust.last_visit = current
                    else:
                        day_cancel += 1

                    day_orders += 1
                    total_items += len(order_items)

            # Daily summary
            completed = day_orders - day_cancel
            summary = DailySummary(
                restaurant_id=rid, summary_date=current,
                total_revenue=day_revenue,
                net_revenue=day_revenue - day_commissions,
                total_tax=day_tax,
                total_discounts=day_discounts,
                total_commissions=day_commissions,
                total_orders=completed,
                dine_in_orders=int(completed * 0.5),
                delivery_orders=int(completed * 0.3),
                takeaway_orders=int(completed * 0.2),
                cancelled_orders=day_cancel,
                avg_order_value=day_revenue // max(completed, 1),
                unique_customers=len(cust_set),
                new_customers=len(cust_set) // 5,
                returning_customers=len(cust_set) - len(cust_set) // 5,
                platform_revenue=platform_rev,
                payment_mode_breakdown=payment_rev,
            )
            db.add(summary)

            # Inventory snapshots
            for item_name, unit in INVENTORY_ITEMS:
                opening = round(random.uniform(5, 50), 1)
                consumed = round(random.uniform(2, opening * 0.6), 1)
                wasted = round(random.uniform(0, consumed * 0.05), 2)
                closing = round(opening - consumed - wasted, 1)
                snap = InventorySnapshot(
                    restaurant_id=rid, snapshot_date=current,
                    item_name=item_name, unit=unit,
                    opening_qty=opening, closing_qty=max(0, closing),
                    consumed_qty=consumed, wasted_qty=wasted,
                )
                db.add(snap)

            # Purchase orders (a few per day)
            if random.random() < 0.6:
                for _ in range(random.randint(1, 3)):
                    inv_item, unit = random.choice(INVENTORY_ITEMS)
                    qty = round(random.uniform(5, 30), 1)
                    unit_cost = random.randint(50, 500) * 100  # paisa
                    po = PurchaseOrder(
                        restaurant_id=rid,
                        vendor_name=random.choice(VENDORS),
                        item_name=inv_item, quantity=qty, unit=unit,
                        unit_cost=unit_cost, total_cost=int(qty * unit_cost),
                        order_date=current, delivery_date=current,
                        status="delivered",
                    )
                    db.add(po)

            total_orders += day_orders
            current += timedelta(days=1)

            # Commit every 10 days to avoid memory buildup
            if (current - start_date).days % 10 == 0:
                db.commit()

        # Update customer loyalty tiers
        for cust in customers:
            if cust.total_visits >= 20:
                cust.loyalty_tier = "champion"
            elif cust.total_visits >= 10:
                cust.loyalty_tier = "loyal"
            elif cust.total_visits >= 5:
                cust.loyalty_tier = "regular"
            elif cust.total_visits >= 1:
                cust.loyalty_tier = "casual"
            if cust.total_visits > 0:
                cust.avg_order_value = cust.total_spend // cust.total_visits

        db.commit()

        print(f"\nSeed complete:")
        print(f"  Days: 90 ({start_date} to {end_date})")
        print(f"  Orders: {total_orders}")
        print(f"  Order items: {total_items}")
        print(f"  Customers: {len(customers)}")
        print(f"  Menu items: {len(MENU_ITEMS)}")
        print(f"  Inventory items: {len(INVENTORY_ITEMS)}")

    except Exception as exc:
        db.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()

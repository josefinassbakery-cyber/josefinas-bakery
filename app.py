from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "josefinas_bakery.db")

app = Flask(__name__)


# ============================================================
# PRODUCTOS — precios corregidos según la lista vigente
# ============================================================

PRODUCTS = [
    # PANES SALADOS
    ("Pan de Jamón 16 pulgadas", 34.00),
    ("Pan de Jamón con queso crema", 35.00),
    ("Mini Pan de Jamón", 10.00),
    ("Mini Pan de Jamón con queso crema", 13.00),
    ("Mini Lunch (jamón y queso)", 6.50),
    ("Cachitos de jamón y bacon", 5.00),

    ("Pan francés", 0.75),
    ("Pan Canilla", 2.50),
    ("Pan Campesino", 3.00),

    ("Pan de queso pequeño 7.5 pulgadas", 11.00),
    ("Pan de queso mediano 12 pulgadas", 17.00),
    ("Pan de queso grande 16 pulgadas", 22.00),
    ("Pack 6 mini panes de queso", 10.00),

    ("Pan Sandwich tipo Subway", 8.00),

    # EXTRAS PANES DE QUESO
    ("Extra Queso + Guayaba", 1.00),
    ("Extra Queso + Tocineta", 1.00),
    ("Extra Guayaba + Queso", 1.00),
    ("Extra Triple relleno", 2.00),

    # PANES DULCES
    ("Dulce Piñita (6)", 7.00),
    ("Pack mini Pan de Leche (9)", 7.00),
    ("Pan de Guayaba", 4.00),
    ("Pan de Guayaba Grande", 12.00),
    ("Golfeado Grande", 4.00),
    ("Pack 6 Golfeados", 7.00),
    ("Pan de Queso Dulce", 1.50),
    ("Corazón de Piña (6)", 9.00),
    ("Piña & Coco (6)", 10.00),
    ("Pan Dulce de Coco (6)", 10.00),

    # CINNAMON ROLLS
    ("Cinnamon Roll Tradicional", 4.00),
    ("Cinnamon Rolls Pack de 2", 8.00),
    ("Cinnamon Rolls Pack de 8", 16.00),
    ("Cinnamon Rolls Pack de 12", 20.00),

    # LEMON ROLLS
    ("Lemon Roll Tradicional", 4.50),
    ("Lemon Rolls Pack de 2", 8.00),
    ("Lemon Rolls Pack de 8", 16.00),

    # TOPPINGS
    ("Topping Nutella", 2.00),
    ("Topping Oreo", 2.00),
    ("Topping Caramelo", 2.00),
    ("Topping Dulce de leche", 2.00),
    ("Topping Fresa", 2.00),
    ("Topping Chocolate", 2.00),

    # OTROS
    ("Panelitas San Joaquín (Pack 5 unidades)", 1.00),
    ("Pastelito individual (Incluye salsa)", 3.00),
    ("25 Mini Pastelitos surtidos (Incluye salsa)", 24.00),
    ("50 Mini Pastelitos surtidos (Incluye salsa)", 45.00),
    ("Arepitas de Yuca - Empaque 10 unidades", 12.00),

    # PANES ARTESANALES
    ("Pan Andino Regular", 14.00),
    ("Pan Andino con Talvina (Masa Madre)", 15.00),
    ("Pan Trenza Josefina's", 15.00),
    ("Pan Masa Madre", 15.00),
]


# ============================================================
# PROMOCIONES
# ============================================================

PROMOTIONS = [
    {
        "id": "promo_pan_queso_grande_16",
        "name": 'Promo Pan de Queso Grande 16" — Piñita gratis',
        "price": 22.00,
        "description": 'Pan de queso grande 16" + 1 pack de Piñitas gratis',
        "includes": "Incluye 1 pack de Piñitas gratis",
        "active": True,
    }
]


# ============================================================
# INVENTARIO INICIAL
# Se crea SOLO si el artículo todavía no existe.
# Nunca borra ni reinicia los datos que ya estén guardados.
# ============================================================

INVENTORY_SEED = [
    ("Ingredientes", "Harina", "King Arthur", "Bolsa", 6.0, "bolsas", None, ""),
    ("Ingredientes", "Azúcar", "", "Saco de 25 lb", 12.5, "lb", None, "½ saco"),
    ("Ingredientes", "Leche", "", "Galón", 0.5, "galón", None, "½ galón"),
    ("Ingredientes", "Mantequilla", "", "Unidad", 6.0, "unidades", None, ""),
    ("Ingredientes", "Mozzarella rallada", "Member's Mark", "5 lb", 2.5, "lb", 12.87, "½ bolsa"),
    ("Ingredientes", "Queso de freír", "", "Presentación registrada", 0.5, "presentación", None, ""),
    ("Ingredientes", "Pasta de guayaba", "Iberia", "15 oz", None, "unidad", 1.08, "Confirmar presentación"),
    ("Ingredientes", "Levadura seca instantánea", "Lesaffre", "2 bolsas de 1 lb", 908.0, "g", None, "2 lb total"),
    ("Ingredientes", "Vainilla", "Watkins", "8 fl oz / 236 ml", None, "ml", 7.98, ""),
    ("Ingredientes", "Sal", "Morton", "3 lb / 1.36 kg", None, "kg", 3.97, ""),

    # Papelón: el costo encontrado en el recetario de costos es $0.58 por 100 g.
    # Se registra como costo de referencia; la existencia se deja NULL hasta confirmar.
    ("Ingredientes", "Papelón", "", "Panela", None, "g", 0.0058, "Costo referencia: $0.58 por 100 g; confirmar compra actual"),

    # MATERIALES
    ("Materiales de empaque", "Bolsas para panes grandes", "", "", None, "unidades", None, "Pendiente de confirmar"),
    ("Materiales de empaque", "Bolsas para pan piñita", "", "", None, "unidades", None, "Pendiente de confirmar"),
    ("Materiales de empaque", "Bolsas para pastelitos", "", "", None, "unidades", None, "Pendiente de confirmar"),
    ("Materiales de empaque", "Papel de horno", "", "", None, "hojas", None, "Pendiente de confirmar cantidad y mínimo"),
    ("Materiales de empaque", "Film", "", "", None, "rollos", None, "Pendiente de confirmar cantidad y mínimo"),
    ("Materiales de empaque", "Stickers", "", "", None, "unidades", None, "Pendiente de confirmar"),
    ("Materiales de empaque", "Cinta", "", "", None, "unidades", None, "Pendiente de confirmar"),
    ("Materiales de empaque", "Sellos", "", "", None, "unidades", None, "Pendiente de confirmar"),
    ("Materiales de empaque", "Cajitas", "", "", None, "unidades", None, "Se agregarán después"),
]


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def init():
    c = db()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client TEXT NOT NULL,
        delivery_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pendiente de elaborar',
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product TEXT NOT NULL,
        qty INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        promotion_id TEXT DEFAULT '',
        promotion_name TEXT DEFAULT '',
        promotion_description TEXT DEFAULT '',
        FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        method TEXT NOT NULL,
        amount REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS inventory(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        name TEXT NOT NULL UNIQUE,
        brand TEXT DEFAULT '',
        presentation TEXT DEFAULT '',
        current_qty REAL,
        unit TEXT DEFAULT '',
        purchase_price REAL,
        minimum_qty REAL,
        notes TEXT DEFAULT '',
        updated_at TEXT NOT NULL
    );
    """)

    # Migración segura de columnas de promociones.
    columns = {row["name"] for row in c.execute("PRAGMA table_info(items)").fetchall()}

    for col, definition in [
        ("promotion_id", "TEXT DEFAULT ''"),
        ("promotion_name", "TEXT DEFAULT ''"),
        ("promotion_description", "TEXT DEFAULT ''"),
    ]:
        if col not in columns:
            c.execute(f"ALTER TABLE items ADD COLUMN {col} {definition}")

    # Agrega inventario base únicamente cuando el nombre no existe.
    now = datetime.now().isoformat()
    for row in INVENTORY_SEED:
        category, name, brand, presentation, qty, unit, price, notes = row
        c.execute(
            """
            INSERT OR IGNORE INTO inventory
            (category,name,brand,presentation,current_qty,unit,purchase_price,minimum_qty,notes,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (category, name, brand, presentation, qty, unit, price, None, notes, now),
        )

    c.commit()
    c.close()


init()


# ============================================================
# PREPARAR PEDIDOS PARA LA INTERFAZ
# ============================================================

def get_orders():
    c = db()
    orders = c.execute(
        "SELECT * FROM orders ORDER BY delivery_date, id DESC"
    ).fetchall()

    result = []

    for o in orders:
        items = c.execute(
            "SELECT * FROM items WHERE order_id=? ORDER BY id",
            (o["id"],)
        ).fetchall()

        pays = c.execute(
            "SELECT * FROM payments WHERE order_id=? ORDER BY id",
            (o["id"],)
        ).fetchall()

        total = sum(i["qty"] * i["unit_price"] for i in items)
        paid = sum(p["amount"] for p in pays)

        result.append({
            **dict(o),
            "items": [dict(i) for i in items],
            "payments": [dict(p) for p in pays],
            "total": total,
            "paid": paid,
            "balance": max(0, total - paid),
        })

    c.close()
    return result


# ============================================================
# INICIO
# ============================================================

@app.route("/")
def home():
    result = get_orders()

    active_orders = [
        o for o in result
        if o["status"] not in ("Entregado", "Cancelado")
    ]

    finalized_orders = [
        o for o in result
        if o["status"] in ("Entregado", "Cancelado")
    ]

    today = datetime.now().date().isoformat()

    sales_today = sum(
        o["total"] for o in result
        if o["status"] == "Entregado"
        and o["delivery_date"] == today
    )

    pending_balance = sum(
        o["balance"] for o in active_orders
        if o["balance"] > 0
    )

    ready_count = sum(
        1 for o in active_orders
        if o["status"] == "Listo para entregar"
    )

    c = db()
    inventory = [
        dict(x) for x in c.execute(
            """
            SELECT * FROM inventory
            ORDER BY category, name
            """
        ).fetchall()
    ]
    c.close()

    return render_template(
        "index.html",
        orders=result,
        active_orders=active_orders,
        finalized_orders=finalized_orders,
        products=PRODUCTS,
        promotions=PROMOTIONS,
        inventory=inventory,
        dashboard={
            "sales_today": sales_today,
            "pending_count": len(active_orders),
            "ready_count": ready_count,
            "pending_balance": pending_balance,
        },
    )


# ============================================================
# INVENTARIO — CONSULTAR
# ============================================================

@app.get("/inventory")
def list_inventory():
    c = db()
    rows = c.execute(
        "SELECT * FROM inventory ORDER BY category, name"
    ).fetchall()
    c.close()
    return jsonify([dict(r) for r in rows])


# ============================================================
# INVENTARIO — ACTUALIZAR
# ============================================================

@app.post("/inventory/<int:item_id>")
def update_inventory(item_id):
    data = request.get_json() or {}

    c = db()
    current = c.execute(
        "SELECT * FROM inventory WHERE id=?",
        (item_id,)
    ).fetchone()

    if not current:
        c.close()
        return jsonify({"ok": False, "error": "Artículo no encontrado"}), 404

    def num_or_none(value):
        if value is None or value == "":
            return None
        return float(value)

    c.execute(
        """
        UPDATE inventory
        SET current_qty=?,
            unit=?,
            purchase_price=?,
            minimum_qty=?,
            notes=?,
            updated_at=?
        WHERE id=?
        """,
        (
            num_or_none(data.get("current_qty")),
            data.get("unit", current["unit"] or ""),
            num_or_none(data.get("purchase_price")),
            num_or_none(data.get("minimum_qty")),
            data.get("notes", current["notes"] or ""),
            datetime.now().isoformat(),
            item_id,
        ),
    )

    c.commit()
    c.close()
    return jsonify({"ok": True})


# ============================================================
# INVENTARIO — AGREGAR ARTÍCULO
# ============================================================

@app.post("/inventory")
def create_inventory():
    data = request.get_json() or {}

    name = str(data.get("name", "")).strip()
    if not name:
        return jsonify({"ok": False, "error": "Falta el nombre"}), 400

    c = db()

    try:
        cur = c.execute(
            """
            INSERT INTO inventory
            (category,name,brand,presentation,current_qty,unit,purchase_price,minimum_qty,notes,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                data.get("category", "Ingredientes"),
                name,
                data.get("brand", ""),
                data.get("presentation", ""),
                float(data["current_qty"]) if data.get("current_qty") not in (None, "") else None,
                data.get("unit", ""),
                float(data["purchase_price"]) if data.get("purchase_price") not in (None, "") else None,
                float(data["minimum_qty"]) if data.get("minimum_qty") not in (None, "") else None,
                data.get("notes", ""),
                datetime.now().isoformat(),
            ),
        )
        c.commit()
        item_id = cur.lastrowid
    except sqlite3.IntegrityError:
        c.close()
        return jsonify({"ok": False, "error": "Ese artículo ya existe"}), 409

    c.close()
    return jsonify({"ok": True, "id": item_id})


# ============================================================
# CREAR PEDIDO
# ============================================================

@app.post("/orders")
def create_order():
    data = request.get_json() or {}

    if not data.get("client") or not data.get("delivery_date"):
        return jsonify({"ok": False, "error": "Cliente y fecha son obligatorios"}), 400

    c = db()

    cur = c.execute(
        """
        INSERT INTO orders(client,delivery_date,status,notes,created_at)
        VALUES(?,?,?,?,?)
        """,
        (
            data["client"],
            data["delivery_date"],
            data.get("status", "Pendiente de elaborar"),
            data.get("notes", ""),
            datetime.now().isoformat(),
        ),
    )

    oid = cur.lastrowid

    for i in data.get("items", []):
        c.execute(
            """
            INSERT INTO items
            (order_id,product,qty,unit_price,promotion_id,promotion_name,promotion_description)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                oid,
                i["product"],
                int(i["qty"]),
                float(i["unit_price"]),
                i.get("promotion_id", ""),
                i.get("promotion_name", ""),
                i.get("promotion_description", ""),
            ),
        )

    for p in data.get("payments", []):
        c.execute(
            """
            INSERT INTO payments(order_id,method,amount)
            VALUES(?,?,?)
            """,
            (
                oid,
                p["method"],
                float(p["amount"]),
            ),
        )

    c.commit()
    c.close()

    return jsonify({"ok": True, "id": oid})


# ============================================================
# ACTUALIZAR PEDIDO
# ============================================================

@app.post("/orders/<int:oid>")
def update_order(oid):
    data = request.get_json() or {}
    c = db()

    exists = c.execute(
        "SELECT id FROM orders WHERE id=?",
        (oid,)
    ).fetchone()

    if not exists:
        c.close()
        return jsonify({"ok": False, "error": "Pedido no encontrado"}), 404

    c.execute(
        """
        UPDATE orders
        SET client=?,delivery_date=?,status=?,notes=?
        WHERE id=?
        """,
        (
            data["client"],
            data["delivery_date"],
            data["status"],
            data.get("notes", ""),
            oid,
        ),
    )

    c.execute("DELETE FROM items WHERE order_id=?", (oid,))
    c.execute("DELETE FROM payments WHERE order_id=?", (oid,))

    for i in data.get("items", []):
        c.execute(
            """
            INSERT INTO items
            (order_id,product,qty,unit_price,promotion_id,promotion_name,promotion_description)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                oid,
                i["product"],
                int(i["qty"]),
                float(i["unit_price"]),
                i.get("promotion_id", ""),
                i.get("promotion_name", ""),
                i.get("promotion_description", ""),
            ),
        )

    for p in data.get("payments", []):
        c.execute(
            """
            INSERT INTO payments(order_id,method,amount)
            VALUES(?,?,?)
            """,
            (
                oid,
                p["method"],
                float(p["amount"]),
            ),
        )

    c.commit()
    c.close()

    return jsonify({"ok": True})


# ============================================================
# ELIMINAR PEDIDO
# ============================================================

@app.delete("/orders/<int:oid>")
def delete_order(oid):
    c = db()

    c.execute("DELETE FROM payments WHERE order_id=?", (oid,))
    c.execute("DELETE FROM items WHERE order_id=?", (oid,))
    c.execute("DELETE FROM orders WHERE id=?", (oid,))

    c.commit()
    c.close()

    return jsonify({"ok": True})


# ============================================================
# EJECUCIÓN LOCAL / RENDER
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

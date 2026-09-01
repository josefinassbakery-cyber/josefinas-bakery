from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime


BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "josefinas_bakery.db")

app = Flask(__name__)


class SafeOrder(dict):
    """Evita que Jinja confunda la clave "items" con dict.items()."""

    @property
    def items(self):
        return dict.get(self, "items", [])




# ============================================================
# PRODUCTOS
# ============================================================

PRODUCTS = [

    # =========================
    # PANES SALADOS
    # =========================

    ("Pan de Jamón 16 pulgadas", 34.00),
    ("Pan de Jamón con queso crema", 35.00),
    ("Mini Pan de Jamón", 10.00),
    ("Mini Pan de Jamón con queso crema", 12.00),
    ("Mini Lunch (jamón y queso)", 6.50),
    ("Cachitos de jamón y bacon", 4.50),

    ("Pan francés", 1.00),
    ("Pan Canilla", 2.50),
    ("Pan Campesino", 3.00),

    ("Pan de queso pequeño 7.5 pulgadas", 10.00),
    ("Pan de queso mediano 12 pulgadas", 15.00),
    ("Pan de queso grande 16 pulgadas", 20.00),
    ("Pack 6 mini panes de queso", 10.00),

    ("Pan Sandwich tipo Subway", 8.00),

    # =========================
    # EXTRAS PANES DE QUESO
    # =========================

    ("Extra Queso + Guayaba", 1.00),
    ("Extra Queso + Tocineta", 1.00),
    ("Extra Guayaba + Queso", 1.00),
    ("Extra Triple relleno", 2.00),

    # =========================
    # PANES DULCES
    # =========================

    ("Dulce Piñita (6)", 8.50),
    ("Pack mini Pan de Leche (9)", 8.00),
    ("Pan de Guayaba", 4.50),
    ("Pan de Guayaba Grande", 16.00),
    ("Golfeado Grande", 4.50),
    ("Pack 6 Golfeados", 10.00),

    ("Pan de Queso Dulce", 2.00),
    ("Corazón de Piña (6)", 10.00),
    ("Piña & Coco (6)", 10.00),
    ("Pan Dulce de Coco (6)", 10.00),

    # =========================
    # CINNAMON ROLLS
    # =========================

    ("Cinnamon Roll Tradicional", 4.50),
    ("Cinnamon Rolls Pack de 2", 8.00),
    ("Cinnamon Rolls Pack de 8", 16.00),

    # =========================
    # LEMON ROLLS
    # =========================

    ("Lemon Roll Tradicional", 4.50),
    ("Lemon Rolls Pack de 2", 8.00),
    ("Lemon Rolls Pack de 8", 16.00),

    # =========================
    # TOPPINGS
    # =========================

    ("Topping Nutella", 2.00),
    ("Topping Oreo", 2.00),
    ("Topping Caramelo", 2.00),
    ("Topping Dulce de leche", 2.00),
    ("Topping Fresa", 2.00),
    ("Topping Chocolate", 2.00),

    # =========================
    # OTROS PRODUCTOS
    # =========================

    ("Panelitas San Joaquín (Pack 5 unidades)", 1.00),
    ("Pastelito individual (Incluye salsa)", 3.00),
    ("25 Mini Pastelitos surtidos (Incluye salsa)", 24.00),
    ("50 Mini Pastelitos surtidos (Incluye salsa)", 47.00),
    ("Arepitas de Yuca - Empaque 10 unidades", 12.00),

    # =========================
    # PANES ARTESANALES
    # =========================

    ("Pan Andino Regular", 14.00),
    ("Pan Andino con Talvina (Masa Madre)", 15.00),
    ("Pan Trenza", 15.00)
]


# ============================================================
# PROMOCIONES
# ============================================================

PROMOTIONS = [

    {
        "id": "promo_pan_queso_grande_16",
        "name": 'Promo Pan de Queso Grande 16" — Piñita gratis',
        "price": 20.00,
        "description": 'Pan de queso grande 16" + 1 pack de Piñitas gratis',
        "includes": 'Incluye 1 pack de Piñitas gratis',
        "active": True
    }

]


# ============================================================
# BASE DE DATOS
# ============================================================

def db():

    c = sqlite3.connect(DB)

    c.row_factory = sqlite3.Row

    return c


def init():

    c = db()

    c.execute("PRAGMA foreign_keys = ON")

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

        FOREIGN KEY(order_id)

        REFERENCES orders(id)

        ON DELETE CASCADE

    );


    CREATE TABLE IF NOT EXISTS payments(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        order_id INTEGER NOT NULL,

        method TEXT NOT NULL,

        amount REAL NOT NULL,

        FOREIGN KEY(order_id)

        REFERENCES orders(id)

        ON DELETE CASCADE

    );

    """)

    # --------------------------------------------------------
    # MIGRACIÓN SEGURA
    # Si la base de datos ya existía con la tabla items vieja,
    # agregamos las columnas de promoción sin borrar pedidos.
    # --------------------------------------------------------

    columns = {
        row["name"]
        for row in c.execute("PRAGMA table_info(items)").fetchall()
    }

    if "promotion_id" not in columns:

        c.execute(
            "ALTER TABLE items ADD COLUMN promotion_id TEXT DEFAULT ''"
        )

    if "promotion_name" not in columns:

        c.execute(
            "ALTER TABLE items ADD COLUMN promotion_name TEXT DEFAULT ''"
        )

    if "promotion_description" not in columns:

        c.execute(
            "ALTER TABLE items ADD COLUMN promotion_description TEXT DEFAULT ''"
        )


    c.commit()

    c.close()


# IMPORTANTE:
# Esto crea las tablas también cuando Render inicia
# la aplicación usando Gunicorn.
init()


# ============================================================
# INICIO / PEDIDOS
# ============================================================

@app.route("/")
def home():

    c = db()

    orders = c.execute(
        "SELECT * FROM orders ORDER BY delivery_date, id DESC"
    ).fetchall()

    result = []

    for o in orders:

        items = c.execute(
            "SELECT * FROM items WHERE order_id=?",
            (o["id"],)
        ).fetchall()

        pays = c.execute(
            "SELECT * FROM payments WHERE order_id=?",
            (o["id"],)
        ).fetchall()

        total = sum(
            i["qty"] * i["unit_price"]
            for i in items
        )

        paid = sum(
            p["amount"]
            for p in pays
        )

        result.append(
            SafeOrder(
                dict(
                    o,
                    items=[dict(i) for i in items],
                    payments=[dict(p) for p in pays],
                    total=total,
                    paid=paid,
                    balance=max(0, total - paid)
                )
            )
        )

    c.close()

    # Pedidos que requieren atención diaria.
    active_orders = [
        o for o in result
        if o["status"] not in ("Entregado", "Cancelado")
    ]

    # Historial: pedidos ya terminados o cancelados.
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

    return render_template(
        "index.html",
        orders=result,
        active_orders=active_orders,
        finalized_orders=finalized_orders,
        products=PRODUCTS,
        promotions=PROMOTIONS,
        dashboard={
            "sales_today": sales_today,
            "pending_count": len(active_orders),
            "ready_count": ready_count,
            "pending_balance": pending_balance
        }
    )


# ============================================================
# CREAR PEDIDO
# ============================================================

@app.post("/orders")
def create_order():

    data = request.get_json() or {}

    c = db()


    cur = c.execute(

        """

        INSERT INTO orders(

            client,

            delivery_date,

            status,

            notes,

            created_at

        )

        VALUES(?,?,?,?,?)

        """,

        (

            data["client"],

            data["delivery_date"],

            data.get(

                "status",

                "Pendiente de elaborar"

            ),

            data.get(

                "notes",

                ""

            ),

            datetime.now().isoformat()

        )

    )


    oid = cur.lastrowid


    for i in data.get("items", []):

        c.execute(

            """

            INSERT INTO items(

                order_id,

                product,

                qty,

                unit_price,

                promotion_id,

                promotion_name,

                promotion_description

            )

            VALUES(?,?,?,?,?,?,?)

            """,

            (

                oid,

                i["product"],

                int(i["qty"]),

                float(i["unit_price"]),

                i.get("promotion_id", ""),

                i.get("promotion_name", ""),

                i.get("promotion_description", "")

            )

        )


    for p in data.get("payments", []):

        c.execute(

            """

            INSERT INTO payments(

                order_id,

                method,

                amount

            )

            VALUES(?,?,?)

            """,

            (

                oid,

                p["method"],

                float(p["amount"])

            )

        )


    c.commit()

    c.close()


    return jsonify(

        {

            "ok": True,

            "id": oid

        }

    )


# ============================================================
# ACTUALIZAR PEDIDO
# ============================================================

@app.post("/orders/<int:oid>")
def update_order(oid):

    data = request.get_json() or {}

    c = db()


    c.execute(

        """

        UPDATE orders

        SET

            client=?,

            delivery_date=?,

            status=?,

            notes=?

        WHERE id=?

        """,

        (

            data["client"],

            data["delivery_date"],

            data["status"],

            data.get("notes", ""),

            oid

        )

    )


    c.execute(

        "DELETE FROM items WHERE order_id=?",

        (oid,)

    )


    c.execute(

        "DELETE FROM payments WHERE order_id=?",

        (oid,)

    )


    for i in data.get("items", []):

        c.execute(

            """

            INSERT INTO items(

                order_id,

                product,

                qty,

                unit_price,

                promotion_id,

                promotion_name,

                promotion_description

            )

            VALUES(?,?,?,?,?,?,?)

            """,

            (

                oid,

                i["product"],

                int(i["qty"]),

                float(i["unit_price"]),

                i.get("promotion_id", ""),

                i.get("promotion_name", ""),

                i.get("promotion_description", "")

            )

        )


    for p in data.get("payments", []):

        c.execute(

            """

            INSERT INTO payments(

                order_id,

                method,

                amount

            )

            VALUES(?,?,?)

            """,

            (

                oid,

                p["method"],

                float(p["amount"])

            )

        )


    c.commit()

    c.close()


    return jsonify(

        {

            "ok": True

        }

    )


# ============================================================
# ELIMINAR PEDIDO
# ============================================================

@app.delete("/orders/<int:oid>")
def delete_order(oid):

    c = db()


    c.execute(

        "DELETE FROM payments WHERE order_id=?",

        (oid,)

    )


    c.execute(

        "DELETE FROM items WHERE order_id=?",

        (oid,)

    )


    c.execute(

        "DELETE FROM orders WHERE id=?",

        (oid,)

    )


    c.commit()

    c.close()


    return jsonify(

        {

            "ok": True

        }

    )


# ============================================================
# EJECUCIÓN LOCAL / RENDER
# ============================================================

if __name__ == "__main__":

    port = int(

        os.environ.get(

            "PORT",

            5000

        )

    )


    app.run(

        host="0.0.0.0",

        port=port,

        debug=False

    )

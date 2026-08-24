from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "josefinas_bakery.db")

app = Flask(__name__)

PRODUCTS = [
    ("Pan francés", 1.00),
    ("Pan Canilla", 2.50),
    ("Pan Campesino", 3.00),
    ("Pan de queso pequeño 7.5\"", 10.00),
    ("Pan de queso mediano 12\"", 15.00),
    ("Pan de queso grande 16\"", 20.00),
    ("Pack 6 mini panes de queso", 10.00),
    ("Pan Sandwich tipo Subway", 8.00),
    ("Dulce Piñita (6)", 8.50),
    ("Pack mini Pan de Leche (9)", 8.00),
    ("Pan de Guayaba", 4.50),
    ("Pan de Guayaba Grande", 16.00),
    ("Golfeado Grande", 4.50),
    ("Pack 6 Golfeados", 10.00),
    ("Mini Golfeados", 10.00),
    ("Cinnamon Rolls", None),
    ("Lemon Rolls", None),
    ("Pan de Jamón", None),
    ("Cachitos", None),
    ("Pan Andino con Talvina", None),
    ("Pancitos de queso dulce", None)
]


def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
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
        FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        method TEXT NOT NULL,
        amount REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
    );
    """)

    c.commit()
    c.close()


# IMPORTANTE:
# Esto se ejecuta también cuando Render inicia la aplicación con Gunicorn.
init()


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
            dict(
                o,
                items=[dict(i) for i in items],
                payments=[dict(p) for p in pays],
                total=total,
                paid=paid,
                balance=max(0, total - paid)
            )
        )

    c.close()

    return render_template(
        "index.html",
        orders=result,
        products=PRODUCTS
    )


@app.post("/orders")
def create_order():
    data = request.get_json()

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
            data.get("notes", ""),
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
                unit_price
            )
            VALUES(?,?,?,?)
            """,
            (
                oid,
                i["product"],
                int(i["qty"]),
                float(i["unit_price"])
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

    return jsonify({
        "ok": True,
        "id": oid
    })


@app.post("/orders/<int:oid>")
def update_order(oid):
    data = request.get_json()

    c = db()

    c.execute(
        """
        UPDATE orders
        SET client=?,
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
                unit_price
            )
            VALUES(?,?,?,?)
            """,
            (
                oid,
                i["product"],
                int(i["qty"]),
                float(i["unit_price"])
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

    return jsonify({
        "ok": True
    })


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

    return jsonify({
        "ok": True
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )

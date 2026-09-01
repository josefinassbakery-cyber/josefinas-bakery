from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime


BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "josefinas_bakery.db")

app = Flask(__name__)


class SafeOrder(dict):
    """Permite acceder a los datos del pedido sin sobrescribir dict.items()."""

    def __getitem__(self, key):
        return super().__getitem__(key)




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

        created_at TEXT NOT NULL,
        is_test INTEGER NOT NULL DEFAULT 0

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


    order_columns = {row["name"] for row in c.execute("PRAGMA table_info(orders)").fetchall()}
    if "is_test" not in order_columns:
        c.execute("ALTER TABLE orders ADD COLUMN is_test INTEGER NOT NULL DEFAULT 0")

    c.execute("""CREATE TABLE IF NOT EXISTS inventory(
        id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, product TEXT NOT NULL,
        presentation TEXT DEFAULT '', purchase_price REAL NOT NULL DEFAULT 0, current_qty REAL NOT NULL DEFAULT 0,
        equivalent_qty REAL NOT NULL DEFAULT 0, equivalent_unit TEXT DEFAULT '', reorder_point REAL NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS promotions(
        id TEXT PRIMARY KEY, name TEXT NOT NULL, price REAL NOT NULL DEFAULT 0,
        description TEXT DEFAULT '', includes TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS recipes(
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, yield_text TEXT DEFAULT '',
        oven_temp TEXT DEFAULT '', bake_time TEXT DEFAULT '', notes TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS recipe_ingredients(
        id INTEGER PRIMARY KEY AUTOINCREMENT, recipe_id INTEGER NOT NULL, ingredient_name TEXT NOT NULL,
        amount TEXT NOT NULL, unit TEXT DEFAULT '', notes TEXT DEFAULT '',
        FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
    )""")

    seed = [
            ("Harina", "King Arthur Bread Flour – Unbleached", "10 lb", 8.38, 6, 60, "lb"),
            ("Azúcar", "Domino Premium Pure Cane Granulated Sugar", "25 lb", 19.48, 0.5, 12.5, "lb"),
            ("Azúcar glass", "Member's Mark Cane Powdered Sugar", "7 lb", 6.98, 1, 7, "lb"),
            ("Leche", "Great Value Vitamin D Whole Milk 3.25%", "1 galón", 3.12, 0.5, 0.5, "galón"),
            ("Mantequilla", "Countryside Creamery Pure Irish Butter – Salted (ALDI, caja verde)", "8 oz", 3.99, 6, 6, "unidades"),
            ("Huevos", "Great Value Large White Eggs – Grade A", "Caja 60", 8.12, 49, 49, "huevos"),
            ("Queso", "Queso (presentación de la foto)", "—", 0, 0.5, 0.5, "pieza"),
            ("Leche en polvo", "NIDO Fortificada Dry Whole Milk Powder", "56.4 oz", 18.12, 0, 0, "oz"),
            ("Mantequilla", "Kerrygold Grass-Fed Salted Pure Irish Butter", "8 oz", 4.68, 0, 0, "unidades"),
            ("Levadura", "Saf-Instant / Lesaffre Instant Yeast", "2 × 16 oz", 13.23, 0, 0, "oz"),
            ("Vainilla", "Watkins Original Gourmet Baking Vanilla", "8 fl oz / 236 ml", 7.98, 0, 0, "ml"),
            ("Sal", "Morton Kosher Salt Flakes", "3 lb", 3.97, 0, 0, "lb"),
            ("Pasas", "Sun-Maid California Sun-Dried Raisins", "32 oz / 2 lb", 6.97, 0, 0, "oz"),
            ("Coco", "Great Value Organic Unsweetened Coconut Flakes", "7 oz / 198 g", 3.78, 0, 0, "g"),
            ("Papel film", "Glad Cling'n Seal", "2 × 400 sq ft", 6.98, 0, 0, "sq ft"),
            ("Papel para hornear", "Great Value Non-Stick Parchment Paper", "100 sq ft", 5.67, 0, 0, "sq ft")
        ]
    now = datetime.now().isoformat()
    for row in seed:
        exists = c.execute("SELECT id FROM inventory WHERE product=? AND presentation=? LIMIT 1", (row[1], row[2])).fetchone()
        if not exists:
            c.execute("""INSERT INTO inventory(category,product,presentation,purchase_price,current_qty,equivalent_qty,equivalent_unit,reorder_point,active,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,0,1,?,?)""", row + (now, now))
    # Recetas base documentadas por Josefina's Bakery. Se insertan solo si no existen.
    if c.execute("SELECT COUNT(*) FROM recipes").fetchone()[0] == 0:
        recipes = [
            ("Pan Piñita Mejorada", "14 porciones de 85 a 90 g", "300°F (150°C)", "25 a 30 min", "Tangzhong: 16 g harina + 43 g agua + 43 g leche."),
            ("Cachitos Venezolanos — 500 g", "12 cachitos aprox.", "180°C (356°F)", "18 a 22 min", "75 g masa + 60 g relleno aprox. por unidad."),
            ("Cachitos Venezolanos — 1,000 g", "20–22 cachitos aprox.", "180°C (356°F)", "18 a 22 min", "Levadura instantánea: 10 g (1%)."),
            ("Pan Andino con Talvina", "2 panes andinos", "170°C (338°F)", "40 a 50 min", "Fermentación con Talvina: 12 a 16 horas."),
            ("Pan de Queso", "2 panes grandes o 13 pequeños", "160°C", "35 min", "Puede llevar queso, queso y tocineta, queso y guayaba o mezcla de quesos."),
            ("Golfeados Venezolanos", "16 golfeados", "180°C (350°F)", "15 min + 10 min", "Receta documentada con papelón y queso blanco duro."),
            ("Pan de Leche Tradicional", "—", "—", "—", "Receta con prefermento; la cantidad de leche en polvo está pendiente en la fuente."),
        ]
        for r in recipes:
            cur=c.execute("INSERT INTO recipes(name,yield_text,oven_temp,bake_time,notes) VALUES(?,?,?,?,?)",r)
            rid=cur.lastrowid
            ing_map={
                "Pan Piñita Mejorada":[("Harina", "616", "g", "600 g masa + 16 g Tangzhong"),("Agua","43","g","Tangzhong"),("Leche","243","g","43 g Tangzhong + 200 g masa"),("Azúcar","150","g",""),("Leche en polvo","30","g",""),("Levadura","6","g","instantánea"),("Mantequilla","90","g","pomada"),("Huevos","1","unidad","+ 1 yema"),("Vainilla","2","cucharadas",""),("Esencia de piña","2","cucharadas","casera"),("Sal","3–4","g","")],
                "Cachitos Venezolanos — 500 g":[("Harina panadera","500","g",""),("Agua o leche","225","g",""),("Azúcar","75","g",""),("Mantequilla","150","g","a temperatura ambiente"),("Sal","8","g",""),("Levadura","8","g","instantánea"),("Huevo","1","unidad","en la masa, aprox. 50 g"),("Huevo","1","unidad","para pincelar"),("Jamón","—","—","relleno; cantidad según producción"),("Tocineta","—","—","relleno; cantidad según producción")],
                "Cachitos Venezolanos — 1,000 g":[("Harina panadera","1000","g",""),("Agua o leche","450","g",""),("Azúcar","150","g",""),("Mantequilla","300","g","a temperatura ambiente"),("Sal","16","g",""),("Levadura","10","g","1%"),("Huevo","2","unidades","en la masa, aprox. 100 g"),("Huevo","1","unidad","para pincelar"),("Jamón","—","—","relleno; cantidad según producción"),("Tocineta","—","—","relleno; cantidad según producción")],
                "Pan Andino con Talvina":[("Harina panadera","550","g",""),("Masa madre Talvina","120","g","activa"),("Leche líquida","140","g",""),("Huevo","1","unidad",""),("Azúcar","150","g",""),("Mantequilla","55","g",""),("Sal","3","g",""),("Manteca de cerdo","55","g","o mantequilla"),("Miel de abejas","5","g",""),("Azúcar vainillado","7","g","o esencia de vainilla")],
                "Pan de Queso":[("Harina panadera","500","g",""),("Huevo","1","unidad",""),("Leche líquida","250","g","tibia"),("Azúcar","60","g",""),("Levadura","7","g","instantánea"),("Sal","9","g",""),("Mantequilla","80","g","pomada"),("Queso","400","g","llanero o mezcla llanero + mozzarella")],
                "Golfeados Venezolanos":[("Harina panadera","800","g",""),("Leche entera","280","ml",""),("Mantequilla","130","g","a temperatura ambiente"),("Azúcar","150","g",""),("Sal","10","g",""),("Huevos","2","unidades",""),("Vainilla","2","cucharadas",""),("Levadura","8","g","instantánea"),("Queso blanco duro","500","g","rallado"),("Papelón","500","g",""),("Agua","200","ml","melado")],
                "Pan de Leche Tradicional":[("Harina de trigo","1750","g","250 g prefermento + 1500 g masa"),("Azúcar","425","g","125 g prefermento + 300 g masa"),("Agua","250","g","prefermento"),("Mantequilla","180","g",""),("Huevos","3","unidades",""),("Sal","30","g",""),("Leche","625","ml","agregar poco a poco"),("Levadura seca","6","g",""),("Leche en polvo","—","—","cantidad pendiente en la fuente")],
            }
            for item in ing_map.get(r[0],[]):
                c.execute("INSERT INTO recipe_ingredients(recipe_id,ingredient_name,amount,unit,notes) VALUES(?,?,?,?,?)",(rid,*item))
    if c.execute("SELECT COUNT(*) FROM promotions").fetchone()[0] == 0:
        for p in PROMOTIONS:
            c.execute("INSERT INTO promotions(id,name,price,description,includes,active) VALUES(?,?,?,?,?,?)",
                      (p["id"],p["name"],p["price"],p.get("description", ""),p.get("includes", ""),1 if p.get("active") else 0))

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

    inventory_for_home = [dict(r) for r in c.execute("SELECT * FROM inventory WHERE active=1 ORDER BY category,product").fetchall()]
    recipes_for_home = []
    for rr in c.execute("SELECT * FROM recipes WHERE active=1 ORDER BY name").fetchall():
        rd=dict(rr)
        rd["ingredients"]=[dict(x) for x in c.execute("SELECT ingredient_name,amount,unit,notes FROM recipe_ingredients WHERE recipe_id=? ORDER BY id",(rr["id"],)).fetchall()]
        recipes_for_home.append(rd)

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
        inventory=inventory_for_home,
        recipes=recipes_for_home,
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

            created_at,
            is_test

        )

        VALUES(?,?,?,?,?,?)

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

            datetime.now().isoformat(),
            1 if data.get("is_test") else 0

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

            notes=?,
            is_test=?

        WHERE id=?

        """,

        (

            data["client"],

            data["delivery_date"],

            data["status"],

            data.get("notes", ""),
            1 if data.get("is_test") else 0,

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
    order = c.execute("SELECT status, is_test FROM orders WHERE id=?", (oid,)).fetchone()
    if not order:
        c.close()
        return jsonify({"ok": False, "error": "Pedido no encontrado"}), 404
    if order["status"] in ("Entregado", "Cancelado") and not int(order["is_test"] or 0):
        c.close()
        return jsonify({"ok": False, "error": "Los pedidos reales finalizados están protegidos"}), 403
    c.execute("DELETE FROM payments WHERE order_id=?", (oid,))
    c.execute("DELETE FROM items WHERE order_id=?", (oid,))
    c.execute("DELETE FROM orders WHERE id=?", (oid,))
    c.commit()
    c.close()
    return jsonify({"ok": True})


# ============================================================
# CLIENTES FRECUENTES
# ============================================================

@app.get("/clients")
def clients():
    q = (request.args.get("q") or "").strip()
    c = db()
    rows = c.execute("SELECT DISTINCT client FROM orders WHERE client LIKE ? COLLATE NOCASE ORDER BY client LIMIT 10", ((q + "%") if q else "%",)).fetchall()
    result=[]
    for row in rows:
        client=row["client"]
        order=c.execute("SELECT id FROM orders WHERE client=? AND status!='Cancelado' ORDER BY delivery_date DESC,id DESC LIMIT 1",(client,)).fetchone()
        items=[dict(x) for x in c.execute("SELECT product,qty,unit_price FROM items WHERE order_id=? AND (promotion_id='' OR promotion_id IS NULL)",(order["id"],)).fetchall()] if order else []
        result.append({"client":client,"items":items})
    c.close(); return jsonify(result)

# ============================================================
# PROMOCIONES
# ============================================================

@app.get("/promotions")
def get_promotions():
    c=db(); rows=c.execute("SELECT * FROM promotions ORDER BY name").fetchall(); c.close(); return jsonify([dict(x) for x in rows])

@app.post("/promotions")
def create_promotion():
    data=request.get_json() or {}; name=(data.get("name") or "").strip()
    if not name:return jsonify({"ok":False}),400
    pid="promo_"+str(abs(hash(name+datetime.now().isoformat())))
    c=db(); c.execute("INSERT INTO promotions(id,name,price,description,includes,active) VALUES(?,?,?,?,?,1)",(pid,name,float(data.get("price") or 0),data.get("description",""),data.get("includes",""))); c.commit(); c.close(); return jsonify({"ok":True,"id":pid})

@app.put("/promotions/<pid>")
def update_promotion(pid):
    data=request.get_json() or {}; c=db(); c.execute("UPDATE promotions SET name=?,price=?,description=?,includes=?,active=? WHERE id=?",((data.get("name") or "").strip(),float(data.get("price") or 0),data.get("description",""),data.get("includes",""),1 if data.get("active",True) else 0,pid)); c.commit(); c.close(); return jsonify({"ok":True})

@app.delete("/promotions/<pid>")
def deactivate_promotion(pid):
    c=db(); c.execute("UPDATE promotions SET active=0 WHERE id=?",(pid,)); c.commit(); c.close(); return jsonify({"ok":True})

# ============================================================
# RECETAS
# ============================================================

@app.get("/recipes")
def get_recipes():
    c=db()
    result=[]
    for rr in c.execute("SELECT * FROM recipes WHERE active=1 ORDER BY name").fetchall():
        rd=dict(rr)
        rd["ingredients"]=[dict(x) for x in c.execute("SELECT ingredient_name,amount,unit,notes FROM recipe_ingredients WHERE recipe_id=? ORDER BY id",(rr["id"],)).fetchall()]
        result.append(rd)
    c.close()
    return jsonify(result)


# ============================================================
# INVENTARIO
# ============================================================

@app.get("/inventory")
def get_inventory():
    c=db(); rows=c.execute("SELECT * FROM inventory WHERE active=1 ORDER BY category,product").fetchall(); c.close(); return jsonify([dict(x) for x in rows])

@app.post("/inventory")
def create_inventory():
    data=request.get_json() or {}
    if not (data.get("category") or "").strip() or not (data.get("product") or "").strip(): return jsonify({"ok":False}),400
    now=datetime.now().isoformat(); c=db(); c.execute("""INSERT INTO inventory(category,product,presentation,purchase_price,current_qty,equivalent_qty,equivalent_unit,reorder_point,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,1,?,?)""",((data.get("category") or "").strip(),(data.get("product") or "").strip(),data.get("presentation",""),float(data.get("purchase_price") or 0),float(data.get("current_qty") or 0),float(data.get("equivalent_qty") or 0),data.get("equivalent_unit",""),float(data.get("reorder_point") or 0),now,now)); c.commit(); c.close(); return jsonify({"ok":True})

@app.put("/inventory/<int:iid>")
def update_inventory(iid):
    data=request.get_json() or {}; now=datetime.now().isoformat(); c=db(); c.execute("UPDATE inventory SET category=?,product=?,presentation=?,purchase_price=?,current_qty=?,equivalent_qty=?,equivalent_unit=?,reorder_point=?,updated_at=? WHERE id=?",((data.get("category") or "").strip(),(data.get("product") or "").strip(),data.get("presentation",""),float(data.get("purchase_price") or 0),float(data.get("current_qty") or 0),float(data.get("equivalent_qty") or 0),data.get("equivalent_unit",""),float(data.get("reorder_point") or 0),now,iid)); c.commit(); c.close(); return jsonify({"ok":True})

@app.delete("/inventory/<int:iid>")
def delete_inventory(iid):
    c=db(); c.execute("UPDATE inventory SET active=0,updated_at=? WHERE id=?",(datetime.now().isoformat(),iid)); c.commit(); c.close(); return jsonify({"ok":True})


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

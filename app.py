from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "josefinas_bakery.db")

app = Flask(__name__)


class SafeOrder(dict):
    @property
    def items_list(self):
        return self.get("items", [])


PRODUCTS = [
    ("Pan de Jamón 16 pulgadas", 34.00),
    ("Pan de Jamón con queso crema", 35.00),
    ("Mini Pan de Jamón", 10.00),
    ("Mini Pan de Jamón con queso crema", 13.00),
    ("Mini Lunch (jamón y queso)", 6.50),
    ("Cachitos de jamón y bacon", 5.00),
    ("Pan francés", 0.75),
    ("Pan Francés Especial", 1.50),
    ("Pan Canilla", 2.50),
    ("Pan Campesino", 3.00),
    ("Pan de queso pequeño 7.5 pulgadas", 11.00),
    ("Pan de queso mediano 12 pulgadas", 17.00),
    ("Pan de queso grande 16 pulgadas", 22.00),
    ("Pack 6 mini panes de queso", 10.00),
    ("Pan Sandwich tipo Subway", 8.00),
    ("Extra Queso + Guayaba", 1.00),
    ("Extra Queso + Tocineta", 1.00),
    ("Extra Guayaba + Queso", 1.00),
    ("Extra Triple relleno", 2.00),
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
    ("Cinnamon Roll Tradicional", 4.00),
    ("Cinnamon Rolls Pack de 2", 8.00),
    ("Cinnamon Rolls Pack de 8", 16.00),
    ("Cinnamon Rolls Pack de 12", 20.00),
    ("Lemon Roll Tradicional", 4.00),
    ("Lemon Rolls Pack de 2", 8.00),
    ("Lemon Rolls Pack de 8", 16.00),
    ("Topping Nutella", 2.00),
    ("Topping Oreo", 2.00),
    ("Topping Caramelo", 2.00),
    ("Topping Dulce de leche", 2.00),
    ("Topping Fresa", 2.00),
    ("Topping Chocolate", 2.00),
    ("Panelitas San Joaquín (Pack 5 unidades)", 1.00),
    ("Pastelito individual (Incluye salsa)", 3.00),
    ("25 Mini Pastelitos surtidos (Incluye salsa)", 24.00),
    ("50 Mini Pastelitos surtidos (Incluye salsa)", 45.00),
    ("Arepitas de Yuca - Empaque 10 unidades", 12.00),
    ("Pan Andino Regular", 14.00),
    ("Pan Andino con Talvina (Masa Madre)", 15.00),
    ("Pan Trenza", 15.00),
    ("Pan Masa Madre", 15.00),
]

PROMOTIONS = [{
    "id": "promo_pan_queso_grande_16",
    "name": 'Promo Pan de Queso Grande 16" — Piñita gratis',
    "price": 20.00,
    "description": 'Pan de queso grande 16" + 1 pack de Piñitas gratis',
    "includes": "Incluye 1 pack de Piñitas gratis",
    "active": True,
}]


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
        product TEXT NOT NULL,
        presentation TEXT DEFAULT '',
        purchase_price REAL NOT NULL DEFAULT 0,
        current_qty REAL NOT NULL DEFAULT 0,
        equivalent_qty REAL NOT NULL DEFAULT 0,
        equivalent_unit TEXT DEFAULT '',
        reorder_point REAL NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS materials(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        product TEXT NOT NULL,
        presentation TEXT DEFAULT '',
        purchase_price REAL NOT NULL DEFAULT 0,
        current_qty REAL NOT NULL DEFAULT 0,
        equivalent_qty REAL NOT NULL DEFAULT 0,
        equivalent_unit TEXT DEFAULT '',
        reorder_point REAL NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS promotions(
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        price REAL NOT NULL DEFAULT 0,
        description TEXT DEFAULT '',
        includes TEXT DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS recipes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        yield_text TEXT DEFAULT '',
        oven_temp TEXT DEFAULT '',
        bake_time TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS recipe_ingredients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        ingredient_name TEXT NOT NULL,
        amount TEXT NOT NULL,
        unit TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
    );
    """)

    now = datetime.now().isoformat()

    inventory_seed = [
        ("Harina", "King Arthur Bread Flour – Unbleached", "10 lb", 8.38, 6, 60, "lb", 0),
        ("Azúcar", "Domino Premium Pure Cane Granulated Sugar", "25 lb", 19.48, 0.5, 12.5, "lb", 0),
        ("Azúcar glass", "Member's Mark Cane Powdered Sugar", "7 lb", 6.98, 1, 7, "lb", 0),
        ("Leche", "Great Value Vitamin D Whole Milk 3.25%", "1 galón", 3.12, 0.5, 0.5, "galón", 0),
        ("Mantequilla", "Countryside Creamery Pure Irish Butter – Salted (ALDI, caja verde)", "8 oz", 3.99, 6, 6, "unidades", 0),
        ("Huevos", "Great Value Large White Eggs – Grade A", "Caja 60", 8.12, 49, 49, "huevos", 0),
        ("Queso", "Queso (presentación de la foto)", "—", 0, 0.5, 0.5, "pieza", 0),
        ("Leche en polvo", "NIDO Fortificada Dry Whole Milk Powder", "56.4 oz", 18.12, 0, 0, "oz", 0),
        ("Mantequilla", "Kerrygold Grass-Fed Salted Pure Irish Butter", "8 oz", 4.68, 0, 0, "unidades", 0),
        ("Levadura", "Saf-Instant / Lesaffre Instant Yeast", "2 × 16 oz", 13.23, 0, 0, "oz", 0),
        ("Vainilla", "Watkins Original Gourmet Baking Vanilla", "8 fl oz / 236 ml", 7.98, 0, 0, "ml", 0),
        ("Sal", "Morton Kosher Salt Flakes", "3 lb", 3.97, 0, 0, "lb", 0),
        ("Pasas", "Sun-Maid California Sun-Dried Raisins", "32 oz / 2 lb", 6.97, 0, 0, "oz", 0),
        ("Coco", "Great Value Organic Unsweetened Coconut Flakes", "7 oz / 198 g", 3.78, 0, 0, "g", 0),
        ("Papel film", "Glad Cling'n Seal", "2 × 400 sq ft", 6.98, 0, 0, "sq ft", 0),
        ("Papel para hornear", "Great Value Non-Stick Parchment Paper", "100 sq ft", 5.67, 0, 0, "sq ft", 0),
        ("Papelón / Panela", "Papelón (Panela) — presentación de la foto", "unidad", 0, 0, 0, "unidades", 3),
    ]

    for row in inventory_seed:
        exists = c.execute(
            "SELECT id FROM inventory WHERE product=? AND presentation=? LIMIT 1",
            (row[1], row[2])
        ).fetchone()
        if not exists:
            c.execute("""
                INSERT INTO inventory(
                    category,product,presentation,purchase_price,current_qty,
                    equivalent_qty,equivalent_unit,reorder_point,active,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,1,?,?)
            """, row[:7] + (row[7], now, now))

    material_seed = [
        ("Papel para hornear", "Great Value Non-Stick Parchment Paper", "100 sq ft", 5.67, 1.5, 150, "sq ft", 1),
        ("Papel film", "Glad Cling'n Seal", "2 × 400 sq ft", 6.98, 2, 800, "sq ft", 1),
    ]
    for row in material_seed:
        old = c.execute("SELECT * FROM inventory WHERE product=? LIMIT 1", (row[1],)).fetchone()
        exists_m = c.execute("SELECT id FROM materials WHERE product=? LIMIT 1", (row[1],)).fetchone()
        if not exists_m:
            c.execute("""
                INSERT INTO materials(
                    category,product,presentation,purchase_price,current_qty,
                    equivalent_qty,equivalent_unit,reorder_point,active,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,1,?,?)
            """, row + (now, now))
        if old:
            c.execute("UPDATE inventory SET active=0,updated_at=? WHERE product=?", (now, row[1]))
    # Mantener los materiales conocidos actualizados.
    for row in material_seed:
        c.execute("""
            UPDATE materials SET category=?,presentation=?,purchase_price=?,
            current_qty=?,equivalent_qty=?,equivalent_unit=?,reorder_point=?,
            active=1,updated_at=? WHERE product=?
        """, (row[0],row[2],row[3],row[4],row[5],row[6],row[7],now,row[1]))

    # Papelón/Panela Del Trópico Oro: una unidad actual; recompra en 3.
    p = c.execute("SELECT id FROM inventory WHERE product LIKE 'Papelón%' OR product LIKE 'Papelon%' LIMIT 1").fetchone()
    if p:
        c.execute("""UPDATE inventory SET category=?,product=?,presentation=?,purchase_price=?,
            current_qty=?,equivalent_qty=?,equivalent_unit=?,reorder_point=?,active=1,updated_at=? WHERE id=?""",
            ("Azúcar / Endulzantes","Papelón / Panela Del Trópico Oro","16 oz",2.92,1,1,"unidad",3,now,p["id"]))
    else:
        c.execute("""INSERT INTO inventory(category,product,presentation,purchase_price,current_qty,
            equivalent_qty,equivalent_unit,reorder_point,active,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
            ("Azúcar / Endulzantes","Papelón / Panela Del Trópico Oro","16 oz",2.92,1,1,"unidad",3,now,now))

    # Segundo queso: mozzarella rallada.
    m = c.execute("SELECT id FROM inventory WHERE product LIKE '%Mozzarella%' LIMIT 1").fetchone()
    if not m:
        c.execute("""INSERT INTO inventory(category,product,presentation,purchase_price,current_qty,
            equivalent_qty,equivalent_unit,reorder_point,active,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,1,?,?)""",
            ("Queso","Member's Mark Mozzarella rallada","5 lb",0,0,0,"lb",0,now,now))

    recipe_defs = [
        ("Pan Francés", "14 panes de 75 g", "350°F (180°C)", "18 min", "Prefermento + masa."),
        ("Pan de Leche (9 pancitos)", "9 pancitos", "350°F (180°C)", "15 a 20 min", "Pack de 9."),
        ("Pan de Leche Tradicional", "80 g pancitos o 400 g panes largos", "350°F (180°C)", "Aprox. 40 min", "Larga fermentación con prefermento."),
        ("Pan de Queso", "2 panes grandes o 13 pequeños", "160°C", "35 min", "Receta oficial: 500 g de harina y 400 g de queso."),
        ("Pan Dulce de Coco", "13 unidades aprox.", "340°F (170°C)", "15 min", "Incluye melado y cobertura."),
        ("Pan de Guayaba", "Aprox. 300 g c/u", "350°F (180°C)", "20 min", "Relleno: pasta de guayaba al gusto."),
        ("Pan de Molde — Dulce Remolino de Chocolate", "1 pan grande de 30 cm", "356°F (180°C)", "50 min", "Masa blanca y masa de chocolate."),
        ("Pan Tipo Subway", "5 panes de aprox. 200 g", "392°F (200°C)", "10 a 15 min", "Con aceite de oliva; barnizado y topping."),
        ("Cachitos Venezolanos — miga 50%", "16 cachitos", "315°F (160°C)", "20 a 25 min", "Biga 50%; 100 g de masa y 80 g de relleno por cachito."),
        ("Cachitos Venezolanos — 1,000 g", "20–22 cachitos aprox.", "180°C (356°F)", "18 a 22 min", "Versión grande con 1.000 g de harina."),
        ("Golfeados Venezolanos", "16 golfeados", "350°F (180°C)", "15 min + 10 min", "500 g de papelón y queso blanco duro."),
        ("Pan Piñita Mejorada", "14 porciones de 85 a 90 g", "300°F (150°C)", "25 a 30 min", "Tangzhong: 16 g harina + 43 g agua + 43 g leche."),
        ("Pan Andino con Talvina", "2 panes andinos", "170°C (338°F)", "40 a 50 min", "Fermentación con Talvina: 12 a 16 horas."),
        ("Cinnamon Rolls", "12 rolls grandes", "180°C (350°F)", "20 a 25 min", "Tiempo total 3 a 4 horas según levado."),
        ("Pancitos de Queso Dulce", "Según ficha de Josefina", "", "", "Receta oficial cargada desde la ficha."),
    ]

    recipe_ingredients = {
        "Pan Francés": [
            ("Harina","600","g","40 g prefermento + 560 g masa"),("Agua","180","g","80 g prefermento + 100 g masa"),
            ("Leche","140","g","masa"),("Azúcar","40","g","10 g prefermento + 30 g masa"),("Levadura","8","g","prefermento"),
            ("Sal","10","g",""),("Mantequilla","40","g",""),
        ],
        "Pan de Leche (9 pancitos)": [
            ("Harina de trigo","500","g",""),("Levadura","5","g","instantánea"),("Azúcar","80","g",""),("Sal","5","g",""),
            ("Leche","250","ml","tibia"),("Mantequilla","50","g","derretida"),("Huevo","1","unidad","masa"),
            ("Vainilla","1","cdita","opcional"),("Azúcar glass","50","g","para espolvorear"),("Huevo","1","unidad","barnizar"),
        ],
        "Pan de Leche Tradicional": [
            ("Harina","1750","g","250 g prefermento + 1500 g masa"),("Azúcar","425","g","125 g prefermento + 300 g masa"),
            ("Agua","250","g","prefermento"),("Mantequilla","180","g",""),("Huevos","3","unidades",""),
            ("Sal","30","g",""),("Leche en polvo","60","g",""),("Agua/leche","625","ml",""),("Levadura seca","6","g",""),
        ],
        "Pan de Queso": [
            ("Harina panadera","500","g",""),("Huevo","1","unidad",""),("Leche líquida","250","g","tibia"),
            ("Azúcar","60","g",""),("Levadura","7","g","instantánea"),("Sal","9","g",""),("Mantequilla","80","g","pomada"),
            ("Queso llanero / mozzarella","400","g",""),
        ],
        "Pan Dulce de Coco": [
            ("Harina de fuerza","500","g",""),("Azúcar","100","g","masa"),("Leche en polvo","40","g",""),("Mantequilla","40","g",""),
            ("Huevos","2","unidades",""),("Agua o leche","200","ml",""),("Levadura fresca","10","g","o 7 g seca"),
            ("Sal","7","g",""),("Esencia de coco","7","g",""),("Canela","1","pizca",""),("Coco rallado","100","g","masa/cobertura"),
            ("Azúcar","200","g","melado"),("Agua","200","ml","melado"),("Azúcar","100","g","corteza"),("Coco rallado","100","g","corteza"),
        ],
        "Pan de Guayaba": [
            ("Harina panadera","850","g",""),("Leche entera","400","ml",""),("Azúcar","120","g",""),("Sal","3","g","1 pizca"),
            ("Huevos","2","unidades",""),("Mantequilla sin sal","95","g",""),("Levadura seca","8","g",""),
            ("Pasta de guayaba","al gusto","","relleno"),
        ],
        "Pan de Molde — Dulce Remolino de Chocolate": [
            ("Harina todo uso","450","g",""),("Azúcar","110","g",""),("Sal","2.5","g",""),
            ("Levadura seca instantánea","10","g",""),("Huevo","1","unidad",""),("Leche","250","ml",""),
            ("Mantequilla sin sal","40","g",""),("Cacao","36","g",""),("Aceite","cantidad necesaria","","para engrasar"),
            ("Papel aluminio","cantidad necesaria","",""),
        ],
        "Pan Tipo Subway": [
            ("Harina panadera","600","g",""),("Leche tibia","350","g",""),("Aceite de oliva virgen light","90","ml",""),
            ("Azúcar","30","g",""),("Sal","10","g",""),("Levadura instantánea","9","g","o 22 g fresca"),
            ("Leche","cantidad necesaria","","para barnizar"),("Parmesano","cantidad necesaria","",""),("Orégano","cantidad necesaria","",""),
        ],
        "Cachitos Venezolanos — miga 50%": [
            ("Harina","627","g","173 g biga + 454 g final"),("Leche","272","g","86 g biga + 186 g final"),
            ("Levadura instantánea","7.57","g","0.57 g biga + 7 g final"),("Sal","7","g",""),("Huevos","2","unidades","aprox. 100 g"),
            ("Mantequilla salada","100","g",""),("Azúcar","100","g",""),("Jamón ahumado","760","g",""),("Tocineta","200","g",""),
        ],
        "Cachitos Venezolanos — 1,000 g": [
            ("Harina de trigo","1000","g",""),("Azúcar","120","g",""),("Sal","16","g",""),("Levadura seca instantánea","10","g",""),
            ("Agua o leche tibia","400","ml",""),("Mantequilla","120","g",""),("Huevos","2","unidades",""),
            ("Leche en polvo","4","cucharadas","opcional"),("Jamón de pierna","al gusto","","relleno"),("Tocineta","al gusto","","relleno"),
        ],
        "Golfeados Venezolanos": [
            ("Harina panadera","800","g",""),("Leche entera","430","ml","280 ml masa + 150 ml barniz"),("Mantequilla","130","g",""),
            ("Azúcar","150","g",""),("Sal","10","g",""),("Huevos","2","unidades",""),("Vainilla","2","cucharadas",""),
            ("Levadura instantánea","8","g",""),("Queso blanco duro","500","g",""),("Papelón","500","g","parte rallado y parte melado"),
            ("Agua","200","ml","melado"),("Melado","70","ml","para barnizar"),
        ],
        "Pan Piñita Mejorada": [
            ("Harina panadera","616","g","600 g masa + 16 g Tangzhong"),("Agua","43","g","Tangzhong"),
            ("Leche","243","g","43 g Tangzhong + 200 g masa"),("Azúcar","150","g",""),("Leche en polvo","20","g",""),
            ("Levadura instantánea","6","g",""),("Mantequilla","70","g","pomada"),("Huevo","1","unidad","más 1 yema"),
            ("Esencia de piña","2","cucharadas",""),("Sal","3-4","g",""),("Vainilla","2","cucharadas",""),
        ],
        "Pan Andino con Talvina": [
            ("Harina de trigo panadera","550","g",""),("Masa madre Talvina","120","g","activa"),("Leche líquida","140","g",""),
            ("Huevo entero","1","unidad",""),("Azúcar","150","g",""),("Mantequilla","55","g",""),("Sal","3","g",""),
            ("Manteca de cerdo","55","g","o mantequilla"),("Miel de abejas","5","g",""),("Azúcar vainillado","7","g","o esencia de vainilla"),
        ],
        "Cinnamon Rolls": [
            ("Harina de trigo","500","g","masa"),("Azúcar","80","g","masa"),("Leche en polvo","25","g","masa"),
            ("Sal","7","g","masa"),("Levadura instantánea","10","g","masa"),("Huevo","1","50 g","masa"),("Leche tibia","250","g","masa"),
            ("Mantequilla sin sal","80","g","masa"),("Mantequilla sin sal","100","g","relleno"),("Azúcar morena","150","g","relleno"),
            ("Canela en polvo","20","g","relleno"),("Mantequilla sin sal","85","g","glaseado"),("Queso crema","85","g","glaseado"),
            ("Azúcar glas","165","g","glaseado"),("Esencia de vainilla","5","ml","glaseado"),("Leche","15","ml","opcional"),
        ],
        "Pancitos de Queso Dulce": [
            ("Harina panadera","500","g","",""),
            ("Azúcar","al gusto","","según ficha"),
            ("Queso","al gusto","","según ficha"),
        ],
    }


    for old_name in ("Cachitos Venezolanos — 500 g", "Pan Piñita Mejorada", "Pan de Queso", "Cachitos Venezolanos — miga 50%"):
        c.execute("DELETE FROM recipes WHERE name=?", (old_name,))

    for r in recipe_defs:
        exists = c.execute("SELECT id FROM recipes WHERE name=?", (r[0],)).fetchone()
        if not exists:
            cur = c.execute(
                "INSERT INTO recipes(name,yield_text,oven_temp,bake_time,notes) VALUES(?,?,?,?,?)",
                r
            )
            rid = cur.lastrowid
            for item in recipe_ingredients.get(r[0], []):
                c.execute(
                    "INSERT INTO recipe_ingredients(recipe_id,ingredient_name,amount,unit,notes) VALUES(?,?,?,?,?)",
                    (rid, *item)
                )

    if c.execute("SELECT COUNT(*) FROM promotions").fetchone()[0] == 0:
        for p in PROMOTIONS:
            c.execute(
                "INSERT INTO promotions(id,name,price,description,includes,active) VALUES(?,?,?,?,?,?)",
                (p["id"], p["name"], p["price"], p["description"], p["includes"], 1)
            )

    c.commit()
    c.close()


def serialize_order(c, row):
    items = [dict(x) for x in c.execute(
        "SELECT * FROM items WHERE order_id=? ORDER BY id", (row["id"],)
    ).fetchall()]
    payments = [dict(x) for x in c.execute(
        "SELECT * FROM payments WHERE order_id=? ORDER BY id", (row["id"],)
    ).fetchall()]
    total = sum(float(i["qty"]) * float(i["unit_price"]) for i in items)
    paid = sum(float(p["amount"]) for p in payments)
    return {
        **dict(row),
        "items": items,
        "payments": payments,
        "total": total,
        "paid": paid,
        "balance": max(0, total - paid),
    }


@app.route("/")
def home():
    c = db()
    rows = c.execute(
        "SELECT * FROM orders ORDER BY delivery_date, id DESC"
    ).fetchall()
    orders = [serialize_order(c, r) for r in rows]

    inventory = [dict(r) for r in c.execute(
        "SELECT * FROM inventory WHERE active=1 ORDER BY category,product"
    ).fetchall()]

    recipes = []
    for rr in c.execute(
        "SELECT * FROM recipes WHERE active=1 ORDER BY name"
    ).fetchall():
        rd = dict(rr)
        rd["ingredients"] = [
            dict(x) for x in c.execute(
                "SELECT ingredient_name,amount,unit,notes FROM recipe_ingredients "
                "WHERE recipe_id=? ORDER BY id", (rr["id"],)
            ).fetchall()
        ]
        recipes.append(rd)

    promotions = [
        dict(x) for x in c.execute(
            "SELECT * FROM promotions ORDER BY name"
        ).fetchall()
    ]

    materials = [dict(x) for x in c.execute(
        "SELECT * FROM materials WHERE active=1 ORDER BY category,product"
    ).fetchall()]

    today = datetime.now().strftime("%Y-%m-%d")
    active = [o for o in orders if o["status"] not in ("Entregado", "Cancelado")]
    finalized = [o for o in orders if o["status"] in ("Entregado", "Cancelado")]

    sales_today = sum(
        o["total"] for o in orders
        if o["status"] == "Entregado" and o["delivery_date"] == today
    )
    pending_balance = sum(o["balance"] for o in active)
    pending_count = sum(1 for o in active if o["status"] == "Pendiente de elaborar")
    ready_count = sum(1 for o in active if o["status"] == "Listo para entregar")

    dashboard = {
        "sales_today": sales_today,
        "pending_balance": pending_balance,
        "pending_count": pending_count,
        "ready_count": ready_count,
    }

    c.close()
    return render_template(
        "index.html",
        products=PRODUCTS,
        promotions=promotions,
        orders=orders,
        active_orders=active,
        finalized_orders=finalized,
        inventory=inventory,
        recipes=recipes,
        materials=materials,
        dashboard=dashboard,
    )


@app.post("/orders")
@app.post("/orders/<int:order_id>")
def save_order(order_id=None):
    data = request.get_json() or {}
    client = (data.get("client") or "").strip()
    delivery_date = (data.get("delivery_date") or "").strip()
    status = (data.get("status") or "Pendiente de elaborar").strip()
    notes = data.get("notes") or ""
    is_test = 1 if data.get("is_test") else 0
    items = data.get("items") or []
    payments = data.get("payments") or []

    if not client or not delivery_date:
        return jsonify({"ok": False, "error": "Cliente y fecha son obligatorios"}), 400

    c = db()
    try:
        if order_id is None:
            cur = c.execute(
                "INSERT INTO orders(client,delivery_date,status,notes,created_at,is_test) VALUES(?,?,?,?,?,?)",
                (client, delivery_date, status, notes, datetime.now().isoformat(), is_test)
            )
            order_id = cur.lastrowid
        else:
            exists = c.execute("SELECT id FROM orders WHERE id=?", (order_id,)).fetchone()
            if not exists:
                return jsonify({"ok": False, "error": "Pedido no encontrado"}), 404
            c.execute(
                "UPDATE orders SET client=?,delivery_date=?,status=?,notes=?,is_test=? WHERE id=?",
                (client, delivery_date, status, notes, is_test, order_id)
            )
            c.execute("DELETE FROM items WHERE order_id=?", (order_id,))
            c.execute("DELETE FROM payments WHERE order_id=?", (order_id,))

        for item in items:
            product = (item.get("product") or "").strip()
            if not product:
                continue
            c.execute(
                "INSERT INTO items(order_id,product,qty,unit_price,promotion_id,promotion_name,promotion_description) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    order_id,
                    product,
                    int(item.get("qty") or 1),
                    float(item.get("unit_price") or 0),
                    item.get("promotion_id") or "",
                    item.get("promotion_name") or "",
                    item.get("promotion_description") or "",
                )
            )

        for payment in payments:
            method = (payment.get("method") or "Otro").strip()
            amount = max(0, float(payment.get("amount") or 0))
            if amount:
                c.execute(
                    "INSERT INTO payments(order_id,method,amount) VALUES(?,?,?)",
                    (order_id, method, amount)
                )

        c.commit()
        return jsonify({"ok": True, "id": order_id})
    except Exception as exc:
        c.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        c.close()


@app.delete("/orders/<int:order_id>")
def delete_order(order_id):
    c = db()
    row = c.execute("SELECT status,is_test FROM orders WHERE id=?", (order_id,)).fetchone()
    if not row:
        c.close()
        return jsonify({"ok": False, "error": "Pedido no encontrado"}), 404
    if int(row["is_test"] or 0) == 0 and row["status"] == "Entregado":
        c.close()
        return jsonify({"ok": False, "error": "Los pedidos reales entregados no se pueden eliminar."}), 403
    c.execute("DELETE FROM orders WHERE id=?", (order_id,))
    c.commit()
    c.close()
    return jsonify({"ok": True})


@app.get("/clients")
def clients():
    q = (request.args.get("q") or "").strip()
    c = db()
    rows = c.execute(
        "SELECT DISTINCT client FROM orders WHERE client LIKE ? COLLATE NOCASE "
        "AND is_test=0 ORDER BY client LIMIT 10", ((q + "%") if q else "%",)
    ).fetchall()
    result = []
    for row in rows:
        order = c.execute(
            "SELECT id,delivery_date,status,notes FROM orders "
            "WHERE client=? AND status!='Cancelado' AND is_test=0 "
            "ORDER BY delivery_date DESC,id DESC LIMIT 1", (row["client"],)
        ).fetchone()
        items = []
        if order:
            items = [dict(x) for x in c.execute(
                "SELECT product,qty,unit_price FROM items "
                "WHERE order_id=? AND (promotion_id='' OR promotion_id IS NULL)",
                (order["id"],)
            ).fetchall()]
        result.append({
            "client": row["client"],
            "items": items,
            "last_order_id": order["id"] if order else None,
            "last_delivery_date": order["delivery_date"] if order else "",
            "last_status": order["status"] if order else "",
            "last_notes": order["notes"] if order else "",
        })
    c.close()
    return jsonify(result)


@app.get("/promotions")
def get_promotions():
    c = db()
    rows = [dict(x) for x in c.execute(
        "SELECT * FROM promotions ORDER BY name"
    ).fetchall()]
    c.close()
    return jsonify(rows)


@app.post("/promotions")
def create_promotion():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False}), 400
    pid = "promo_" + str(abs(hash(name + datetime.now().isoformat())))
    c = db()
    c.execute(
        "INSERT INTO promotions(id,name,price,description,includes,active) VALUES(?,?,?,?,?,1)",
        (pid, name, float(data.get("price") or 0), data.get("description", ""), data.get("includes", ""))
    )
    c.commit()
    c.close()
    return jsonify({"ok": True, "id": pid})


@app.put("/promotions/<pid>")
def update_promotion(pid):
    data = request.get_json() or {}
    c = db()
    c.execute(
        "UPDATE promotions SET name=?,price=?,description=?,includes=?,active=? WHERE id=?",
        (
            (data.get("name") or "").strip(),
            float(data.get("price") or 0),
            data.get("description", ""),
            data.get("includes", ""),
            1 if data.get("active", True) else 0,
            pid,
        )
    )
    c.commit()
    c.close()
    return jsonify({"ok": True})


@app.delete("/promotions/<pid>")
def deactivate_promotion(pid):
    c = db()
    c.execute("UPDATE promotions SET active=0 WHERE id=?", (pid,))
    c.commit()
    c.close()
    return jsonify({"ok": True})


@app.get("/recipes")
def get_recipes():
    c = db()
    result = []
    for rr in c.execute(
        "SELECT * FROM recipes WHERE active=1 ORDER BY name"
    ).fetchall():
        rd = dict(rr)
        rd["ingredients"] = [
            dict(x) for x in c.execute(
                "SELECT ingredient_name,amount,unit,notes FROM recipe_ingredients "
                "WHERE recipe_id=? ORDER BY id", (rr["id"],)
            ).fetchall()
        ]
        result.append(rd)
    c.close()
    return jsonify(result)


def inventory_payload(data):
    return (
        (data.get("category") or "").strip(),
        (data.get("product") or "").strip(),
        data.get("presentation", ""),
        float(data.get("purchase_price") or 0),
        float(data.get("current_qty") or 0),
        float(data.get("equivalent_qty") or 0),
        data.get("equivalent_unit", ""),
        float(data.get("reorder_point") or 0),
    )


@app.get("/inventory")
def get_inventory():
    c = db()
    rows = [dict(x) for x in c.execute(
        "SELECT * FROM inventory WHERE active=1 ORDER BY category,product"
    ).fetchall()]
    c.close()
    return jsonify(rows)


@app.post("/inventory")
def create_inventory():
    data = request.get_json() or {}
    category, product, presentation, price, current, equivalent, unit, reorder = inventory_payload(data)
    if not category or not product:
        return jsonify({"ok": False}), 400
    now = datetime.now().isoformat()
    c = db()
    c.execute(
        "INSERT INTO inventory(category,product,presentation,purchase_price,current_qty,equivalent_qty,equivalent_unit,reorder_point,active,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,1,?,?)",
        (category, product, presentation, price, current, equivalent, unit, reorder, now, now)
    )
    c.commit()
    c.close()
    return jsonify({"ok": True})


@app.put("/inventory/<int:iid>")
def update_inventory(iid):
    data = request.get_json() or {}
    category, product, presentation, price, current, equivalent, unit, reorder = inventory_payload(data)
    if not category or not product:
        return jsonify({"ok": False}), 400
    c = db()
    c.execute(
        "UPDATE inventory SET category=?,product=?,presentation=?,purchase_price=?,current_qty=?,equivalent_qty=?,equivalent_unit=?,reorder_point=?,updated_at=? WHERE id=?",
        (category, product, presentation, price, current, equivalent, unit, reorder, datetime.now().isoformat(), iid)
    )
    c.commit()
    c.close()
    return jsonify({"ok": True})


@app.delete("/inventory/<int:iid>")
def delete_inventory(iid):
    c = db()
    c.execute(
        "UPDATE inventory SET active=0,updated_at=? WHERE id=?",
        (datetime.now().isoformat(), iid)
    )
    c.commit()
    c.close()
    return jsonify({"ok": True})


@app.get("/materials")
def get_materials():
    c = db()
    rows = [dict(x) for x in c.execute(
        "SELECT * FROM materials WHERE active=1 ORDER BY category,product"
    ).fetchall()]
    c.close()
    return jsonify(rows)


@app.post("/materials")
def create_material():
    data = request.get_json() or {}
    category, product, presentation, price, current, equivalent, unit, reorder = inventory_payload(data)
    if not category or not product:
        return jsonify({"ok": False}), 400
    now = datetime.now().isoformat()
    c = db()
    c.execute(
        "INSERT INTO materials(category,product,presentation,purchase_price,current_qty,equivalent_qty,equivalent_unit,reorder_point,active,created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?,?,1,?,?)",
        (category, product, presentation, price, current, equivalent, unit, reorder, now, now)
    )
    c.commit()
    c.close()
    return jsonify({"ok": True})


@app.put("/materials/<int:iid>")
def update_material(iid):
    data = request.get_json() or {}
    category, product, presentation, price, current, equivalent, unit, reorder = inventory_payload(data)
    if not category or not product:
        return jsonify({"ok": False}), 400
    c = db()
    c.execute(
        "UPDATE materials SET category=?,product=?,presentation=?,purchase_price=?,current_qty=?,equivalent_qty=?,equivalent_unit=?,reorder_point=?,updated_at=? WHERE id=?",
        (category, product, presentation, price, current, equivalent, unit, reorder, datetime.now().isoformat(), iid)
    )
    c.commit()
    c.close()
    return jsonify({"ok": True})


@app.delete("/materials/<int:iid>")
def delete_material(iid):
    c = db()
    c.execute(
        "UPDATE materials SET active=0,updated_at=? WHERE id=?",
        (datetime.now().isoformat(), iid)
    )
    c.commit()
    c.close()
    return jsonify({"ok": True})


init()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

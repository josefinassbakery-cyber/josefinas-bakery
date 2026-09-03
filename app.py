from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "josefinas_bakery.db")

app = Flask(__name__)


class SafeOrder(dict):
    """Evita que Jinja confunda la clave 'items' con dict.items()."""
    @property
    def items(self):
        return dict.get(self, "items", [])


# ============================================================
# MENÚ OFICIAL — ORDEN DE LAS 5 SECCIONES
# ============================================================

PRODUCTS = [
    # 1. PANES SALADOS
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
    ("Extra Queso + Guayaba", 1.00),
    ("Extra Queso + Tocineta", 1.00),
    ("Extra Guayaba + Queso", 1.00),
    ("Extra Triple relleno", 2.00),

    # 2. PANES DULCES
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

    # 3. ESPECIALIDADES Y ACOMPAÑANTES
    ("Cinnamon Roll Tradicional", 4.50),
    ("Cinnamon Rolls Pack de 2", 8.00),
    ("Cinnamon Rolls Pack de 8", 16.00),
    ("Lemon Roll Tradicional", 4.50),
    ("Lemon Rolls Pack de 2", 8.00),
    ("Lemon Rolls Pack de 8", 16.00),
    ("Topping Nutella", 2.00),
    ("Topping Oreo", 2.00),
    ("Topping Caramelo", 2.00),
    ("Topping Dulce de leche", 2.00),
    ("Topping Fresa", 2.00),
    ("Topping Chocolate", 2.00),

    # 4. OTROS PRODUCTOS
    ("Panelitas San Joaquín (Pack 5 unidades)", 1.00),
    ("Pastelito individual (Incluye salsa)", 3.00),
    ("25 Mini Pastelitos surtidos (Incluye salsa)", 24.00),
    ("50 Mini Pastelitos surtidos (Incluye salsa)", 47.00),
    ("Arepitas de Yuca - Empaque 10 unidades", 12.00),

    # 5. PANES ARTESANALES
    ("Pan Andino Regular", 14.00),
    ("Pan Andino con Talvina (Masa Madre)", 15.00),
    ("Pan Trenza", 15.00),
]

PRODUCT_CATEGORIES = {}
for name, price in PRODUCTS:
    if name.startswith(("Extra ",)):
        category = "Panes Salados"
    elif name.startswith(("Dulce ", "Pack mini Pan de Leche", "Pan de Guayaba",
                           "Golfeado", "Pack 6 Golfeados", "Pan de Queso Dulce",
                           "Corazón de Piña", "Piña & Coco", "Pan Dulce de Coco")):
        category = "Panes Dulces"
    elif name.startswith(("Cinnamon", "Lemon", "Topping ")):
        category = "Especialidades y Acompañantes"
    elif name.startswith(("Panelitas", "Pastelito", "25 Mini", "50 Mini", "Arepitas")):
        category = "Otros Productos"
    else:
        category = "Panes Salados"
    PRODUCT_CATEGORIES[name] = category

# Catálogo listo para una interfaz que quiera agrupar explícitamente por sección.
PRODUCT_CATALOG = [
    {"name": name, "price": price, "category": PRODUCT_CATEGORIES[name]}
    for name, price in PRODUCTS
]

PROMOTIONS = [
    {
        "id": "promo_pan_queso_grande_16",
        "name": 'Promo Pan de Queso Grande 16" — Piñita gratis',
        "price": 20.00,
        "description": 'Pan de queso grande 16" + 1 pack de Piñitas gratis',
        "includes": "Incluye 1 pack de Piñitas gratis",
        "active": True,
    }
]


# ============================================================
# BASE DE DATOS
# ============================================================

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def table_columns(c, table):
    return {r["name"] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}


def ensure_column(c, table, column, definition):
    if column not in table_columns(c, table):
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


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

    CREATE TABLE IF NOT EXISTS clients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE COLLATE NOCASE,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1
    );
    """)

    ensure_column(c, "orders", "is_test", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(c, "items", "promotion_id", "TEXT DEFAULT ''")
    ensure_column(c, "items", "promotion_name", "TEXT DEFAULT ''")
    ensure_column(c, "items", "promotion_description", "TEXT DEFAULT ''")

    now = datetime.now().isoformat()

    # --------------------------------------------------------
    # INVENTARIO — ingredientes. Papel film y papel de horno
    # se trasladan a MATERIALES automáticamente.
    # --------------------------------------------------------
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

    # --------------------------------------------------------
    # MOVER materiales existentes del inventario a Materiales.
    # No se borra el registro: se conserva históricamente pero
    # queda inactivo en inventario.
    # --------------------------------------------------------
    material_names = {"Papel film", "Papel para hornear"}

    for name in material_names:
        rows = c.execute(
            "SELECT * FROM inventory WHERE category=? OR product LIKE ?",
            (name, f"%{name}%")
        ).fetchall()

        # También cubre nombres exactos guardados en product.
        for r in rows:
            if r["active"] != 1:
                continue
            already = c.execute(
                "SELECT id FROM materials WHERE product=? AND presentation=? LIMIT 1",
                (r["product"], r["presentation"])
            ).fetchone()
            if not already:
                c.execute("""
                    INSERT INTO materials(
                        category,product,presentation,purchase_price,current_qty,
                        equivalent_qty,equivalent_unit,reorder_point,active,created_at,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,1,?,?)
                """, (
                    "Materiales de trabajo", r["product"], r["presentation"],
                    r["purchase_price"], r["current_qty"], r["equivalent_qty"],
                    r["equivalent_unit"], r["reorder_point"], now, now
                ))
            c.execute(
                "UPDATE inventory SET active=0,updated_at=? WHERE id=?",
                (now, r["id"])
            )

    # Si los registros aún no existían en ninguna parte, créalos en Materiales.
    materials_seed = [
        ("Materiales de trabajo", "Glad Cling'n Seal", "2 × 400 sq ft", 6.98, 0, 0, "sq ft", 0),
        ("Materiales de trabajo", "Great Value Non-Stick Parchment Paper", "100 sq ft", 5.67, 0, 0, "sq ft", 0),
    ]
    for row in materials_seed:
        exists = c.execute(
            "SELECT id FROM materials WHERE product=? AND presentation=? LIMIT 1",
            (row[1], row[2])
        ).fetchone()
        if not exists:
            c.execute("""
                INSERT INTO materials(
                    category,product,presentation,purchase_price,current_qty,
                    equivalent_qty,equivalent_unit,reorder_point,active,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,1,?,?)
            """, row + (now, now))

    # --------------------------------------------------------
    # RECETAS
    # --------------------------------------------------------
    recipe_defs = [
        ("Pan Francés", "13 panes de 90 g", "350°F (180°C)", "18 min", "Prefermento + masa."),
        ("Pan de Leche (9 pancitos)", "9 pancitos aprox. 65 g", "350°F (180°C)", "15 a 20 min", "Versión rápida."),
        ("Pan de Queso", "2 panes grandes o 13 pequeños", "160°C", "35 min", "520 g harina y 400 g queso."),
        ("Pan Dulce de Coco", "13 unidades aprox.", "340°F (170°C)", "15 min", "Incluye melado y cobertura."),
        ("Pan de Guayaba", "Aprox. 300 g c/u", "350°F (180°C)", "20 min", "Relleno: pasta de guayaba al gusto."),
        ("Pan de Molde — Dulce Remolino de Chocolate", "1 pan grande de 30 cm", "356°F (180°C)", "50 min", "Masa blanca y masa de chocolate con 36 g de cacao."),
        ("Pan Tipo Subway", "5 panes de aprox. 200 g", "392°F (200°C)", "10 a 15 min", "90 ml aceite de oliva; 9 g seca o 22 g fresca."),
        ("Pan de Leche Tradicional", "80 g pancitos o 400 g panes largos", "350°F (180°C)", "Aprox. 40 min", "Larga fermentación con prefermento."),
        ("Cachitos Venezolanos — miga 50%", "16 cachitos", "315°F (160°C)", "20 a 25 min", "Biga 50%; 80 g relleno por cachito."),
        ("Golfeados Venezolanos", "16 golfeados", "350°F (180°C)", "15 min + 10 min", "500 g papelón y queso blanco duro."),
        ("Pan Piñita Mejorada", "14 porciones de 85 a 90 g", "320°F (160°C)", "18 a 25 min", "Tangzhong: 16 g harina + 43 g agua + 43 g leche."),
    ]

    recipe_ingredients = {
        "Pan Francés": [
            ("Harina", "600", "g", "40 g prefermento + 560 g masa"),
            ("Agua", "180", "g", "80 g prefermento + 100 g masa"),
            ("Leche", "140", "g", "masa"),
            ("Azúcar", "40", "g", "10 g prefermento + 30 g masa"),
            ("Levadura", "6", "g", "seca instantánea"),
            ("Sal", "10", "g", ""),
            ("Mantequilla", "40", "g", ""),
        ],
        "Pan de Leche (9 pancitos)": [
            ("Harina de trigo", "500", "g", ""),
            ("Levadura", "5", "g", "instantánea"),
            ("Azúcar", "80", "g", ""),
            ("Sal", "5", "g", ""),
            ("Leche", "250", "ml", "tibia"),
            ("Mantequilla", "50", "g", "derretida"),
            ("Huevo", "1", "unidad", "masa"),
            ("Vainilla", "1", "cdita", "opcional"),
            ("Azúcar glass", "50", "g", "para espolvorear"),
            ("Huevo", "1", "unidad", "batido para barnizar"),
        ],
        "Pan de Queso": [
            ("Harina panadera", "520", "g", ""),
            ("Huevo", "1", "unidad", ""),
            ("Leche líquida", "250", "g", "tibia"),
            ("Azúcar", "60", "g", ""),
            ("Levadura", "7", "g", "instantánea"),
            ("Sal", "9", "g", ""),
            ("Mantequilla", "80", "g", "pomada"),
            ("Queso", "400", "g", "llanero o mezcla llanero/mozzarella"),
        ],
        "Pan Dulce de Coco": [
            ("Harina de fuerza", "500", "g", ""),
            ("Azúcar", "100", "g", "masa"),
            ("Leche en polvo", "40", "g", ""),
            ("Mantequilla", "40", "g", ""),
            ("Huevos", "2", "unidades", ""),
            ("Agua o leche", "200", "ml", ""),
            ("Levadura fresca", "10", "g", "o 7 g seca"),
            ("Sal", "7", "g", ""),
            ("Esencia de coco", "7", "g", ""),
            ("Canela", "1", "pizca", ""),
            ("Coco rallado", "100", "g", "masa/cobertura"),
            ("Azúcar", "200", "g", "melado"),
            ("Agua", "200", "ml", "melado"),
            ("Azúcar", "100", "g", "corteza"),
            ("Coco rallado", "100", "g", "corteza"),
        ],
        "Pan de Guayaba": [
            ("Harina panadera", "850", "g", ""),
            ("Leche entera", "400", "ml", ""),
            ("Azúcar", "120", "g", ""),
            ("Sal", "3", "g", ""),
            ("Huevos", "2", "unidades", ""),
            ("Mantequilla sin sal", "95", "g", ""),
            ("Levadura seca", "8", "g", ""),
            ("Pasta de guayaba", "al gusto", "", "relleno"),
        ],
        "Pan de Molde — Dulce Remolino de Chocolate": [
            ("Harina todo uso", "450", "g", ""),
            ("Azúcar", "110", "g", ""),
            ("Sal", "2.5", "g", ""),
            ("Levadura seca instantánea", "10", "g", ""),
            ("Huevo", "1", "unidad", ""),
            ("Leche", "250", "ml", ""),
            ("Mantequilla sin sal", "40", "g", ""),
            ("Cacao", "36", "g", ""),
            ("Aceite", "cantidad necesaria", "", "para engrasar"),
            ("Papel aluminio", "cantidad necesaria", "", ""),
        ],
        "Pan Tipo Subway": [
            ("Harina panadera", "600", "g", ""),
            ("Leche tibia", "350", "g", ""),
            ("Aceite de oliva virgen light", "90", "ml", ""),
            ("Azúcar", "30", "g", ""),
            ("Sal", "10", "g", ""),
            ("Levadura instantánea", "9", "g", "o 22 g fresca"),
            ("Leche", "cantidad necesaria", "", "para barnizar"),
            ("Parmesano", "cantidad necesaria", "", ""),
            ("Orégano", "cantidad necesaria", "", ""),
        ],
        "Pan de Leche Tradicional": [
            ("Harina", "1750", "g", "250 g prefermento + 1500 g masa"),
            ("Azúcar", "425", "g", "125 g prefermento + 300 g masa"),
            ("Agua", "250", "g", "prefermento"),
            ("Mantequilla", "180", "g", ""),
            ("Huevos", "3", "unidades", ""),
            ("Sal", "30", "g", ""),
            ("Leche en polvo", "60", "g", ""),
            ("Agua/leche", "625", "ml", ""),
            ("Levadura seca", "6", "g", ""),
        ],
        "Cachitos Venezolanos — miga 50%": [
            ("Harina", "627", "g", "173 g biga + 454 g final"),
            ("Leche", "272", "g", "86 g biga + 186 g final"),
            ("Levadura instantánea", "7.57", "g", "0.57 g biga + 7 g final"),
            ("Sal", "7", "g", ""),
            ("Huevos", "2", "unidades", "aprox. 100 g"),
            ("Mantequilla salada", "100", "g", ""),
            ("Azúcar", "100", "g", ""),
            ("Jamón ahumado", "760", "g", ""),
            ("Tocineta", "200", "g", ""),
        ],
        "Golfeados Venezolanos": [
            ("Harina panadera", "800", "g", ""),
            ("Leche entera", "430", "ml", "280 ml masa + 150 ml barniz"),
            ("Mantequilla", "130", "g", ""),
            ("Azúcar", "150", "g", ""),
            ("Sal", "10", "g", ""),
            ("Huevos", "2", "unidades", ""),
            ("Vainilla", "2", "cucharadas", ""),
            ("Levadura instantánea", "8", "g", ""),
            ("Queso blanco duro", "500", "g", ""),
            ("Papelón", "500", "g", ""),
            ("Agua", "200", "ml", "melado"),
            ("Melado", "70", "ml", "para barnizar"),
        ],
        "Pan Piñita Mejorada": [
            ("Harina panadera", "616", "g", "600 g masa + 16 g tangzhong"),
            ("Agua", "43", "g", "tangzhong"),
            ("Leche", "243", "g", "43 g tangzhong + 200 g masa"),
            ("Azúcar", "150", "g", ""),
            ("Leche en polvo", "20", "g", ""),
            # CORRECCIÓN SOLICITADA: 6 g de levadura instantánea.
            ("Levadura instantánea", "6", "g", ""),
            ("Mantequilla", "70", "g", ""),
            ("Huevo", "1", "unidad", "más 1 yema"),
            ("Esencia de piña", "2", "cucharadas", ""),
            ("Sal", "3-4", "g", ""),
            ("Vainilla", "2", "cucharadas", ""),
        ],
    }

    for r in recipe_defs:
        c.execute("""
            INSERT INTO recipes(name,yield_text,oven_temp,bake_time,notes,active)
            VALUES(?,?,?,?,?,1)
            ON CONFLICT(name) DO UPDATE SET
                yield_text=excluded.yield_text,
                oven_temp=excluded.oven_temp,
                bake_time=excluded.bake_time,
                notes=excluded.notes,
                active=1
        """, r)

        rid = c.execute("SELECT id FROM recipes WHERE name=?", (r[0],)).fetchone()["id"]
        # Solo reemplazamos los ingredientes de estas recetas administradas.
        c.execute("DELETE FROM recipe_ingredients WHERE recipe_id=?", (rid,))
        for item in recipe_ingredients.get(r[0], []):
            c.execute("""
                INSERT INTO recipe_ingredients(
                    recipe_id,ingredient_name,amount,unit,notes
                ) VALUES(?,?,?,?,?)
            """, (rid, *item))

    # Asegurar que la promoción oficial exista y quede activa.
    for p in PROMOTIONS:
        c.execute("""
            INSERT INTO promotions(id,name,price,description,includes,active)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                price=excluded.price,
                description=excluded.description,
                includes=excluded.includes,
                active=1
        """, (
            p["id"], p["name"], p["price"],
            p["description"], p["includes"], 1
        ))

    # Cliente frecuente solicitado: queda disponible desde el primer arranque.
    # Si ya existe, no se duplica.
    c.execute("""
        INSERT INTO clients(name,created_at,updated_at,active)
        VALUES(?,?,?,1)
        ON CONFLICT(name) DO UPDATE SET
            updated_at=excluded.updated_at,
            active=1
    """, ("Carhil Brazon", now, now))

    # Recuperar clientes que ya existen en pedidos históricos.
    for r in c.execute(
        "SELECT DISTINCT client FROM orders WHERE TRIM(client)<>''"
    ).fetchall():
        name = r["client"].strip()
        c.execute("""
            INSERT INTO clients(name,created_at,updated_at,active)
            VALUES(?,?,?,1)
            ON CONFLICT(name) DO UPDATE SET
                updated_at=excluded.updated_at,
                active=1
        """, (name, now, now))

    c.commit()
    c.close()


# ============================================================
# PEDIDOS
# ============================================================

def serialize_order(c, row):
    items = [dict(x) for x in c.execute(
        "SELECT * FROM items WHERE order_id=? ORDER BY id",
        (row["id"],)
    ).fetchall()]
    payments = [dict(x) for x in c.execute(
        "SELECT * FROM payments WHERE order_id=? ORDER BY id",
        (row["id"],)
    ).fetchall()]

    total = sum(float(i["qty"]) * float(i["unit_price"]) for i in items)
    paid = sum(float(p["amount"]) for p in payments)

    return SafeOrder({
        **dict(row),
        "items": items,
        "payments": payments,
        "total": total,
        "paid": paid,
        "balance": max(0, total - paid),
    })


def save_client(c, name):
    name = (name or "").strip()
    if not name:
        return
    now = datetime.now().isoformat()
    c.execute("""
        INSERT INTO clients(name,created_at,updated_at,active)
        VALUES(?,?,?,1)
        ON CONFLICT(name) DO UPDATE SET
            updated_at=excluded.updated_at,
            active=1
    """, (name, now, now))


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

    materials = [dict(r) for r in c.execute(
        "SELECT * FROM materials WHERE active=1 ORDER BY category,product"
    ).fetchall()]

    recipes = []
    for rr in c.execute(
        "SELECT * FROM recipes WHERE active=1 ORDER BY name"
    ).fetchall():
        rd = dict(rr)
        rd["ingredients"] = [
            dict(x) for x in c.execute(
                "SELECT ingredient_name,amount,unit,notes "
                "FROM recipe_ingredients WHERE recipe_id=? ORDER BY id",
                (rr["id"],)
            ).fetchall()
        ]
        recipes.append(rd)

    promotions = [dict(x) for x in c.execute(
        "SELECT * FROM promotions WHERE active=1 ORDER BY name"
    ).fetchall()]

    clients = [dict(x) for x in c.execute(
        "SELECT * FROM clients WHERE active=1 ORDER BY name COLLATE NOCASE"
    ).fetchall()]

    today = datetime.now().date().isoformat()
    active = [o for o in orders if o["status"] not in ("Entregado", "Cancelado")]
    finalized = [o for o in orders if o["status"] in ("Entregado", "Cancelado")]

    sales_today = sum(
        o["total"] for o in orders
        if o["status"] == "Entregado" and o["delivery_date"] == today
    )
    pending_balance = sum(o["balance"] for o in active if o["balance"] > 0)
    ready_count = sum(
        1 for o in active if o["status"] == "Listo para entregar"
    )

    dashboard = {
        "sales_today": sales_today,
        "pending_count": len(active),
        "ready_count": ready_count,
        "pending_balance": pending_balance,
    }

    c.close()

    return render_template(
        "index.html",
        products=PRODUCTS,
        product_catalog=PRODUCT_CATALOG,
        promotions=promotions,
        orders=orders,
        active_orders=active,
        finalized_orders=finalized,
        inventory=inventory,
        materials=materials,
        recipes=recipes,
        clients=clients,
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
        return jsonify({
            "ok": False,
            "error": "Cliente y fecha son obligatorios"
        }), 400

    c = db()

    try:
        if order_id is None:
            cur = c.execute("""
                INSERT INTO orders(
                    client,delivery_date,status,notes,created_at,is_test
                ) VALUES(?,?,?,?,?,?)
            """, (
                client, delivery_date, status, notes,
                datetime.now().isoformat(), is_test
            ))
            order_id = cur.lastrowid
        else:
            exists = c.execute(
                "SELECT id FROM orders WHERE id=?",
                (order_id,)
            ).fetchone()
            if not exists:
                return jsonify({
                    "ok": False,
                    "error": "Pedido no encontrado"
                }), 404

            c.execute("""
                UPDATE orders
                SET client=?,delivery_date=?,status=?,notes=?,is_test=?
                WHERE id=?
            """, (
                client, delivery_date, status, notes, is_test, order_id
            ))
            c.execute("DELETE FROM items WHERE order_id=?", (order_id,))
            c.execute("DELETE FROM payments WHERE order_id=?", (order_id,))

        save_client(c, client)

        for item in items:
            product = (item.get("product") or "").strip()
            if not product:
                continue
            c.execute("""
                INSERT INTO items(
                    order_id,product,qty,unit_price,
                    promotion_id,promotion_name,promotion_description
                ) VALUES(?,?,?,?,?,?,?)
            """, (
                order_id,
                product,
                int(item.get("qty") or 1),
                float(item.get("unit_price") or 0),
                item.get("promotion_id") or "",
                item.get("promotion_name") or "",
                item.get("promotion_description") or "",
            ))

        for payment in payments:
            method = (payment.get("method") or "Otro").strip()
            amount = max(0, float(payment.get("amount") or 0))
            if amount:
                c.execute("""
                    INSERT INTO payments(order_id,method,amount)
                    VALUES(?,?,?)
                """, (order_id, method, amount))

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
    c.execute("DELETE FROM orders WHERE id=?", (order_id,))
    c.commit()
    c.close()
    return jsonify({"ok": True})


# ============================================================
# CLIENTES — AUTOCOMPLETADO / HISTORIAL / PEDIDO REPETIBLE
# ============================================================

@app.get("/clients")
def clients():
    q = (request.args.get("q") or "").strip()

    c = db()

    if q:
        rows = c.execute("""
            SELECT id,name
            FROM clients
            WHERE active=1 AND name LIKE ? COLLATE NOCASE
            ORDER BY name COLLATE NOCASE
            LIMIT 20
        """, (q + "%",)).fetchall()
    else:
        rows = c.execute("""
            SELECT id,name
            FROM clients
            WHERE active=1
            ORDER BY name COLLATE NOCASE
            LIMIT 50
        """).fetchall()

    result = []

    for row in rows:
        latest = c.execute("""
            SELECT id,delivery_date,status
            FROM orders
            WHERE client=? AND status!='Cancelado'
            ORDER BY delivery_date DESC,id DESC
            LIMIT 1
        """, (row["name"],)).fetchone()

        items = []
        if latest:
            items = [dict(x) for x in c.execute("""
                SELECT product,qty,unit_price,
                       promotion_id,promotion_name,promotion_description
                FROM items
                WHERE order_id=?
                ORDER BY id
            """, (latest["id"],)).fetchall()]

        result.append({
            "id": row["id"],
            "client": row["name"],
            "last_order_id": latest["id"] if latest else None,
            "last_order_date": latest["delivery_date"] if latest else None,
            "last_status": latest["status"] if latest else None,
            "items": items,
        })

    c.close()
    return jsonify(result)


@app.get("/clients/<int:client_id>")
def get_client(client_id):
    c = db()
    row = c.execute(
        "SELECT * FROM clients WHERE id=? AND active=1",
        (client_id,)
    ).fetchone()

    if not row:
        c.close()
        return jsonify({"ok": False, "error": "Cliente no encontrado"}), 404

    orders = []
    for o in c.execute("""
        SELECT * FROM orders
        WHERE client=?
        ORDER BY delivery_date DESC,id DESC
    """, (row["name"],)).fetchall():
        orders.append(dict(serialize_order(c, o)))

    result = {
        "client": dict(row),
        "orders": orders,
    }

    c.close()
    return jsonify(result)


@app.get("/clients/<int:client_id>/repeat")
def repeat_client_order(client_id):
    """Devuelve el último pedido del cliente listo para precargar."""
    c = db()
    row = c.execute(
        "SELECT name FROM clients WHERE id=? AND active=1",
        (client_id,)
    ).fetchone()

    if not row:
        c.close()
        return jsonify({"ok": False, "error": "Cliente no encontrado"}), 404

    order = c.execute("""
        SELECT * FROM orders
        WHERE client=? AND status!='Cancelado'
        ORDER BY delivery_date DESC,id DESC
        LIMIT 1
    """, (row["name"],)).fetchone()

    if not order:
        c.close()
        return jsonify({
            "ok": True,
            "client": row["name"],
            "items": [],
            "message": "El cliente todavía no tiene pedidos."
        })

    serialized = serialize_order(c, order)
    c.close()

    return jsonify({
        "ok": True,
        "client": row["name"],
        "order_id": serialized["id"],
        "items": serialized["items"],
        "notes": serialized.get("notes", ""),
    })


@app.post("/clients")
def create_client():
    data = request.get_json() or {}
    name = (data.get("name") or data.get("client") or "").strip()

    if not name:
        return jsonify({
            "ok": False,
            "error": "El nombre del cliente es obligatorio"
        }), 400

    c = db()
    now = datetime.now().isoformat()

    c.execute("""
        INSERT INTO clients(name,created_at,updated_at,active)
        VALUES(?,?,?,1)
        ON CONFLICT(name) DO UPDATE SET
            updated_at=excluded.updated_at,
            active=1
    """, (name, now, now))

    c.commit()
    row = c.execute(
        "SELECT * FROM clients WHERE name=? COLLATE NOCASE",
        (name,)
    ).fetchone()
    c.close()

    return jsonify({"ok": True, "client": dict(row)})


# ============================================================
# PROMOCIONES
# ============================================================

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
    c.execute("""
        INSERT INTO promotions(
            id,name,price,description,includes,active
        ) VALUES(?,?,?,?,?,1)
    """, (
        pid,
        name,
        float(data.get("price") or 0),
        data.get("description", ""),
        data.get("includes", "")
    ))
    c.commit()
    c.close()

    return jsonify({"ok": True, "id": pid})


@app.put("/promotions/<pid>")
def update_promotion(pid):
    data = request.get_json() or {}
    c = db()

    c.execute("""
        UPDATE promotions
        SET name=?,price=?,description=?,includes=?,active=?
        WHERE id=?
    """, (
        (data.get("name") or "").strip(),
        float(data.get("price") or 0),
        data.get("description", ""),
        data.get("includes", ""),
        1 if data.get("active", True) else 0,
        pid,
    ))

    c.commit()
    c.close()
    return jsonify({"ok": True})


@app.delete("/promotions/<pid>")
def deactivate_promotion(pid):
    c = db()
    c.execute(
        "UPDATE promotions SET active=0 WHERE id=?",
        (pid,)
    )
    c.commit()
    c.close()
    return jsonify({"ok": True})


# ============================================================
# RECETAS
# ============================================================

@app.get("/recipes")
def get_recipes():
    c = db()
    result = []

    for rr in c.execute(
        "SELECT * FROM recipes WHERE active=1 ORDER BY name"
    ).fetchall():
        rd = dict(rr)
        rd["ingredients"] = [
            dict(x) for x in c.execute("""
                SELECT ingredient_name,amount,unit,notes
                FROM recipe_ingredients
                WHERE recipe_id=?
                ORDER BY id
            """, (rr["id"],)).fetchall()
        ]
        result.append(rd)

    c.close()
    return jsonify(result)


# ============================================================
# INVENTARIO
# ============================================================

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
    values = inventory_payload(data)
    category, product = values[0], values[1]

    if not category or not product:
        return jsonify({"ok": False}), 400

    now = datetime.now().isoformat()
    c = db()

    c.execute("""
        INSERT INTO inventory(
            category,product,presentation,purchase_price,current_qty,
            equivalent_qty,equivalent_unit,reorder_point,active,
            created_at,updated_at
        ) VALUES(?,?,?,?,?,?,?,?,1,?,?)
    """, values + (now, now))

    c.commit()
    c.close()
    return jsonify({"ok": True})


@app.put("/inventory/<int:iid>")
def update_inventory(iid):
    data = request.get_json() or {}
    values = inventory_payload(data)
    category, product = values[0], values[1]

    if not category or not product:
        return jsonify({"ok": False}), 400

    c = db()

    c.execute("""
        UPDATE inventory
        SET category=?,product=?,presentation=?,purchase_price=?,
            current_qty=?,equivalent_qty=?,equivalent_unit=?,
            reorder_point=?,updated_at=?
        WHERE id=?
    """, values + (datetime.now().isoformat(), iid))

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


# ============================================================
# MATERIALES
# ============================================================

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
    values = inventory_payload(data)
    category, product = values[0], values[1]

    if not category or not product:
        return jsonify({"ok": False}), 400

    now = datetime.now().isoformat()
    c = db()

    c.execute("""
        INSERT INTO materials(
            category,product,presentation,purchase_price,current_qty,
            equivalent_qty,equivalent_unit,reorder_point,active,
            created_at,updated_at
        ) VALUES(?,?,?,?,?,?,?,?,1,?,?)
    """, values + (now, now))

    c.commit()
    c.close()
    return jsonify({"ok": True})


@app.put("/materials/<int:iid>")
def update_material(iid):
    data = request.get_json() or {}
    values = inventory_payload(data)
    category, product = values[0], values[1]

    if not category or not product:
        return jsonify({"ok": False}), 400

    c = db()

    c.execute("""
        UPDATE materials
        SET category=?,product=?,presentation=?,purchase_price=?,
            current_qty=?,equivalent_qty=?,equivalent_unit=?,
            reorder_point=?,updated_at=?
        WHERE id=?
    """, values + (datetime.now().isoformat(), iid))

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


# ============================================================
# EJECUCIÓN LOCAL / RENDER
# ============================================================

init()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

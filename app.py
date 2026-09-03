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


    order_columns = {
        row["name"]
        for row in c.execute("PRAGMA table_info(orders)").fetchall()
    }

    if "is_test" not in order_columns:
        c.execute(
            "ALTER TABLE orders ADD COLUMN is_test INTEGER NOT NULL DEFAULT 0"
        )


    c.execute("""
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
    )
    """)


    c.execute("""
    CREATE TABLE IF NOT EXISTS promotions(
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        price REAL NOT NULL DEFAULT 0,
        description TEXT DEFAULT '',
        includes TEXT DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1
    )
    """)


    c.execute("""
    CREATE TABLE IF NOT EXISTS recipes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        yield_text TEXT DEFAULT '',
        oven_temp TEXT DEFAULT '',
        bake_time TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1
    )
    """)


    c.execute("""
    CREATE TABLE IF NOT EXISTS recipe_ingredients(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        ingredient_name TEXT NOT NULL,
        amount TEXT NOT NULL,
        unit TEXT DEFAULT '',
        notes TEXT DEFAULT '',

        FOREIGN KEY(recipe_id)
        REFERENCES recipes(id)
        ON DELETE CASCADE
    )
    """)


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
        exists = c.execute(
            "SELECT id FROM inventory WHERE product=? AND presentation=? LIMIT 1",
            (row[1], row[2])
        ).fetchone()
       # ============================================================
    # INVENTARIO INICIAL
    # ============================================================

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
        ("Papel para hornear", "Great Value Non-Stick Parchment Paper", "100 sq ft", 5.67, 0, 0, "sq ft"),
        ("Papelón / Panela", "Papelón (Panela) — presentación de la foto", "unidad", 0, 0, 0, "unidades")
    ]

    now = datetime.now().isoformat()

    for row in seed:

        exists = c.execute(
            "SELECT id FROM inventory WHERE product=? AND presentation=? LIMIT 1",
            (row[1], row[2])
        ).fetchone()

        if not exists:

            reorder = 3 if row[1] == "Papelón / Panela" else 0

            c.execute("""
                INSERT INTO inventory(
                    category,
                    product,
                    presentation,
                    purchase_price,
                    current_qty,
                    equivalent_qty,
                    equivalent_unit,
                    reorder_point,
                    active,
                    created_at,
                    updated_at
                )
                VALUES(?,?,?,?,?,?,?, ?,1,?,?)
            """, row[:7] + (reorder, now, now))


    # ============================================================
    # RECETAS ACTUALIZADAS
    # ============================================================

    # Recetas documentadas a partir de las tarjetas que Josefina
    # acaba de pasar.
    #
    # Se reemplazan las versiones anteriores de estas recetas para
    # evitar duplicados y conservar las cantidades nuevas.
    # Ejemplo: Pan Piñita = 70 g de mantequilla.

    recipe_defs = [

        (
            "Pan Francés",
            "13 panes de 90 g",
            "350°F (180°C)",
            "18 min",
            "Prefermento + masa."
        ),

        (
            "Pan de Leche (9 pancitos)",
            "9 pancitos aprox. 65 g",
            "350°F (180°C)",
            "15 a 20 min",
            "Versión rápida; distinta del Pan de Leche Tradicional de larga fermentación."
        ),

        (
            "Pan de Queso",
            "2 panes grandes o 13 pequeños",
            "160°C",
            "35 min",
            "Receta nueva correcta: 520 g harina y 400 g queso."
        ),

        (
            "Pan Dulce de Coco",
            "13 unidades aprox.",
            "340°F (170°C)",
            "15 min",
            "Incluye melado y cobertura de azúcar y coco."
        ),

        (
            "Pan de Guayaba",
            "Aprox. 300 g c/u",
            "350°F (180°C)",
            "20 min",
            "Relleno: pasta de guayaba al gusto."
        ),

        (
            "Pan de Molde — Dulce Remolino de Chocolate",
            "1 pan grande de 30 cm",
            "356°F (180°C)",
            "50 min",
            "Masa blanca y masa de chocolate con 36 g de cacao."
        ),

        (
            "Pan Tipo Subway",
            "5 panes de aprox. 200 g",
            "392°F (200°C)",
            "10 a 15 min",
            "90 ml de aceite de oliva virgen light; 9 g levadura seca o 22 g fresca."
        ),

        (
            "Pan de Leche Tradicional",
            "Según división: 80 g pancitos o 400 g panes largos",
            "350°F (180°C)",
            "Aprox. 40 min",
            "Larga fermentación con prefermento de 2 a 18 h y fermentación final de 10 a 12 h."
        ),

        (
            "Cachitos Venezolanos — miga 50%",
            "16 cachitos",
            "315°F (160°C)",
            "20 a 25 min",
            "Biga 50% preparada el día anterior; 80 g relleno por cachito."
        ),

        (
            "Golfeados Venezolanos",
            "16 golfeados",
            "350°F (180°C)",
            "15 min + 10 min",
            "Incluye 500 g de papelón y queso blanco duro."
        ),

        (
            "Pan Piñita Mejorada",
            "14 porciones de 85 a 90 g",
            "320°F (160°C)",
            "18 a 25 min",
            "Tangzhong: 16 g harina + 43 g agua + 43 g leche. Mantequilla: 70 g."
        ),
    ]


    recipe_ingredients = {

        "Pan Francés": [
            ("Harina", "600", "g", "40 g prefermento + 560 g masa"),
            ("Agua", "180", "g", "80 g prefermento + 100 g masa"),
            ("Leche", "140", "g", "masa"),
            ("Azúcar", "40", "g", "10 g prefermento + 30 g masa"),
            ("Levadura", "6", "g", "seca instantánea"),
            ("Sal", "10", "g", ""),
            ("Mantequilla", "40", "g", "")
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
            ("Huevo", "1", "unidad", "batido para barnizar")
        ],

        "Pan de Queso": [
            ("Harina panadera", "520", "g", ""),
            ("Huevo", "1", "unidad", ""),
            ("Leche líquida", "250", "g", "tibia"),
            ("Azúcar", "60", "g", ""),
            ("Levadura", "7", "g", "instantánea"),
            ("Sal", "9", "g", ""),
            ("Mantequilla", "80", "g", "pomada"),
            ("Queso", "400", "g", "llanero o mezcla de quesos llanero y mozzarella")
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
            ("Coco rallado", "100", "g", "corteza")
        ],

        "Pan de Guayaba": [
            ("Harina panadera", "850", "g", ""),
            ("Leche entera", "400", "ml", ""),
            ("Azúcar", "120", "g", ""),
            ("Sal", "3", "g", "1 pizca"),
            ("Huevos", "2", "unidades", ""),
            ("Mantequilla", "95", "g", "sin sal"),
            ("Levadura", "8", "g", "seca"),
            ("Pasta de guayaba", "—", "—", "al gusto")
        ],

        "Pan de Molde — Dulce Remolino de Chocolate": [
            ("Harina de trigo todo uso", "450", "g", ""),
            ("Azúcar", "110", "g", ""),
            ("Sal", "2.5", "g", "1/2 cucharadita aprox."),
            ("Levadura", "10", "g", "seca instantánea"),
            ("Huevo", "1", "unidad", ""),
            ("Leche", "250", "ml", "tibia"),
            ("Mantequilla", "40", "g", "sin sal"),
            ("Cacao en polvo sin azúcar", "36", "g", "masa de chocolate"),
            ("Aceite", "—", "—", "para engrasar"),
            ("Papel de aluminio", "—", "—", "para envolver el molde")
        ],

        "Pan Tipo Subway": [
            ("Harina de trigo para pan", "600", "g", ""),
            ("Leche tibia", "350", "g", ""),
            ("Aceite de oliva virgen light", "90", "ml", "65 ml + 25 ml"),
            ("Azúcar", "30", "g", ""),
            ("Sal", "10", "g", ""),
            ("Levadura seca instantánea", "9", "g", "o 22 g fresca"),
            ("Leche", "—", "—", "para pincelar"),
            ("Queso parmesano", "—", "—", "rallado, al gusto"),
            ("Orégano seco", "—", "—", "al gusto")
        ],

        "Pan de Leche Tradicional": [
            ("Harina de trigo", "1750", "g", "250 g prefermento + 1500 g masa"),
            ("Azúcar", "425", "g", "125 g prefermento + 300 g masa"),
            ("Agua", "250", "g", "prefermento"),
            ("Mantequilla", "180", "g", ""),
            ("Huevos", "3", "unidades", ""),
            ("Sal", "30", "g", ""),
            ("Leche en polvo", "60", "g", ""),
            ("Agua o leche líquida", "625", "ml", "incorporar poco a poco"),
            ("Levadura seca", "6", "g", "")
        ],

        "Cachitos Venezolanos — miga 50%": [
            ("Harina panadera", "627", "g", "173 g biga + 454 g masa final"),
            ("Leche", "272", "g", "86 g biga + 186 g masa final"),
            ("Levadura instantánea", "7.57", "g", "0.57 g biga + 7 g masa final"),
            ("Sal", "7", "g", ""),
            ("Huevos", "2", "unidades aprox.", "100 g en masa"),
            ("Mantequilla con sal", "100", "g", ""),
            ("Azúcar", "100", "g", ""),
            ("Jamón ahumado", "760", "g", "picado en cubos"),
            ("Tocineta", "200", "g", "picada")
        ],

        "Golfeados Venezolanos": [
            ("Harina panadera", "800", "g", ""),
            ("Leche entera", "430", "ml", "280 ml masa + 150 ml para pincelar"),
            ("Mantequilla", "130", "g", "a temperatura ambiente"),
            ("Azúcar blanca", "150", "g", ""),
            ("Sal", "10", "g", "la tarjeta también muestra 1 cdita/4 g; se conserva como aparece"),
            ("Huevos", "2", "unidades", ""),
            ("Vainilla", "2", "cucharadas", ""),
            ("Levadura instantánea", "8", "g", ""),
            ("Queso blanco duro", "500", "g", "rallado"),
            ("Papelón", "500", "g", "mezcla de papelón"),
            ("Agua", "200", "ml", "melado"),
            ("Melado de papelón", "70", "ml", "para pincelar")
        ],

        "Pan Piñita Mejorada": [
            ("Harina panadera", "616", "g", "600 g masa + 16 g Tangzhong"),
            ("Agua", "43", "g", "Tangzhong"),
            ("Leche", "243", "g", "43 g Tangzhong + 200 g masa"),
            ("Azúcar", "150", "g", ""),
            ("Leche en polvo", "20", "g", ""),
            ("Levadura instantánea", "8", "g", ""),
            ("Mantequilla", "70", "g", "pomada"),
            ("Huevo", "1", "unidad", ""),
            ("Yema", "1", "unidad", ""),
            ("Esencia de piña", "2", "cucharadas", "casera"),
            ("Sal", "3–4", "g", ""),
            ("Vainilla", "2", "cucharadas", "")
        ]
    }


    # ============================================================
    # REEMPLAZAR RECETAS ANTERIORES
    # ============================================================

    managed_names = [r[0] for r in recipe_defs]

    for old in managed_names:

        old_rows = c.execute(
            "SELECT id FROM recipes WHERE name=?",
            (old,)
        ).fetchall()

        for rr in old_rows:

            c.execute(
                "DELETE FROM recipes WHERE id=?",
                (rr["id"],)
            )


    for r in recipe_defs:

        cur = c.execute(
            """
            INSERT INTO recipes(
                name,
                yield_text,
                oven_temp,
                bake_time,
                notes
            )
            VALUES(?,?,?,?,?)
            """,
            r
        )

        rid = cur.lastrowid

        for item in recipe_ingredients.get(r[0], []):

            c.execute(
                """
                INSERT INTO recipe_ingredients(
                    recipe_id,
                    ingredient_name,
                    amount,
                    unit,
                    notes
                )
                VALUES(?,?,?,?,?)
                """,
                (rid, *item)
            )


    # ============================================================
    # PROMOCIONES
    # ============================================================

    if c.execute(
        "SELECT COUNT(*) FROM promotions"
    ).fetchone()[0] == 0:

        for p in PROMOTIONS:

            c.execute(
                """
                INSERT INTO promotions(
                    id,
                    name,
                    price,
                    description,
                    includes,
                    active
                )
                VALUES(?,?,?,?,?,?)
                """,
                (
                    p["id"],
                    p["name"],
                    p["price"],
                    p.get("description", ""),
                    p.get("includes", ""),
                    1 if p.get("active") else 0
                )
            )


    c.commit()

    c.close()


# ============================================================
# INICIALIZACIÓN
# ============================================================

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


    inventory_for_home = [
        dict(r)
        for r in c.execute(
            """
            SELECT * FROM inventory
            WHERE active=1
            ORDER BY category, product
            """
        ).fetchall()
    ]

    recipes_for_home = []

    for rr in c.execute(
        """
        SELECT * FROM recipes
        WHERE active=1
        ORDER BY name
        """
    ).fetchall():

        rd = dict(rr)

        rd["ingredients"] = [
            dict(x)
            for x in c.execute(
                """
                SELECT ingredient_name, amount, unit, notes
                FROM recipe_ingredients
                WHERE recipe_id=?
                ORDER BY id
                """,
                (rr["id"],)
            ).fetchall()
        ]

        recipes_for_home.append(rd)


    c.close() 
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

    rows = c.execute(
        "SELECT DISTINCT client FROM orders "
        "WHERE client LIKE ? COLLATE NOCASE "
        "ORDER BY client LIMIT 10",
        ((q + "%") if q else "%",)
    ).fetchall()

    result = []

    for row in rows:
        client = row["client"]

        order = c.execute(
            "SELECT id FROM orders "
            "WHERE client=? AND status!='Cancelado' "
            "ORDER BY delivery_date DESC,id DESC LIMIT 1",
            (client,)
        ).fetchone()

        items = [
            dict(x)
            for x in c.execute(
                "SELECT product,qty,unit_price FROM items "
                "WHERE order_id=? AND (promotion_id='' OR promotion_id IS NULL)",
                (order["id"],)
            ).fetchall()
        ] if order else []

        result.append({
            "client": client,
            "items": items
        })

    c.close()
    return jsonify(result)


# ============================================================
# PROMOCIONES
# ============================================================

@app.get("/promotions")
def get_promotions():
    c = db()

    rows = c.execute(
        "SELECT * FROM promotions ORDER BY name"
    ).fetchall()

    c.close()

    return jsonify([
        dict(x) for x in rows
    ])


@app.post("/promotions")
def create_promotion():

    data = request.get_json() or {}

    name = (data.get("name") or "").strip()

    if not name:
        return jsonify({"ok": False}), 400

    pid = "promo_" + str(
        abs(hash(name + datetime.now().isoformat()))
    )

    c = db()

    c.execute(
        """
        INSERT INTO promotions(
            id,
            name,
            price,
            description,
            includes,
            active
        )
        VALUES(?,?,?,?,?,1)
        """,
        (
            pid,
            name,
            float(data.get("price") or 0),
            data.get("description", ""),
            data.get("includes", "")
        )
    )

    c.commit()
    c.close()

    return jsonify({
        "ok": True,
        "id": pid
    })


@app.put("/promotions/<pid>")
def update_promotion(pid):

    data = request.get_json() or {}

    c = db()

    c.execute(
        """
        UPDATE promotions
        SET name=?,
            price=?,
            description=?,
            includes=?,
            active=?
        WHERE id=?
        """,
        (
            (data.get("name") or "").strip(),
            float(data.get("price") or 0),
            data.get("description", ""),
            data.get("includes", ""),
            1 if data.get("active", True) else 0,
            pid
        )
    )

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
        "SELECT * FROM recipes "
        "WHERE active=1 ORDER BY name"
    ).fetchall():

        rd = dict(rr)

        rd["ingredients"] = [
            dict(x)
            for x in c.execute(
                """
                SELECT ingredient_name,
                       amount,
                       unit,
                       notes
                FROM recipe_ingredients
                WHERE recipe_id=?
                ORDER BY id
                """,
                (rr["id"],)
            ).fetchall()
        ]

        result.append(rd)

    c.close()

    return jsonify(result)


# ============================================================
# INVENTARIO
# ============================================================

@app.get("/inventory")
def get_inventory():

    c = db()

    rows = c.execute(
        """
        SELECT *
        FROM inventory
        WHERE active=1
        ORDER BY category,product
        """
    ).fetchall()

    c.close()

    return jsonify([
        dict(x) for x in rows
    ])


@app.post("/inventory")
def create_inventory():

    data = request.get_json() or {}

    if not (data.get("category") or "").strip() \
       or not (data.get("product") or "").strip():

        return jsonify({"ok": False}), 400

    now = datetime.now().isoformat()

    c = db()

    c.execute(
        """
        INSERT INTO inventory(
            category,
            product,
            presentation,
            purchase_price,
            current_qty,
            equivalent_qty,
            equivalent_unit,
            reorder_point,
            active,
            created_at,
            updated_at
        )
        VALUES(?,?,?,?,?,?,?,?,1,?,?)
        """,
        (
            (data.get("category") or "").strip(),
            (data.get("product") or "").strip(),
            data.get("presentation", ""),
            float(data.get("purchase_price") or 0),
            float(data.get("current_qty") or 0),
            float(data.get("equivalent_qty") or 0),
            data.get("equivalent_unit", ""),
            float(data.get("reorder_point") or 0),
            now,
            now
        )
    )

    c.commit()
    c.close()

    return jsonify({"ok": True})


@app.put("/inventory/<int:iid>")
def update_inventory(iid):

    data = request.get_json() or {}

    now = datetime.now().isoformat()

    c = db()

    c.execute(
        """
        UPDATE inventory
        SET category=?,
            product=?,
            presentation=?,
            purchase_price=?,
            current_qty=?,
            equivalent_qty=?,
            equivalent_unit=?,
            reorder_point=?,
            updated_at=?
        WHERE id=?
        """,
        (
            (data.get("category") or "").strip(),
            (data.get("product") or "").strip(),
            data.get("presentation", ""),
            float(data.get("purchase_price") or 0),
            float(data.get("current_qty") or 0),
            float(data.get("equivalent_qty") or 0),
            data.get("equivalent_unit", ""),
            float(data.get("reorder_point") or 0),
            now,
            iid
        )
    )

    c.commit()
    c.close()

    return jsonify({"ok": True})


@app.delete("/inventory/<int:iid>")
def delete_inventory(iid):

    c = db()

    c.execute(
        """
        UPDATE inventory
        SET active=0,
            updated_at=?
        WHERE id=?
        """,
        (
            datetime.now().isoformat(),
            iid
        )
    )

    c.commit()
    c.close()

    return jsonify({"ok": True})


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

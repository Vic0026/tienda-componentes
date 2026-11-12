"""
PCForge - tienda ficticia de componentes de PC.

!!! APLICACION DELIBERADAMENTE VULNERABLE (solo para practicas de auditoria) !!!
- Ejecutar SOLO en local (127.0.0.1) o en la VLAN del aula.
- No desplegar en Internet. Todos los datos son ficticios.
"""
import base64
import hashlib
import os
import sqlite3
from flask import Flask, request, redirect, render_template, make_response, g

APP_VERSION = "1.0.0-vulnerable"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tienda.db")

app = Flask(__name__)


# ---------------------------------------------------------------- base de datos
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def md5(texto):
    return hashlib.md5(texto.encode()).hexdigest()


def init_db():
    if os.path.exists(DB_PATH):
        return
    c = sqlite3.connect(DB_PATH)
    c.executescript("""
    CREATE TABLE usuarios(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT,
                          rol TEXT, email TEXT);
    CREATE TABLE productos(id INTEGER PRIMARY KEY, nombre TEXT, categoria TEXT,
                           descripcion TEXT, precio REAL, stock INTEGER);
    CREATE TABLE resenas(id INTEGER PRIMARY KEY, producto_id INTEGER, autor TEXT, texto TEXT);
    CREATE TABLE pedidos(id INTEGER PRIMARY KEY, usuario_id INTEGER, producto_id INTEGER,
                         cantidad INTEGER, direccion TEXT, telefono TEXT, total REAL);
    """)
    usuarios = [
        (1, "admin", md5("Admin#2026"), "admin", "admin@pcforge.test"),
        (2, "ana", md5("ana123"), "cliente", "ana@pcforge.test"),
        (3, "luis", md5("luis123"), "cliente", "luis@pcforge.test"),
    ]
    c.executemany("INSERT INTO usuarios VALUES(?,?,?,?,?)", usuarios)
    productos = [
        ("Ryzen 7 7700X", "Procesador", "8 nucleos, 16 hilos, 4.5-5.4 GHz. Socket AM5.", 299.90, 14),
        ("Core i5-14600K", "Procesador", "14 nucleos (6P+8E), hasta 5.3 GHz. Socket LGA1700.", 319.00, 9),
        ("GeForce RTX 4070 Super", "Tarjeta grafica", "12 GB GDDR6X, DLSS 3, ideal para 1440p.", 619.00, 6),
        ("Radeon RX 7800 XT", "Tarjeta grafica", "16 GB GDDR6, FSR 3, gran relacion precio/rendimiento.", 489.50, 8),
        ("Kingston Fury 32 GB DDR5-6000", "Memoria RAM", "Kit 2x16 GB, CL36, perfil EXPO/XMP.", 124.95, 25),
        ("Corsair Vengeance 16 GB DDR4-3200", "Memoria RAM", "Kit 2x8 GB, CL16, compatible AM4/LGA1200.", 49.90, 40),
        ("Samsung 990 Pro 1 TB", "Almacenamiento", "NVMe PCIe 4.0, lectura 7450 MB/s.", 109.00, 18),
        ("WD Blue SN580 500 GB", "Almacenamiento", "NVMe PCIe 4.0, buena opcion economica.", 44.99, 30),
        ("ASUS TUF B650-Plus", "Placa base", "AM5, DDR5, PCIe 5.0, WiFi 6.", 189.00, 11),
        ("MSI MAG B760 Tomahawk", "Placa base", "LGA1700, DDR5, 2x M.2, WiFi 6E.", 179.00, 7),
        ("Corsair RM750e 750 W", "Fuente", "80 Plus Gold, modular, ATX 3.0.", 99.90, 20),
        ("NZXT H5 Flow", "Caja", "Semitorre ATX con excelente flujo de aire.", 94.90, 12),
    ]
    c.executemany("INSERT INTO productos(nombre,categoria,descripcion,precio,stock) VALUES(?,?,?,?,?)", productos)
    c.executemany("INSERT INTO resenas(producto_id,autor,texto) VALUES(?,?,?)", [
        (1, "ana", "Va muy fino para compilar y jugar. Recomendado."),
        (3, "luis", "Silenciosa y fresquita, rinde de sobra a 1440p."),
        (5, "ana", "Perfil EXPO a la primera, sin sustos."),
    ])
    c.executemany("INSERT INTO pedidos(usuario_id,producto_id,cantidad,direccion,telefono,total) VALUES(?,?,?,?,?,?)", [
        (2, 1, 1, "C/ Ficticia 12, 3B, 46001 Valencia", "600111222", 299.90),
        (2, 5, 2, "C/ Ficticia 12, 3B, 46001 Valencia", "600111222", 249.90),
        (3, 3, 1, "Av. de Prueba 7, 46900 Torrent", "600333444", 619.00),
    ])
    c.commit()
    c.close()


# ---------------------------------------------------------------- sesion
def usuario_actual():
    """Lee la cookie 'sid' y devuelve el usuario (o None)."""
    sid = request.cookies.get("sid")
    if not sid:
        return None
    try:
        uid = int(base64.b64decode(sid).decode().split(":")[0])
    except Exception:
        return None
    return db().execute("SELECT * FROM usuarios WHERE id=?", (uid,)).fetchone()


@app.context_processor
def inyectar():
    return {"usuario": usuario_actual(), "version": APP_VERSION}


def crear_sesion(user_row, destino="/"):
    resp = make_response(redirect(destino))
    token = base64.b64encode(f"{user_row['id']}:{user_row['username']}".encode()).decode()
    resp.set_cookie("sid", token)  # sin HttpOnly, sin Secure, sin SameSite, nunca rota
    return resp


# ---------------------------------------------------------------- rutas publicas
@app.route("/")
def index():
    cat = request.args.get("cat")
    if cat:
        filas = db().execute("SELECT * FROM productos WHERE categoria=?", (cat,)).fetchall()
    else:
        filas = db().execute("SELECT * FROM productos").fetchall()
    cats = [r[0] for r in db().execute("SELECT DISTINCT categoria FROM productos")]
    return render_template("index.html", productos=filas, cats=cats, cat=cat)


@app.route("/producto/<int:pid>")
def producto(pid):
    p = db().execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
    if not p:
        return "Producto no encontrado", 404
    resenas = db().execute("SELECT * FROM resenas WHERE producto_id=? ORDER BY id DESC", (pid,)).fetchall()
    return render_template("producto.html", p=p, resenas=resenas)


@app.route("/producto/<int:pid>/resena", methods=["POST"])
def nueva_resena(pid):
    u = usuario_actual()
    if not u:
        return redirect("/login")
    texto = request.form.get("texto", "")
    db().execute("INSERT INTO resenas(producto_id,autor,texto) VALUES(?,?,?)", (pid, u["username"], texto))
    db().commit()
    return redirect(f"/producto/{pid}")


@app.route("/buscar")
def buscar():
    q = request.args.get("q", "")
    error = None
    filas = []
    try:
        # VULN: concatenacion directa en la consulta
        sql = f"SELECT id, nombre, categoria, descripcion, precio, stock FROM productos WHERE nombre LIKE '%{q}%'"
        filas = db().execute(sql).fetchall()
    except Exception as e:
        error = str(e)  # VULN: se muestra el error SQL al usuario
    return render_template("buscar.html", q=q, filas=filas, error=error)


# ---------------------------------------------------------------- cuentas
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        try:
            # VULN: concatenacion directa + hash MD5 sin sal
            sql = f"SELECT * FROM usuarios WHERE username='{u}' AND password='{md5(p)}'"
            fila = db().execute(sql).fetchone()
        except Exception as e:
            fila, error = None, str(e)
        if fila:
            return crear_sesion(fila)
        error = error or "Usuario o contrasena incorrectos"
    return render_template("login.html", error=error)


@app.route("/registro", methods=["GET", "POST"])
def registro():
    error = None
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        e = request.form.get("email", "").strip()
        if not u or not p:
            error = "Usuario y contrasena son obligatorios"
        else:
            try:
                db().execute("INSERT INTO usuarios(username,password,rol,email) VALUES(?,?,?,?)",
                             (u, md5(p), "cliente", e))
                db().commit()
                return redirect("/login")
            except sqlite3.IntegrityError:
                error = "Ese usuario ya existe"
    return render_template("registro.html", error=error)


@app.route("/logout")
def logout():
    resp = make_response(redirect("/"))
    resp.delete_cookie("sid")
    return resp


# ---------------------------------------------------------------- pedidos
@app.route("/comprar/<int:pid>", methods=["POST"])
def comprar(pid):
    u = usuario_actual()
    if not u:
        return redirect("/login")
    p = db().execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
    if not p:
        return "Producto no encontrado", 404
    try:
        cant = max(1, int(request.form.get("cantidad", "1")))
    except ValueError:
        cant = 1
    cur = db().execute(
        "INSERT INTO pedidos(usuario_id,producto_id,cantidad,direccion,telefono,total) VALUES(?,?,?,?,?,?)",
        (u["id"], pid, cant, request.form.get("direccion", ""), request.form.get("telefono", ""),
         round(p["precio"] * cant, 2)))
    db().commit()
    return redirect(f"/pedido/{cur.lastrowid}")


@app.route("/pedidos")
def pedidos():
    u = usuario_actual()
    if not u:
        return redirect("/login")
    filas = db().execute(
        "SELECT pe.*, pr.nombre FROM pedidos pe JOIN productos pr ON pr.id=pe.producto_id "
        "WHERE pe.usuario_id=? ORDER BY pe.id DESC", (u["id"],)).fetchall()
    return render_template("pedidos.html", filas=filas)


@app.route("/pedido/<int:oid>")
def pedido(oid):
    u = usuario_actual()
    if not u:
        return redirect("/login")
    # VULN (IDOR): no se comprueba que el pedido pertenezca al usuario
    fila = db().execute(
        "SELECT pe.*, pr.nombre, us.username, us.email FROM pedidos pe "
        "JOIN productos pr ON pr.id=pe.producto_id JOIN usuarios us ON us.id=pe.usuario_id "
        "WHERE pe.id=?", (oid,)).fetchone()
    if not fila:
        return "Pedido no encontrado", 404
    return render_template("pedido.html", o=fila)


# ---------------------------------------------------------------- administracion
@app.route("/admin")
def admin():
    u = usuario_actual()
    if not u or u["rol"] != "admin":
        return "Acceso restringido", 403
    usuarios = db().execute("SELECT id, username, email, rol FROM usuarios").fetchall()
    ventas = db().execute(
        "SELECT pe.id, us.username, pr.nombre, pe.cantidad, pe.total FROM pedidos pe "
        "JOIN usuarios us ON us.id=pe.usuario_id JOIN productos pr ON pr.id=pe.producto_id "
        "ORDER BY pe.id DESC").fetchall()
    return render_template("admin.html", usuarios=usuarios, ventas=ventas)


if __name__ == "__main__":
    init_db()
    # Solo escucha en local. Sin debug (la consola de Werkzeug permite ejecutar codigo).
    app.run(host="127.0.0.1", port=5000, debug=False)

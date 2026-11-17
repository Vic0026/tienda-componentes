"""
PCForge - Tienda de componentes de PC (Version Segura para Produccion).
"""
import os
import re
import secrets
import smtplib
import sqlite3
import time
from datetime import datetime
from email.message import EmailMessage
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

try:
    import stripe
except ImportError:
    stripe = None

load_dotenv()

APP_VERSION = "2.0.0-secure"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "tienda.db")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("HTTPS_ENABLED", "0") == "1",
    PERMANENT_SESSION_LIFETIME=3600 * 4,
)

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "").strip()
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
if stripe and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Control basico de fuerza bruta en memoria: {ip: [timestamps]}
LOGIN_ATTEMPTS = {}
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300


# ---------------------------------------------------------------- base de datos
def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db():
    if os.path.exists(DB_PATH):
        return
    c = sqlite3.connect(DB_PATH)
    c.executescript("""
    CREATE TABLE usuarios(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        rol TEXT NOT NULL DEFAULT 'cliente',
        email TEXT NOT NULL
    );
    CREATE TABLE productos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        categoria TEXT NOT NULL,
        descripcion TEXT NOT NULL,
        precio REAL NOT NULL,
        stock INTEGER NOT NULL
    );
    CREATE TABLE resenas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER NOT NULL,
        autor TEXT NOT NULL,
        texto TEXT NOT NULL,
        FOREIGN KEY(producto_id) REFERENCES productos(id)
    );
    CREATE TABLE pedidos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        producto_id INTEGER NOT NULL,
        cantidad INTEGER NOT NULL,
        direccion TEXT NOT NULL,
        telefono TEXT NOT NULL,
        total REAL NOT NULL,
        estado_pago TEXT NOT NULL DEFAULT 'pendiente',
        stripe_session_id TEXT,
        metodo_pago TEXT,
        referencia_pago TEXT,
        tarjeta_ultimos4 TEXT,
        pagado_en TIMESTAMP,
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
        FOREIGN KEY(producto_id) REFERENCES productos(id)
    );
    CREATE TABLE mensajes_contacto(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        email TEXT NOT NULL,
        asunto TEXT NOT NULL,
        mensaje TEXT NOT NULL,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    clave_admin = os.environ.get("ADMIN_PASSWORD") or secrets.token_urlsafe(12)
    if not os.environ.get("ADMIN_PASSWORD"):
        print(f"[PCForge] Contrasena de admin generada (guardala): {clave_admin}")
    usuarios = [
        ("admin", generate_password_hash(clave_admin), "admin", "admin@pcforge.es"),
        ("ana", generate_password_hash("Ana#2026!Segura"), "cliente", "ana@pcforge.es"),
        ("luis", generate_password_hash("Luis#2026!Segura"), "cliente", "luis@pcforge.es"),
    ]
    c.executemany("INSERT INTO usuarios(username,password,rol,email) VALUES(?,?,?,?)", usuarios)
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
    c.executemany(
        "INSERT INTO productos(nombre,categoria,descripcion,precio,stock) VALUES(?,?,?,?,?)",
        productos,
    )
    c.executemany(
        "INSERT INTO resenas(producto_id,autor,texto) VALUES(?,?,?)",
        [
            (1, "ana", "Va muy fino para compilar y jugar. Recomendado."),
            (3, "luis", "Silenciosa y fresquita, rinde de sobra a 1440p."),
            (5, "ana", "Perfil EXPO a la primera, sin sustos."),
        ],
    )
    c.commit()
    c.close()


RATE = {}


def permitir(nombre, maximo, ventana):
    """Limitador simple por IP y accion. Devuelve False si se supera el maximo."""
    clave = (nombre, request.remote_addr or "local")
    ahora = time.time()
    marcas = [t for t in RATE.get(clave, []) if ahora - t < ventana]
    if len(marcas) >= maximo:
        RATE[clave] = marcas
        return False
    marcas.append(ahora)
    RATE[clave] = marcas
    return True


def migrar_db():
    """Anade las columnas de pago a bases de datos creadas con versiones anteriores."""
    c = sqlite3.connect(DB_PATH)
    cols = {r[1] for r in c.execute("PRAGMA table_info(pedidos)")}
    for nombre, tipo in (("metodo_pago", "TEXT"), ("referencia_pago", "TEXT"),
                         ("tarjeta_ultimos4", "TEXT"), ("pagado_en", "TIMESTAMP")):
        if nombre not in cols:
            c.execute(f"ALTER TABLE pedidos ADD COLUMN {nombre} {tipo}")
    c.commit()
    c.close()


# ---------------------------------------------------------------- seguridad y CSRF
def generar_csrf():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return session["_csrf_token"]


@app.before_request
def proteger_csrf():
    # Excluir webhook externo de Stripe (verificado por firma criptografica)
    if request.endpoint == "stripe_webhook":
        return
    if request.method in ("POST", "PUT", "DELETE"):
        token_sesion = session.get("_csrf_token")
        token_form = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
        if not token_sesion or not token_form or not secrets.compare_digest(token_sesion, token_form):
            abort(403, description="Token CSRF invalido o caducado.")


@app.after_request
def cabeceras_seguridad(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "form-action 'self' https://checkout.stripe.com; "
        "frame-ancestors 'none';"
    )
    return resp


def usuario_actual():
    uid = session.get("user_id")
    if not uid:
        return None
    return db().execute("SELECT id, username, email, rol FROM usuarios WHERE id=?", (uid,)).fetchone()


def login_requerido(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not usuario_actual():
            flash("Debes iniciar sesion para continuar.", "err")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)

    return wrapper


def admin_requerido(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u = usuario_actual()
        if not u or u["rol"] != "admin":
            abort(403)
        return fn(*args, **kwargs)

    return wrapper


@app.context_processor
def inyectar():
    return {
        "usuario": usuario_actual(),
        "version": APP_VERSION,
        "csrf_token": generar_csrf,
        "stripe_activo": bool(stripe and STRIPE_SECRET_KEY),
        "demo_activo": demo_activo(),
    }


# ---------------------------------------------------------------- servicio de correo
def enviar_correo(destinatario, asunto, cuerpo):
    host = os.environ.get("SMTP_HOST", "").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    pwd = os.environ.get("SMTP_PASSWORD", "").strip()

    if not (host and user and pwd):
        # Si no hay SMTP configurado en .env, registramos en consola sin romper la app
        app.logger.info(f"[CORREO SIMULADO] Para: {destinatario} | Asunto: {asunto}\n{cuerpo}")
        return True

    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = user
    msg["To"] = destinatario
    msg.set_content(cuerpo)

    with smtplib.SMTP(host, port, timeout=10) as server:
        server.starttls()
        server.login(user, pwd)
        server.send_message(msg)
    return True


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
        abort(404)
    resenas = db().execute("SELECT * FROM resenas WHERE producto_id=? ORDER BY id DESC", (pid,)).fetchall()
    return render_template("producto.html", p=p, resenas=resenas)


@app.route("/producto/<int:pid>/resena", methods=["POST"])
@login_requerido
def nueva_resena(pid):
    u = usuario_actual()
    texto = request.form.get("texto", "").strip()
    if not texto or len(texto) > 600:
        flash("La opinion debe tener entre 1 y 600 caracteres.", "err")
        return redirect(url_for("producto", pid=pid))
    db().execute("INSERT INTO resenas(producto_id,autor,texto) VALUES(?,?,?)", (pid, u["username"], texto))
    db().commit()
    flash("Opinion publicada correctamente.", "ok")
    return redirect(url_for("producto", pid=pid))


@app.route("/buscar")
def buscar():
    q = request.args.get("q", "").strip()[:100]
    filas = []
    if q:
        patron = f"%{q}%"
        filas = db().execute(
            "SELECT id, nombre, categoria, descripcion, precio, stock FROM productos "
            "WHERE nombre LIKE ? OR descripcion LIKE ?",
            (patron, patron),
        ).fetchall()
    return render_template("buscar.html", q=q, filas=filas)


# ---------------------------------------------------------------- contacto
@app.route("/contacto", methods=["GET", "POST"])
def contacto():
    if request.method == "POST":
        if not permitir("contacto", 3, 600):
            flash("Has enviado varios mensajes seguidos. Espera unos minutos.", "err")
            return render_template("contacto.html"), 429
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip()
        asunto = request.form.get("asunto", "").strip()
        mensaje = request.form.get("mensaje", "").strip()
        honeypot = request.form.get("website", "").strip()

        if honeypot:
            # Bot detectado silenciosamente
            flash("Mensaje enviado. Te responderemos pronto.", "ok")
            return redirect(url_for("contacto"))

        if not (nombre and email and asunto and mensaje):
            flash("Por favor, completa todos los campos.", "err")
            return render_template("contacto.html")

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            flash("Introduce un correo electronico valido.", "err")
            return render_template("contacto.html")

        db().execute(
            "INSERT INTO mensajes_contacto(nombre,email,asunto,mensaje) VALUES(?,?,?,?)",
            (nombre[:100], email[:120], asunto[:150], mensaje[:2000]),
        )
        db().commit()

        receptor = os.environ.get("CONTACT_RECEIVER", "ventas@pcforge.es")
        try:
            enviar_correo(
                receptor,
                f"[Contacto Web] {asunto}",
                f"De: {nombre} <{email}>\n\n{mensaje}",
            )
            enviar_correo(
                email,
                "Hemos recibido tu consulta - PCForge",
                f"Hola {nombre},\n\nGracias por contactar con PCForge. Hemos recibido tu mensaje sobre '{asunto}' y te responderemos en menos de 24h.\n\nUn saludo,\nEquipo PCForge",
            )
            flash("Tu mensaje ha sido enviado. Te hemos mandado una confirmacion por correo.", "ok")
            return redirect(url_for("contacto"))
        except Exception:
            app.logger.exception("Error enviando correo de contacto")
            flash("Tu mensaje se guardo, pero hubo un problema al enviar el aviso por correo.", "err")

    return render_template("contacto.html")


# ---------------------------------------------------------------- cuentas
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        ip = request.remote_addr or "local"
        ahora = time.time()
        intentos = [t for t in LOGIN_ATTEMPTS.get(ip, []) if ahora - t < WINDOW_SECONDS]
        if len(intentos) >= MAX_ATTEMPTS:
            error = "Demasiados intentos fallidos. Espera 5 minutos."
            return render_template("login.html", error=error), 429

        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        fila = db().execute("SELECT * FROM usuarios WHERE username=?", (u,)).fetchone()
        if fila and check_password_hash(fila["password"], p):
            LOGIN_ATTEMPTS.pop(ip, None)
            session.clear()
            session["user_id"] = fila["id"]
            session.permanent = True
            generar_csrf()
            flash(f"Bienvenido de nuevo, {fila['username']}.", "ok")
            return redirect(url_for("index"))

        intentos.append(ahora)
        LOGIN_ATTEMPTS[ip] = intentos
        error = "Usuario o contrasena incorrectos"
    return render_template("login.html", error=error)


@app.route("/registro", methods=["GET", "POST"])
def registro():
    error = None
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        e = request.form.get("email", "").strip()
        if not re.match(r"^[a-zA-Z0-9_.-]{3,30}$", u):
            error = "El usuario debe tener 3-30 caracteres alfanumericos."
        elif not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e):
            error = "Correo electronico no valido."
        elif len(p) < 8:
            error = "La contrasena debe tener al menos 8 caracteres."
        else:
            try:
                db().execute(
                    "INSERT INTO usuarios(username,password,rol,email) VALUES(?,?,?,?)",
                    (u, generate_password_hash(p), "cliente", e),
                )
                db().commit()
                flash("Cuenta creada correctamente. Ya puedes iniciar sesion.", "ok")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "Ese nombre de usuario ya esta en uso."
    return render_template("registro.html", error=error)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Has cerrado sesion.", "ok")
    return redirect(url_for("index"))


# ---------------------------------------------------------------- pedidos y pagos
@app.route("/comprar/<int:pid>", methods=["POST"])
@login_requerido
def comprar(pid):
    u = usuario_actual()
    p = db().execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
    if not p:
        abort(404)
    try:
        cant = int(request.form.get("cantidad", "1"))
    except ValueError:
        cant = 1

    if cant < 1 or cant > p["stock"]:
        flash(f"Cantidad no valida. Stock disponible: {p['stock']}.", "err")
        return redirect(url_for("producto", pid=pid))

    direccion = request.form.get("direccion", "").strip()
    telefono = request.form.get("telefono", "").strip()
    if len(direccion) < 5 or len(telefono) < 6:
        flash("Por favor, indica una direccion y telefono validos.", "err")
        return redirect(url_for("producto", pid=pid))

    total = round(p["precio"] * cant, 2)
    cur = db().execute(
        "INSERT INTO pedidos(usuario_id,producto_id,cantidad,direccion,telefono,total,estado_pago) "
        "VALUES(?,?,?,?,?,?,?)",
        (u["id"], pid, cant, direccion[:250], telefono[:30], total, "pendiente"),
    )
    oid = cur.lastrowid
    db().commit()

    if stripe and STRIPE_SECRET_KEY:
        return iniciar_stripe(oid, p["nombre"], p["precio"], cant, u["email"])
    if demo_activo():
        return redirect(url_for("pagar", oid=oid))
    flash("Pedido registrado. El pago online no esta disponible ahora mismo.", "err")
    return redirect(url_for("pedido", oid=oid))


# ---------------------------------------------------------------- pagos
def demo_activo():
    """Pasarela simulada: solo sin Stripe y con DEMO_PAYMENTS=1 (poner 0 en produccion)."""
    return not (stripe and STRIPE_SECRET_KEY) and os.environ.get("DEMO_PAYMENTS", "1") == "1"


def luhn_ok(num):
    total = 0
    for i, d in enumerate(reversed(num)):
        n = int(d)
        if i % 2:
            n = n * 2 - 9 if n * 2 > 9 else n * 2
        total += n
    return total % 10 == 0


def marca_tarjeta(num):
    if num.startswith("4"):
        return "Visa"
    if num[:2] in ("51", "52", "53", "54", "55") or 2221 <= int(num[:4]) <= 2720:
        return "Mastercard"
    if num[:2] in ("34", "37"):
        return "Amex"
    return "Tarjeta"


def marcar_pagado(oid, metodo, referencia, ultimos4=None):
    """Idempotente: solo la primera llamada marca el pago, descuenta stock y envia el recibo."""
    conn = db()
    cur = conn.execute(
        "UPDATE pedidos SET estado_pago='pagado', metodo_pago=?, referencia_pago=?, "
        "tarjeta_ultimos4=?, pagado_en=CURRENT_TIMESTAMP WHERE id=? AND estado_pago!='pagado'",
        (metodo, referencia, ultimos4, oid),
    )
    if cur.rowcount != 1:
        conn.rollback()
        return False
    fila = conn.execute(
        "SELECT pe.*, pr.nombre, us.username, us.email FROM pedidos pe "
        "JOIN productos pr ON pr.id=pe.producto_id JOIN usuarios us ON us.id=pe.usuario_id WHERE pe.id=?",
        (oid,),
    ).fetchone()
    conn.execute("UPDATE productos SET stock = MAX(0, stock - ?) WHERE id=?", (fila["cantidad"], fila["producto_id"]))
    conn.commit()
    try:
        enviar_correo(
            fila["email"],
            f"Recibo del pedido #{oid} - PCForge",
            f"Hola {fila['username']},\n\nHemos recibido tu pago de {fila['total']:.2f} EUR.\n\n"
            f"Pedido #{oid}: {fila['nombre']} x{fila['cantidad']}\nReferencia de pago: {referencia}\n"
            f"Envio a: {fila['direccion']}\n\nGracias por tu compra,\nEquipo PCForge",
        )
    except Exception:
        app.logger.exception("No se pudo enviar el recibo del pedido %s", oid)
    return True


def iniciar_stripe(oid, nombre, precio, cant, email):
    try:
        cs = stripe.checkout.Session.create(
            payment_method_types=["card"],
            customer_email=email,
            line_items=[{
                "price_data": {"currency": "eur", "product_data": {"name": nombre},
                               "unit_amount": int(round(precio * 100))},
                "quantity": cant,
            }],
            mode="payment",
            metadata={"pedido_id": str(oid)},
            success_url=url_for("pago_exito", oid=oid, _external=True) + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("pedido", oid=oid, _external=True),
        )
        db().execute("UPDATE pedidos SET stripe_session_id=? WHERE id=?", (cs.id, oid))
        db().commit()
        return redirect(cs.url, code=303)
    except Exception:
        app.logger.exception("Error creando sesion de Stripe")
        flash("No se pudo iniciar el pago. Puedes reintentarlo desde tu pedido.", "err")
        return redirect(url_for("pedido", oid=oid))


@app.route("/pedido/<int:oid>/pagar", methods=["GET", "POST"])
@login_requerido
def pagar(oid):
    u = usuario_actual()
    o = db().execute(
        "SELECT pe.*, pr.nombre, pr.precio, pr.stock FROM pedidos pe JOIN productos pr ON pr.id=pe.producto_id "
        "WHERE pe.id=? AND pe.usuario_id=?",
        (oid, u["id"]),
    ).fetchone()
    if not o:
        abort(404)
    if o["estado_pago"] == "pagado":
        return redirect(url_for("pedido", oid=oid))
    if o["stock"] < o["cantidad"]:
        flash("Ya no queda stock suficiente para este pedido.", "err")
        return redirect(url_for("pedido", oid=oid))

    if stripe and STRIPE_SECRET_KEY:  # pago real: siempre en la pagina de Stripe
        if request.method != "POST":
            return redirect(url_for("pedido", oid=oid))
        return iniciar_stripe(oid, o["nombre"], o["precio"], o["cantidad"], u["email"])
    if not demo_activo():
        abort(404)

    error = None
    if request.method == "POST":
        if not permitir("pago", 8, 600):
            return render_template("pago.html", o=o, error="Demasiados intentos. Espera unos minutos."), 429
        titular = request.form.get("titular", "").strip()
        num = re.sub(r"[ -]", "", request.form.get("numero", ""))
        exp = request.form.get("caducidad", "").strip()
        cvv = request.form.get("cvv", "").strip()
        m = re.match(r"^(\d{2})\s*/\s*(\d{2})$", exp)
        ahora = datetime.now()
        if len(titular) < 3:
            error = "Indica el nombre del titular."
        elif not (num.isdigit() and 13 <= len(num) <= 19 and luhn_ok(num)):
            error = "El numero de tarjeta no es valido."
        elif not m or not (1 <= int(m[1]) <= 12) or (int(m[2]), int(m[1])) < (ahora.year % 100, ahora.month):
            error = "La fecha de caducidad no es valida o la tarjeta ha caducado."
        elif not re.match(r"^\d{3,4}$", cvv):
            error = "El CVV no es valido."
        elif num == "4000000000000002":
            error = "Tarjeta rechazada por el emisor. Prueba con otra tarjeta."
        else:
            # Nunca se guarda el numero completo ni el CVV: solo la marca y los 4 ultimos digitos.
            marcar_pagado(oid, "simulado " + marca_tarjeta(num), "SIM-" + secrets.token_hex(5).upper(), num[-4:])
            flash("Pago aceptado. Te hemos enviado el recibo por correo.", "ok")
            return redirect(url_for("pedido", oid=oid))
    return render_template("pago.html", o=o, error=error)


@app.route("/pago/exito/<int:oid>")
@login_requerido
def pago_exito(oid):
    u = usuario_actual()
    fila = db().execute("SELECT * FROM pedidos WHERE id=? AND usuario_id=?", (oid, u["id"])).fetchone()
    if not fila:
        abort(404)
    session_id = request.args.get("session_id", "")
    if stripe and STRIPE_SECRET_KEY and session_id and fila["stripe_session_id"] == session_id:
        try:
            cs = stripe.checkout.Session.retrieve(session_id)
            if cs.payment_status == "paid" and cs.amount_total == int(round(fila["total"] * 100)):
                marcar_pagado(oid, "stripe", cs.payment_intent or cs.id)
        except Exception:
            app.logger.exception("Error verificando sesion Stripe")
    actual = db().execute("SELECT estado_pago FROM pedidos WHERE id=?", (oid,)).fetchone()
    if actual["estado_pago"] == "pagado":
        flash("Pago confirmado. Te hemos enviado el recibo por correo.", "ok")
    else:
        flash("Estamos esperando la confirmacion del pago. Recarga en unos segundos.", "err")
    return redirect(url_for("pedido", oid=oid))


@app.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    if not (stripe and STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET):
        return "", 400
    try:
        event = stripe.Webhook.construct_event(
            request.get_data(), request.headers.get("Stripe-Signature", ""), STRIPE_WEBHOOK_SECRET)
    except Exception:
        return "", 400
    if event["type"] in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        cs = event["data"]["object"]
        oid = (cs.get("metadata") or {}).get("pedido_id")
        if oid and cs.get("payment_status") == "paid":
            fila = db().execute("SELECT total FROM pedidos WHERE id=?", (oid,)).fetchone()
            if fila and cs.get("amount_total") == int(round(fila["total"] * 100)):
                marcar_pagado(int(oid), "stripe", cs.get("payment_intent") or cs.get("id"))
    return "", 200


@app.route("/pedidos")
@login_requerido
def pedidos():
    u = usuario_actual()
    filas = db().execute(
        "SELECT pe.*, pr.nombre FROM pedidos pe JOIN productos pr ON pr.id=pe.producto_id "
        "WHERE pe.usuario_id=? ORDER BY pe.id DESC",
        (u["id"],),
    ).fetchall()
    return render_template("pedidos.html", filas=filas)


@app.route("/pedido/<int:oid>")
@login_requerido
def pedido(oid):
    u = usuario_actual()
    # Correccion IDOR: solo el propietario del pedido o un admin pueden verlo
    if u["rol"] == "admin":
        fila = db().execute(
            "SELECT pe.*, pr.nombre, us.username, us.email FROM pedidos pe "
            "JOIN productos pr ON pr.id=pe.producto_id JOIN usuarios us ON us.id=pe.usuario_id "
            "WHERE pe.id=?",
            (oid,),
        ).fetchone()
    else:
        fila = db().execute(
            "SELECT pe.*, pr.nombre, us.username, us.email FROM pedidos pe "
            "JOIN productos pr ON pr.id=pe.producto_id JOIN usuarios us ON us.id=pe.usuario_id "
            "WHERE pe.id=? AND pe.usuario_id=?",
            (oid, u["id"]),
        ).fetchone()
    if not fila:
        abort(404)
    return render_template("pedido.html", o=fila)


# ---------------------------------------------------------------- administracion
@app.route("/admin")
@admin_requerido
def admin():
    usuarios = db().execute("SELECT id, username, email, rol FROM usuarios").fetchall()
    ventas = db().execute(
        "SELECT pe.id, us.username, pr.nombre, pe.cantidad, pe.total, pe.estado_pago FROM pedidos pe "
        "JOIN usuarios us ON us.id=pe.usuario_id JOIN productos pr ON pr.id=pe.producto_id "
        "ORDER BY pe.id DESC"
    ).fetchall()
    mensajes = db().execute("SELECT * FROM mensajes_contacto ORDER BY id DESC").fetchall()
    return render_template("admin.html", usuarios=usuarios, ventas=ventas, mensajes=mensajes)


# ---------------------------------------------------------------- paginas legales y errores
@app.route("/legal/<seccion>")
def legal(seccion):
    if seccion not in ("privacidad", "aviso-legal", "cookies"):
        abort(404)
    return render_template("legal.html", seccion=seccion)


@app.errorhandler(403)
def err_403(_e):
    return render_template("error.html", codigo=403, titulo="Acceso denegado", mensaje="No tienes permisos para acceder a este recurso."), 403


@app.errorhandler(404)
def err_404(_e):
    return render_template("error.html", codigo=404, titulo="Pagina no encontrada", mensaje="El recurso solicitado no existe o no esta disponible."), 404


if __name__ == "__main__":
    init_db()
    migrar_db()
    app.run(host="127.0.0.1", port=5000, debug=False)


# PCForge · tienda de componentes de PC

Tienda web de ejemplo para vender componentes de ordenador (procesadores, gráficas, RAM, SSD, placas base, fuentes y cajas). Está hecha con **Python + Flask + SQLite** y pensada con la seguridad en mente: consultas parametrizadas, protección CSRF, sesiones seguras, cabeceras de seguridad y pago con Stripe o con una pasarela simulada para pruebas.

> Proyecto educativo. Los productos, usuarios, correos y direcciones son ficticios. No uses tarjetas reales en la pasarela simulada.

---

## Qué incluye

- Catálogo por categorías, buscador y ficha de producto con imagen y opiniones.
- Registro e inicio de sesión de usuarios.
- Compra con dirección y teléfono, y listado de pedidos.
- **Pago**: Stripe Checkout o pasarela simulada (pruebas).
- **Correo**: recibo del pedido y confirmación del formulario de contacto.
- Panel de administración (usuarios, ventas y mensajes de contacto).
- Páginas legales (aviso legal, privacidad y cookies) y formulario de contacto.

## Estructura del repositorio

```
.
├── app.py                 # Aplicación Flask (rutas, pagos, correo, seguridad)
├── requirements.txt       # Dependencias de Python
├── .env.example           # Plantilla de configuración (copiar a .env)
├── .gitignore             # Evita subir .env, tienda.db y .venv
├── templates/             # Páginas HTML (Jinja)
└── static/
    ├── style.css          # Estilos
    └── img/               # Una imagen SVG por producto
```

La base de datos `tienda.db` **se crea sola** la primera vez que arrancas la app y no forma parte del repositorio.

---

## Puesta en marcha

Necesitas **Python 3.10 o superior**.

### 1. Crear el entorno virtual (solo la primera vez)

Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
```
Mac / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar las dependencias (solo la primera vez)

```bash
pip install -r requirements.txt
```

### 3. Configurar el archivo `.env`

```bash
cp .env.example .env        # En Windows: copy .env.example .env
```

Para probar en local no hace falta cambiar nada, pero conviene definir un `SECRET_KEY` fijo (si no, las sesiones se cierran cada vez que reinicias la app).

### 4. Arrancar la web

```bash
python app.py
```

Abre <http://127.0.0.1:5000>. La terminal debe quedarse abierta mientras uses la web; para pararla, pulsa `Ctrl+C`.

En el primer arranque, la consola muestra la contraseña del usuario `admin` (si no definiste `ADMIN_PASSWORD`). Guárdala: solo se muestra una vez. Para tener clientes de prueba, regístrate desde la web o arranca con `SEED_DEMO_USERS=1`.

---

## Configuración (`.env`)

| Variable | Para qué sirve | Valor por defecto |
|---|---|---|
| `SECRET_KEY` | Firma las sesiones. Usa una cadena larga y aleatoria | aleatoria en cada arranque |
| `HTTPS_ENABLED` | `1` cuando la web se sirve por HTTPS (activa la cookie `Secure`) | `0` |
| `BEHIND_PROXY` | `1` si la web va detrás de un proxy de hosting (usa la IP real del cliente) | `0` |
| `ADMIN_PASSWORD` | Contraseña inicial del admin | se genera y se muestra en consola |
| `SEED_DEMO_USERS` | `1` crea los usuarios de prueba `ana` y `luis` con contraseña aleatoria | `0` |
| `DEMO_PAYMENTS` | `1` activa la pasarela simulada (poner `0` en producción) | `1` |
| `STRIPE_SECRET_KEY` | Clave secreta de Stripe | vacío |
| `STRIPE_WEBHOOK_SECRET` | Secreto del webhook de Stripe | vacío |
| `SMTP_HOST`, `SMTP_PORT` | Servidor de correo saliente | vacío, `587` |
| `SMTP_USER`, `SMTP_PASSWORD` | Cuenta que envía los correos | vacío |
| `CONTACT_RECEIVER` | Correo que recibe los mensajes de contacto | `ventas@pcforge.es` |

> El archivo `.env` contiene secretos y **no debe subirse al repositorio**. El `.gitignore` ya lo excluye.

---

## Pago

### Pasarela simulada (por defecto)

Con `DEMO_PAYMENTS=1` y sin claves de Stripe, al comprar aparece un formulario de tarjeta en modo pruebas:

| Tarjeta de prueba | Resultado |
|---|---|
| `4242 4242 4242 4242` | Pago aprobado |
| `4000 0000 0000 0002` | Pago rechazado |

Usa cualquier fecha futura y cualquier CVV de 3 cifras. La aplicación no guarda el número completo ni el CVV, solo la marca y los 4 últimos dígitos.

### Stripe Checkout

1. Crea una cuenta en <https://stripe.com> y trabaja primero en modo pruebas.
2. Copia la clave secreta en `STRIPE_SECRET_KEY`.
3. Para recibir la confirmación de pago en local, instala la [Stripe CLI](https://stripe.com/docs/stripe-cli) y ejecuta:
   ```bash
   stripe listen --forward-to localhost:5000/stripe/webhook
   ```
   Copia el secreto que muestra en `STRIPE_WEBHOOK_SECRET`.
4. Reinicia la app. El pago se hará en la página de Stripe y la pasarela simulada quedará desactivada.
5. En producción, registra el endpoint `https://TU-DOMINIO/stripe/webhook` en el panel de Stripe (evento `checkout.session.completed`).

## Correo

Sin configuración, los correos no se envían: solo aparecen en la consola. Para enviarlos, rellena el SMTP. Ejemplo con una cuenta que use contraseña de aplicación:

```
SMTP_HOST=smtp.ejemplo.com
SMTP_PORT=587
SMTP_USER=tu-cuenta@ejemplo.com
SMTP_PASSWORD=tu-contraseña-de-aplicacion
CONTACT_RECEIVER=tu-cuenta@ejemplo.com
```

El recibo del pedido se envía siempre al correo de la cuenta del cliente.

---

## Seguridad

| Protección | Cómo |
|---|---|
| Inyección SQL | Consultas parametrizadas |
| XSS | Escape automático de plantillas y política CSP |
| CSRF | Token en los formularios POST |
| Sesiones | Cookie `HttpOnly` y `SameSite=Lax` (más `Secure` con HTTPS), sesión regenerada al entrar |
| Contraseñas | Almacenadas con hash `scrypt` |
| Control de acceso | Cada pedido solo es visible para su dueño o un administrador |
| Abuso | Límite de intentos en login, contacto y pago |
| Pagos | Pago idempotente, importe verificado y sin guardar datos de tarjeta |
| Cabeceras | CSP, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` |

---

## Publicarla online

GitHub solo guarda el código: **GitHub Pages no puede ejecutar esta web** (solo sirve archivos estáticos). Para tener una URL pública hace falta un servicio que ejecute Python. Un ejemplo sencillo, conectado a este repositorio, es [Render](https://render.com):

El repositorio incluye un archivo `render.yaml` que lo configura todo automáticamente: en Render elige **New → Blueprint**, conecta el repositorio, escribe una contraseña para `ADMIN_PASSWORD` y pulsa **Apply**. Si prefieres hacerlo a mano:

1. Sube el código a GitHub (sin `.env` ni `tienda.db`).
2. En Render: **New → Web Service** y conecta el repositorio.
3. Configura el servicio:

   | Ajuste | Valor |
   |---|---|
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `gunicorn app:app` |
   | Instance Type | Free (pruebas) |

4. En **Environment**, añade las variables:

   | Variable | Valor |
   |---|---|
   | `SECRET_KEY` | una cadena larga y aleatoria |
   | `ADMIN_PASSWORD` | una contraseña fuerte para el admin |
   | `HTTPS_ENABLED` | `1` |
   | `BEHIND_PROXY` | `1` |
   | `DEMO_PAYMENTS` | `1` para la pasarela simulada, o `0` si usas Stripe |

5. Pulsa **Create Web Service**. Al terminar, tendrás una URL `https://TU-SERVICIO.onrender.com`, y cada `git push` la actualiza.

Limitaciones del plan gratuito (conviene comprobarlas en la documentación del servicio):

- El servicio se **duerme tras unos 15 minutos sin visitas** y tarda cerca de un minuto en despertar.
- El disco no es persistente, así que la base de datos SQLite **puede reiniciarse** al reiniciar o volver a desplegar. Para datos permanentes hace falta un disco de pago o una base de datos externa.

Antes de publicar en cualquier servicio, deja `SEED_DEMO_USERS=0`, usa siempre HTTPS y no uses `python app.py` en producción.

## Problemas frecuentes

| Problema | Solución |
|---|---|
| `No module named flask` | Activa el entorno `.venv` y ejecuta `pip install -r requirements.txt` |
| Las sesiones se cierran al reiniciar | Define un `SECRET_KEY` fijo en `.env` |
| No llegan los correos | Revisa el SMTP del `.env`; sin él solo se escriben en la consola |
| Las imágenes no se ven | Comprueba que existe `static/img/` con los archivos `.svg` y recarga con Ctrl+F5 |
| El pedido sigue "pendiente" con Stripe | Falta el webhook o `STRIPE_WEBHOOK_SECRET` |
| Error 403 al enviar un formulario | La sesión caducó: recarga la página e inténtalo de nuevo |
>>>>>>> a85c18a (Despliegue en Render)

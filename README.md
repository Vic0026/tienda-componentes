# PCForge · tienda ficticia de componentes de PC

> ⚠️ **Aplicación deliberadamente vulnerable.** Creada para practicas de auditoria web
> (CE Ciberseguridad). Ejecutar **solo en local (127.0.0.1) o en la VLAN del aula**.
> **No desplegar en Internet.** Todos los datos son ficticios.

## Version y alcance (para el auditor)

| | |
|---|---|
| Version | `1.0.0-vulnerable` |
| Tecnologia | Python 3 + Flask + SQLite |
| URL base | `http://127.0.0.1:5000` |
| En alcance | Todas las rutas de la aplicacion |
| Fuera de alcance | El sistema operativo, otros servicios y cualquier otra maquina |

## Arranque

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abre <http://127.0.0.1:5000>. La base de datos `tienda.db` se crea sola al primer arranque;
para volver al estado inicial, borra `tienda.db` y reinicia.

## Cuentas ficticias

| Usuario | Contrasena | Rol |
|---|---|---|
| `ana` | `ana123` | cliente |
| `luis` | `luis123` | cliente |

Tambien existe una cuenta de administracion; forma parte del reto conseguir acceso a ella.

## Funcionalidades

Catalogo por categorias, busqueda, ficha de producto con opiniones, registro y login,
compra con direccion y telefono, listado y detalle de pedidos y panel de administracion.

## Reglas para quien audita

- Documenta cada hallazgo con peticion, respuesta, efecto e impacto.
- Propon una correccion y una prueba de cierre por hallazgo.
- No ataques nada fuera del alcance indicado.

## Version estatica para GitHub Pages (`docs/`)

La carpeta `docs/` contiene una version **solo HTML/CSS/JS** de la tienda, pensada para
publicarse en GitHub Pages (`https://vic0026.github.io/tienda-componentes/`).
No tiene servidor ni base de datos, asi que los fallos son de **cliente**:
XSS en el DOM, autenticacion y control de acceso en el navegador, ficheros de datos
publicos y archivos olvidados. Todo el contenido es ficticio.

<<<<<<< HEAD
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
=======
Para activarla: **Settings → Pages → Deploy from a branch → `main` / `/docs`**.
Para probarla en local: `cd docs && python -m http.server 8000` y abrir <http://127.0.0.1:8000>.
>>>>>>> 3a2ada6 (Actualización del proyecto)

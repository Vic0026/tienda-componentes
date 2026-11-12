# PCForge · Tienda de Componentes (Versión Segura)

Aplicación web de comercio electrónico desarrollada con **Python 3 + Flask + SQLite**, saneada para producción e integrada con envío de correos, pasarela de pagos y páginas legales.

## Mejoras realizadas respecto al proyecto original

1. **Eliminación completa de vulnerabilidades:**
   - **Inyección SQL corregida:** Todas las consultas en `/login`, `/buscar`, `/pedido` y `/comprar` usan parámetros preparados (`?`).
   - **XSS reflejado y almacenado eliminados:** Eliminado el filtro `|safe` en plantillas y activado el escape automático de Jinja2 + validación de longitud.
   - **IDOR corregido:** `/pedido/<id>` verifica que el pedido pertenezca al usuario autenticado (o que sea administrador).
   - **Sesiones seguras:** Sustituida la cookie manipulable en Base64 por `session` firmada de Flask con `HttpOnly`, `SameSite=Lax` y soporte `Secure`.
   - **Contraseñas robustas:** Sustituido MD5 por hashing con sal (`werkzeug.security.generate_password_hash`).
   - **Protección CSRF y fuerza bruta:** Token CSRF obligatorio en todos los formularios `POST` y bloqueo temporal tras 5 intentos fallidos de login.
   - **Cabeceras HTTP de seguridad:** `Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` y `Referrer-Policy`.
   - **Limpieza de archivos expuestos:** Eliminada la carpeta `docs/` con credenciales hardcodeadas, `usuarios.json` público y `config.bak.json`.

2. **Nuevas funcionalidades incluidas:**
   - **Formulario de contacto (`/contacto`):** Con protección anti-spam (honeypot), validación, almacenamiento en base de datos, visualización en `/admin` y envío automático de correos por SMTP (con modo simulación si aún no configuras `.env`).
   - **Sistema de pagos (`/comprar/<id>`):** Integrado con **Stripe Checkout** (incluyendo webhook `/stripe/webhook`) y un flujo de confirmación inmediata para pruebas locales sin cuenta de Stripe.
   - **Esenciales de una web moderna:** Avisos legales (Privacidad, Aviso Legal, Cookies), páginas personalizadas de error `403` y `404`, metaetiquetas SEO y notificaciones *flash*.

## Instalación y arranque

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Edita .env con tus claves reales
python app.py
```

Abre `http://127.0.0.1:5000`.

### Usuarios iniciales de prueba
- **Admin:** `admin` / `Admin#2026!Segura`
- **Cliente:** `ana` / `Ana#2026!Segura`
- **Cliente:** `luis` / `Luis#2026!Segura`

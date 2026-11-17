# Solucionario (SOLO PARA EL AUTOR - no compartir con quien audita)

Vulnerabilidades intencionadas de PCForge 1.0.0-vulnerable y su correccion.

| # | Fallo | Donde | Como se manifiesta | Correccion |
|---|---|---|---|---|
| 1 | Inyeccion SQL | `/login` (campo usuario) | Entrar como `admin` sin contrasena con `admin'--` | Consultas parametrizadas (`?`) |
| 2 | Inyeccion SQL | `/buscar?q=` | `UNION SELECT` permite leer la tabla `usuarios`; ademas se muestra el error SQL | Consultas parametrizadas y mensajes de error genericos |
| 3 | XSS reflejado | `/buscar?q=` | `q` se imprime con `\|safe` | Quitar `\|safe` (autoescape de Jinja) |
| 4 | XSS almacenado | Opiniones de `/producto/<id>` | El texto se guarda y se pinta con `\|safe` | Quitar `\|safe`; validar longitud |
| 5 | IDOR | `/pedido/<id>` | Un usuario ve pedidos de otro cambiando el numero | Comprobar `usuario_id == usuario actual` (o 403/404) |
| 6 | Sesion debil | Cookie `sid` | Es `base64("id:usuario")`: predecible y forjable (`MTphZG1pbg==` = admin); sin `HttpOnly`/`Secure`/`SameSite`; no rota | Token aleatorio en servidor (o `session` firmada), flags de cookie, rotar al login |
| 7 | Hashes debiles | Tabla `usuarios` | MD5 sin sal | Argon2id (UT5) |
| 8 | Falta de CSRF y de limite de intentos | Formularios y `/login` | Sin token CSRF ni bloqueo por fuerza bruta | Token CSRF, limitacion de intentos |
| 9 | Cabeceras ausentes | Todas las respuestas | Sin CSP, `X-Frame-Options`, etc. | Cabeceras de seguridad (nginx o Flask) |

## Ideas de prueba de cierre (regresion)

- Login con `admin'--` debe devolver error, no sesion.
- `/buscar?q=<script>` debe aparecer escapado (`&lt;script&gt;`).
- `luis` pidiendo `/pedido/1` debe recibir 403/404.
- La cookie de sesion debe llevar `HttpOnly` y `SameSite`, y cambiar tras el login.

---

# Version estatica (`docs/`) - fallos de cliente

| # | Fallo | Donde | Como se manifiesta | Correccion |
|---|---|---|---|---|
| 1 | XSS en el DOM (reflejado) | `index.html?q=` | `q` se pinta con `innerHTML` | `textContent` o escapar |
| 2 | XSS almacenado en el navegador | Opiniones (`producto.html`) | El texto de `localStorage` se inyecta con `innerHTML` | Escapar al pintar |
| 3 | Credenciales en el cliente | `js/app.js` | Usuarios y contrasenas visibles en el codigo | Autenticacion en servidor |
| 4 | Sesion falsificable | `localStorage.sesion` | `{"usuario":"admin","rol":"admin"}` pegado en la consola da acceso a `admin.html` | Sesion/validacion en servidor |
| 5 | "IDOR" por ficheros publicos | `data/pedidos/N.json` y `pedido.html?id=N` | Cualquiera ve pedidos de otros cambiando N | Datos privados solo en servidor con autorizacion |
| 6 | Datos de admin accesibles | `data/admin/usuarios.json` | Se descarga sin sesion | No publicar ese fichero |
| 7 | Fichero de backup olvidado | `data/config.bak.json` | Clave ficticia y credenciales de soporte | No subir copias ni secretos al repo |
| 8 | Sin cabeceras de seguridad | GitHub Pages | Sin CSP ni `X-Frame-Options` (no configurable en Pages) | Documentar como limitacion |

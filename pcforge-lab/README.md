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

Para activarla: **Settings → Pages → Deploy from a branch → `main` / `/docs`**.
Para probarla en local: `cd docs && python -m http.server 8000` y abrir <http://127.0.0.1:8000>.

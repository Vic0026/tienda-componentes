# PCForge Lab + Wazuh

La aplicación escribe eventos JSON por línea en `logs/pcforge-events.jsonl`.
Añade esta configuración dentro de `<ossec_config>` en `/var/ossec/etc/ossec.conf` del agente:

```xml
<localfile>
  <location>/RUTA/COMPLETA/tienda-componentes/pcforge-lab/logs/pcforge-events.jsonl</location>
  <log_format>json</log_format>
</localfile>
```
Sustituye la ruta por la ruta real de tu VM. Asegura que el usuario del agente pueda leer el fichero. Reinicia:
```bash
sudo systemctl restart wazuh-agent
sudo tail -f /var/ossec/logs/ossec.log
```

## Eventos disponibles
`http_request`, `http_response`, `login_attempt`, `login_success`, `login_failure`,
`possible_sqli`, `possible_xss`, `possible_traversal`, `review_submitted`,
`order_view_attempt`, `admin_panel_access`.

## Actividades de clase
1. Provoca varios logins fallidos y busca `login_failure`.
2. Prueba cadenas de laboratorio en el buscador y localiza `possible_sqli`.
3. Envía una opinión de prueba con una cadena XSS inocua y localiza `possible_xss`.
4. Inicia sesión como cliente e intenta consultar un pedido que no sea suyo; revisa `order_view_attempt`.
5. Accede a `/admin` como cliente y analiza el código HTTP 403 y `admin_panel_access`.
6. Correlaciona IP, ruta, método, User-Agent y respuesta.

## Red/IP
Por defecto la app escucha solo en `127.0.0.1:5000`. Para una VM de laboratorio accesible desde otra máquina, cambia al final de `app.py` `host="127.0.0.1"` por `host="0.0.0.0"`. La IP de la VM puede cambiar sin tener que modificar el código de registro. Limita el acceso a una red aislada.

## Aviso
La app conserva vulnerabilidades intencionadas de formación: SQLi en login/búsqueda, XSS almacenado en opiniones, sesión débil e IDOR en detalle de pedidos. Solo datos ficticios y entorno aislado; no publicar en Internet.

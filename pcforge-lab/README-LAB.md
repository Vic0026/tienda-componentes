# PCForge Lab
Copia independiente de la aplicación vulnerable original, con interfaz renovada y registros JSON para Wazuh.

## Arranque
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```
Abre http://127.0.0.1:5000. La base SQLite se crea en el primer arranque.
Cuentas demo iniciales: `ana` / `ana123`, `luis` / `luis123`.
Consulta `wazuh/README-WAZUH.md` para integrar el agente.
**Solo laboratorio aislado. No desplegar en Internet.**

# Pruebas de calidad – Odoo 18 Inventario (Entrega 2)

Curso: Calidad de Productos de Software – Universidad del Valle.
Integrantes: Heidy Mina, Rubén Darío Saa, Kevin Burgos, Daniel Arteaga.

## Estructura
| Carpeta / archivo | Contenido |
|---|---|
| `docker-compose.yml` | Odoo 18 + PostgreSQL local |
| `functional/` | Pruebas funcionales (Selenium + pytest). Un archivo por integrante |
| `unit/` | Pruebas unitarias (módulo Odoo con `TransactionCase`) |
| `evidencia/` | Capturas y reportes de ejecución |
| `docs/` | Diseños de casos, MRP e informes |

## Puesta en marcha (cada integrante, una vez)
Ver `README_SETUP.md`: levantar Odoo con Docker y preparar el entorno de Python.

## Reglas de trabajo
1. Cada integrante trabaja **solo en su archivo**: `functional/test_heidy.py`, `test_ruben.py`, `test_kevin.py`, `test_daniel.py`.
2. `functional/conftest.py` es compartido: no se modifica sin avisar al grupo.
3. Cada quien trabaja en su rama `feature/<nombre>` y la une a `main` con un Pull Request.
4. **Nunca** subir contraseñas ni carpetas `.venv`.
5. Mensajes de commit claros, por ejemplo: `Agrega caso FC-05 ajuste de inventario`.

## Ejecutar las pruebas funcionales
```
cd functional
pytest test_heidy.py -v --html=../evidencia/reporte_heidy.html --self-contained-html
```

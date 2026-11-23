# Entorno de pruebas – Entrega 2 (Odoo Inventario)

## 1. Levantar Odoo (una sola vez)
```
docker compose up -d db
docker compose run --rm odoo odoo -d calidad -i stock,sale_management --stop-after-init
docker compose up -d odoo
```
El segundo comando crea la base `calidad` con datos de demostración (tarda unos minutos).
Abra http://localhost:8069 e ingrese con usuario `admin` y clave `admin`.

Versión instalada (anótela en el informe):
```
docker compose exec odoo odoo --version
```

## 2. Entorno de Python para Selenium
```
python -m venv .venv
.venv\Scripts\activate          (Windows)   |   source .venv/bin/activate   (Linux/Mac)
pip install -r requirements.txt
```
Se necesita Google Chrome instalado (Selenium 4 descarga el driver solo).

## 3. Prueba de humo
```
cd functional
pytest test_00_smoke.py -v --html=../evidencia/reporte_humo.html --self-contained-html
```
Las capturas quedan en `evidencia/test_smoke_crear_producto/`. Si falla, envíe esa carpeta (o `FALLO.png`) y el texto del error.
Si usa Odoo 17: `set ODOO_VERSION=17` (Windows) / `export ODOO_VERSION=17` antes de correr.

## 4. Código fuente de métodos para las pruebas unitarias
```
docker compose exec -T odoo odoo shell -d calidad --no-http --db_host=db --db_user=odoo --db_password=odoo < unit/dump_methods.py > unit/metodos.txt
```
Envíe `unit/metodos.txt`. Con el código real diseño los casos de caja blanca (caminos, decisiones, condiciones).

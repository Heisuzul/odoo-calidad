# Incorporación del aporte de Daniel (Entrega 2)

Este paquete contiene nuevos archivos para el proyecto `Heisuzul/odoo-calidad`, sin alterar `main` ni los archivos de los otros integrantes.

## Qué se puede incorporar ahora

- `docs/diseno_pruebas_funcionales_daniel.md`: ocho diseños FC-05..FC-12 con técnicas, datos y resultados esperados.
- `docs/mrp_daniel.md`: matriz de trazabilidad inicial para el informe.
- `docs/registro_resultados_daniel.md`: plantilla realista, sin aprobar pruebas no ejecutadas.
- `functional/test_daniel.py`: **cuatro casos automatizados (FC-05, FC-06, FC-07 y FC-09)**, todavía **sin validar contra Odoo local**. Reemplaza únicamente la plantilla inicial de Daniel.

## Requisitos previos

- Base local `calidad`, módulo Inventory, usuario de prueba con permisos.
- `.venv` e instalación de `requirements.txt`.
- Variables `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASS` definidas en la sesión local de PowerShell.
- `git branch --show-current` debe responder `feature/daniel`.

## Ejecución inicial controlada

Desde la raíz del repo:

```powershell
.\.venv\Scripts\python.exe -m pytest functional/test_daniel.py --collect-only -q
.\.venv\Scripts\python.exe -m pytest functional/test_daniel.py::test_fc05_modificar_precio -v -s --html=evidencia/reporte_daniel_fc05.html --self-contained-html
```

Analizar errores de selectores, credenciales y configuraciones ANTES de continuar con otros casos. No ejecutar FC-08/FC-10/FC-11/FC-12 hasta implementar su UI y asegurar limpieza.

## Evidencia y reporte

Después de cada ejecución, registrar la fecha, el estado, el resultado real, la ruta de captura y las no conformidades verdaderamente confirmadas en `docs/registro_resultados_daniel.md` y la MRP. No usar cifras inventadas para los indicadores/gráficos.

## Envío a GitHub

```powershell
git status
git add functional/test_daniel.py docs/diseno_pruebas_funcionales_daniel.md docs/mrp_daniel.md docs/registro_resultados_daniel.md
git commit -m "Diseña ocho pruebas funcionales y automatiza primeros cuatro casos de Daniel"
git push -u origin feature/daniel
```

Enviar Pull Request a `main` solo después de revisar los cambios y la evidencia.

**Nota:** la conexión remota del asistente devolvió `403` cuando intentó crear `feature/daniel` en GitHub. El commit y push de este paquete se deben hacer desde el repositorio local autenticado del estudiante.

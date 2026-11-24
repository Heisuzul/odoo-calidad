# Diseño de pruebas funcionales — Daniel — Entrega 2

**Curso:** Calidad de Productos de Software — Universidad del Valle  
**Sistema bajo prueba:** Odoo 18 Community, módulo Inventario (`stock`), base de datos local `calidad`  
**Automatización:** Selenium + pytest (navegador Chrome)  
**Versión del diseño:** 0.1 — 24 de noviembre de 2026  
**Estado general:** diseños propuestos; falta confirmar la ejecución en la instalación local.

## Alcance y fundamentos

La rúbrica pide **4 casos funcionales por persona**, **al menos dos técnicas de caja negra**, automatización, evidencias, MRP, resultados, indicadores, cuatro gráficos explicados y lecciones aprendidas. Se proponen **ocho** casos propios (FC-05 a FC-12), sin alterar los de Heidy (FC-01 a FC-04). Los RF a continuación son **requisitos de prueba formulados por el equipo**: no se presentan como especificaciones contractuales oficiales de Odoo.

Técnicas: **PE** = partición de equivalencia; **VL** = análisis de valor límite; **TD** = tabla de decisión; **TE** = transición de estados. PE y VL cubren el mínimo de dos técnicas. Las pruebas de Odoo sobre productos se basan en la interfaz de Inventario; ajustes de existencias se basan en la documentación oficial Odoo 18 [Inventario: ajustes](https://www.odoo.com/documentation/18.0/applications/inventory_and_mrp/inventory/warehouses_storage/inventory_management/count_products.html).

**Criterio de interpretación:** no marcar un comportamiento como no conformidad hasta confirmar la regla de negocio aplicable. En particular, Odoo puede admitir precio 0 y ciertas cantidades de inventario distintas de lo que intuitivamente esperamos. Distinguir fallo de automatización, precondición incumplida y defecto real del producto.

**Preparación compartida:** base de pruebas local y aislada; Inventory instalado; usuario con permisos de producto, costo y ajustes de inventario; interfaz English; un producto aislado por caso con referencia única `DAN-<ID>-<uuid>`; sin datos de producción. Para cantidades, producto almacenable con seguimiento de inventario activo, unidad `Units`, almacén `WH/Stock` y sin operaciones en paralelo.

## FC-05 — Modificar precio de venta

- **RF-05:** un usuario autorizado puede actualizar el precio de venta (`list_price`) de un producto existente y el valor guardado se conserva tras recargar el registro.
- **Técnica:** PE: clase válida de precio positivo; clase a confirmar de edición no autorizada queda fuera de esta ejecución.
- **Precondición:** producto de pruebas recién creado con precio 100.00; permiso de edición.
- **Entrada:** `list_price=25000.00`.
- **Pasos:** abrir Productos; crear producto con identificador único y precio inicial; guardar; editar precio; guardar; recargar; reabrir registro/verificar su valor almacenado.
- **Esperado:** `list_price=25000.00` persistido y mostrado en el formulario, sin duplicar el producto.
- **Evidencia:** captura de precio inicial y final; reporte de pytest.
- **Estado:** implementado en código inicial, ejecución local pendiente.

## FC-06 — Precio en el borde inferior

- **RF-06:** en la configuración estándar de prueba, se determina el tratamiento del precio de venta cero y del menor incremento monetario de prueba. La aceptación de ambos valores deberá confirmarse en Odoo antes de usarla como criterio de defecto.
- **Técnica:** VL: `0.00` (borde inferior hipotético no negativo), `0.01` (inmediatamente por encima). Complementar con precio negativo **solo después de verificar** regla y precisión de moneda.
- **Precondición:** producto propio a precio `100.00`; precisión monetaria centesimal.
- **Entrada:** `0.00`, `0.01` en secuencia, con guardado y recarga independiente.
- **Pasos:** cambiar precio a cero y guardar; recargar y observar; establecer 0.01, guardar, recargar y observar.
- **Esperado provisional:** ambos valores se guardan y persisten sin error en una instalación estándar; si no ocurre, registrar observación y examinar configuración antes de declarar una no conformidad.
- **Evidencia:** dos capturas de frontera y salida de pytest.
- **Estado:** implementado en código inicial, ejecución local pendiente.

## FC-07 — Buscar producto por referencia interna

- **RF-07:** la búsqueda del catálogo permite localizar un producto por su referencia interna y distinguir una referencia inexistente.
- **Técnica:** PE: referencia existente (válida para búsqueda con resultados) e inexistente (válida para búsqueda sin resultados; **no** es entrada inválida del sistema).
- **Precondición:** producto propio con referencia única; listado de Productos habilitado.
- **Entradas:** referencia `DAN-FC07-<uuid>` y otra referencia aleatoria ausente.
- **Pasos:** crear producto; buscar su referencia usando la barra de búsqueda; comprobar lista; volver a listado sin filtros; buscar referencia inexistente.
- **Esperado:** en primera consulta aparece el producto creado; en segunda, cero resultados. La búsqueda no modifica el producto.
- **Evidencia:** capturas de lista con resultado y sin resultados.
- **Estado:** implementado en código inicial, ejecución local pendiente.

## FC-08 — Archivar y restaurar un producto

- **RF-08:** tras archivar un producto, deja de aparecer entre activos; cuando se desarchiva vuelve a mostrarse en la lista de activos.
- **Técnica:** TE, con estados `activo → archivado → activo`; comprobaciones de visibilidad con filtro normal y `Archived`.
- **Precondición:** producto propio activo; derechos para archivar/desarchivar.
- **Entradas:** acciones de interfaz `Archive` y `Unarchive`.
- **Pasos:** crear producto; archivar y confirmar; buscar sin filtro y comprobar ausencia; aplicar filtro Archived y localizarlo; abrir, usar Unarchive, comprobar regreso a activos.
- **Esperado:** `active=True → False → True` y visibilidad coherente en ambas listas.
- **Evidencia:** capturas de los tres estados.
- **Estado:** diseño completo; la automatización requiere verificar selectores de archivados en la instalación local.

## FC-09 — Modificar costo de un producto

- **RF-09:** un usuario autorizado puede guardar una modificación de costo estándar (`standard_price`) y recuperarla tras recarga para un producto sin existencias.
- **Técnica:** PE: costo positivo normal; no extrapolar automáticamente la aceptación/rechazo de costos negativos.
- **Precondición:** producto de prueba nuevo, sin existencias ni movimientos, y costo 120.00; permisos de edición.
- **Entrada:** `standard_price=200.00`.
- **Pasos:** crear producto con costo 120; guardar; editar a 200; guardar; recargar; verificar campo y valor persistido.
- **Esperado:** costo estándar igual a 200.00. No inferir ajustes de valoración de existencias: este caso no las crea.
- **Evidencia:** captura inicial y final.
- **Estado:** implementado en código inicial, ejecución local pendiente.

## FC-10 — Conteo inicial desde cero

- **RF-10:** al aplicar un conteo físico de 5 unidades a un producto sin existencias, la cantidad disponible del producto en la ubicación probada se actualiza a 5.
- **Técnica:** PE: conteo físico no negativo/valor válido; estado anterior 0.
- **Precondición:** producto almacenable con `Track Inventory` activo, ubicación WH/Stock, cantidad inicial 0; sin reservas ni movimientos.
- **Entradas:** cantidad contada 5.
- **Pasos:** crear producto propio; abrir Inventory > Operations > Inventory Adjustments; registrar conteo en WH/Stock; pulsar Apply y confirmar; volver a existencias.
- **Esperado:** cantidad en WH/Stock 5 y movimiento de ajuste de +5.
- **Evidencia:** antes/conteo/después, reporte.
- **Estado:** diseño completo; pendiente validar ruta UI y automatizar.

## FC-11 — Ajuste positivo de existencias

- **RF-11:** aplicar un conteo mayor que las existencias incrementa la cantidad disponible hasta el valor contado.
- **Técnica:** VL sobre diferencia de inventario; ejemplo anterior 5, contado 6 (`+1`: incremento mínimo de unidad entera), además de escenario representativo contado 10 (`+5`).
- **Precondición:** producto aislado con existencias 5 en WH/Stock, unidad de medida que no permite fracciones, sin otros movimientos.
- **Entradas:** cantidad contada 6. Un segundo subescenario 10 queda previsto para cobertura ampliada.
- **Pasos:** consultar cantidad 5; editar `Counted Quantity` a 6; aplicar; comprobar nueva cantidad y diferencia.
- **Esperado:** nueva cantidad 6, diferencia +1, historial de ajuste.
- **Evidencia:** antes, línea del ajuste, después.
- **Estado:** diseño completo; automatización pendiente.

## FC-12 — Ajuste negativo, cero y reglas de resultado

- **RF-12:** aplicar un conteo inferior a las existencias reduce la cantidad hasta la contada; aplicar cero deja cero unidades.
- **Técnica:** TD y VL: condiciones `C1: conteo < cantidad anterior`, `C2: conteo == 0` con cantidad anterior positiva.

| Regla | C1 | C2 | Acción esperada |
|---|---|---|---|
| R1 | Sí | No | Reducir inventario a cantidad contada positiva |
| R2 | Sí | Sí | Reducir inventario a cero |
| R3 | No | No | No corresponde a un decremento (fuera de FC-12) |
| R4 | No | Sí | Imposible si cantidad anterior > 0 |

- **Precondición:** producto aislado, con 5 unidades exactas en WH/Stock; sin reservas ni movimientos simultáneos.
- **Entradas:** subescenarios independientes `5→4` (decremento unitario) y `5→0` (límite cero). Preparar stock entre subescenarios; nunca reutilizar un estado incierto.
- **Pasos:** registrar cada conteo; aplicar; verificar cantidad final y movimiento de inventario.
- **Esperado:** resultados 4 y 0 respectivamente; diferencias -1 y -5 en historial de cada subescenario.
- **Evidencia:** pantallazos previos y posteriores, movimientos de ajuste.
- **Estado:** diseño completo; pendiente automatización.

## Reglas de trazabilidad, ejecución y limpieza

1. Mantener correspondencia `FC-XX ↔ RF-XX ↔ técnica ↔ evidencia ↔ resultado observado ↔ defecto`.
2. Un caso no es `PASS` por estar implementado: debe ejecutarse. Usar `NO EJECUTADO`, `PASS`, `FAIL`, `BLOQUEADO` o `ERROR AUTOMATIZACIÓN`.
3. Toda falla se clasifica antes de describirla como defecto del producto: precondición, selector, entorno, aplicación o especificación ambigua.
4. Usar datos únicos por caso y eliminar solo los registros de prueba propios. Los casos con movimientos de inventario requieren limpieza y restauración revisadas aparte; por eso no se automatizan antes de verificar el entorno.
5. Nunca usar cuentas reales ni subir contraseñas, `.env`, cookies o capturas con información personal.

## Referencias de trabajo

- [Documentación Odoo 18: ajustes de inventario](https://www.odoo.com/documentation/18.0/applications/inventory_and_mrp/inventory/warehouses_storage/inventory_management/count_products.html)
- [Documentación Odoo 18: configuración de tipos de producto y seguimiento](https://www.odoo.com/documentation/18.0/applications/inventory_and_mrp/inventory/product_management/configure/type.html)
- [Repositorio Odoo, rama 18.0, modelos de stock](https://github.com/odoo/odoo/tree/18.0/addons/stock/models)
- Apuntes del curso: caja negra, particiones de equivalencia y valores límite; tablas de decisión.

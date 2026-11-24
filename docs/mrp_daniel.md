# MRP — Matriz de Requerimientos de Pruebas (aporte Daniel)

Proyecto: Odoo 18 — Inventario · Entrega 2 · Corte de trabajo: 2026-11-24

**Leyenda:** D = diseñado; A = automatizado (sin ejecutar); NE = no ejecutado; PASS/FAIL = requiere evidencia de ejecución real.

| Requisito de prueba* | Descripción verificable | Casos | Técnica | Automatización | Ejecución | Evidencia prevista |
|---|---|---|---|---|---|---|
| RF-05 | Actualización persistente del precio de venta | FC-05 | PE | A | NE | `evidencia/test_fc05_modificar_precio/` |
| RF-06 | Tratamiento del precio 0 y 0.01 | FC-06 | VL | A | NE | `evidencia/test_fc06_valores_frontera_precio/` |
| RF-07 | Búsqueda por referencia existente/inexistente | FC-07 | PE | A | NE | `evidencia/test_fc07_buscar_referencia/` |
| RF-08 | Restauración de producto archivado | FC-08 | TE | D | NE | `evidencia/test_fc08_restaurar_producto/` |
| RF-09 | Actualización persistente de costo estándar | FC-09 | PE | A | NE | `evidencia/test_fc09_modificar_costo/` |
| RF-10 | Aplicar conteo inicial 0→5 | FC-10 | PE | D | NE | `evidencia/test_fc10_conteo_inicial/` |
| RF-11 | Ajustar inventario 5→6 | FC-11 | VL | D | NE | `evidencia/test_fc11_ajuste_positivo/` |
| RF-12 | Ajustar inventario 5→4 y 5→0 | FC-12 | TD + VL | D | NE | `evidencia/test_fc12_ajuste_negativo/` |

*Los códigos RF-05 a RF-12 son requisitos de **prueba redactados por el equipo** a partir de funcionalidades evaluables, no requisitos oficiales identificados en la documentación de Odoo. Los resultados esperados de FC-06 y de los ajustes deberán contrastarse con la instalación y la especificación efectiva antes de registrar no conformidades.

## Indicadores después de ejecutar

- **Casos ejecutados (%)** = ejecutados con resultado terminal / casos planificados × 100.
- **Tasa de éxito (%)** = casos PASS / (casos PASS + casos FAIL) × 100, excluyendo bloqueados/errores de entorno y explicando el denominador.
- **Cobertura de requisitos de prueba (%)** = RF con al menos un caso ejecutado / RF trazados × 100. **No** equivale a cobertura del código ni de todos los requisitos de Odoo.
- **No conformidades** = defectos de producto confirmados, con ID, gravedad, evidencia, pasos para reproducir y estado. No contabilizar un fallo de localizador Selenium como defecto del producto.

## Cuatro visualizaciones obligatorias (sin cifras inventadas)

1. Estado de casos (PASS / FAIL / BLOQUEADO / ERROR / NE).
2. Resultado por técnica de diseño (PE / VL / TD / TE), indicando casos multitécnica.
3. Cobertura de RF de prueba ejecutados frente a pendientes.
4. No conformidades confirmadas por severidad; si ninguna se confirma, registrar **cero** y explicarlo, no forzar un gráfico de defectos ficticios.

## Lecciones aprendidas (redactar al cierre)

Registrar al menos: selección de clases representativas y límites, diferencia entre falla de Selenium y defecto de Odoo, manejo de datos de prueba/aislamiento, trazabilidad y reproducibilidad, límites de cobertura.

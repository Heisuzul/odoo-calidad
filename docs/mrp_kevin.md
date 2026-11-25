# MRP — Matriz de Requerimientos de Pruebas (Kevin Burgos)

Odoo 18 — Inventario · Entrega 2 · 2026-11-25.
Leyenda: A = automatizado; PASS = ejecutado y aprobado con evidencia.
Los RF-K y RU-K son criterios de prueba de este aporte.

| Requisito de prueba | Descripción verificable | Casos | Técnica | Automatización | Ejecución | Evidencia prevista / obtenida |
|---|---|---|---|---|---|---|
| RF-K13 | Barcode único/vacío; rechazo de duplicado | FC-13 (3 escenarios) | PE | A | 3 PASS | `evidencia/test_FC13_codigo_barras[...]/`, HTML |
| RF-K14 | Persistencia de peso firmado | FC-14 (4 escenarios) | PE + VL | A | 4 PASS | `evidencia/test_FC14_peso[...]/`, HTML |
| RF-K15 | Persistencia de volumen firmado | FC-15 (4 escenarios) | PE + VL | A | 4 PASS | `evidencia/test_FC15_volumen[...]/`, HTML |
| RF-K16 | Nombre obligatorio de ubicación, longitud 0/1/2 | FC-16 (3 escenarios) | PE + VL | A | 3 PASS | `evidencia/test_FC16_nombre_ubicacion[...]/`, HTML |
| RU-K01 | check_quantity excluye no serial | UK01 | Ramas + camino básico | A | PASS | `evidencia/test_unit_kevin/salida.txt` |
| RU-K01 | check_quantity excluye inventory | UK02 | Ramas + camino básico | A | PASS | ídem |
| RU-K01 | check_quantity excluye sin lote | UK03 | Ramas + camino básico | A | PASS | ídem |
| RU-K01 | check_quantity admite abs(cantidad) ≤ 1 | UK04 | Ramas + camino básico | A | PASS | ídem y `cobertura.json` |
| RU-K01 | check_quantity rechaza −2 y 2 | UK05 | Ramas + camino básico | A | PASS | ídem y `cobertura.json` |
| RU-K01 | check_quantity acepta recordset vacío | UK06 | Ramas + camino básico | A | PASS | ídem |

## Indicadores

- Funciones/casos funcionales: 4/4 ejecutados; escenarios: 14/14.
- Pruebas unitarias: 6/6; métodos seleccionados: 1/1.
- Aprobación: 20/20 escenarios/pruebas = 100%.
- Requisitos únicos ejercitados: 5/5 = 100%. Las seis filas RU-K01 no son seis RF.
- Sentencias del método: 8/8; arcos de if/for: 6/6. No se extrapola a Inventario.
- NC confirmadas: 0. Detalle y límites de interpretación en `informe_kevin.md`.

## Trazabilidad y visualizaciones

Diseño: `diseno_pruebas_funcionales_kevin.md`.
Resultados: `registro_resultados_kevin.md`.
Datos gráficos: `evidencia/graficos_kevin/datos_reales.json`.
Cuatro gráficos e interpretación: `informe_kevin.md`.

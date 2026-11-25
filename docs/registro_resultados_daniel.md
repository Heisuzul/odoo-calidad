# Registro de resultados — Daniel · Odoo 18 (Entrega 2)

**Estado:** plantilla para completar con ejecuciones reales. **No hay pruebas ejecutadas desde este asistente contra el Odoo local del estudiante.**

| Caso | Fecha/hora local | Estado | Resultado observado | Evidencia | NC asociada | Ambiente / versión |
|---|---|---|---|---|---|---|
| FC-05 | — | NO EJECUTADO | — | — | — | Odoo 18 / calidad |
| FC-06 | — | NO EJECUTADO | — | — | — | Odoo 18 / calidad |
| FC-07 | — | NO EJECUTADO | — | — | — | Odoo 18 / calidad |
| FC-08 | — | NO EJECUTADO | — | — | — | Odoo 18 / calidad |
| FC-09 | — | NO EJECUTADO | — | — | — | Odoo 18 / calidad |
| FC-10 | — | NO EJECUTADO | — | — | — | Odoo 18 / calidad |
| FC-11 | — | NO EJECUTADO | — | — | — | Odoo 18 / calidad |
| FC-12 | — | NO EJECUTADO | — | — | — | Odoo 18 / calidad |

## No conformidades

Por cada no conformidad real agregar: ID, RF/FC, pasos exactos, entrada, esperado, observado, severidad, capturas, versión, reproductibilidad y estado. El resultado `ERROR AUTOMATIZACIÓN` no constituye por sí solo una NC del software.

## Indicadores y gráficos

Usar las fórmulas y cuatro gráficos planteados en `mrp_daniel.md` **únicamente al disponer de resultados reales**. Escribir interpretación y denominador de cada porcentaje.

## Aporte al informe grupal

Después de verificar las ejecuciones, trasladar: descripción de técnicas aplicadas; tabla de resultados FC-05..FC-12; vínculos de capturas; indicadores; análisis de fallos/no conformidades y lecciones aprendidas. Los cuatro gráficos del informe deben construirse de forma coordinada con todos los integrantes para evitar que un gráfico individual se presente como resultado total del grupo.

### FC-05 — Modificación del precio de venta

- Fecha de ejecución: 24/11/2026
- Técnica: partición de equivalencia, clase válida
- Herramientas: Selenium, Python, pytest
- Aplicación: Odoo 18 - Inventario
- Precio inicial: 100
- Precio esperado después de modificar: 25000
- Precio observado después de recargar: 25000
- Resultado: PASSED
- Duración: 13,28 segundos
- No conformidades funcionales confirmadas: 0
- Evidencia: evidencia/reporte_daniel_fc05.html
- Capturas: evidencia/test_fc05_modificar_precio/

Conclusión: El sistema permitió modificar el precio de venta y
persistió correctamente el nuevo valor. La verificación se realizó
mediante consulta del registro y recarga de la interfaz.

Observación: Durante ejecuciones previas se presentaron problemas
de automatización relacionados con navegación y sincronización.
Después de ajustar las esperas, la prueba finalizó correctamente.


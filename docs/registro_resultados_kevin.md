# Registro de resultados — Kevin Burgos · Odoo 18

**Ejecución real:** 25 de noviembre de 2026, zona local UTC−05.
Funcionales iniciadas a las 00:33:44; duración de pytest 146.49 s.
Unitarias: seis pruebas, duración de la corrida final 0.496 s, salida 0.
Ambiente: Windows 11, Python 3.12.10, pytest 9.2.0, Selenium 4.54.0,
Chrome headless 1600×1000; Odoo Docker 18, stock 18.0.1.1, base calidad.

En la tabla, el nombre del escenario coincide exactamente con el directorio
en `evidencia/`. Cada escenario contiene `01_entrada.png` y una segunda captura
de persistencia o rechazo. Las duraciones incluyen preparación y cierre.

| Caso | Fecha/hora local | Estado | Resultado observado | Evidencia | NC asociada | Ambiente / versión |
|---|---|---|---|---|---|---|
| FC-13 único | 2026-11-25 00:33–00:36 | PASS | Código único persistido, 11.217 s | `test_FC13_codigo_barras[unico]/` | Ninguna | Odoo 18 / calidad |
| FC-13 vacío | ídem | PASS | Código eliminado, 11.439 s | `test_FC13_codigo_barras[vacio]/` | Ninguna | ídem |
| FC-13 duplicado | ídem | PASS | Diálogo identifica el código; BD no lo guarda, 10.531 s | `test_FC13_codigo_barras[duplicado]/` | Ninguna | ídem |
| FC-14 negativo | ídem | PASS | −0.01 persistido, 11.253 s | `test_FC14_peso[negativo]/` | Ninguna | ídem |
| FC-14 cero | ídem | PASS | 0 persistido, 10.258 s | `test_FC14_peso[cero]/` | Ninguna | ídem |
| FC-14 mínimo positivo | ídem | PASS | 0.01 persistido, 10.340 s | `test_FC14_peso[minimo_positivo]/` | Ninguna | ídem |
| FC-14 positivo | ídem | PASS | 1 persistido, 10.109 s | `test_FC14_peso[positivo]/` | Ninguna | ídem |
| FC-15 negativo | ídem | PASS | −0.01 persistido, 9.979 s | `test_FC15_volumen[negativo]/` | Ninguna | ídem |
| FC-15 cero | ídem | PASS | 0 persistido, 10.282 s | `test_FC15_volumen[cero]/` | Ninguna | ídem |
| FC-15 mínimo positivo | ídem | PASS | 0.01 persistido, 11.021 s | `test_FC15_volumen[minimo_positivo]/` | Ninguna | ídem |
| FC-15 positivo | ídem | PASS | 1 persistido, 10.553 s | `test_FC15_volumen[positivo]/` | Ninguna | ídem |
| FC-16 vacío | ídem | PASS | Nombre inválido; BD conserva original, 9.409 s | `test_FC16_nombre_ubicacion[vacio]/` | Ninguna | ídem |
| FC-16 uno | ídem | PASS | K persistido, 9.851 s | `test_FC16_nombre_ubicacion[uno]/` | Ninguna | ídem |
| FC-16 dos | ídem | PASS | KB persistido, 10.176 s | `test_FC16_nombre_ubicacion[dos]/` | Ninguna | ídem |
| UK01 | 2026-11-25, antes de funcionales | PASS | None para tracking none | `test_unit_kevin/salida.txt` | Ninguna | Odoo 18 / TransactionCase |
| UK02 | ídem | PASS | None para inventory | ídem | Ninguna | ídem |
| UK03 | ídem | PASS | None para serial sin lote | ídem | Ninguna | ídem |
| UK04 | ídem | PASS | −1/0/1 admitidos | ídem | Ninguna | ídem |
| UK05 | ídem | PASS | −2/2 lanzan ValidationError | ídem | Ninguna | ídem |
| UK06 | ídem | PASS | Recordset vacío devuelve None | ídem | Ninguna | ídem |

La salida unittest no incluye hora individual: no se inventan marcas por caso.
La marca exacta de inicio funcional y tiempos están en
`evidencia/resultados_kevin.xml`; el HTML completo en `evidencia/reporte_kevin.html`.

## Cobertura observada

`evidencia/test_unit_kevin/cobertura.json`:

- Sentencias: 610, 611, 612, 613, 618, 623, 624, 625 (8/8).
- Arcos: 611→612, 611→614, 623→salida, 623→624, 624→623, 624→625 (6/6).
- Filtro lambda: alternativas justificadas por UK01/02/03/04; no porcentaje
  automático de condiciones ni MC/DC.

## No conformidades e incidencias de automatización

**No hay NC de producto confirmadas.** El rechazo de duplicado/nombre vacío y
las excepciones por serial con magnitud 2 son resultados esperados, no fallos.
El peso/volumen negativo es admitido por esta configuración y no se clasificó
como NC sin una especificación que prohíba ese valor.

Incidencias corregidas antes de cerrar:

1. El primer contador de arcos suponía 611→613; Python evalúa primero el elemento
   de lista en 614. Las seis pruebas ya pasaban, pero el ejecutor salía 1 por
   esta medición. Se corrigió el contador y se reejecutó: seis pruebas PASS,
   ocho sentencias y seis arcos cubiertos, salida 0.
2. La exploración inicial buscaba un botón New al cambiar desde un formulario
   nuevo sin guardar. Se descartó esa navegación para las pruebas y se usan
   registros propios preparados por API y abiertos por acción/ID. No es NC.
3. La consola no tenía Python real ni venv heredado: se instaló Python 3.12,
   se creó `.venv` y se instalaron dependencias.

No se cambió ningún resultado esperado después de observar un fallo del producto.
La primera corrida completa de las 14 funcionales aprobó todos los escenarios.

r"""Pruebas unitarias de Daniel - Odoo 18 Inventario (Entrega 2).

Metodos propios, distintos de los de Heidy, Ruben y Kevin:
- M1: stock.quant._compute_inventory_diff_quantity
- M2: stock.warehouse.orderpoint._compute_qty_to_order_computed

Se usan los metodos originales del ORM, sin mocks ni cambios de Odoo.
Cada caso usa TransactionCase: no persiste los datos de prueba.

Desde la raiz del worktree odoo-calidad-unitarias (PowerShell):
  Get-Content -Raw -Encoding UTF8 .\unit\test_daniel.py | docker exec -i odoo-calidad-odoo-1 /entrypoint.sh odoo shell -d calidad --no-http --log-level=error
"""

import ast
import inspect
import sys
import textwrap
import types
import unittest
from uuid import uuid4

from odoo.addons.stock.models.stock_orderpoint import StockWarehouseOrderpoint
from odoo.addons.stock.models.stock_quant import StockQuant
from odoo.tests.common import TransactionCase


class TestDanielDiferenciaConteo(TransactionCase):
    """M1: diferencia = cantidad contada - cantidad teorica (stock.quant)."""

    test_tags = {"daniel", "post_install"}
    test_module = "stock"
    test_class = "TestDanielDiferenciaConteo"
    test_sequence = 0

    def _quant(self, teorica, contada, con_lote=False):
        almacen = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        self.assertTrue(almacen, "Se requiere un almacen configurado para la compania")
        producto = self.env["product.product"].create({
            "name": f"UD-DAN-QUANT-{uuid4().hex[:10]}",
            "type": "consu",
            "is_storable": True,
            "tracking": "lot" if con_lote else "none",
        })
        datos = {
            "product_id": producto.id,
            "location_id": almacen.lot_stock_id.id,
            "quantity": teorica,
            "inventory_quantity": contada,
        }
        if con_lote:
            lote = self.env["stock.lot"].create({
                "name": f"UD-DAN-LOTE-{uuid4().hex[:10]}",
                "product_id": producto.id,
                "company_id": self.env.company.id,
            })
            datos["lot_id"] = lote.id
        # new(): registro ORM en memoria; no crea movimientos de inventario.
        return self.env["stock.quant"].new(datos)

    def test_ud101_diferencia_positiva(self):
        """Cantidad 5, conteo 8 => +3."""
        quant = self._quant(5, 8)
        quant._compute_inventory_diff_quantity()
        self.assertAlmostEqual(quant.inventory_diff_quantity, 3.0)

    def test_ud102_diferencia_cero(self):
        """Cantidad 5, conteo 5 => 0."""
        quant = self._quant(5, 5)
        quant._compute_inventory_diff_quantity()
        self.assertAlmostEqual(quant.inventory_diff_quantity, 0.0)

    def test_ud103_diferencia_negativa(self):
        """Cantidad 8, conteo 3 => -5."""
        quant = self._quant(8, 3)
        quant._compute_inventory_diff_quantity()
        self.assertAlmostEqual(quant.inventory_diff_quantity, -5.0)

    def test_ud104_calculo_independiente_con_lote(self):
        """Con lote, cantidad 6 y conteo 2 => -4."""
        quant = self._quant(6, 2, con_lote=True)
        quant._compute_inventory_diff_quantity()
        self.assertAlmostEqual(quant.inventory_diff_quantity, -4.0)

    def test_ud105_varios_quants_en_lote(self):
        """Bucle con dos registros: +3 y -3."""
        quants = self._quant(2, 5) | self._quant(9, 6)
        quants._compute_inventory_diff_quantity()
        self.assertEqual(len(quants), 2)
        self.assertEqual([q.inventory_diff_quantity for q in quants], [3.0, -3.0])

    def test_ud106_recordset_vacio(self):
        """Bucle de cero iteraciones no genera datos ni excepciones."""
        quants = self.env["stock.quant"].browse([])
        quants._compute_inventory_diff_quantity()
        self.assertEqual(len(quants), 0)


class TestDanielCalculoReabastecimiento(TransactionCase):
    """M2: calculo previo de reposicion (NO seleccion manual vs computed)."""

    test_tags = {"daniel", "post_install"}
    test_module = "stock"
    test_class = "TestDanielCalculoReabastecimiento"
    test_sequence = 0

    def _datos(self, minimo, maximo, multiplo=1):
        almacen = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        self.assertTrue(almacen, "Se requiere un almacen configurado para la compania")
        producto = self.env["product.product"].create({
            "name": f"UD-DAN-REPOSICION-{uuid4().hex[:10]}",
            "type": "consu",
            "is_storable": True,
        })
        return {
            "product_id": producto.id,
            "location_id": almacen.lot_stock_id.id,
            "warehouse_id": almacen.id,
            "company_id": self.env.company.id,
            "product_min_qty": minimo,
            "product_max_qty": maximo,
            "qty_multiple": multiplo,
            "trigger": "manual",
        }

    def _regla(self, minimo, maximo, multiplo=1):
        valores = self._datos(minimo, maximo, multiplo)
        regla = self.env["stock.warehouse.orderpoint"].create(valores)
        # Producto propio y sin movimientos: el pronostico debe ser cero.
        self.assertAlmostEqual(regla.qty_forecast, 0.0)
        self.assertAlmostEqual(regla.product_min_qty, minimo)
        self.assertAlmostEqual(regla.product_max_qty, maximo)
        return regla

    def test_ud201_pronostico_inferior_al_minimo(self):
        """Rama verdadera: 0 < minimo 5, repone hasta maximo 10."""
        regla = self._regla(5, 10)
        regla._compute_qty_to_order_computed()
        self.assertAlmostEqual(regla.qty_to_order_computed, 10.0)

    def test_ud202_pronostico_igual_al_minimo(self):
        """Rama falsa: pronostico 0 y minimo 0 => no repone."""
        regla = self._regla(0, 0)
        regla._compute_qty_to_order_computed()
        self.assertAlmostEqual(regla.qty_to_order_computed, 0.0)

    def test_ud203_minimo_igual_maximo(self):
        """Si minimo=maximo=5 y pronostico 0, sugiere 5."""
        regla = self._regla(5, 5)
        regla._compute_qty_to_order_computed()
        self.assertAlmostEqual(regla.qty_to_order_computed, 5.0)

    def test_ud204_multiplo_de_reposicion(self):
        """Min 5, max 10 y multiplo 3: sugiere 9 al ajustar hacia abajo."""
        regla = self._regla(5, 10, multiplo=3)
        regla._compute_qty_to_order_computed()
        self.assertAlmostEqual(regla.qty_to_order_computed, 9.0)

    def test_ud205_reglas_mixtas_en_lote(self):
        """Una regla requiere pedido (10); otra no (0)."""
        reglas = self._regla(5, 10) | self._regla(0, 0)
        reglas._compute_qty_to_order_computed()
        self.assertEqual(
            [regla.qty_to_order_computed for regla in reglas], [10.0, 0.0]
        )

    def test_ud206_regla_no_guardada(self):
        """Una regla transitoria con NewId no se considera para pedido."""
        valores = self._datos(5, 10)
        regla = self.env["stock.warehouse.orderpoint"].new(valores)
        self.assertFalse(bool(regla.id))
        regla._compute_qty_to_order_computed()
        self.assertAlmostEqual(regla.qty_to_order_computed, 0.0)

    def test_ud207_recordset_vacio(self):
        """Bucle de cero iteraciones, sin pedidos calculados."""
        reglas = self.env["stock.warehouse.orderpoint"].browse([])
        reglas._compute_qty_to_order_computed()
        self.assertEqual(len(reglas), 0)


def _codigos_de_metodo(metodo):
    """Codigo propio del metodo y funciones internas (no helpers ajenos)."""
    pendientes = [metodo.__code__]
    while pendientes:
        codigo = pendientes.pop()
        yield codigo
        pendientes.extend(x for x in codigo.co_consts if isinstance(x, types.CodeType))


def _lineas_de_sentencia(metodo):
    """Denominador: instrucciones AST de ambos metodos, sin docstrings."""
    fuente, inicial = inspect.getsourcelines(metodo)
    raiz = ast.parse(textwrap.dedent("".join(fuente)))
    resultado = set()
    for nodo in ast.walk(raiz):
        if not isinstance(nodo, ast.stmt) or isinstance(
            nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Pass)
        ):
            continue
        if isinstance(nodo, ast.Expr) and isinstance(nodo.value, ast.Constant) \
                and isinstance(nodo.value.value, str):
            continue
        resultado.add(inicial + nodo.lineno - 1)
    return resultado


def ejecutar_pruebas_daniel():
    """Ejecuta xUnit y reporta lineas recorridas, sin afirmar cobertura de Odoo entero."""
    metodos = [
        StockQuant._compute_inventory_diff_quantity,
        StockWarehouseOrderpoint._compute_qty_to_order_computed,
    ]
    codigos = {code for fn in metodos for code in _codigos_de_metodo(fn)}
    ejecutadas = set()

    def observar(frame, evento, arg):
        if frame.f_code in codigos:
            if evento == "line":
                ejecutadas.add(frame.f_lineno)
            return observar
        return None

    suite = unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(TestDanielDiferenciaConteo),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestDanielCalculoReabastecimiento),
    ])
    print("DANIEL | Odoo 18 | 2 metodos originales | 13 casos", flush=True)
    anterior = sys.gettrace()
    try:
        sys.settrace(observar)
        resultado = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    finally:
        sys.settrace(anterior)

    print("\nCOBERTURA DE SENTENCIAS (solo los 2 metodos elegidos)")
    completa = True
    for metodo in metodos:
        lineas = _lineas_de_sentencia(metodo)
        cubiertas = lineas & ejecutadas
        faltantes = lineas - cubiertas
        print(
            f"{metodo.__qualname__}: {len(cubiertas)}/{len(lineas)} "
            f"({100 * len(cubiertas)/len(lineas):.1f}%); "
            f"fuente={inspect.getsourcefile(metodo)}",
            flush=True,
        )
        if faltantes:
            completa = False
            print(f"  Lineas no observadas: {sorted(faltantes)}")

    print("DECISIONES DISENADAS (validacion por escenarios, no medidor automatico)")
    print("  M1: bucle cero/uno/varios; diferencias positiva/cero/negativa.")
    print("  M2: id transitorio vs guardado; pronostico < minimo vs igual;")
    print("      bucle cero/varios; reposicion con/sin multiplo.")
    print(
        f"RESULTADO: {resultado.testsRun} pruebas; "
        f"{len(resultado.failures)} fallidas, "
        f"{len(resultado.errors)} errores, "
        f"{len(resultado.skipped)} omitidas.",
        flush=True,
    )
    return resultado.wasSuccessful() and completa


if __name__ == "__main__":
    raise SystemExit(0 if ejecutar_pruebas_daniel() else 1)

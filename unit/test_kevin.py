"""Kevin Burgos: seis casos del metodo real stock.quant.check_quantity.

Get-Content -Raw unit/test_kevin.py | docker compose exec -T odoo /entrypoint.sh odoo shell -d calidad --no-http --log-level=error
"""
import ast
import inspect
import json
import sys
import textwrap
import unittest

from odoo.addons.stock.models.stock_quant import StockQuant
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestKevinCheckQuantity(TransactionCase):
    test_tags = {'kevin', 'post_install'}
    test_module = 'stock'
    test_class = 'TestKevinCheckQuantity'
    test_sequence = 0

    def setUp(self):
        super().setUp()
        self.Quant = self.env['stock.quant']
        self.location = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1).lot_stock_id

    def quant(self, quantity, tracking='serial', usage=None, lot=True):
        product = self.env['product.product'].create({
            'name': 'KEVIN UK serial', 'type': 'consu',
            'is_storable': True, 'tracking': tracking,
        })
        location = self.location
        if usage:
            location = self.env['stock.location'].create({
                'name': 'KEVIN UK inventory', 'usage': usage,
                'company_id': self.env.company.id,
            })
        serial = self.env['stock.lot']
        if lot:
            serial = serial.create({
                'name': 'KEVIN UK SN', 'product_id': product.id,
                'company_id': self.env.company.id,
            })
        return self.Quant.create({
            'product_id': product.id, 'location_id': location.id,
            'lot_id': serial.id, 'quantity': quantity,
        })

    def test_UK01_no_serial(self):
        """Filtro falso en primer operando; dos unidades sin seguimiento."""
        q = self.quant(2, tracking='none', lot=False)
        self.assertIsNone(q.check_quantity())
        self.assertEqual(q.quantity, 2)

    def test_UK02_inventory_excluido(self):
        """Filtro falso en segundo operando: contrapartida de inventario."""
        q = self.quant(2, usage='inventory')
        self.assertIsNone(q.check_quantity())
        self.assertEqual(q.quantity, 2)

    def test_UK03_sin_lote(self):
        """Filtro falso en tercer operando."""
        q = self.quant(2, lot=False)
        self.assertIsNone(q.check_quantity())
        self.assertFalse(q.lot_id)

    def test_UK04_limites_validos(self):
        """Camino normal: abs(-1), 0 y 1 no superan uno; varias iteraciones."""
        quants = self.quant(-1) | self.quant(0) | self.quant(1)
        self.assertIsNone(quants.check_quantity())
        self.assertEqual(sorted(quants.mapped('quantity')), [-1, 0, 1])

    def test_UK05_limites_invalidos(self):
        """Camino de excepcion: abs(-2) y 2 superan uno."""
        for quantity in (-2, 2):
            with self.subTest(quantity=quantity):
                q = self.quant(quantity)
                with self.assertRaises(ValidationError):
                    q.check_quantity()
                self.assertEqual(q.quantity, quantity)

    def test_UK06_recordset_vacio(self):
        """Sin evaluaciones de filtro, salida temprana."""
        self.assertIsNone(self.Quant.browse([]).check_quantity())


def ejecutar_pruebas_kevin():
    method = StockQuant.check_quantity
    source, start = inspect.getsourcelines(method)
    print('FUENTE REAL:', inspect.getsourcefile(method), start)
    print(''.join(source))
    executed, arcs = set(), set()
    previous = {}

    def trace(frame, event, arg):
        if frame.f_code is not method.__code__:
            return None
        key = id(frame)
        if event == 'call':
            previous[key] = -1
        elif event == 'line':
            executed.add(frame.f_lineno)
            arcs.add((previous.get(key, -1), frame.f_lineno))
            previous[key] = frame.f_lineno
        elif event == 'return':
            arcs.add((previous.pop(key, -1), -1))
        return trace

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestKevinCheckQuantity)
    before = sys.gettrace()
    try:
        sys.settrace(trace)
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    finally:
        sys.settrace(before)
    tree = ast.parse(textwrap.dedent(''.join(source)))
    statements = {start + node.lineno - 1 for node in ast.walk(tree)
                  if isinstance(node, ast.stmt) and not isinstance(node, ast.FunctionDef)}
    branch_arcs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For)):
            line = start + node.lineno - 1
            branch_arcs.add((line, start + node.body[0].lineno - 1))
            following = start + node.end_lineno if node.end_lineno < tree.body[0].end_lineno else -1
            if isinstance(node, ast.If) and node.end_lineno == tree.body[0].end_lineno:
                following = start + next(n.lineno for n in ast.walk(tree) if isinstance(n, ast.For)) - 1
            if isinstance(node, ast.If) and isinstance(node.body[0], ast.Return):
                # Python evaluates the first list element before the multiline assignment.
                domain = next(n for n in ast.walk(tree) if isinstance(n, ast.Assign)
                              and any(isinstance(t, ast.Name) and t.id == 'domain' for t in n.targets))
                following = start + domain.value.elts[0].lineno - 1
            branch_arcs.add((line, following))
    # The only nonterminal false edge is the early-return if -> domain assignment.
    summary = {
        'tests': result.testsRun, 'failures': len(result.failures),
        'errors': len(result.errors), 'skipped': len(result.skipped),
        'statement_lines': sorted(statements),
        'covered_statement_lines': sorted(statements & executed),
        'branch_arcs': sorted(branch_arcs),
        'covered_branch_arcs': sorted(branch_arcs & arcs),
        'observed_arcs': sorted(arcs),
        'metric': 'lineas de sentencias AST y arcos de if/for; lambda por casos, no por arcos',
    }
    print('KEVIN_RESULT_JSON=' + json.dumps(summary))
    return result.wasSuccessful() and statements <= executed and branch_arcs <= arcs


if __name__ == '__main__':
    raise SystemExit(0 if ejecutar_pruebas_kevin() else 1)

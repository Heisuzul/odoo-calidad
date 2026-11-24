"""Heidy: dos métodos reales de Odoo 18, sin mocks ni cambios al producto.

Ejecutar desde PowerShell en la raíz del proyecto:
Get-Content -Raw unit/test_heidy.py | docker compose exec -T odoo /entrypoint.sh odoo shell -d calidad --no-http --log-level=error

Se utiliza TransactionCase: cada caso dispone de un savepoint y todos los
cambios de base de datos se revierten. No requiere pytest dentro de Docker.
La salida y la cobertura se imprimen en consola; no se escriben reportes.
"""
import ast
import inspect
import sys
import textwrap
import unittest

from odoo.addons.product.models.product_category import ProductCategory
from odoo.addons.stock.models.stock_orderpoint import StockWarehouseOrderpoint
from odoo.tests.common import TransactionCase


class TestHeidyNombreCategoria(TransactionCase):
    """Método 1: ProductCategory._compute_complete_name, modelo product.category.

    Fuente instalada: odoo/addons/product/models/product_category.py:29.
    Sentencias: iterar, evaluar parent_id, asignar la ruta con padre o el nombre
    sin padre. Decisión: parent_id verdadero/falso; bucle con cero/uno/varios
    registros. Se invoca el método original sobre registros ORM reales.
    """

    # Metadatos explícitos: el archivo se ejecuta fuera de un addon instalable.
    test_tags = {'heidy', 'post_install'}
    test_module = 'product'
    test_class = 'TestHeidyNombreCategoria'
    test_sequence = 0

    def test_uh01_categoria_sin_padre(self):
        """Rama falsa: sin padre -> el nombre completo es el nombre propio."""
        categoria = self.env['product.category'].create({'name': 'UH01 Ropa'})
        categoria._compute_complete_name()
        self.assertEqual(categoria.complete_name, 'UH01 Ropa')

    def test_uh02_categoria_con_padre(self):
        """Rama verdadera: padre e hijo -> concatenación con separador ' / '."""
        padre = self.env['product.category'].create({'name': 'UH02 Hogar'})
        hija = self.env['product.category'].create({
            'name': 'Mesas', 'parent_id': padre.id,
        })
        hija._compute_complete_name()
        self.assertEqual(hija.complete_name, 'UH02 Hogar / Mesas')

    def test_uh03_categoria_multinivel(self):
        """La sentencia con padre usa su complete_name, no sólo su name."""
        raiz = self.env['product.category'].create({'name': 'UH03 Inventario'})
        padre = self.env['product.category'].create({
            'name': 'Ropa', 'parent_id': raiz.id,
        })
        hija = self.env['product.category'].create({
            'name': 'Camisas', 'parent_id': padre.id,
        })
        hija._compute_complete_name()
        self.assertEqual(hija.complete_name, 'UH03 Inventario / Ropa / Camisas')

    def test_uh04_categorias_en_lote(self):
        """Sentencias y ramas: varias iteraciones, con y sin padre en un lote."""
        raiz = self.env['product.category'].create({'name': 'UH04 Productos'})
        hija = self.env['product.category'].create({
            'name': 'Bienes', 'parent_id': raiz.id,
        })
        categorias = raiz | hija
        categorias._compute_complete_name()
        self.assertEqual(categorias.mapped('complete_name'),
                         ['UH04 Productos', 'UH04 Productos / Bienes'])

    def test_uh05_categorias_vacias(self):
        """Bucle sin iteraciones: el recordset vacío se conserva vacío."""
        categorias = self.env['product.category'].browse([])
        categorias._compute_complete_name()
        self.assertEqual(categorias.mapped('complete_name'), [])


class TestHeidyCantidadAPedir(TransactionCase):
    """Método 2: StockWarehouseOrderpoint._compute_qty_to_order.

    Modelo stock.warehouse.orderpoint; fuente instalada:
    odoo/addons/stock/models/stock_orderpoint.py:320.
    Sentencias: iterar y asignar qty_to_order. Decisión ternaria: si manual es
    distinto de cero, usar manual; si es cero, usar computed. Un negativo es
    verdadero en Python: este método selecciona el valor, no lo limita a cero.

    Entradas mediante new() del ORM real: registros en memoria, incluidos los
    valores del campo computed que recibe este método. No se simula ni se
    sustituye ningún método. El cálculo previo de computed queda fuera del
    alcance de estas pruebas de selección entre manual y calculado.
    """

    test_tags = {'heidy', 'post_install'}
    test_module = 'stock'
    test_class = 'TestHeidyCantidadAPedir'
    test_sequence = 0

    def _regla(self, manual, calculada):
        return self.env['stock.warehouse.orderpoint'].new({
            'qty_to_order_manual': manual,
            'qty_to_order_computed': calculada,
        })

    def test_uh06_cantidad_manual_positiva(self):
        """Rama verdadera: manual=5, calculada=12 -> 5."""
        regla = self._regla(5.0, 12.0)
        regla._compute_qty_to_order()
        self.assertEqual(regla.qty_to_order, 5.0)

    def test_uh07_cantidad_manual_negativa(self):
        """Rama verdadera: manual=-2, calculada=12 -> -2, no 12 ni cero."""
        regla = self._regla(-2.0, 12.0)
        regla._compute_qty_to_order()
        self.assertEqual(regla.qty_to_order, -2.0)

    def test_uh08_manual_cero_usa_calculada(self):
        """Rama falsa: manual=0, calculada=8 -> 8."""
        regla = self._regla(0.0, 8.0)
        regla._compute_qty_to_order()
        self.assertEqual(regla.qty_to_order, 8.0)

    def test_uh09_calculada_negativa(self):
        """Rama falsa: manual=0, calculada=-3 -> -3 sin alterar el valor."""
        regla = self._regla(0.0, -3.0)
        regla._compute_qty_to_order()
        self.assertEqual(regla.qty_to_order, -3.0)

    def test_uh10_ambas_cantidades_cero(self):
        """Rama falsa: manual=0, calculada=0 -> 0."""
        regla = self._regla(0.0, 0.0)
        regla._compute_qty_to_order()
        self.assertEqual(regla.qty_to_order, 0.0)

    def test_uh11_reglas_en_lote(self):
        """Sentencias y ambas ramas en un lote: (4,9), (0,7) -> [4,7]."""
        reglas = self._regla(4.0, 9.0) | self._regla(0.0, 7.0)
        reglas._compute_qty_to_order()
        self.assertEqual(reglas.mapped('qty_to_order'), [4.0, 7.0])

    def test_uh12_reglas_vacias(self):
        """Bucle sin iteraciones: no asigna cantidades ni crea reglas."""
        reglas = self.env['stock.warehouse.orderpoint'].browse([])
        reglas._compute_qty_to_order()
        self.assertEqual(reglas.mapped('qty_to_order'), [])


def ejecutar_pruebas_heidy():
    """Ejecuta sólo estas clases y mide líneas de sentencias del código real.

    sys.settrace observa la ejecución, sin reemplazar la lógica de Odoo.
    La cobertura de decisiones se comprueba con los casos de ambas ramas;
    la cifra impresa mide sentencias, no cobertura de todo el módulo.
    """
    metodos = [ProductCategory._compute_complete_name,
               StockWarehouseOrderpoint._compute_qty_to_order]
    ejecutadas = {metodo.__code__: set() for metodo in metodos}

    def observar(frame, evento, arg):
        if frame.f_code in ejecutadas:
            if evento == 'line':
                ejecutadas[frame.f_code].add(frame.f_lineno)
            return observar
        return None

    suite = unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(TestHeidyNombreCategoria),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestHeidyCantidadAPedir),
    ])
    print('HEIDY | Odoo 18 | 2 metodos originales | 12 casos', flush=True)
    anterior = sys.gettrace()
    try:
        sys.settrace(observar)
        resultado = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    finally:
        sys.settrace(anterior)

    cobertura_completa = True
    print('\nCOBERTURA DE SENTENCIAS (solo los 2 metodos seleccionados)')
    for metodo in metodos:
        fuente, inicio = inspect.getsourcelines(metodo)
        arbol = ast.parse(textwrap.dedent(''.join(fuente)))
        sentencias = {inicio + nodo.lineno - 1 for nodo in ast.walk(arbol)
                      if isinstance(nodo, ast.stmt)
                      and not isinstance(nodo, ast.FunctionDef)}
        cubiertas = sentencias & ejecutadas[metodo.__code__]
        print(f'{metodo.__qualname__}: {len(cubiertas)}/{len(sentencias)}; '
              f'fuente={inspect.getsourcefile(metodo)}:{inicio}')
        if sentencias - cubiertas:
            cobertura_completa = False
            print(f'  Lineas sin ejecutar: {sorted(sentencias - cubiertas)}')
    print(f'RESULTADO: {resultado.testsRun} ejecutadas, '
          f'{len(resultado.failures)} fallidas, {len(resultado.errors)} errores, '
          f'{len(resultado.skipped)} omitidas', flush=True)
    return resultado.wasSuccessful() and cobertura_completa


if __name__ == '__main__':
    raise SystemExit(0 if ejecutar_pruebas_heidy() else 1)

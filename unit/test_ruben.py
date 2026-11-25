"""Rubén Darío Saa: dos métodos reales de Odoo 18 (modelo stock.quant), sin mocks ni cambios al producto.

Ejecutar desde PowerShell en la raíz del proyecto:
Get-Content -Raw unit/test_ruben.py | docker compose exec -T odoo /entrypoint.sh odoo shell -d calidad --no-http --log-level=error

Se utiliza TransactionCase: cada caso dispone de un savepoint y todos los
cambios de base de datos se revierten. No requiere pytest dentro de Docker.
La salida y la cobertura se imprimen en consola; no se escriben reportes.

Técnica de caja blanca: cobertura de decisiones (DEC), con una prueba para el
resultado verdadero (V) y falso (F) de cada decisión (D1, D2, ...), y caminos
básicos (CB). La complejidad ciclomática V(G) = decisiones + 1 se calculó con un
script propio sobre el código fuente instalado.
"""
import ast
import inspect
import sys
import textwrap
import unittest
from datetime import datetime

from odoo.addons.stock.models.stock_quant import StockQuant
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class BaseRuben(TransactionCase):
    """Base común: almacén, ubicaciones y ayudas para crear productos, lotes y existencias."""

    test_tags = {'ruben', 'post_install'}
    test_module = 'stock'
    test_sequence = 0

    def setUp(self):
        super().setUp()
        self.Quant = self.env['stock.quant']
        self.almacen = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1)
        self.ubic = self.almacen.lot_stock_id
        self.ubic_clientes = self.env.ref('stock.stock_location_customers')
        self.ubic_proveedores = self.env.ref('stock.stock_location_suppliers')

    def crear_producto(self, nombre='UR producto', tracking='none'):
        return self.env['product.product'].create({
            'name': nombre, 'type': 'consu', 'is_storable': True, 'tracking': tracking})

    def crear_lote(self, producto, nombre='UR-L1'):
        return self.env['stock.lot'].create({
            'name': nombre, 'product_id': producto.id, 'company_id': self.env.company.id})

    def poner(self, producto, cantidad, lote=None, ubic=None):
        """Suma (o resta) existencias usando el método de la capa de quants."""
        return self.Quant._update_available_quantity(producto, ubic or self.ubic, cantidad, lot_id=lote)

    def reservar(self, producto, cantidad, lote=None):
        return self.Quant._update_available_quantity(
            producto, self.ubic, reserved_quantity=cantidad, lot_id=lote)

    def quants(self, producto, ubic=None):
        return self.Quant.search([('product_id', '=', producto.id),
                                  ('location_id', '=', (ubic or self.ubic).id)])


class TestRubenCantidadDisponible(BaseRuben):
    """Método 1: StockQuant._get_available_quantity, modelo stock.quant. V(G) = 13.

    Decisiones: D1 tracking == 'none'; D2 allow_negative (sin lote); D3 disponible >= 0 (sin lote);
    D4 bucle for quant in quants; D5 not lot and strict and lot_id; D6 not quant.lot_id;
    D7 allow_negative (con lote); D8 disponible > 0 en la suma (con lote).
    Se invoca el método original sobre registros ORM reales; no se simula ninguna parte.
    """

    test_class = 'TestRubenCantidadDisponible'

    def test_UR101_sin_lote_resta_reservado(self):
        """DEC D1-V, D2-F, D3-V | 10 en stock y 3 reservadas -> 7."""
        p = self.crear_producto()
        self.poner(p, 10)
        self.reservar(p, 3)
        self.assertEqual(self.Quant._get_available_quantity(p, self.ubic), 7.0)

    def test_UR102_sin_lote_negativo_devuelve_cero(self):
        """DEC D3-F | existencia -5 sin permitir negativos -> 0."""
        p = self.crear_producto()
        self.poner(p, -5)
        self.assertEqual(self.Quant._get_available_quantity(p, self.ubic), 0.0)

    def test_UR103_sin_lote_negativo_permitido(self):
        """DEC D2-V | existencia -5 con allow_negative -> -5."""
        p = self.crear_producto()
        self.poner(p, -5)
        self.assertEqual(self.Quant._get_available_quantity(p, self.ubic, allow_negative=True), -5.0)

    def test_UR104_sin_existencias_devuelve_cero(self):
        """DEC D4 sin iteraciones | no hay quants -> 0."""
        p = self.crear_producto()
        self.assertEqual(self.Quant._get_available_quantity(p, self.ubic), 0.0)

    def test_UR105_con_lote_resta_reservado(self):
        """DEC D1-F, D6-F, D7-F, D8-V | lote con 10 y 4 reservadas -> 6."""
        p = self.crear_producto(tracking='lot')
        lote = self.crear_lote(p)
        self.poner(p, 10, lote)
        self.reservar(p, 4, lote)
        self.assertEqual(self.Quant._get_available_quantity(p, self.ubic, lot_id=lote), 6.0)

    def test_UR106_con_lote_negativo_no_se_suma(self):
        """DEC D8-F | lote con -3 sin permitir negativos -> 0."""
        p = self.crear_producto(tracking='lot')
        lote = self.crear_lote(p)
        self.poner(p, -3, lote)
        self.assertEqual(self.Quant._get_available_quantity(p, self.ubic, lot_id=lote), 0.0)

    def test_UR107_con_lote_negativo_permitido(self):
        """DEC D7-V | lote con -3 y allow_negative -> -3."""
        p = self.crear_producto(tracking='lot')
        lote = self.crear_lote(p)
        self.poner(p, -3, lote)
        self.assertEqual(self.Quant._get_available_quantity(p, self.ubic, lot_id=lote, allow_negative=True), -3.0)

    def test_UR108_producto_con_lote_pero_quant_sin_lote(self):
        """DEC D6-V | producto rastreado con 5 sin lote (cubeta 'untracked') -> 5."""
        p = self.crear_producto(tracking='lot')
        self.poner(p, 5)
        self.assertEqual(self.Quant._get_available_quantity(p, self.ubic), 5.0)

    def test_UR109_modo_estricto_con_lote(self):
        """DEC D5-F (operandos strict y lot_id verdaderos, quant con lote) | lote con 10, strict -> 10."""
        p = self.crear_producto(tracking='lot')
        lote = self.crear_lote(p)
        self.poner(p, 10, lote)
        self.assertEqual(self.Quant._get_available_quantity(p, self.ubic, lot_id=lote, strict=True), 10.0)


class TestRubenActualizarCantidad(BaseRuben):
    """Método 2: StockQuant._update_available_quantity, modelo stock.quant. V(G) = 22.

    Decisiones: D1 sin cantidad ni reserva (error); D2 lote y D2b cantidad > 0; D3 ubicación que omite
    reservas; D4 in_date explícito; D5 hay fechas de entrada; D6 hay quants; D7 quant bloqueado por
    otro proceso; D8 existe quant (actualiza); D9 quantity; D10 reserved (actualiza); D11 quantity;
    D12 reserved (crea). Se invoca el método original sobre registros ORM reales.
    """

    test_class = 'TestRubenActualizarCantidad'

    def test_UR201_sin_cantidad_ni_reserva_lanza_error(self):
        """DEC D1-V | sin quantity ni reserved_quantity (o ambos 0) -> ValidationError."""
        p = self.crear_producto()
        with self.assertRaises(ValidationError):
            self.Quant._update_available_quantity(p, self.ubic)
        with self.assertRaises(ValidationError):
            self.Quant._update_available_quantity(p, self.ubic, quantity=0, reserved_quantity=0)

    def test_UR202_crea_quant_nuevo(self):
        """DEC D1-F, D2-F, D3-F, D5-F, D6-F, D8-F, D11-V, D12-F | producto sin quants, +10 -> quant nuevo con 10."""
        p = self.crear_producto()
        disponible, fecha = self.Quant._update_available_quantity(p, self.ubic, 10)
        self.assertEqual(disponible, 10.0)
        self.assertTrue(fecha)
        q = self.quants(p)
        self.assertEqual(len(q), 1)
        self.assertEqual(q.quantity, 10.0)

    def test_UR203_actualiza_quant_existente(self):
        """DEC D5-V, D6-V, D7-V, D8-V, D9-V, D10-F | +10, luego +5 -> 15 en un solo quant; luego -20 -> -5."""
        p = self.crear_producto()
        self.poner(p, 10)
        disponible, _ = self.Quant._update_available_quantity(p, self.ubic, 5)
        self.assertEqual(disponible, 15.0)
        self.assertEqual(len(self.quants(p)), 1)
        disponible, _ = self.Quant._update_available_quantity(p, self.ubic, -20)
        self.assertEqual(disponible, -5.0)

    def test_UR204_reserva_y_liberacion_con_piso_en_cero(self):
        """DEC D9-F, D10-V | 10 en stock, reserva +4 -> disponible 6; reserva -10 -> reservado queda en 0 (max(0, ...))."""
        p = self.crear_producto()
        self.poner(p, 10)
        disponible, _ = self.Quant._update_available_quantity(p, self.ubic, reserved_quantity=4)
        self.assertEqual(disponible, 6.0)
        self.assertEqual(self.quants(p).reserved_quantity, 4.0)
        disponible, _ = self.Quant._update_available_quantity(p, self.ubic, reserved_quantity=-10)
        self.assertEqual(self.quants(p).reserved_quantity, 0.0)
        self.assertEqual(disponible, 10.0)

    def test_UR205_reserva_sin_quant_previo(self):
        """DEC D11-F, D12-V | sin quants, reserva 3 -> quant con cantidad 0 y reservado 3; disponible -3."""
        p = self.crear_producto()
        disponible, _ = self.Quant._update_available_quantity(p, self.ubic, reserved_quantity=3)
        q = self.quants(p)
        self.assertEqual(q.quantity, 0.0)
        self.assertEqual(q.reserved_quantity, 3.0)
        self.assertEqual(disponible, -3.0)

    def test_UR206_fecha_de_entrada_explicita(self):
        """DEC D4-V | in_date=2020-01-01 en quant nuevo -> el quant conserva esa fecha."""
        p = self.crear_producto()
        fecha = datetime(2020, 1, 1, 10, 0, 0)
        _, devuelta = self.Quant._update_available_quantity(p, self.ubic, 5, in_date=fecha)
        self.assertEqual(devuelta, fecha)
        self.assertEqual(self.quants(p).in_date, fecha)

    def test_UR207_ubicacion_virtual_omite_reservas(self):
        """DEC D3-V | ubicacion de proveedores (virtual) +5 -> disponible 5."""
        p = self.crear_producto()
        disponible, _ = self.Quant._update_available_quantity(p, self.ubic_proveedores, 5)
        self.assertEqual(disponible, 5.0)

    def test_UR208_con_lote_cantidad_positiva_y_negativa(self):
        """DEC D2-V, D2b-V y D2b-F | lote +5, +3 -> 8; luego -2 -> 6 sobre el quant del lote."""
        p = self.crear_producto(tracking='lot')
        lote = self.crear_lote(p)
        self.poner(p, 5, lote)
        disponible, _ = self.Quant._update_available_quantity(p, self.ubic, 3, lot_id=lote)
        self.assertEqual(disponible, 8.0)
        disponible, _ = self.Quant._update_available_quantity(p, self.ubic, -2, lot_id=lote)
        self.assertEqual(disponible, 6.0)
        self.assertEqual(len(self.quants(p)), 1)


def ejecutar_pruebas_ruben():
    """Ejecuta sólo estas clases y mide líneas de sentencias del código real.

    sys.settrace observa la ejecución, sin reemplazar la lógica de Odoo.
    La cobertura de decisiones se comprueba con los casos V y F de cada decisión
    (ver docstrings); la cifra impresa mide sentencias, no cobertura de todo el módulo.
    """
    metodos = [StockQuant._get_available_quantity, StockQuant._update_available_quantity]
    ejecutadas = {metodo.__code__: set() for metodo in metodos}

    def observar(frame, evento, arg):
        if frame.f_code in ejecutadas:
            if evento == 'line':
                ejecutadas[frame.f_code].add(frame.f_lineno)
            return observar
        return None

    suite = unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(TestRubenCantidadDisponible),
        unittest.defaultTestLoader.loadTestsFromTestCase(TestRubenActualizarCantidad),
    ])
    print('RUBEN | Odoo 18 | 2 metodos originales | 17 casos', flush=True)
    anterior = sys.gettrace()
    try:
        sys.settrace(observar)
        resultado = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    finally:
        sys.settrace(anterior)

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
            print(f'  Lineas sin ejecutar: {sorted(sentencias - cubiertas)}')
    print(f'RESULTADO: {resultado.testsRun} ejecutadas, '
          f'{len(resultado.failures)} fallidas, {len(resultado.errors)} errores, '
          f'{len(resultado.skipped)} omitidas', flush=True)
    return resultado.wasSuccessful()


if __name__ == '__main__':
    raise SystemExit(0 if ejecutar_pruebas_ruben() else 1)

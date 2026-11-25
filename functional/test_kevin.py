"""Kevin Burgos, FC-13..16: PE y valores limite, Odoo 18 Inventario.

Preparar con XML-RPC -> actuar con Selenium -> verificar UI y persistencia.
Las credenciales se reutilizan de conftest; limpieza exclusiva por IDs propios.
"""
from uuid import uuid4
import xmlrpc.client

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from conftest import (BASE_URL, ODOO_DB, ODOO_USER, ODOO_PASS, TIMEOUT,
                      abrir_accion, clic, esperar)


class OdooAPI:
    def __init__(self):
        common = xmlrpc.client.ServerProxy(f'{BASE_URL}/xmlrpc/2/common')
        self.uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
        assert self.uid, 'No se pudo autenticar para preparar datos'
        self.models = xmlrpc.client.ServerProxy(f'{BASE_URL}/xmlrpc/2/object')
        self.created = []

    def call(self, model, method, *args, **kwargs):
        return self.models.execute_kw(
            ODOO_DB, self.uid, ODOO_PASS, model, method, list(args), kwargs)

    def create(self, model, values):
        ident = self.call(model, 'create', values)
        self.created.append((model, ident))
        return ident

    def read(self, model, ident, field):
        return self.call(model, 'read', [ident], fields=[field])[0][field]

    def product(self, **values):
        return self.create('product.template', {
            'name': f'KEVIN-{uuid4().hex}', 'type': 'consu', **values})


@pytest.fixture
def api():
    client = OdooAPI()
    yield client
    for model, ident in reversed(client.created):
        client.call(model, 'unlink', [ident])


def campo(driver, name):
    return esperar(driver, f'.o_field_widget[name="{name}"] input, '
                   f'.o_field_widget[name="{name}"] textarea')


def escribir(driver, name, value):
    element = campo(driver, name)
    element.send_keys(Keys.CONTROL, 'a')
    element.send_keys(Keys.BACKSPACE)
    element.send_keys(str(value))
    element.send_keys(Keys.TAB)


def abrir_registro(driver, action, ident):
    abrir_accion(driver, action)
    driver.get(f'{BASE_URL}/odoo/action-{action}/{ident}')
    esperar(driver, '.o_form_view')


def guardar_numero(driver, api, ident, field, value, shot):
    clic(driver, 'a[name="inventory"]')
    escribir(driver, field, value)
    shot('entrada')
    clic(driver, '.o_form_button_save')
    WebDriverWait(driver, TIMEOUT).until(
        lambda d: api.read('product.template', ident, field) == pytest.approx(value))
    driver.refresh()
    esperar(driver, '.o_form_view')
    clic(driver, 'a[name="inventory"]')
    displayed = campo(driver, field).get_attribute('value')
    assert float(displayed.replace(',', '.')) == pytest.approx(value)
    assert api.read('product.template', ident, field) == pytest.approx(value)
    shot('persistencia_verificada')


@pytest.mark.parametrize('clase', ['unico', 'vacio', 'duplicado'],
                         ids=['unico', 'vacio', 'duplicado'])
def test_FC13_codigo_barras(sesion, shot, api, clase):
    """RF-K13 | PE: codigo unico/vacio aceptado; duplicado rechazado."""
    code = f'KEVIN-{uuid4().hex}'
    if clase == 'duplicado':
        api.product(barcode=code)
    ident = api.product(barcode=False)
    abrir_registro(sesion, 'stock.product_template_action_product', ident)
    # Set a nonempty initial value for the empty class, to verify an actual edit.
    if clase == 'vacio':
        escribir(sesion, 'barcode', code)
        clic(sesion, '.o_form_button_save')
        WebDriverWait(sesion, TIMEOUT).until(
            lambda d: api.read('product.template', ident, 'barcode') == code)
    escribir(sesion, 'barcode', '' if clase == 'vacio' else code)
    shot('entrada')
    clic(sesion, '.o_form_button_save')
    if clase == 'duplicado':
        dialog = esperar(sesion, '.o_dialog .modal-body')
        assert code in dialog.text, dialog.text
        assert not api.read('product.template', ident, 'barcode')
        shot('duplicado_rechazado')
    else:
        expected = False if clase == 'vacio' else code
        WebDriverWait(sesion, TIMEOUT).until(
            lambda d: api.read('product.template', ident, 'barcode') == expected)
        sesion.refresh()
        assert campo(sesion, 'barcode').get_attribute('value') == (expected or '')
        shot('persistencia_verificada')


@pytest.mark.parametrize('valor', [-0.01, 0, 0.01, 1],
                         ids=['negativo', 'cero', 'minimo_positivo', 'positivo'])
def test_FC14_peso(sesion, shot, api, valor):
    """RF-K14 | PE+VL: campo numerico firmado; frontera de signo -0.01/0/0.01."""
    ident = api.product(weight=2)
    abrir_registro(sesion, 'stock.product_template_action_product', ident)
    guardar_numero(sesion, api, ident, 'weight', valor, shot)


@pytest.mark.parametrize('valor', [-0.01, 0, 0.01, 1],
                         ids=['negativo', 'cero', 'minimo_positivo', 'positivo'])
def test_FC15_volumen(sesion, shot, api, valor):
    """RF-K15 | PE+VL: persistencia del volumen, sin inventar minimo contractual."""
    ident = api.product(volume=2)
    abrir_registro(sesion, 'stock.product_template_action_product', ident)
    guardar_numero(sesion, api, ident, 'volume', valor, shot)


@pytest.mark.parametrize('nombre', ['', 'K', 'KB'], ids=['vacio', 'uno', 'dos'])
def test_FC16_nombre_ubicacion(sesion, shot, api, nombre):
    """RF-K16 | PE+VL: nombre obligatorio, longitudes 0/1/2."""
    original = f'KEVIN-{uuid4().hex}'
    ident = api.create('stock.location', {'name': original, 'usage': 'internal'})
    abrir_registro(sesion, 'stock.action_location_form', ident)
    escribir(sesion, 'name', nombre)
    shot('entrada')
    clic(sesion, '.o_form_button_save')
    if not nombre:
        esperar(sesion, '.o_field_widget[name="name"].o_field_invalid')
        assert api.read('stock.location', ident, 'name') == original
        assert campo(sesion, 'name').get_attribute('value') == ''
        shot('nombre_obligatorio_rechazado')
    else:
        WebDriverWait(sesion, TIMEOUT).until(
            lambda d: api.read('stock.location', ident, 'name') == nombre)
        sesion.refresh()
        assert campo(sesion, 'name').get_attribute('value') == nombre
        shot('persistencia_verificada')

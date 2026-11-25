"""FC-05 a FC-08: pruebas funcionales de caja negra de Rubén Darío Saa (Odoo 18, Inventario).

Técnicas: análisis de valores límite (AVL) y partición de equivalencia (PE).
Estructura de cada prueba: PREPARAR datos (API) -> ACTUAR en el navegador (Selenium) -> VERIFICAR lo guardado.
Archivo autónomo: solo depende de conftest.py (driver, sesion, shot, esperar, clic, abrir_accion).

Ejecutar desde la carpeta functional:
  pytest test_ruben.py -v --html=../evidencia/reporte_ruben.html --self-contained-html
"""
import os
import time
import xmlrpc.client

import pytest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from conftest import TIMEOUT, abrir_accion, clic, esperar

URL = os.getenv("ODOO_URL", "http://localhost:8069")
DB = os.getenv("ODOO_DB", "calidad")
USUARIO = os.getenv("ODOO_USER", "admin")
CLAVE = os.getenv("ODOO_PASS", "admin")
TODOS = {"active_test": False}  # incluir también los registros archivados
PATRONES_LIMPIEZA = (" FC05", " FC06", " FC07", " FC08")
ACCION_PRODUCTOS = "stock.product_template_action_product"


# ===================================================================== API (XML-RPC)
class OdooAPI:
    """Acceso por XML-RPC para preparar (precondiciones) y verificar datos guardados."""

    def __init__(self):
        comun = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
        self.uid = comun.authenticate(DB, USUARIO, CLAVE, {})
        if not self.uid:
            raise RuntimeError("No se pudo autenticar en Odoo: revise ODOO_DB, ODOO_USER y ODOO_PASS")
        self.modelos = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

    def call(self, modelo, metodo, *args, **kwargs):
        return self.modelos.execute_kw(DB, self.uid, CLAVE, modelo, metodo, list(args), kwargs)

    def crear_producto(self, nombre, precio=0.0):
        return self.call("product.template", "create", {
            "name": nombre, "type": "consu", "is_storable": True, "list_price": precio})

    def buscar_id(self, nombre):
        ids = self.call("product.template", "search", [("name", "=", nombre)], context=TODOS)
        return ids[0] if ids else None

    def leer(self, id_producto, campos):
        return self.call("product.template", "read", [id_producto], fields=campos, context=TODOS)[0]

    def archivar(self, id_producto):
        self.call("product.template", "write", [id_producto], {"active": False})

    def _id_variante(self, id_plantilla):
        return self.call("product.template", "read", [id_plantilla],
                         fields=["product_variant_id"], context=TODOS)[0]["product_variant_id"][0]

    def ubicacion_principal(self):
        """Ubicación de existencias (WH/Stock) de la primera bodega."""
        bodega = self.call("stock.warehouse", "search_read", [], fields=["lot_stock_id"], limit=1)[0]
        return bodega["lot_stock_id"][0]

    def poner_stock(self, id_plantilla, cantidad, ubicacion=None):
        """Deja el producto con 'cantidad' unidades a mano en la ubicación indicada (por defecto WH/Stock)."""
        producto = self._id_variante(id_plantilla)
        quant = self.call("stock.quant", "create",
                          {"product_id": producto, "location_id": ubicacion or self.ubicacion_principal(),
                           "inventory_quantity": cantidad}, context={"inventory_mode": True})
        try:
            self.call("stock.quant", "action_apply_inventory", [quant])
        except xmlrpc.client.Fault as error:      # Odoo aplicó el ajuste; solo falla al devolver 'None'
            if "marshal None" not in error.faultString:
                raise

    def stock_a_mano(self, id_plantilla):
        return self.leer(id_plantilla, ["qty_available"])["qty_available"]

    def habilitar_variantes(self):
        """Activa en Ajustes la opción 'Variantes de producto' (precondición de FC-07)."""
        ajuste = self.call("res.config.settings", "create", {"group_product_variant": True})
        self.call("res.config.settings", "execute", [ajuste])

    def crear_atributo(self, nombre, valores):
        return self.call("product.attribute", "create", {
            "name": nombre, "create_variant": "always",
            "value_ids": [[0, 0, {"name": v}] for v in valores]})

    def contar_variantes(self, id_plantilla):
        return self.call("product.product", "search_count",
                         [("product_tmpl_id", "=", id_plantilla)], context=TODOS)

    def leer_reglas(self, id_plantilla):
        return self.call("stock.warehouse.orderpoint", "search_read",
                         [("product_id.product_tmpl_id", "=", id_plantilla)],
                         fields=["product_min_qty", "product_max_qty"], context=TODOS)


def limpiar_datos(api):
    """Borra los productos y atributos creados por ESTAS pruebas (nombres con ' FC05'...' FC08').
    Se usan patrones propios para no tocar los datos de las pruebas FC-01 a FC-04 ni de otros.
    Si un producto ya tiene movimientos de inventario no se puede borrar: entonces se archiva."""
    for patron in PATRONES_LIMPIEZA:
        try:
            ids = api.call("product.template", "search", [("name", "ilike", patron)], context=TODOS)
        except Exception as error:
            print(f"[limpieza] no se pudo buscar '{patron}': {error}")
            continue
        for id_producto in ids:
            try:
                api.call("product.template", "unlink", [id_producto])
            except Exception:
                try:
                    api.archivar(id_producto)
                except Exception as error:
                    print(f"[limpieza] no se pudo limpiar el producto {id_producto}: {error}")
        try:
            atributos = api.call("product.attribute", "search", [("name", "ilike", patron)])
            if atributos:
                api.call("product.attribute", "unlink", atributos)
        except Exception as error:
            print(f"[limpieza] atributos '{patron}': {error}")


# ===================================================================== ayudas de interfaz
def clic_xpath(driver, xpath, timeout=TIMEOUT):
    elemento = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, xpath)))
    driver.execute_script("arguments[0].click();", elemento)


def elegir_many2one(driver, campo, texto, opcion=None, ambito=""):
    """Escribe en un campo de selección y elige la opción pedida (no la primera de la lista).
    opcion: texto exacto de la opción; si no se da, se elige la que contiene 'texto'.
    ambito: selector CSS que limita dónde buscar el campo (ej. '.o_selected_row' dentro de una lista)."""
    caja = esperar(driver, f"{ambito} div[name='{campo}'] input".strip())
    caja.click()
    caja.send_keys(Keys.CONTROL, "a")
    caja.send_keys(texto)
    if opcion:
        condicion = f"normalize-space(.)='{opcion}'"
    else:
        condicion = f"contains(., '{texto}')"
    clic_xpath(driver, f"//li[contains(@class,'o-autocomplete--dropdown-item')][{condicion}]")
    time.sleep(1)


def buscar(driver, texto):
    """Escribe en el buscador de la vista y pulsa Enter."""
    caja = WebDriverWait(driver, TIMEOUT).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".o_searchview_input")))
    caja.click()
    caja.send_keys(texto)
    caja.send_keys(Keys.ENTER)
    time.sleep(1.5)


def escribir_en_fila(driver, campo, valor):
    """Escribe en un campo de la fila que se está editando en una lista."""
    caja = esperar(driver, f".o_selected_row [name='{campo}'] input")
    caja.click()
    caja.send_keys(Keys.CONTROL, "a")
    caja.send_keys(str(valor))


def aplicar_conteo(driver, nombre_producto, cantidad):
    """Inventario > Operaciones > Inventario físico: fija la cantidad contada y la aplica."""
    abrir_accion(driver, "stock.action_view_inventory_tree")
    buscar(driver, nombre_producto)
    esperar(driver, ".o_data_row")
    clic(driver, ".o_data_row td[name='inventory_quantity']")
    escribir_en_fila(driver, "inventory_quantity", cantidad)
    clic(driver, ".o_list_button_save")
    time.sleep(1)
    clic(driver, ".o_data_row button[name='action_apply_inventory']")
    try:                                        # algunas versiones piden confirmar en una ventana
        clic(driver, ".modal-footer .btn-primary", timeout=5)
    except TimeoutException:
        pass
    time.sleep(2)


def leer_stock_en_pantalla(driver):
    """Lee el número del botón 'On Hand / A mano' de la ficha del producto.
    Busca el botón por su texto (no por su nombre interno) y, si no lo encuentra,
    muestra en el error qué botones sí hay en pantalla."""
    xpath = ("//button[contains(@class,'oe_stat_button')]"
             "[contains(.,'On Hand') or contains(.,'A mano') or contains(.,'En existencia')]")
    try:
        boton = WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.XPATH, xpath)))
    except TimeoutException:
        botones = [b.text.replace("\n", " ") for b in driver.find_elements(By.CSS_SELECTOR, ".oe_stat_button")]
        raise AssertionError(f"No se encontró el botón 'A mano'. Botones visibles: {botones}")
    return float(boton.text.replace(",", "").split()[0])


def abrir_registro(driver, texto):
    clic_xpath(driver, f"(//*[contains(@class,'o_kanban_record') or contains(@class,'o_data_row')]"
                       f"[contains(., '{texto}')])[1]")
    esperar(driver, ".o_form_view")
    time.sleep(1)


# ===================================================================== pruebas
@pytest.fixture(scope="session")
def api():
    """Conexión por API (XML-RPC) a Odoo. Al terminar la sesión borra los datos de prueba."""
    cliente = OdooAPI()
    yield cliente
    limpiar_datos(cliente)


@pytest.fixture
def sello():
    """Texto único por ejecución (hora-minuto-segundo) para que los nombres no se repitan."""
    return time.strftime("%H%M%S")



def _formulario_nuevo(driver):
    abrir_accion(driver, ACCION_PRODUCTOS)
    clic(driver, ".o_list_button_add, .o-kanban-button-new")
    esperar(driver, ".o_form_view")
    time.sleep(2)


# ---------------------------------------------------------------- FC-05
@pytest.mark.parametrize("contado, esperado", [(0, 0), (9, 9), (10, 10), (11, 11), (-1, 10)],
                         ids=["FC05a_cero", "FC05b_nueve", "FC05c_diez", "FC05d_once", "FC05e_negativo"])
def test_FC05_ajuste_de_inventario(sesion, shot, api, sello, contado, esperado):
    """FC-05 | HU-015 | AVL alrededor de la cantidad actual (10).
    Esperado: con 0, 9, 10 y 11 la cantidad a mano queda igual a la contada.
    Con -1 el sistema debería rechazarlo y dejar 10 (a confirmar)."""
    driver = sesion
    nombre = f"Camiseta FC05 {sello}"
    id_producto = api.crear_producto(nombre, precio=30000)
    api.poner_stock(id_producto, 10)
    assert api.stock_a_mano(id_producto) == 10, "Precondición: el producto debía tener 10 a mano"

    aplicar_conteo(driver, nombre, contado)
    shot(f"conteo_{contado}_aplicado")

    obtenido = api.stock_a_mano(id_producto)
    assert obtenido == esperado, f"Conteo {contado}: se esperaba {esperado} a mano y Odoo dejó {obtenido}"


# ---------------------------------------------------------------- FC-06
@pytest.mark.parametrize("cantidad", [7, 0], ids=["FC06a_con_stock", "FC06b_sin_stock"])
def test_FC06_consultar_cantidad_a_mano(sesion, shot, api, sello, cantidad):
    """FC-06 | HU-013 | PE (con stock / sin stock).
    Esperado: el botón 'A mano' de la ficha muestra 7 para el producto con stock y 0 para el otro."""
    driver = sesion
    nombre = f"Zapato FC06 {sello}"
    id_producto = api.crear_producto(nombre, precio=80000)
    if cantidad:
        api.poner_stock(id_producto, cantidad)

    abrir_accion(driver, ACCION_PRODUCTOS)
    buscar(driver, nombre)
    abrir_registro(driver, nombre)
    shot("ficha_del_producto")

    assert leer_stock_en_pantalla(driver) == cantidad


# ---------------------------------------------------------------- FC-07
def _agregar_linea_atributo(driver, atributo, valores):
    """En la pestaña Atributos y variantes: agrega una línea con un atributo y sus valores."""
    clic(driver, "div[name='attribute_line_ids'] .o_field_x2many_list_row_add a")
    elegir_many2one(driver, "attribute_id", atributo, atributo, ambito=".o_selected_row")
    for valor in valores:
        elegir_many2one(driver, "value_ids", valor, valor, ambito=".o_selected_row")


@pytest.mark.parametrize("usa_color, variantes", [(True, 4), (False, 2)],
                         ids=["FC07a_talla_y_color", "FC07b_solo_talla"])
def test_FC07_crear_variantes(sesion, shot, api, sello, usa_color, variantes):
    """FC-07 | HU-011 | PE. Clase A: Talla {S, M} y Color {Rojo, Azul} -> 4 variantes.
    Clase B: solo Talla {S, M} -> 2 variantes."""
    driver = sesion
    nombre = f"Chaqueta FC07 {sello}{'A' if usa_color else 'B'}"
    talla = f"Talla FC07 {sello}{'A' if usa_color else 'B'}"
    color = f"Color FC07 {sello}{'A' if usa_color else 'B'}"
    api.habilitar_variantes()                               # precondición: activar variantes en Ajustes
    api.crear_atributo(talla, ["S", "M"])
    api.crear_atributo(color, ["Rojo", "Azul"])

    _formulario_nuevo(driver)
    driver.switch_to.active_element.send_keys(nombre)
    clic(driver, "a[name='variants']")                      # pestaña Atributos y variantes
    _agregar_linea_atributo(driver, talla, ["S", "M"])
    if usa_color:
        _agregar_linea_atributo(driver, color, ["Rojo", "Azul"])
    shot("lineas_de_atributos")

    clic(driver, ".o_form_button_save")
    time.sleep(2)
    shot("producto_guardado")

    assert api.contar_variantes(api.buscar_id(nombre)) == variantes


# ---------------------------------------------------------------- FC-08
@pytest.mark.parametrize("minimo, maximo, se_guarda",
                         [(5, 4, False), (5, 5, True), (5, 6, True)],
                         ids=["FC08a_max_menor_que_min", "FC08b_max_igual_a_min", "FC08c_max_mayor_que_min"])
def test_FC08_regla_de_reabastecimiento(sesion, shot, api, sello, minimo, maximo, se_guarda):
    """FC-08 | HU-014 | AVL sobre la relación mínimo/máximo (máx = mín-1, mín, mín+1).
    Esperado: (5,5) y (5,6) se guardan; (5,4) debería rechazarse (a confirmar)."""
    driver = sesion
    nombre = f"Pantalon FC08 {sello}"
    id_producto = api.crear_producto(nombre, precio=45000)

    abrir_accion(driver, "stock.action_orderpoint")
    clic(driver, ".o_list_button_add")
    elegir_many2one(driver, "product_id", nombre, ambito=".o_selected_row")
    escribir_en_fila(driver, "product_min_qty", minimo)
    escribir_en_fila(driver, "product_max_qty", maximo)
    shot("regla_llena")

    clic(driver, ".o_list_button_save")
    time.sleep(2)
    shot("intento_de_guardar")

    reglas = api.leer_reglas(id_producto)
    detalle = [(r["product_min_qty"], r["product_max_qty"]) for r in reglas]
    assert len(reglas) == (1 if se_guarda else 0), \
        f"Se pidió (mín={minimo}, máx={maximo}); reglas guardadas (mín, máx): {detalle}"

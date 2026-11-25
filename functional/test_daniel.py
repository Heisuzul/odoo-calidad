"""Pruebas funcionales de Daniel — Odoo 18 / Inventario, Entrega 2.

Cuatro casos independientes, sin duplicar los escenarios funcionales de
Heidy (FC-01..FC-04) ni de Ruben (FC-05..FC-08):

FC-17: modificar precio de venta (particion de equivalencia).
FC-18: valores limite del precio 0 y 0.01 (analisis de valores limite).
FC-19: modificar costo estandar (particion de equivalencia).
FC-20: modificar referencia interna (particion de equivalencia).

Las acciones evaluadas se realizan en la interfaz con Selenium. Las lecturas
RPC solo corroboran persistencia y eliminan los productos de prueba creados.
Las credenciales se configuran con las variables ODOO_* del entorno local.

Ejecutar desde la raiz del repositorio:
  python -m pytest functional/test_daniel.py -v -s
"""


from uuid import uuid4

import pytest
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from conftest import BASE_URL, ODOO_VERSION, TIMEOUT, clic, esperar


def _rpc(driver, modelo, metodo, args, **kwargs):
    """Consultas/limpieza solamente: opera con la cookie local ya autenticada."""
    respuesta = driver.execute_async_script(
        """
        const [model, method, args, kwargs, done] = arguments;
        fetch(`/web/dataset/call_kw/${model}/${method}`, {
            method: 'POST', credentials: 'same-origin',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({jsonrpc: '2.0', method: 'call',
                                  params: {model, method, args, kwargs}})
        }).then(r => r.json()).then(done)
          .catch(e => done({error: {message: String(e)}}));
        """,
        modelo, metodo, args, kwargs,
    )
    if not isinstance(respuesta, dict) or 'error' in respuesta:
        raise AssertionError(f"RPC de verificación falló: {modelo}.{metodo}: {respuesta}")
    return respuesta['result']


def _registros(driver, referencia):
    return _rpc(
        driver, 'product.template', 'search_read',
        [[('default_code', '=', referencia)]],
        fields=['id', 'name', 'default_code', 'list_price',
                'standard_price', 'active'],
        context={'active_test': False},
    )


@pytest.fixture
def productos_daniel(sesion):
    """Elimina únicamente los productos creados por estos casos de prueba.

    Nunca borra productos preexistentes. Las pruebas de ajuste de inventario
    necesitarán una estrategia de limpieza específica cuando se implementen.
    """
    referencias = []
    yield referencias
    for ref in referencias:
        try:
            resultados = _registros(sesion, ref)
            if resultados:
                ids = [r['id'] for r in resultados]
                _rpc(sesion, 'product.template', 'unlink', [ids])
                print(f"Limpieza de prueba: {ref}")
        except Exception as exc:
            # Una falla de limpieza no se oculta: queda reportada con el ID
            # para eliminar manualmente SOLO el registro de prueba afectado.
            pytest.fail(f"No fue posible limpiar el producto de prueba {ref}: {exc}")


def _campo(driver, nombre):
    return esperar(
        driver,
        f'.o_field_widget[name="{nombre}"] input, '
        f'.o_field_widget[name="{nombre}"] textarea',
    )


def _escribir(driver, nombre, valor):
    campo = _campo(driver, nombre)
    campo.send_keys(Keys.CONTROL, 'a')
    campo.send_keys(Keys.BACKSPACE)
    campo.send_keys(str(valor))
    campo.send_keys(Keys.TAB)


def _abrir_lista(driver):
    """Abre una única vez la lista de productos de Odoo."""

    ruta = (
        "/odoo/action-stock.product_template_action_product"
        if ODOO_VERSION >= 18
        else "/web#action=stock.product_template_action_product"
    )

    driver.get(BASE_URL + ruta)

    esperar(driver, ".o_searchview_input")

    WebDriverWait(driver, TIMEOUT).until(
        lambda d: (
            d.find_elements(By.CSS_SELECTOR, ".o_list_view")
            or d.find_elements(
                By.CSS_SELECTOR,
                "button.o_switch_view.o_list"
            )
        )
    )

    listas = driver.find_elements(
        By.CSS_SELECTOR, ".o_list_view"
    )

    if not any(lista.is_displayed() for lista in listas):
        WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "button.o_switch_view.o_list"
            ))
        ).click()

    esperar(driver, ".o_list_view")
    esperar(driver, ".o_list_button_add")

    print("Vista de productos disponible", flush=True)


def _crear_producto(driver, referencias, id_caso, **campos):
    """Crea el producto por la UI; devuelve la referencia interna única."""
    _abrir_lista(driver)
    clic(driver, '.o_list_button_add')
    esperar(driver, '.o_form_view')
    referencia = f'DAN-{id_caso}-{uuid4().hex[:12]}'
    nombre = f'Producto {id_caso} {uuid4().hex[:8]}'
    referencias.append(referencia)  # Registrar incluso si autoguarda antes de fallar.
    _escribir(driver, 'default_code', referencia)
    _escribir(driver, 'name', nombre)
    for campo, valor in campos.items():
        _escribir(driver, campo, valor)
    clic(driver, '.o_form_button_save')
    registros = WebDriverWait(driver, TIMEOUT).until(
        lambda d: _registros(d, referencia),
        message=f'No se guardó el producto de {id_caso}',
    )
    assert len(registros) == 1, 'Creación duplicada o referencia ambigua'
    return referencia, nombre


def _verificar_persistencia(driver, referencia, campo, esperado):
    """Espera hasta confirmar el valor persistido en Odoo."""

    esperado = float(esperado)
    ultimo = []

    def coincide(d):
        nonlocal ultimo

        ultimo = _registros(d, referencia)

        if len(ultimo) != 1:
            return False

        real = float(ultimo[0][campo])

        return real == pytest.approx(
            esperado, abs=0.000001
        )

    try:
        WebDriverWait(
            driver, 20, poll_frequency=0.5
        ).until(coincide)

    except TimeoutException as exc:
        real = (
            ultimo[0].get(campo)
            if len(ultimo) == 1
            else "producto no encontrado"
        )

        raise AssertionError(
            f"{campo}: esperado={esperado}, "
            f"persistido={real} después de 20 segundos"
        ) from exc

    print(
        f"Persistencia confirmada: "
        f"{campo}={esperado}",
        flush=True
    )

    return ultimo[0]


def _actualizar_y_recargar(driver, referencia, campo, valor):
    """Edita, guarda y comprueba persistencia."""

    antes = _campo(driver, campo).get_attribute("value")

    _escribir(driver, campo, valor)

    despues = _campo(driver, campo).get_attribute("value")

    print(f"Valor antes de editar: {antes}", flush=True)
    print(f"Valor después de escribir: {despues}", flush=True)

    clic(driver, ".o_form_button_save")

    print("Botón Guardar presionado", flush=True)

    # Esperar a que cambie el valor en la base de datos.
    _verificar_persistencia(
        driver, referencia, campo, valor
    )

    # Recargar la página.
    driver.refresh()

    esperar(driver, ".o_form_view")

    print(
        "Valor visible tras recargar:",
        _campo(driver, campo).get_attribute("value"),
        flush=True
    )

    return _verificar_persistencia(
        driver, referencia, campo, valor
    )


def test_fc17_modificar_precio(sesion, productos_daniel, shot):
    """FC-17 | RF-17 | PE: precio positivo, edición y persistencia."""
    d = sesion
    referencia, _ = _crear_producto(d, productos_daniel, 'FC17', list_price=100)
    _verificar_persistencia(d, referencia, 'list_price', 100)
    shot('precio_inicial_100')
    _actualizar_y_recargar(d, referencia, 'list_price', 25000)
    shot('precio_final_25000')


def test_fc18_valores_frontera_precio(sesion, productos_daniel, shot):
    """FC-18 | RF-18 | VL: 0.00 y 0.01, dos fronteras consecutivas.

    Expectativa provisional para configuración estándar de prueba. Si falla,
    revisar la regla real de Odoo antes de clasificar como defecto de producto.
    """
    d = sesion
    referencia, _ = _crear_producto(d, productos_daniel, 'FC18', list_price=100)
    _actualizar_y_recargar(d, referencia, 'list_price', 0)
    shot('frontera_cero')
    _actualizar_y_recargar(d, referencia, 'list_price', 0.01)
    shot('frontera_001')


def test_fc19_modificar_costo(sesion, productos_daniel, shot):
    """FC-19 | RF-19 | PE: cambio del costo estándar y persistencia."""
    d = sesion
    referencia, _ = _crear_producto(d, productos_daniel, 'FC19', standard_price=120)
    _verificar_persistencia(d, referencia, 'standard_price', 120)
    shot('costo_inicial_120')
    _actualizar_y_recargar(d, referencia, 'standard_price', 200)
    shot('costo_final_200')


def test_fc20_modificar_referencia_interna(sesion, productos_daniel, shot):
    """FC-20 | RF-20 | PE: cambio de referencia sin duplicar producto.

    Se valida que la referencia anterior ya no identifique el producto,
    que la referencia nueva identifique el mismo registro y que el nuevo
    valor permanezca visible despues de recargar la interfaz.
    """
    d = sesion
    referencia_original, nombre = _crear_producto(
        d, productos_daniel, "FC20"
    )
    originales = _registros(d, referencia_original)
    assert len(originales) == 1
    id_producto = originales[0]["id"]
    shot("referencia_interna_original")

    referencia_nueva = f"{referencia_original}-NUEVA"
    assert not _registros(d, referencia_nueva), (
        "La nueva referencia no debe existir antes de editar"
    )
    # Registrar la nueva referencia ANTES del guardado para que la limpieza
    # pueda encontrar el producto aunque falle una asercion posterior.
    productos_daniel.append(referencia_nueva)

    _escribir(d, "default_code", referencia_nueva)
    clic(d, ".o_form_button_save")

    def cambio_persistido(driver):
        nuevos = _registros(driver, referencia_nueva)
        viejos = _registros(driver, referencia_original)
        return (
            len(nuevos) == 1
            and not viejos
            and nuevos[0]["id"] == id_producto
            and nuevos[0]["name"] == nombre
        )

    WebDriverWait(d, 20, poll_frequency=0.5).until(
        cambio_persistido,
        message="FC-20: no se confirmo el cambio de referencia en Odoo",
    )

    d.refresh()
    esperar(d, ".o_form_view")
    visible = _campo(d, "default_code").get_attribute("value")
    assert visible == referencia_nueva, (
        f"FC-20: la referencia visible no coincide: {visible!r}"
    )
    assert cambio_persistido(d), (
        "FC-20: la referencia no persistio despues de la recarga"
    )
    shot("referencia_interna_actualizada")
    print(
        f"FC-20 PASSED: referencia actualizada; "
        f"producto original ID={id_producto} conservado sin duplicacion",
        flush=True,
    )

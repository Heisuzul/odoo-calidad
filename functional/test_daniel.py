r"""Pruebas funcionales de Daniel para Odoo 18, módulo Inventario.

Aporte correspondiente a la Entrega 2 de Calidad de Productos de Software.

Diseño documental FC-05..FC-12: docs/diseno_pruebas_funcionales_daniel.md

IMPLEMENTADAS PARA EJECUCIÓN LOCAL: FC-05, FC-06, FC-07, FC-09.
POR IMPLEMENTAR Y VERIFICAR UI DE INVENTARIO: FC-08, FC-10, FC-11, FC-12.

Todas las acciones funcionales evaluadas se ejecutan en la interfaz de Odoo
mediante Selenium. Las lecturas RPC reutilizan la sesión del navegador SOLO
para corroborar persistencia y limpiar registros de prueba. No se modifican
registros preexistentes ni se usan credenciales incrustadas en el código.

Ejemplo (desde la raíz del repo, en PowerShell):
  .\.venv\Scripts\python.exe -m pytest functional/test_daniel.py -v -s \
      --html=evidencia/reporte_daniel.html --self-contained-html

Configurar ODOO_URL, ODOO_DB, ODOO_USER y ODOO_PASS previamente, de forma local.
"""

from uuid import uuid4

import pytest
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
)
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
    """Abre Productos y cambia a vista de lista en Odoo 18."""

    ruta = (
        "/odoo/action-stock.product_template_action_product"
        if ODOO_VERSION >= 18
        else "/web#action=stock.product_template_action_product"
    )

    driver.get(BASE_URL + ruta)

    # Esperar a que el buscador esté disponible.
    esperar(driver, ".o_searchview_input")

    # Esperar a que Odoo termine de mostrar
    # la vista o el botón para cambiarla.
    WebDriverWait(driver, TIMEOUT).until(
        lambda d: d.find_elements(
            By.CSS_SELECTOR, ".o_list_view"
        ) or d.find_elements(
            By.CSS_SELECTOR, "button.o_switch_view.o_list"
        )
    )

    # Comprobar si ya estamos en la vista de lista.
    vista_lista = driver.find_elements(
        By.CSS_SELECTOR, ".o_list_view"
    )

    if not any(v.is_displayed() for v in vista_lista):
        # Esperar hasta que el botón sea interactivo.
        boton_lista = WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "button.o_switch_view.o_list"
            ))
        )
        boton_lista.click()

    # Confirmar que la vista terminó de cambiar.
    esperar(driver, ".o_list_view")

    # Confirmar que podemos crear un producto.
    esperar(driver, ".o_list_button_add")

    print("FC-05: vista de productos disponible")

    """Abre la lista de productos de Odoo 18."""

    ruta = (
        '/odoo/action-stock.product_template_action_product'
        if ODOO_VERSION >= 18
        else '/web#action=stock.product_template_action_product'
    )

    driver.get(BASE_URL + ruta)

    # Esperar a que cargue la vista de productos.
    esperar(driver, '.o_searchview_input')

    # Cambiar a vista de lista cuando sea necesario.
    botones_lista = driver.find_elements(
        By.CSS_SELECTOR, '.o_switch_view.o_list'
    )

    if botones_lista and botones_lista[0].is_displayed():
        clic(driver, '.o_switch_view.o_list')

    # Confirmar que la lista está disponible.
    esperar(driver, '.o_list_view')

    ruta = ('/odoo/action-stock.product_template_action_product'
            if ODOO_VERSION >= 18 else
            '/web#action=stock.product_template_action_product')
    driver.get(BASE_URL + ruta)
    esperar(driver, '.o_searchview_input')
    # Retiramos posibles filtros predeterminados (Goods, etc.).
    for _ in range(8):
        botones = driver.find_elements(By.CSS_SELECTOR,
                                       '.o_searchview .o_facet_remove')
        if not botones:
            break
        cantidad = len(botones)
        clic(driver, '.o_searchview .o_facet_remove')
        WebDriverWait(driver, TIMEOUT).until(
            lambda d: len(d.find_elements(
                By.CSS_SELECTOR, '.o_searchview .o_facet_remove')) < cantidad
        )
    # Odoo normalmente abre productos en vista kanban.
    botones_lista = driver.find_elements(By.CSS_SELECTOR, '.o_switch_view.o_list')
    if botones_lista and botones_lista[0].is_displayed():
        botones_lista[0].click()
    esperar(driver, '.o_list_view')


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


def _buscar(driver, texto):
    buscador = esperar(driver, '.o_searchview_input')
    buscador.send_keys(texto)
    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, '.o_searchview_autocomplete')
        )
    )
    buscador.send_keys(Keys.ENTER)
    WebDriverWait(driver, TIMEOUT).until(
        lambda d: any(texto in e.text for e in
                      d.find_elements(By.CSS_SELECTOR, '.o_searchview_facet')),
    )



def _nombres_lista(driver):
    """Lee los nombres visibles desde el DOM actual de Odoo.

    La lectura ocurre en una sola operación, evitando
    referencias obsoletas durante el renderizado.
    """
    return driver.execute_script("""
        return Array.from(
            document.querySelectorAll(
                '.o_list_view .o_data_row td[name="name"]'
            )
        )
        .filter(el => el.getClientRects().length > 0)
        .map(el => (el.innerText || el.textContent).trim())
        .filter(Boolean);
    """)


def test_fc05_modificar_precio(sesion, productos_daniel, shot):
    """FC-05 | RF-05 | PE: precio positivo, edición y persistencia."""
    d = sesion
    referencia, _ = _crear_producto(d, productos_daniel, 'FC05', list_price=100)
    _verificar_persistencia(d, referencia, 'list_price', 100)
    shot('precio_inicial_100')
    _actualizar_y_recargar(d, referencia, 'list_price', 25000)
    shot('precio_final_25000')


def test_fc06_valores_frontera_precio(sesion, productos_daniel, shot):
    """FC-06 | RF-06 | VL: 0.00 y 0.01, dos fronteras consecutivas.

    Expectativa provisional para configuración estándar de prueba. Si falla,
    revisar la regla real de Odoo antes de clasificar como defecto de producto.
    """
    d = sesion
    referencia, _ = _crear_producto(d, productos_daniel, 'FC06', list_price=100)
    _actualizar_y_recargar(d, referencia, 'list_price', 0)
    shot('frontera_cero')
    _actualizar_y_recargar(d, referencia, 'list_price', 0.01)
    shot('frontera_001')


def test_fc07_buscar_referencia(sesion, productos_daniel, shot):
    """FC-07 | RF-07 | PE: referencia interna existente e inexistente."""
    d = sesion
    referencia, nombre = _crear_producto(d, productos_daniel, 'FC07')
    _abrir_lista(d)
    _buscar(d, referencia)
    WebDriverWait(d, TIMEOUT).until(lambda x: nombre in _nombres_lista(x))
    encontrados = _nombres_lista(d)
    assert encontrados == [nombre], f'Resultados de referencia: {encontrados!r}'
    shot('referencia_existente')

    _abrir_lista(d)
    inexistente = f'DAN-NO-EXISTE-{uuid4().hex}'
    _buscar(d, inexistente)
    WebDriverWait(d, TIMEOUT).until(
        lambda x: not _nombres_lista(x) and bool(x.find_elements(
            By.CSS_SELECTOR, '.o_view_nocontent')),
    )
    assert _nombres_lista(d) == [], 'La referencia inexistente produjo filas'
    shot('referencia_inexistente')


def test_fc09_modificar_costo(sesion, productos_daniel, shot):
    """FC-09 | RF-09 | PE: cambio del costo estándar y persistencia."""
    d = sesion
    referencia, _ = _crear_producto(d, productos_daniel, 'FC09', standard_price=120)
    _verificar_persistencia(d, referencia, 'standard_price', 120)
    shot('costo_inicial_120')
    _actualizar_y_recargar(d, referencia, 'standard_price', 200)
    shot('costo_final_200')

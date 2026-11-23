"""FC-01 a FC-04: pruebas de caja negra de Inventario en Odoo 18.

Las acciones y comprobaciones de listas se realizan con Selenium. El RPC usa
la sesión del navegador para aislar/limpiar datos y corroborar la persistencia;
no reemplaza la creación, la búsqueda ni el archivado desde la interfaz.
"""
from uuid import uuid4

import pytest
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from conftest import BASE_URL, ODOO_VERSION, TIMEOUT, clic, esperar


def _rpc(driver, modelo, metodo, args, **kwargs):
    """Reutiliza la cookie autenticada, sin introducir credenciales."""
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
        """, modelo, metodo, args, kwargs,
    )
    assert 'error' not in respuesta, f"RPC {modelo}.{metodo}: {respuesta.get('error')}"
    return respuesta['result']


def _productos(driver, dominio, campos=None):
    return _rpc(driver, 'product.template', 'search_read', [dominio],
                fields=campos or ['name', 'default_code', 'active'],
                context={'active_test': False})


@pytest.fixture
def datos_productos(sesion):
    """Cada ejecución usa referencias únicas y elimina sólo sus registros."""
    referencias = []
    yield referencias
    if referencias:
        registros = _productos(sesion, [('default_code', 'in', referencias)])
        if registros:
            _rpc(sesion, 'product.template', 'unlink',
                 [[registro['id'] for registro in registros]])


def _campo(driver, nombre):
    return esperar(driver, f'.o_field_widget[name="{nombre}"] input, '
                   f'.o_field_widget[name="{nombre}"] textarea')


def _escribir(driver, nombre, valor):
    campo = _campo(driver, nombre)
    campo.send_keys(Keys.CONTROL, 'a')
    campo.send_keys(Keys.BACKSPACE)
    campo.send_keys(str(valor))
    campo.send_keys(Keys.TAB)


def _lista(driver):
    # Abrir de nuevo la acción elimina búsquedas previas. Se retiran también
    # los filtros predeterminados (p. ej. Bienes) para consultar todos los tipos.
    ruta = ('/odoo/action-stock.product_template_action_product'
            if ODOO_VERSION >= 18
            else '/web#action=stock.product_template_action_product')
    driver.get(BASE_URL + ruta)
    esperar(driver, '.o_searchview_input')
    while driver.find_elements(By.CSS_SELECTOR, '.o_searchview .o_facet_remove'):
        cantidad = len(driver.find_elements(By.CSS_SELECTOR, '.o_searchview .o_facet_remove'))
        clic(driver, '.o_searchview .o_facet_remove')
        WebDriverWait(driver, TIMEOUT).until(
            lambda d: len(d.find_elements(
                By.CSS_SELECTOR, '.o_searchview .o_facet_remove')) < cantidad)
    assert not driver.find_elements(By.CSS_SELECTOR, '.o_searchview_facet'), (
        'La lista conserva filtros o búsquedas anteriores')
    clic(driver, '.o_switch_view.o_list')
    esperar(driver, '.o_list_view')


def _capturar_sesion(driver, shot):
    """Espera contenido visible de Inventario antes de guardar el acceso."""
    _lista(driver)
    WebDriverWait(driver, TIMEOUT,
                  ignored_exceptions=(StaleElementReferenceException,)).until(
        EC.any_of(
            EC.visibility_of_element_located((
                By.CSS_SELECTOR, '.o_list_view .o_data_row td[name="name"]')),
            EC.visibility_of_element_located((
                By.CSS_SELECTOR, '.o_list_view .o_view_nocontent')),
        ), message='Inventario aún no muestra productos ni el indicador de lista vacía')
    shot('sesion_iniciada')


def _nuevo(driver, referencias, nombre):
    if nombre:
        assert not _productos(driver, [('name', '=', nombre)]), (
            f'Ya existe {nombre!r}. Se conserva: no pertenece a esta ejecución. '
            'Utiliza una base de pruebas sin ese nombre para evitar duplicados.')
    _lista(driver)
    clic(driver, '.o_list_button_add')
    esperar(driver, '.o_form_view')
    referencia = f'HEIDY-{uuid4().hex}'
    referencias.append(referencia)  # Antes de editar: cubre incluso fallos/autoguardado.
    _escribir(driver, 'default_code', referencia)
    if nombre:
        _escribir(driver, 'name', nombre)
    return referencia


def _guardar(driver, referencia, nombre):
    clic(driver, '.o_form_button_save')
    registros = WebDriverWait(driver, TIMEOUT).until(
        lambda d: _productos(d, [('default_code', '=', referencia)]),
        message=f'No se guardó {nombre!r}')
    assert len(registros) == 1, f'Se esperaba un único producto {nombre!r}'
    WebDriverWait(driver, TIMEOUT).until(
        lambda d: nombre in esperar(d, '.o_breadcrumb').text)
    # Reabrir del servidor permite comprobar valores realmente persistidos.
    driver.refresh()
    WebDriverWait(driver, TIMEOUT).until(
        lambda d: _campo(d, 'name').get_attribute('value') == nombre)
    return registros[0]['id']


def _buscar(driver, texto):
    # Se invoca sobre una lista limpia; Enter aplica el primer criterio de la
    # búsqueda de productos (nombre/referencia/código de barras en Odoo).
    entrada = esperar(driver, '.o_searchview_input')
    entrada.send_keys(texto)
    WebDriverWait(driver, TIMEOUT).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, '.o_searchview_autocomplete')))
    entrada.send_keys(Keys.ENTER)
    WebDriverWait(driver, TIMEOUT).until(
        lambda d: any(texto in e.text for e in
                      d.find_elements(By.CSS_SELECTOR, '.o_searchview_facet')))


def _nombres_lista(driver):
    return [e.text.strip() for e in driver.find_elements(
        By.CSS_SELECTOR, '.o_list_view .o_data_row td[name="name"]')]


def _resultados(driver, esperados, escenario):
    """Espera el render y falla mostrando resultados reales, incluso si hay cero."""
    def coincide(d):
        nombres = _nombres_lista(d)
        if sorted(nombres) != sorted(esperados):
            return False
        if not esperados:
            return any(e.is_displayed() for e in d.find_elements(
                By.CSS_SELECTOR, '.o_view_nocontent'))
        return True

    try:
        WebDriverWait(driver, TIMEOUT,
                      ignored_exceptions=(StaleElementReferenceException,)).until(coincide)
    except TimeoutException:
        pass  # La aserción conserva el resultado esperado y muestra la diferencia.
    reales = _nombres_lista(driver)
    assert sorted(reales) == sorted(esperados), (
        f'{escenario}: esperados={esperados!r}; resultados reales={reales!r}')
    if not esperados:
        assert coincide(driver), f'{escenario}: no aparece el indicador de lista vacía'
    return reales


def _filtrar_archivados(driver):
    clic(driver, '.o_searchview_dropdown_toggler')
    filtro = WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((
        By.XPATH, "//div[contains(@class,'o_filter_menu')]"
        "//*[@role='menuitemcheckbox'][normalize-space()='Archived' "
        "or normalize-space()='Archivados']")))
    filtro.click()
    # El menú de filtros permanece abierto en Odoo 18.
    clic(driver, '.o_searchview_dropdown_toggler')
    WebDriverWait(driver, TIMEOUT).until(
        lambda d: any(e.text.strip() in ('Archived', 'Archivados') for e in
                      d.find_elements(By.CSS_SELECTOR, '.o_facet_value')))


def test_fc01_crear_producto(sesion, datos_productos, shot):
    """FC-01 | HU001 | PE: nombre válido y nombre obligatorio vacío."""
    driver = sesion
    _capturar_sesion(driver, shot)
    # Clase válida: Bienes, venta 25000, costo 12000.
    referencia = _nuevo(driver, datos_productos, 'Camisa FC01')
    clic(driver, '.o_field_widget[name="type"] input[data-value="consu"]')
    _escribir(driver, 'list_price', 25000)
    _escribir(driver, 'standard_price', 12000)
    shot('producto_valido_completado')
    producto_id = _guardar(driver, referencia, 'Camisa FC01')
    shot('producto_valido_guardado')
    assert _campo(driver, 'name').get_attribute('value') == 'Camisa FC01', (
        'Clase válida: el título del formulario no corresponde al producto')
    registro = _productos(driver, [('id', '=', producto_id)],
                          ['name', 'type', 'list_price', 'standard_price'])[0]
    assert registro['type'] == 'consu', 'Clase válida: no se guardó como Bienes'
    assert registro['list_price'] == 25000, 'Clase válida: precio de venta incorrecto'
    assert registro['standard_price'] == 12000, 'Clase válida: costo incorrecto'
    _lista(driver)
    _buscar(driver, 'Camisa FC01')
    _resultados(driver, ['Camisa FC01'], 'FC-01, clase válida en la lista')
    shot('producto_visible_en_lista')

    # Clase inválida: nombre vacío. La referencia identifica cualquier creación indebida.
    referencia_invalida = _nuevo(driver, datos_productos, None)
    _escribir(driver, 'list_price', 25000)
    clic(driver, '.o_form_button_save')
    invalido = esperar(driver, '.o_field_widget[name="name"].o_field_invalid')
    shot('nombre_vacio_rechazado')
    assert 'o_required_modifier' in invalido.get_attribute('class'), (
        'Clase inválida: no se indica que el nombre es obligatorio')
    assert _campo(driver, 'name').get_attribute('value') == '', (
        'Clase inválida: el nombre debía permanecer vacío')
    assert not _productos(driver, [('default_code', '=', referencia_invalida)]), (
        'Posible no conformidad FC-01: Odoo creó un producto sin nombre')


def test_fc02_asignar_categoria(sesion, datos_productos, shot):
    """FC-02 | HU002 | PE: categoría explícita y categoría predeterminada."""
    driver = sesion
    _capturar_sesion(driver, shot)
    # Clase A: seleccionar una categoría existente, sin crear categorías nuevas.
    referencia = _nuevo(driver, datos_productos, 'Mesa FC02')
    categoria = _campo(driver, 'categ_id')
    categoria.send_keys(Keys.CONTROL, 'a')
    categoria.send_keys('Saleable')
    WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((
        By.XPATH, "//li[contains(@class,'o-autocomplete--dropdown-item')]/a"
        "[normalize-space()='All / Saleable']"))).click()
    shot('categoria_saleable_seleccionada')
    _guardar(driver, referencia, 'Mesa FC02')
    shot('categoria_saleable_guardada')
    assert _campo(driver, 'categ_id').get_attribute('value') == 'All / Saleable', (
        'Clase A: no se persistió la categoría All / Saleable')

    # Clase B: identificar el valor real del formulario ANTES de guardar.
    referencia = _nuevo(driver, datos_productos, 'Mesa FC02 predeterminada')
    categoria_predeterminada = _campo(driver, 'categ_id').get_attribute('value')
    assert categoria_predeterminada, 'Clase B: Odoo no propuso una categoría'
    shot('categoria_predeterminada_propuesta')
    print(f'FC-02, categoría predeterminada real: {categoria_predeterminada}')
    _guardar(driver, referencia, 'Mesa FC02 predeterminada')
    shot('categoria_predeterminada_guardada')
    assert _campo(driver, 'categ_id').get_attribute('value') == categoria_predeterminada, (
        f'Clase B: no se conservó la categoría predeterminada '
        f'{categoria_predeterminada!r}')


def test_fc03_buscar_producto(sesion, datos_productos, shot):
    """FC-03 | HU004 | PE: búsqueda existente e inexistente."""
    driver = sesion
    _capturar_sesion(driver, shot)
    existentes = _productos(driver, [('name', '=', 'Camisa FC03')])
    if not existentes:
        referencia = _nuevo(driver, datos_productos, 'Camisa FC03')
        _guardar(driver, referencia, 'Camisa FC03')
    else:
        assert len(existentes) == 1 and existentes[0]['active'], (
            'Precondición FC-03: debe existir una única Camisa FC03 activa; '
            'se conservan los datos preexistentes')
    # Clase existente: exactamente un resultado y nombre exacto en la lista real.
    _lista(driver)
    _buscar(driver, 'Camisa FC03')
    _resultados(driver, ['Camisa FC03'], 'FC-03, clase existente')
    shot('busqueda_existente_un_resultado')

    # Clase inexistente: volver a la acción limpia evita combinar búsquedas.
    _lista(driver)
    _buscar(driver, 'Zzz no existe')
    resultados = _resultados(driver, [], 'FC-03, clase inexistente')
    shot('busqueda_inexistente_sin_resultados')
    assert len(resultados) == 0, 'Clase inexistente: deben aparecer cero productos'


def test_fc04_archivar_producto(sesion, datos_productos, shot):
    """FC-04 | HU010 | TD: activo/archivado × sin/con filtro Archivados."""
    driver = sesion
    _capturar_sesion(driver, shot)
    referencia_a = _nuevo(driver, datos_productos, 'Prod FC04-A')
    _guardar(driver, referencia_a, 'Prod FC04-A')
    shot('producto_a_activo')
    referencia_b = _nuevo(driver, datos_productos, 'Prod FC04-B')
    producto_b = _guardar(driver, referencia_b, 'Prod FC04-B')
    shot('producto_b_activo')
    assert all(p['active'] for p in _productos(
        driver, [('default_code', 'in', [referencia_a, referencia_b])])), (
        'Precondición FC-04: ambos productos deben estar activos')

    clic(driver, '.o_cp_action_menus button')
    WebDriverWait(driver, TIMEOUT).until(EC.element_to_be_clickable((
        By.XPATH, "//*[@role='menuitem'][normalize-space()='Archive' "
        "or normalize-space()='Archivar']"))).click()
    clic(driver, '.o_dialog .modal-footer .btn-primary')
    WebDriverWait(driver, TIMEOUT).until(
        lambda d: not _productos(d, [('id', '=', producto_b)])[0]['active'],
        message='FC-04: Acción > Archivar no archivó el producto B')
    shot('producto_b_archivado')

    # Reglas 1 y 3: sin filtro, activo visible y archivado no visible.
    _lista(driver)
    _buscar(driver, 'Prod FC04-')
    sin_filtro = _resultados(driver, ['Prod FC04-A'], 'FC-04, sin filtro Archivados')
    shot('sin_filtro_activo_visible_archivado_oculto')
    assert 'Prod FC04-A' in sin_filtro, 'Regla 1: activo sin filtro debe ser visible'
    assert 'Prod FC04-B' not in sin_filtro, 'Regla 3: archivado sin filtro debe ocultarse'

    # Reglas 2 y 4: sólo Archivados, activo oculto y archivado visible.
    _lista(driver)
    _filtrar_archivados(driver)
    _buscar(driver, 'Prod FC04-')
    con_filtro = _resultados(driver, ['Prod FC04-B'], 'FC-04, con filtro Archivados')
    shot('con_filtro_activo_oculto_archivado_visible')
    assert 'Prod FC04-A' not in con_filtro, 'Regla 2: activo con filtro debe ocultarse'
    assert 'Prod FC04-B' in con_filtro, 'Regla 4: archivado con filtro debe ser visible'

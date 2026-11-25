r"""Pruebas funcionales de Daniel para Odoo 18, módulo Inventario.

Aporte correspondiente a la Entrega 2 de Calidad de Productos de Software.

Casos funcionales propios: FC-17 a FC-24 (ocho pruebas automatizadas).
La matriz y el informe final pertenecen al documento grupal Entrega 2.

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


def test_fc19_buscar_referencia(sesion, productos_daniel, shot):
    """FC-19 | RF-19 | PE: referencia interna existente e inexistente."""
    d = sesion
    referencia, nombre = _crear_producto(d, productos_daniel, 'FC19')
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


def test_fc21_modificar_costo(sesion, productos_daniel, shot):
    """FC-21 | RF-21 | PE: cambio del costo estándar y persistencia."""
    d = sesion
    referencia, _ = _crear_producto(d, productos_daniel, 'FC21', standard_price=120)
    _verificar_persistencia(d, referencia, 'standard_price', 120)
    shot('costo_inicial_120')
    _actualizar_y_recargar(d, referencia, 'standard_price', 200)
    shot('costo_final_200')


def _filtrar_archivados_daniel(driver):
    """Activa el filtro Archived desde la interfaz de Odoo 18."""

    clic(driver, ".o_searchview_dropdown_toggler")

    filtro = WebDriverWait(driver, TIMEOUT).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//div[contains(@class,'o_filter_menu')]"
            "//*[@role='menuitemcheckbox']"
            "[normalize-space()='Archived' "
            "or normalize-space()='Archivados']"
        ))
    )

    filtro.click()

    # Cerrar el menú de búsqueda.
    clic(driver, ".o_searchview_dropdown_toggler")

    WebDriverWait(driver, TIMEOUT).until(
        lambda d: any(
            e.text.strip() in ("Archived", "Archivados")
            for e in d.find_elements(
                By.CSS_SELECTOR, ".o_facet_value"
            )
        )
    )


def _estado_activo_daniel(driver, referencia):
    """Consulta exclusivamente el estado persistido del producto."""

    registros = _registros(driver, referencia)

    assert len(registros) == 1, (
        f"Se esperaba un único producto: {referencia}"
    )

    return bool(registros[0]["active"])


def test_fc20_restaurar_producto(sesion, productos_daniel, shot):
    """FC-20 | RF-20 | TE: activo -> archivado -> activo."""

    d = sesion

    # ESTADO 1: crear producto activo.
    referencia, nombre = _crear_producto(
        d, productos_daniel, "FC20"
    )

    assert _estado_activo_daniel(d, referencia) is True

    shot("01_producto_activo")

    # TRANSICIÓN 1: archivar mediante la interfaz.
    clic(d, ".o_cp_action_menus button")

    WebDriverWait(d, TIMEOUT).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//*[@role='menuitem']"
            "[normalize-space()='Archive' "
            "or normalize-space()='Archivar']"
        ))
    ).click()

    # Confirmar archivado.
    clic(d, ".o_dialog .modal-footer .btn-primary")

    WebDriverWait(d, TIMEOUT).until(
        lambda x: _estado_activo_daniel(
            x, referencia
        ) is False
    )

    # El producto archivado no debe aparecer
    # en el listado normal de productos activos.
    _abrir_lista(d)
    _buscar(d, referencia)

    WebDriverWait(d, TIMEOUT).until(
        lambda x: (
            not _nombres_lista(x)
            and any(
                e.is_displayed()
                for e in x.find_elements(
                    By.CSS_SELECTOR, ".o_view_nocontent"
                )
            )
        )
    )

    assert _nombres_lista(d) == []

    shot("02_producto_archivado_oculto")

    # ESTADO 2: localizarlo con el filtro Archived.
    _abrir_lista(d)
    _filtrar_archivados_daniel(d)
    _buscar(d, referencia)

    WebDriverWait(d, TIMEOUT).until(
        lambda x: nombre in _nombres_lista(x)
    )

    assert _nombres_lista(d) == [nombre]

    shot("03_producto_en_archivados")

    # Abrir el producto archivado.
    WebDriverWait(d, TIMEOUT).until(
        EC.element_to_be_clickable((
            By.CSS_SELECTOR,
            '.o_list_view .o_data_row td[name="name"]'
        ))
    ).click()

    esperar(d, ".o_form_view")

    # TRANSICIÓN 2: restaurar desde Acción > Unarchive.
    clic(d, ".o_cp_action_menus button")

    WebDriverWait(d, TIMEOUT).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//*[@role='menuitem']"
            "[normalize-space()='Unarchive' "
            "or normalize-space()='Desarchivar']"
        ))
    ).click()

    WebDriverWait(d, TIMEOUT).until(
        lambda x: _estado_activo_daniel(
            x, referencia
        ) is True
    )

    
    # ESTADO 3: comprobar que volvió al listado activo.
    _abrir_lista(d)
    _buscar(d, referencia)

    # Esperar a que Odoo termine de filtrar.
    # No basta con que el producto aparezca entre otros.
    WebDriverWait(
        d,
        20,
        poll_frequency=0.3
    ).until(
        lambda x: _nombres_lista(x) == [nombre],
        message=(
            "FC-20: la búsqueda no devolvió "
            "únicamente el producto restaurado"
        )
    )

    encontrados = _nombres_lista(d)

    assert encontrados == [nombre], (
        f"FC-20: resultados inesperados: {encontrados}"
    )

    assert _estado_activo_daniel(
        d, referencia
    ) is True


    shot("04_producto_restaurado_activo")

    print(
        "FC-20: activo -> archivado -> activo "
        "verificado correctamente",
        flush=True
    )



def test_fc22_existencias_iniciales(sesion, shot):
    """FC-22 | RF-22 | PE: registrar 5 unidades desde stock cero."""

    d = sesion

    # PRECONDICIÓN: un único almacén en la base de pruebas.
    almacenes = _rpc(
        d, "stock.warehouse", "search_read", [[]],
        fields=["id", "name", "lot_stock_id"],
        limit=2,
    )

    assert len(almacenes) == 1, (
        "FC-22 requiere un único almacén de pruebas."
    )

    ubicacion_id = almacenes[0]["lot_stock_id"][0]

    # Crear un producto propio desde la interfaz.
    # No usar productos_daniel: los movimientos de inventario
    # deben conservarse como evidencia y trazabilidad.
    referencia, nombre = _crear_producto(d, [], "FC22")

    print(f"Producto FC-22: {referencia}", flush=True)

    # Activar Track Inventory desde la interfaz.
    widget = esperar(
        d, '.o_field_widget[name="is_storable"]'
    )

    casilla = widget.find_element(
        By.CSS_SELECTOR, 'input[type="checkbox"]'
    )

    
    if not casilla.is_selected():
        casilla.click()
        print("FC-22: Track Inventory activado", flush=True)
    else:
        print("FC-22: Track Inventory ya estaba activo", flush=True)

    # Guardar solamente si hay cambios pendientes.
    botones_guardar = d.find_elements(
        By.CSS_SELECTOR, ".o_form_button_save"
    )

    if botones_guardar:
        if botones_guardar[0].is_displayed():
            botones_guardar[0].click()
            print("FC-22: cambios guardados", flush=True)

    # Confirmar que Odoo almacenó el cambio.
    WebDriverWait(d, TIMEOUT).until(
        lambda x: _rpc(
            x,
            "product.template",
            "search_read",
            [[("default_code", "=", referencia)]],
            fields=["is_storable"],
        )[0]["is_storable"] is True
    )

    print("FC-22: inventario habilitado", flush=True)


    # Consultar el identificador de la variante creada.
    plantilla = _registros(d, referencia)[0]

    variantes = WebDriverWait(d, TIMEOUT).until(
        lambda x: _rpc(
            x, "product.product", "search_read",
            [[("product_tmpl_id", "=", plantilla["id"])]],
            fields=["id", "is_storable"],
        )
    )

    assert len(variantes) == 1
    assert variantes[0]["is_storable"] is True

    producto_id = variantes[0]["id"]

    def cantidad_en_almacen(driver):
        quants = _rpc(
            driver, "stock.quant", "search_read",
            [[
                ("product_id", "=", producto_id),
                ("location_id", "=", ubicacion_id),
            ]],
            fields=["quantity"],
        )
        return sum(float(q["quantity"]) for q in quants)

    # Verificar inventario inicial.
    assert cantidad_en_almacen(d) == 0, (
        "El producto no comenzó con inventario cero"
    )

    shot("fc10_stock_inicial_cero")

    # Acción funcional desde el formulario del producto.
    boton = WebDriverWait(d, TIMEOUT).until(
        lambda x: next(
            (
                e for e in x.find_elements(
                    By.CSS_SELECTOR,
                    '.o_form_view button'
                    '[name="action_update_quantity_on_hand"]'
                )
                if e.is_displayed() and e.is_enabled()
            ),
            False,
        )
    )

    boton.click()

    # El formulario simplificado puede variar según permisos
    # de inventario y ubicaciones avanzadas.
    try:
        esperar(
            d,
            '.o_dialog .o_field_widget'
            '[name="new_quantity"] input',
            timeout=8,
        )
    except TimeoutException:
        shot("fc10_interfaz_alternativa")
        pytest.fail(
            "Odoo abrió una interfaz de cantidades distinta "
            "del formulario simplificado. Revisar la captura "
            "antes de automatizar la aplicación del ajuste."
        )

    # Registrar el conteo físico.
    _escribir(d, "new_quantity", 5)

    shot("fc10_conteo_cinco")

    clic(
        d,
        '.o_dialog button[name="change_product_qty"]'
    )

    # Verificar que Odoo registró las cinco unidades.
    WebDriverWait(d, 20).until(
        lambda x: cantidad_en_almacen(x) == 5,
        message="No se persistieron las cinco unidades"
    )

    # Verificar trazabilidad del ajuste.
    movimientos = _rpc(
        d, "stock.move", "search_read",
        [[
            ("product_id", "=", producto_id),
            ("is_inventory", "=", True),
            ("state", "=", "done"),
        ]],
        fields=["id", "state"],
    )

    assert movimientos, (
        "No se encontró un movimiento de inventario validado"
    )

    d.refresh()
    shot("fc10_existencias_finales")

    print(
        f"FC-22 PASSED: {referencia}, 0 -> 5 unidades. "
        f"Movimientos: {len(movimientos)}",
        flush=True,
    )

    print(
        "Producto conservado en la base de pruebas "
        "para mantener la trazabilidad del ajuste.",
        flush=True,
    )



def test_fc23_ajuste_positivo(sesion, shot):
    """FC-23 | RF-23 | VL: incremento mínimo de 5 a 6 unidades."""

    d = sesion

    almacenes = _rpc(
        d, "stock.warehouse", "search_read", [[]],
        fields=["id", "lot_stock_id"],
        limit=2,
    )
    assert len(almacenes) == 1, (
        "FC-23 requiere un único almacén de pruebas"
    )

    ubicacion_id = almacenes[0]["lot_stock_id"][0]

    # Producto exclusivo de esta prueba.
    # Se conserva por sus movimientos de inventario.
    referencia, _ = _crear_producto(d, [], "FC23")
    print(f"Producto FC-23: {referencia}", flush=True)

    widget = esperar(
        d, '.o_field_widget[name="is_storable"]'
    )
    casilla = widget.find_element(
        By.CSS_SELECTOR, 'input[type="checkbox"]'
    )

    if not casilla.is_selected():
        casilla.click()
        clic(d, ".o_form_button_save")

    plantilla = _registros(d, referencia)[0]

    variantes = WebDriverWait(d, TIMEOUT).until(
        lambda x: _rpc(
            x, "product.product", "search_read",
            [[("product_tmpl_id", "=", plantilla["id"])]],
            fields=["id", "is_storable"],
        )
    )

    assert len(variantes) == 1
    assert variantes[0]["is_storable"] is True

    producto_id = variantes[0]["id"]

    def cantidad(driver):
        registros = _rpc(
            driver, "stock.quant", "search_read",
            [[
                ("product_id", "=", producto_id),
                ("location_id", "=", ubicacion_id),
            ]],
            fields=["quantity"],
        )
        return sum(float(r["quantity"]) for r in registros)

    def movimientos(driver):
        return _rpc(
            driver, "stock.move", "search_read",
            [[
                ("product_id", "=", producto_id),
                ("is_inventory", "=", True),
                ("state", "=", "done"),
            ]],
            fields=["id"],
        )

    def aplicar_conteo(nueva_cantidad):
        boton = WebDriverWait(d, TIMEOUT).until(
            lambda x: next(
                (
                    e for e in x.find_elements(
                        By.CSS_SELECTOR,
                        '.o_form_view button'
                        '[name="action_update_quantity_on_hand"]'
                    )
                    if e.is_displayed() and e.is_enabled()
                ),
                False,
            )
        )
        boton.click()

        esperar(
            d,
            '.o_dialog .o_field_widget'
            '[name="new_quantity"] input',
            timeout=8,
        )

        _escribir(d, "new_quantity", nueva_cantidad)
        shot(f"conteo_{nueva_cantidad}")

        clic(
            d,
            '.o_dialog button[name="change_product_qty"]'
        )

        WebDriverWait(d, TIMEOUT).until(
            EC.invisibility_of_element_located((
                By.CSS_SELECTOR, ".o_dialog"
            ))
        )

    # Precondición: producto nuevo con cero existencias.
    assert cantidad(d) == pytest.approx(0)
    assert len(movimientos(d)) == 0

    # Preparación por la UI: 0 -> 5.
    aplicar_conteo(5)

    WebDriverWait(d, 20).until(
        lambda x: cantidad(x) == pytest.approx(5)
    )

    anteriores = movimientos(d)
    assert len(anteriores) == 1

    shot("stock_inicial_cinco")
    print("FC-23: precondición de 5 unidades confirmada")

    d.refresh()
    esperar(d, ".o_form_view")

    # Escenario evaluado: 5 -> 6 (+1 unidad).
    aplicar_conteo(6)

    WebDriverWait(d, 20).until(
        lambda x: cantidad(x) == pytest.approx(6)
    )

    posteriores = movimientos(d)

    ids_anteriores = {m["id"] for m in anteriores}
    ids_posteriores = {m["id"] for m in posteriores}

    nuevos_movimientos = (
        ids_posteriores - ids_anteriores
    )

    assert len(nuevos_movimientos) == 1, (
        "Se esperaba un nuevo movimiento de ajuste"
    )

    assert cantidad(d) == pytest.approx(6)

    d.refresh()
    esperar(d, ".o_form_view")
    shot("stock_final_seis")

    print(
        f"FC-23 PASSED: {referencia}, "
        "5 -> 6 unidades (+1). "
        "Un nuevo movimiento confirmado.",
        flush=True,
    )

    print(
        "Producto conservado para trazabilidad.",
        flush=True,
    )



def test_fc24_ajuste_negativo(sesion, shot):
    """FC-24 | RF-24 | TD: ajustes 5->4 y 5->0."""

    d = sesion

    almacenes = _rpc(
        d, "stock.warehouse", "search_read", [[]],
        fields=["id", "lot_stock_id"],
        limit=2,
    )

    assert len(almacenes) == 1, (
        "FC-24 requiere un único almacén de pruebas"
    )

    ubicacion_id = almacenes[0]["lot_stock_id"][0]

    def cantidad(producto_id):
        registros = _rpc(
            d, "stock.quant", "search_read",
            [[
                ("product_id", "=", producto_id),
                ("location_id", "=", ubicacion_id),
            ]],
            fields=["quantity"],
        )
        return sum(float(r["quantity"]) for r in registros)

    def movimientos(producto_id):
        return _rpc(
            d, "stock.move", "search_read",
            [[
                ("product_id", "=", producto_id),
                ("is_inventory", "=", True),
                ("state", "=", "done"),
            ]],
            fields=[
                "id",
                "product_uom_qty",
                "location_id",
                "location_dest_id",
            ],
        )

    def aplicar_conteo(nueva_cantidad, etiqueta):
        boton = WebDriverWait(d, TIMEOUT).until(
            lambda x: next(
                (
                    e for e in x.find_elements(
                        By.CSS_SELECTOR,
                        '.o_form_view button'
                        '[name="action_update_quantity_on_hand"]'
                    )
                    if e.is_displayed() and e.is_enabled()
                ),
                False,
            )
        )

        boton.click()

        esperar(
            d,
            '.o_dialog .o_field_widget'
            '[name="new_quantity"] input',
        )

        _escribir(d, "new_quantity", nueva_cantidad)

        shot(f"{etiqueta}_conteo_{nueva_cantidad}")

        clic(
            d,
            '.o_dialog button[name="change_product_qty"]'
        )

        WebDriverWait(d, TIMEOUT).until(
            EC.invisibility_of_element_located((
                By.CSS_SELECTOR, ".o_dialog"
            ))
        )

    # Dos reglas independientes de la tabla de decisión.
    escenarios = [
        ("R1", 4),
        ("R2", 0),
    ]

    for regla, cantidad_final in escenarios:

        # Crear un producto exclusivo para cada escenario.
        referencia, _ = _crear_producto(
            d, [], f"FC24{regla}"
        )

        print(
            f"FC-24 {regla}: producto {referencia}",
            flush=True,
        )

        widget = esperar(
            d, '.o_field_widget[name="is_storable"]'
        )

        casilla = widget.find_element(
            By.CSS_SELECTOR, 'input[type="checkbox"]'
        )

        if not casilla.is_selected():
            casilla.click()
            clic(d, ".o_form_button_save")

        plantilla = _registros(d, referencia)[0]

        variantes = WebDriverWait(d, TIMEOUT).until(
            lambda x: _rpc(
                x, "product.product", "search_read",
                [[
                    ("product_tmpl_id", "=", plantilla["id"])
                ]],
                fields=["id", "is_storable"],
            )
        )

        assert len(variantes) == 1
        assert variantes[0]["is_storable"] is True

        producto_id = variantes[0]["id"]

        # Precondición: producto nuevo sin inventario.
        assert cantidad(producto_id) == pytest.approx(0)
        assert len(movimientos(producto_id)) == 0

        # Preparación: 0 -> 5 unidades.
        aplicar_conteo(5, regla)

        WebDriverWait(d, 20).until(
            lambda x: cantidad(producto_id)
            == pytest.approx(5)
        )

        anteriores = movimientos(producto_id)
        assert len(anteriores) == 1

        shot(f"{regla}_stock_inicial_cinco")

        d.refresh()
        esperar(d, ".o_form_view")

        # Ejecutar el escenario: 5 -> 4 o 5 -> 0.
        aplicar_conteo(cantidad_final, regla)

        WebDriverWait(d, 20).until(
            lambda x: cantidad(producto_id)
            == pytest.approx(cantidad_final)
        )

        posteriores = movimientos(producto_id)

        ids_anteriores = {m["id"] for m in anteriores}

        nuevos = [
            m for m in posteriores
            if m["id"] not in ids_anteriores
        ]

        assert len(nuevos) == 1, (
            f"{regla}: se esperaba un nuevo movimiento"
        )

        movimiento = nuevos[0]
        diferencia = 5 - cantidad_final

        # Verificar la magnitud del decremento.
        assert float(
            movimiento["product_uom_qty"]
        ) == pytest.approx(diferencia), (
            f"{regla}: cantidad del movimiento incorrecta"
        )

        # Verificar que el stock sale de WH/Stock.
        assert movimiento["location_id"][0] == ubicacion_id, (
            f"{regla}: origen del movimiento incorrecto"
        )

        assert (
            movimiento["location_dest_id"][0] != ubicacion_id
        ), (
            f"{regla}: destino del movimiento incorrecto"
        )

        # Verificar nuevamente la cantidad final.
        assert cantidad(producto_id) == pytest.approx(
            cantidad_final
        )

        d.refresh()
        esperar(d, ".o_form_view")

        shot(f"{regla}_resultado_{cantidad_final}")

        print(
            f"FC-24 {regla} PASSED: "
            f"5 -> {cantidad_final} unidades "
            f"(-{diferencia}). "
            "Movimiento confirmado.",
            flush=True,
        )

    print(
        "FC-24: ambas reglas verificadas. "
        "Productos conservados para trazabilidad.",
        flush=True,
    )

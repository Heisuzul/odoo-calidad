"""Prueba de humo: confirma que el entorno, el login y los selectores básicos funcionan."""
import time

from conftest import abrir_accion, clic, esperar


def test_smoke_crear_producto(sesion, shot):
    driver = sesion
    shot("login_exitoso")

    abrir_accion(driver, "stock.product_template_action_product")
    shot("lista_de_productos")

    clic(driver, ".o_list_button_add, .o-kanban-button-new")
    esperar(driver, ".o_form_view")
    time.sleep(2)  # Odoo deja el campo Nombre activo al abrir el formulario

    nombre = f"Producto humo {int(time.time())}"
    driver.switch_to.active_element.send_keys(nombre)  # escribir sin hacer clic
    shot("formulario_con_nombre")

    clic(driver, ".o_form_button_save")
    time.sleep(2)
    shot("producto_guardado")

    migas = esperar(driver, ".o_breadcrumb").text
    assert nombre in migas, f"No se ve el producto guardado: {migas!r}"
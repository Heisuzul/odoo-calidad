"""Configuración común de las pruebas funcionales (Selenium + pytest).

Variables de entorno opcionales:
  ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASS, ODOO_VERSION (17 o 18), HEADLESS=1
Las capturas se guardan en ../evidencia/<nombre_de_la_prueba>/.
"""
import os
import pathlib
import time

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "calidad")
ODOO_USER = os.getenv("ODOO_USER", "admin")
ODOO_PASS = os.getenv("ODOO_PASS", "admin")
ODOO_VERSION = int(os.getenv("ODOO_VERSION", "18"))
HEADLESS = os.getenv("HEADLESS", "0") == "1"
EVIDENCIA = pathlib.Path(__file__).resolve().parent.parent / "evidencia"
TIMEOUT = 15


# ---------- ejecución y evidencias ----------
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    setattr(item, "rep_" + call.when, outcome.get_result())


@pytest.fixture
def driver(request):    
    opts = Options()

    if HEADLESS:
        opts.add_argument("--headless=new")

    opts.add_argument("--window-size=1600,1000")

    # Evitar ventanas emergentes del gestor de contraseñas.
    opts.add_experimental_option("prefs", {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.password_manager_leak_detection": False,
    })

    opts.add_argument("--disable-features=PasswordLeakDetection")

    drv = webdriver.Chrome(options=opts)

    drv.implicitly_wait(0)
    yield drv
    rep = getattr(request.node, "rep_call", None)
    if rep is not None and rep.failed:
        carpeta = EVIDENCIA / request.node.name
        carpeta.mkdir(parents=True, exist_ok=True)
        drv.save_screenshot(str(carpeta / "FALLO.png"))
    drv.quit()


@pytest.fixture
def shot(driver, request):
    """shot('descripcion_del_paso') guarda una captura numerada como evidencia."""
    carpeta = EVIDENCIA / request.node.name
    carpeta.mkdir(parents=True, exist_ok=True)
    contador = {"n": 0}

    def _shot(paso):
        contador["n"] += 1
        driver.save_screenshot(str(carpeta / f"{contador['n']:02d}_{paso}.png"))

    return _shot


# ---------- ayudas para Odoo ----------
def esperar(driver, css, timeout=TIMEOUT):
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, css)))


def clic(driver, css, timeout=TIMEOUT):
    WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, css))).click()


def login(driver, usuario=None, clave=None):
    driver.get(f"{BASE_URL}/web/login?db={ODOO_DB}")
    esperar(driver, "input[name='login']").send_keys(usuario or ODOO_USER)
    driver.find_element(By.CSS_SELECTOR, "input[name='password']").send_keys(clave or ODOO_PASS)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    esperar(driver, ".o_main_navbar")


def abrir_accion(driver, xmlid):
    """Abre una acción de Odoo por su id externo (no depende del idioma de la interfaz)."""
    if ODOO_VERSION >= 18:
        driver.get(f"{BASE_URL}/odoo/action-{xmlid}")
    else:
        driver.get(f"{BASE_URL}/web#action={xmlid}")
    esperar(driver, ".o_action_manager, .o_content")
    time.sleep(1)


@pytest.fixture
def sesion(driver):
    login(driver)
    return driver

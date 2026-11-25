# Vuelca el código fuente real de métodos candidatos para las pruebas unitarias.
# Se ejecuta dentro del shell de Odoo (ver README). Imprime la fuente de cada método.
import inspect

CANDIDATOS = [
    ("stock.quant", "check_quantity"),
    ("stock.quant", "_get_available_quantity"),
    ("stock.quant", "_update_available_quantity"),
    ("stock.quant", "_update_reserved_quantity"),
    ("stock.quant", "_compute_inventory_diff_quantity"),
    ("stock.quant", "action_apply_inventory"),
    ("stock.warehouse.orderpoint", "_compute_qty_to_order"),
    ("stock.warehouse.orderpoint", "_compute_qty"),
    ("stock.lot", "_check_unique_lot"),
    ("product.product", "_check_barcode_uniqueness"),
    ("product.product", "_compute_quantities_dict"),
    ("product.template", "_compute_quantities_dict"),
    ("product.template", "action_archive"),
    ("product.category", "_compute_complete_name"),
    ("stock.move", "_compute_product_qty"),
]

for modelo, metodo in CANDIDATOS:
    print("=" * 80)
    try:
        fn = getattr(env[modelo], metodo)
        print(f"# {modelo}.{metodo}   ({inspect.getsourcefile(fn)})")
        print(inspect.getsource(fn))
    except Exception as e:
        print(f"# {modelo}.{metodo}  -> NO DISPONIBLE en esta versión: {e}")

# Kevin: TODO desarrollar pruebas para 2 métodos reales de Odoo 18.
# TODO método 1: StockQuant._get_available_quantity (stock.quant).
# Fuente: odoo/addons/stock/models/stock_quant.py.
# TODO analizar seguimiento por lotes, reservas, strict y allow_negative;
# diseñar casos de sentencias/ramas y comprobar las cantidades resultantes.
# TODO método 2: StockLot._check_unique_lot (stock.lot).
# Fuente: odoo/addons/stock/models/stock_lot.py.
# TODO probar unicidad por producto/compañía y ValidationError por duplicados.
# TODO usar TransactionCase y revertir todos los datos creados.

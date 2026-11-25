"""Regenera cuatro PNG y metricas desde las evidencias reales de Kevin.

Desde raiz: .venv\\Scripts\\python.exe docs/generar_graficos_kevin.py
Dependencia adicional: matplotlib (python -m pip install matplotlib).
"""
from pathlib import Path
import json
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'evidencia' / 'graficos_kevin'


def main():
    raw = (ROOT / 'evidencia/test_unit_kevin/salida.txt').read_bytes()
    text = raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig')
    unit = json.loads(next(line.split('=', 1)[1] for line in text.splitlines()
                           if line.startswith('KEVIN_RESULT_JSON=')))
    cases = []
    tree = ET.parse(ROOT / 'evidencia/resultados_kevin.xml')
    for case in tree.findall('.//testcase'):
        status = 'PASS'
        for tag, label in [('failure', 'FAIL'), ('error', 'ERROR'), ('skipped', 'SKIP')]:
            if case.find(tag) is not None:
                status = label
        cases.append({'name': case.attrib['name'], 'status': status,
                      'seconds': float(case.attrib['time'])})
    if len(cases) != 14 or unit['tests'] != 6:
        raise RuntimeError('Se requiere la corrida completa: 14 funcionales y 6 unitarias')
    OUT.mkdir(parents=True, exist_ok=True)
    metrics = {'functional': cases, 'unit': unit,
               'nonconformities': [],
               'nc_note': 'Clasificacion manual del informe; no inferida automaticamente de pytest.',
               'timestamp': tree.find('.//testsuite').attrib.get('timestamp')}
    (OUT / 'datos_reales.json').write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding='utf-8')
    (ROOT / 'evidencia/test_unit_kevin/cobertura.json').write_text(
        json.dumps(unit, indent=2, ensure_ascii=False), encoding='utf-8')

    def chart(filename, title, labels, values, ylabel, maximum=None):
        fig, ax = plt.subplots(figsize=(9, 5))
        bars = ax.bar(labels, values, color=['#237a57', '#236a93', '#947028', '#6a5392'][:len(labels)])
        ax.bar_label(bars, padding=3)
        ax.set(title=title, ylabel=ylabel)
        ax.set_ylim(0, maximum or max(max(values) * 1.2, 1))
        fig.tight_layout()
        fig.savefig(OUT / filename, dpi=150)
        plt.close(fig)

    passed = sum(c['status'] == 'PASS' for c in cases)
    u_passed = unit['tests'] - unit['failures'] - unit['errors'] - unit['skipped']
    chart('01_resultados.png', 'Resultados reales por tipo (escenarios)',
          ['Func. PASS', 'Func. no PASS', 'Unit. PASS', 'Unit. no PASS'],
          [passed, len(cases)-passed, u_passed, unit['tests']-u_passed], 'Escenarios')
    pe_pass = passed
    vl_pass = sum(c['status'] == 'PASS' and not c['name'].startswith('test_FC13') for c in cases)
    fig, ax = plt.subplots(figsize=(9, 5))
    labels = ['PE', 'VL', 'Ramas + caminos']
    ax.bar(labels, [pe_pass, vl_pass, u_passed], label='PASS', color='#237a57')
    ax.bar(labels, [14-pe_pass, 11-vl_pass, 6-u_passed],
           bottom=[pe_pass, vl_pass, u_passed], label='No PASS', color='#ad4242')
    ax.set(title='Resultado por tecnica (PE/VL se solapan)', ylabel='Escenarios')
    ax.legend()
    for x, n in enumerate([pe_pass, vl_pass, u_passed]):
        ax.text(x, n, str(n), ha='center', va='bottom')
    fig.tight_layout()
    fig.savefig(OUT / '02_tecnicas.png', dpi=150)
    plt.close(fig)
    chart('03_no_conformidades.png', 'No conformidades confirmadas: ninguna',
          ['Critica', 'Alta', 'Media', 'Baja'], [0, 0, 0, 0], 'NC confirmadas', 1)
    chart('04_cobertura.png', 'Cobertura limitada al metodo check_quantity',
          ['Sentencias cubiertas', 'Sentencias pendientes', 'Arcos cubiertos', 'Arcos pendientes'],
          [len(unit['covered_statement_lines']),
           len(unit['statement_lines'])-len(unit['covered_statement_lines']),
           len(unit['covered_branch_arcs']),
           len(unit['branch_arcs'])-len(unit['covered_branch_arcs'])], 'Lineas / arcos')
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    main()

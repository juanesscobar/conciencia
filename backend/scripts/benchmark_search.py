"""Search benchmark (spec §40) — mide las 5 queries de referencia.

Uso: python scripts/benchmark_search.py [--json]
Mide: interpretación NL, total de resultados, latencia, precision proxy
(% de resultados cuyo sector/región matchea lo esperado).

Requiere la DB local con leads (backend/). No toca red (solo búsqueda local).
"""

import argparse
import json
import sys
import time
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.modules.leadhunter.nlu import interpret_with_llm_fallback
from app.modules.leadhunter.search import SearchEngine, SearchQuery

# spec §40: queries de referencia con expectativas
BENCHMARK_QUERIES = [
    {
        "query": "playas de autos usados en Ciudad del Este",
        "expected_keywords": ["automotriz", "auto", "vehiculo"],
        "expected_geo": "ciudad del este",
    },
    {
        "query": "empresas logísticas en Paraguay",
        "expected_keywords": ["logistica", "transporte", "carga"],
        "expected_geo": None,
    },
    {
        "query": "farmacias en Asunción con teléfono",
        "expected_keywords": ["farmacia"],
        "expected_geo": "asuncion",
    },
    {
        "query": "distribuidoras de bebidas en Central",
        "expected_keywords": ["distribuidora"],
        "expected_geo": "central",
    },
    {
        "query": "cooperativas con website",
        "expected_keywords": ["cooperativa"],
        "expected_geo": None,
    },
]


def _norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def run_benchmark() -> list:
    db = SessionLocal()
    engine = SearchEngine()
    results = []
    try:
        for case in BENCHMARK_QUERIES:
            t0 = time.time()
            try:
                sq = interpret_with_llm_fallback(case["query"], default_country="PY")
            except Exception as e:  # noqa: BLE001
                results.append({"query": case["query"], "error": f"interpret falló: {e}"})
                continue
            t_interpret = (time.time() - t0) * 1000

            t0 = time.time()
            res = engine.execute(db, sq)
            t_search = (time.time() - t0) * 1000

            # precision proxy: sector esperado + geografía esperada
            matched_industry = 0
            matched_geo = 0
            for item in res.items:
                ind = _norm(item.industry or "")
                if any(k in ind for k in case["expected_keywords"]):
                    matched_industry += 1
                if case["expected_geo"] and item.region and _norm(case["expected_geo"]) in _norm(item.region):
                    matched_geo += 1
            n = max(1, res.total)
            results.append({
                "query": case["query"],
                "filters": {k: v for k, v in sq.filter_fields().items() if v},
                "total": res.total,
                "interpret_ms": round(t_interpret, 1),
                "search_ms": round(t_search, 1),
                "precision_sector": round(matched_industry / min(n, res.page_size) * 100),
                "precision_geo": round(matched_geo / min(n, res.page_size) * 100) if case["expected_geo"] else None,
            })
    finally:
        db.close()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Search benchmark (spec §40)")
    parser.add_argument("--json", action="store_true", help="Salida JSON")
    args = parser.parse_args()

    results = run_benchmark()
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    print(f"{'QUERY':<42} {'TOTAL':>6} {'INT(ms)':>8} {'SRCH(ms)':>9} {'SECTOR%':>8} {'GEO%':>6}")
    print("-" * 85)
    for r in results:
        if "error" in r:
            print(f"{r['query'][:40]:<42} ERROR: {r['error']}")
            continue
        print(f"{r['query'][:40]:<42} {r['total']:>6} {r['interpret_ms']:>8} {r['search_ms']:>9} "
              f"{r['precision_sector']:>7}% {str(r['precision_geo'])+'%' if r['precision_geo'] is not None else '—':>6}")
    avg_search = sum(r.get("search_ms", 0) for r in results if "error" not in r) / max(1, len([r for r in results if "error" not in r]))
    print(f"\nLatencia promedio de búsqueda: {avg_search:.1f} ms")


if __name__ == "__main__":
    main()

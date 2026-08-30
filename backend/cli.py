"""CLI `conciencia` — misma lógica de dominio que UI/API (spec §19/§41).

Usa los MISMOS services que la Web (search.py, discovery.py, ranking.py, geo.py)
— cero backend duplicado. Ejecutá:

    cd backend
    .venv\\Scripts\\conciencia --help
    .venv\\Scripts\\conciencia search "empresas logísticas" --country PY
    .venv\\Scripts\\conciencia leads export --format csv --out leads.csv
    .venv\\Scripts\\conciencia lead score <id>

En tests se puede apuntar a otra DB con DATABASE_URL.
"""

import csv
import io
import json
import os
import sys
from datetime import datetime
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

# El CLI puede correr desde cualquier CWD: garantizamos que `app` resuelva
# (válido para `python cli.py` y para el entry point `conciencia`).
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.database import SessionLocal
from app.modules.leadhunter.models import Lead, LeadStatus
from app.modules.leadhunter.search import SearchEngine, SearchQuery
from app.modules.leadhunter.ranking import (
    lead_score, opportunity_score, data_quality_score, explain,
    get_ranking_weights, enrich_lead_dict,
)
from app.modules.leadhunter.service import compute_score
from app.modules.leadhunter.enrich import enrich_from_website
from app.modules.leadhunter.discovery import run_discovery, add_event

app = typer.Typer(
    name="conciencia",
    help="Conciencia Platform — Control Plane CLI (misma lógica que UI/API).",
    no_args_is_help=True,
)
leads_app = typer.Typer(help="Leads: listar, exportar, inspeccionar.")
lead_app = typer.Typer(help="Lead individual: inspect, enrich, score.")
config_app = typer.Typer(help="Configuración persistente (Settings).")
app.add_typer(leads_app, name="leads")
app.add_typer(lead_app, name="lead")
app.add_typer(config_app, name="config")

console = Console()

CONFIG_KEY_MAP = {
    "search.country": "SEARCH_DEFAULT_COUNTRY",
    "search.region": "SEARCH_DEFAULT_REGION",
    "search.city": "SEARCH_DEFAULT_CITY",
    "search.scope": "SEARCH_SCOPE",
    "leadhunter.cron": "LEADHUNTER_CRON",
    "leadhunter.bbox": "LEADHUNTER_BBOX",
    "embeddings.enabled": "EMBEDDING_ENABLED",
    "embeddings.model": "EMBEDDING_MODEL",
    "embeddings.provider": "EMBEDDING_PROVIDER",
    "embeddings.backend": "EMBEDDING_BACKEND",
    "ranking.weights": "RANKING_WEIGHTS",
}

MODULES = [
    ("core", "Núcleo reutilizable: config, permisos, audit, eventos", "active"),
    ("leadhunter", "Prospección + pipeline CRM + búsqueda (NL/semántica)", "active"),
    ("crm", "Clientes y seguimiento", "planned"),
    ("erp", "Facturación, inventario, finanzas", "planned"),
    ("logistics", "Operación logística", "planned"),
    ("software-engineering", "Workspace de ingeniería (repos, tareas, agentes)", "planned"),
]


def _make_session():
    """Sesión propia del CLI: respeta DATABASE_URL (para tests/deploy)."""
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        kw = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
        engine = create_engine(url, **kw)
        return sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    return SessionLocal()


def _json(obj) -> None:
    console.print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def _lead_rows(db, leads: List[Lead], sq: Optional[SearchQuery] = None) -> list:
    """Leads enriquecidos (Fase 4) para salida JSON/CSV."""
    out = []
    for lead in leads:
        d = enrich_lead_dict(lead, db=db, sq=sq)
        out.append(d)
    return out


@app.command("health")
def health():
    """Estado del sistema: DB, conteos, embeddings."""
    db = _make_session()
    try:
        from app.modules.leadhunter.embeddings import embeddings_enabled, embedding_model, get_backend
        leads = db.query(Lead).count()
        agents = 0
        try:
            from app.models.agent import Agent
            agents = db.query(Agent).count()
        except Exception:
            pass
        table = Table(title="Conciencia health")
        table.add_column("Componente", style="cyan")
        table.add_column("Estado", style="green")
        table.add_row("Base de datos", "ok")
        table.add_row("Leads", str(leads))
        table.add_row("Agentes", str(agents))
        table.add_row("Embeddings", f"{'enabled' if embeddings_enabled() else 'disabled'} · {embedding_model()}")
        console.print(table)
    finally:
        db.close()


def _search(db, text: Optional[str], country: Optional[str], region: Optional[str],
            city: Optional[str], category: Optional[str], industry: Optional[str],
            segment: Optional[str], online: Optional[str], min_score: Optional[int],
            sort: str, limit: int) -> SearchQuery:
    sq = SearchQuery(
        query=text or None,
        country=country,
        region=region,
        city=city,
        category=category,
        industry=industry,
        segment=segment,
        online=online,
        min_score=min_score,
        sort=sort,
        page_size=min(200, limit),
        page=1,
    )
    return sq


@app.command("search")
def search(
    query: str = typer.Argument("", help="Texto libre (opcional si usás filtros)"),
    country: Optional[str] = typer.Option(None, "--country", "-c", help="País (default PY)"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Región/ciudad"),
    city: Optional[str] = typer.Option(None, "--city", help="Ciudad específica"),
    category: Optional[str] = typer.Option(None, "--category", help="Categoría canónica"),
    industry: Optional[str] = typer.Option(None, "--industry", help="Industria libre"),
    segment: Optional[str] = typer.Option(None, "--segment", help="pyme|mediana|corporativo"),
    online: Optional[str] = typer.Option(None, "--online", help="website|email|phone|any"),
    min_score: Optional[int] = typer.Option(None, "--min-score", help="Score mínimo"),
    sort: str = typer.Option("score", "--sort", help="newest|oldest|score|company"),
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=200),
    json_out: bool = typer.Option(False, "--json", help="Salida JSON"),
):
    """Busca leads (misma lógica que POST /api/v1/leads/search)."""
    db = _make_session()
    try:
        sq = _search(db, query, country, region, city, category, industry, segment, online, min_score, sort, limit)
        res = SearchEngine().execute(db, sq)
        lead_objs = [db.get(Lead, item.id) for item in res.items]
        lead_objs = [l for l in lead_objs if l is not None]
        if json_out:
            _json({"total": res.total, "items": _lead_rows(db, lead_objs, sq)})
            return
        if not res.items:
            console.print("Sin resultados.", style="yellow")
            return
        rows = _lead_rows(db, lead_objs, sq)
        table = Table(title=f"Leads ({res.total} total)")
        for col in ("Empresa", "Región", "Sector", "Score", "Oport.", "Calidad"):
            table.add_column(col, style="cyan" if col == "Empresa" else None)
        for r in rows:
            table.add_row(
                r["company"], r.get("region") or "—", r.get("industry") or "—",
                str(r.get("score")), str(r.get("opportunity_score") or "—"), str(r.get("data_quality") or "—"),
            )
        console.print(table)
    finally:
        db.close()


@leads_app.command("list")
def leads_list(
    status: Optional[str] = typer.Option(None, "--status", help="new|contacted|qualified|proposal|won|lost"),
    source: Optional[str] = typer.Option(None, "--source", help="manual|conciencia|overpass|..." ),
    region: Optional[str] = typer.Option(None, "--region"),
    industry: Optional[str] = typer.Option(None, "--industry"),
    sort: str = typer.Option("newest", "--sort"),
    limit: int = typer.Option(50, "--limit", "-n", min=1, max=200),
    json_out: bool = typer.Option(False, "--json"),
):
    """Lista leads (igual que GET /api/v1/leads/)."""
    db = _make_session()
    try:
        q = db.query(Lead)
        if status:
            q = q.filter(Lead.status == LeadStatus(status))
        if source:
            q = q.filter(Lead.source == source)
        if region:
            q = q.filter(Lead.region.ilike(f"%{region}%"))
        if industry:
            q = q.filter(Lead.industry.ilike(f"%{industry}%"))
        order = {"oldest": Lead.created_at.asc(), "company": Lead.company.asc(),
                 "score": Lead.score.desc()}.get(sort, Lead.created_at.desc())
        leads = q.order_by(order).limit(limit).all()
        if json_out:
            _json({"total": len(leads), "items": _lead_rows(db, leads)})
            return
        if not leads:
            console.print("Sin leads.", style="yellow")
            return
        table = Table(title=f"Leads ({len(leads)})")
        for col in ("Empresa", "Región", "Sector", "Score", "Status"):
            table.add_column(col, style="cyan" if col == "Empresa" else None)
        for l in leads:
            table.add_row(l.company, l.region or "—", l.industry or "—", str(l.score), l.status.value if hasattr(l.status, "value") else str(l.status))
        console.print(table)
    finally:
        db.close()


@leads_app.command("export")
def leads_export(
    fmt: str = typer.Option("csv", "--format", "-f", help="csv|json"),
    out: str = typer.Option("-", "--out", "-o", help="Archivo de salida ('-' = stdout)"),
    limit: int = typer.Option(5000, "--limit", "-n", min=1, max=100000),
    status: Optional[str] = typer.Option(None, "--status"),
):
    """Exporta leads a CSV/JSON (spec §38)."""
    db = _make_session()
    try:
        q = db.query(Lead).order_by(Lead.created_at.desc())
        if status:
            q = q.filter(Lead.status == LeadStatus(status))
        leads = q.limit(limit).all()
        rows = _lead_rows(db, leads)
        payload = ""
        if fmt == "json":
            payload = json.dumps(rows, ensure_ascii=False, indent=2, default=str)
        else:
            buf = io.StringIO()
            fieldnames = ["id", "company", "contact_name", "email", "phone", "website",
                          "source", "industry", "segment", "region", "status", "score",
                          "opportunity_score", "data_quality", "created_at"]
            writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
            payload = buf.getvalue()
        if out == "-":
            console.print(payload)
        else:
            with open(out, "w", encoding="utf-8", newline="") as f:
                f.write(payload)
            console.print(f"{len(leads)} leads exportados a {out}", style="green")
    finally:
        db.close()


def _get_lead(db, lead_id: str) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        console.print(f"Lead no encontrado: {lead_id}", style="red")
        raise typer.Exit(1)
    return lead


@lead_app.command("inspect")
def lead_inspect(
    lead_id: str = typer.Argument(..., help="ID del lead"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Muestra detalle completo de un lead (con scores Fase 4)."""
    db = _make_session()
    try:
        lead = _get_lead(db, lead_id)
        d = enrich_lead_dict(lead, db=db)
        if json_out:
            _json(d)
            return
        table = Table(title=lead.company)
        table.add_column("Campo", style="cyan")
        table.add_column("Valor")
        for k in ("id", "contact_name", "email", "phone", "website", "source", "industry",
                  "segment", "region", "status", "score", "opportunity_score", "data_quality"):
            table.add_row(k, str(d.get(k) or "—"))
        console.print(table)
        if d.get("reasons"):
            console.print("\n[cyan]¿Por qué este lead?[/cyan]")
            for r in d["reasons"]:
                console.print(f"  ▸ {r}")
    finally:
        db.close()


@lead_app.command("score")
def lead_score_cmd(
    lead_id: str = typer.Argument(...),
    json_out: bool = typer.Option(False, "--json"),
):
    """Muestra los scores separados del lead (spec §16)."""
    db = _make_session()
    try:
        lead = _get_lead(db, lead_id)
        weights = get_ranking_weights(db)
        d = {
            "id": lead.id,
            "company": lead.company,
            "lead_score": lead_score(lead, weights),
            "opportunity_score": opportunity_score(lead, weights),
            "data_quality": data_quality_score(lead),
            "persisted_score": lead.score,
            "reasons": explain(lead, None, weights),
        }
        if json_out:
            _json(d)
            return
        for k in ("lead_score", "opportunity_score", "data_quality", "persisted_score"):
            console.print(f"[cyan]{k}[/cyan]: {d[k]}")
        console.print("\n[cyan]Razones:[/cyan]")
        for r in d["reasons"]:
            console.print(f"  ▸ {r}")
    finally:
        db.close()


@lead_app.command("enrich")
def lead_enrich(lead_id: str = typer.Argument(...)):
    """Enriquece desde el website del lead (email/tel)."""
    db = _make_session()
    try:
        lead = _get_lead(db, lead_id)
        result = enrich_from_website(lead)
        if result.get("changed"):
            lead.score = compute_score(
                company=lead.company or "", industry=lead.industry or "",
                source=lead.source or "manual", email=lead.email or "",
                phone=lead.phone or "", notes=lead.notes or "", metadata=lead.meta,
            )
            db.add(add_event(db, lead.id, "enriched", f"Enriquecido desde website: email={result.get('email')} tel={result.get('phone')}"))
            db.commit()
            console.print(f"✅ Enriquecido: email={result.get('email')} tel={result.get('phone')}", style="green")
        else:
            console.print(f"Sin cambios ({result.get('reason', 'ya completo')})", style="yellow")
    finally:
        db.close()


@app.command("hunt")
def hunt(
    source: Optional[str] = typer.Option("overpass", "--source", "-s", help="Fuente (overpass, ...)"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Máx por fuente"),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Acotar a región"),
    industry: Optional[str] = typer.Option(None, "--industry", help="Acotar a sector"),
    segment: Optional[str] = typer.Option(None, "--segment", help="pyme|mediana|corporativo"),
):
    """Corre una caza de leads (misma lógica que POST /leads/hunt/run)."""
    db = _make_session()
    try:
        filters = {k: v for k, v in {"industry": industry, "segment": segment, "region": region}.items() if v}
        summary = run_discovery(db, source=source, limit=limit, filters=filters)
        table = Table(title=f"Hunt {source}")
        for col in ("Fuente", "Encontrados", "Nuevos", "Duplicados", "Estado"):
            table.add_column(col, style="cyan")
        for r in summary.get("results", []):
            table.add_row(r["source"], str(r.get("found", 0)), str(r.get("added", 0)),
                          str(r.get("duplicates", 0)), r.get("status", "?"))
        console.print(table)
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)
    finally:
        db.close()


@config_app.command("get")
def config_get(
    key: Optional[str] = typer.Argument(None, help="Clave corta (search.country) — vacío lista todas"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Lee Settings persistentes (tabla settings + env)."""
    db = _make_session()
    try:
        from app.models.setting import Setting
        if key:
            real = CONFIG_KEY_MAP.get(key, key.upper())
            row = db.query(Setting).filter(Setting.key == real).first()
            value = row.value if row else os.getenv(real, "")
            if json_out:
                _json({key: value})
            else:
                console.print(f"[cyan]{key}[/cyan] = {value or '∅'}")
            return
        rows = db.query(Setting).order_by(Setting.key).all()
        if json_out:
            _json({r.key: r.value for r in rows})
            return
        table = Table(title="Settings")
        table.add_column("Key", style="cyan")
        table.add_column("Value")
        for r in rows:
            table.add_row(r.key, r.value if len(r.value) < 60 else r.value[:57] + "...")
        console.print(table)
    finally:
        db.close()


@config_app.command("set")
def config_set(key: str = typer.Argument(...), value: str = typer.Argument(...)):
    """Persiste un setting (ej: `config set search.country BR`)."""
    db = _make_session()
    try:
        from app.models.setting import Setting
        real = CONFIG_KEY_MAP.get(key, key.upper())
        row = db.query(Setting).filter(Setting.key == real).first()
        if row:
            row.value = value
        else:
            db.add(Setting(key=real, value=value))
        db.commit()
        os.environ[real] = value
        console.print(f"✅ {key} ({real}) = {value}", style="green")
    finally:
        db.close()


@app.command("agents")
def agent_list(json_out: bool = typer.Option(False, "--json")):
    """Lista agentes registrados (tabla agents)."""
    db = _make_session()
    try:
        from app.models.agent import Agent
        agents = db.query(Agent).order_by(Agent.name).all()
        if json_out:
            _json([{"id": str(a.id), "name": a.name, "emoji": a.emoji,
                    "role": a.role.value if hasattr(a.role, "value") else str(a.role),
                    "status": a.status.value if hasattr(a.status, "value") else str(a.status)}
                   for a in agents])
            return
        if not agents:
            console.print("Sin agentes registrados.", style="yellow")
            return
        table = Table(title=f"Agentes ({len(agents)})")
        for col in ("Emoji", "Nombre", "Rol", "Estado"):
            table.add_column(col, style="cyan" if col == "Nombre" else None)
        for a in agents:
            table.add_row(a.emoji or "", a.name,
                          a.role.value if hasattr(a.role, "value") else str(a.role),
                          a.status.value if hasattr(a.status, "value") else str(a.status))
        console.print(table)
    finally:
        db.close()


@app.command("modules")
def module_list(json_out: bool = typer.Option(False, "--json")):
    """Lista módulos del sistema (spec §21)."""
    if json_out:
        _json([{"id": m[0], "description": m[1], "status": m[2]} for m in MODULES])
        return
    table = Table(title="Módulos")
    table.add_column("Módulo", style="cyan")
    table.add_column("Descripción")
    table.add_column("Estado")
    for mid, desc, st in MODULES:
        table.add_row(mid, desc, st)
    console.print(table)


MAP_ART = r'''
╔══════════════════════════════════════════════════════════════════════════════╗
║                CONCIENCIA PLATFORM · MAPA CONCEPTUAL (CLI)                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

  1) CAZAR LEADS ────────────────────────────────────────────────────────────
     conciencia hunt ────────► Overpass/OSM (sin API key, bbox configurable)
     leads import ───────────► CSV/JSON manual
                    │ dedupe: nombre normalizado · dominio · teléfono
                    ▼
     ┌─────────────────────┐        ┌─────────────────────┐
     │      DB LEADS       │◄───────│ jobs async + cron   │
     │ (Postgres / SQLite) │        │ (APScheduler, lunes │
     └─────────┬───────────┘        │  09:00 PY)          │
               │                    └─────────────────────┘
               ▼
  2) BUSCAR / RANKEAR ───────────────────────────────────────────────────────
     conciencia search ────► NLU: texto libre + filtros (país/industria/…)
     búsqueda semántica ────► embeddings (simulados o reales, vía UI/API)
                    │
                    ▼
     ┌─────────────────────────────────────────────┐
     │ SCORE INTELLIGENCE (4 scores explicables)   │
     │ · Search Relevance  (match de búsqueda)     │
     │ · Lead Score        (calidad del lead)      │
     │ · Opportunity Score (potencial comercial)   │
     │ · Data Quality      (completitud)           │
     │ + "why this match" (razones)                │
     └─────────────────────────────────────────────┘
               │
               ▼
  3) ENRIQUECER ─────────────────────────────────────────────────────────────
     conciencia lead enrich <id> ──► website → email/tel reales (anti-junk)
     conciencia lead enrich/agent  ─► agentes IA research/classify/contacts
               │
               ▼
  4) PIPELINE CRM ───────────────────────────────────────────────────────────
     new → contacted → qualified → proposal → won / lost
               │
               ▼
  5) PROPONER / EXPORTAR ────────────────────────────────────────────────────
     proposal generate ──► PDF ──► email / WhatsApp
     leads export ──► CSV / JSON

  OPERACIÓN:
     conciencia health  ──► estado DB / leads / agentes / embeddings
     conciencia agents  ──► 11 agentes (SOUL.md) + runtimes multi-proveedor
     conciencia config  ──► settings persistentes (ranking, bbox, cron, …)
     conciencia modules ──► catálogo de módulos (core, leadhunter, crm, …)

  TIP: agregá --json a casi cualquier comando para salida máquina-parseable.
'''


@app.command("map")
def platform_map():
    """Mapa conceptual del flujo de la plataforma (ASCII, CLI-friendly)."""
    console.print(MAP_ART)


if __name__ == "__main__":
    app()

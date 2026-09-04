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
import re
import sys
import uuid
from datetime import datetime
from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

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
from app.services import mission_service
from app.models.mission import Mission, MissionRun, MISSION_TYPES

app = typer.Typer(
    name="conciencia",
    help="Conciencia Platform — Mission Orchestration Control Plane CLI (misma lógica que UI/API).",
    no_args_is_help=False,
    invoke_without_command=True,
)
leads_app = typer.Typer(help="Leads: listar, exportar, inspeccionar.")
lead_app = typer.Typer(help="Lead individual: inspect, enrich, score.")
config_app = typer.Typer(help="Configuración persistente (Settings).")
mission_app = typer.Typer(help="Missions: crear, planear, ejecutar, inspeccionar.")
run_app = typer.Typer(help="Runs: listar e inspeccionar ejecuciones de missions.")
agent_app = typer.Typer(help="Agente individual: inspect, run.")
workflow_app = typer.Typer(help="Workflows: listar, inspeccionar y ejecutar.", invoke_without_command=True)
team_app = typer.Typer(help="Teams: agrupar agentes especializados (Fase F).")
harness_app = typer.Typer(help="Harnesses: contratos versionados de ejecución (Fase G).")
signal_app = typer.Typer(help="Signals: hallazgos trazables con evidencia (Fase I).")
context_app = typer.Typer(help="Context packs: retrieval eficiente de contexto (Fase J).")
webmcp_app = typer.Typer(help="WebMCP: interactuar con apps web WebMCP-enabled (Fase K).")
economics_app = typer.Typer(help="Economics: economía de misiones inspeccionable (Fase L).")
app.add_typer(leads_app, name="leads")
app.add_typer(lead_app, name="lead")
app.add_typer(config_app, name="config")
app.add_typer(mission_app, name="mission")
app.add_typer(run_app, name="run")
app.add_typer(agent_app, name="agent")
app.add_typer(workflow_app, name="workflow")
app.add_typer(team_app, name="team")
app.add_typer(harness_app, name="harness")
app.add_typer(signal_app, name="signal")
app.add_typer(context_app, name="context")
app.add_typer(webmcp_app, name="webmcp")
app.add_typer(economics_app, name="economics")

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

# Claves cuyo valor es secreto → se enmascaran en `conciencia config get`
_SECRET_KEY_RE = re.compile(r"(KEY|SECRET|PASSWORD|PASS|TOKEN)", re.IGNORECASE)


# master-prompt-cli §8: short IDs tipo M-6998bc52 → UUID canónico
_SHORT_PREFIX = {
    "M": "mission", "R": "run", "W": "workflow", "T": "team",
    "H": "harness", "S": "signal", "A": "agent",
}
_ACTIVE_STATUSES = ("draft", "planned", "ready", "running", "paused", "waiting_approval")


def _resolve_uuid(db, raw: str, kind: str):
    """Resuelve un id corto (M-6998bc52) o UUID completo a su UUID canónico.

    kind: mission|run|workflow|team|harness|signal|agent (usa el prefijo).
    Devuelve el str(UUID) o lanza ValueError con mensaje amigable.
    """
    import uuid as _uuid
    from app.models.mission import Mission, MissionRun
    from app.models.team import Team
    from app.models.harness import Harness
    from app.models.signal import Signal
    from app.models.workflow import Workflow
    from app.models.agent import Agent

    models = {
        "mission": Mission, "run": MissionRun, "workflow": Workflow,
        "team": Team, "harness": Harness, "signal": Signal, "agent": Agent,
    }
    model = models[kind]
    raw = (raw or "").strip()
    if not raw:
        raise ValueError(f"Falta el ID de {kind}. Ej: conciencia {kind} inspect M-6998bc52")

    # full UUID directo
    try:
        return str(_uuid.UUID(raw))
    except ValueError:
        pass

    # prefijo + corto: M-6998bc52 o M-<uuid completo>
    if len(raw) > 2 and raw[1] == "-" and raw[0].upper() in _SHORT_PREFIX:
        if _SHORT_PREFIX[raw[0].upper()] != kind:
            raise ValueError(f"Prefijo '{raw[0]}' es de {_SHORT_PREFIX[raw[0].upper()]}, no de {kind}")
        token = raw[2:].replace("-", "")
        try:
            return str(_uuid.UUID(token))
        except ValueError:
            token8 = token[:8].lower()
            hits = [m for m in db.query(model).all() if str(m.id).startswith(token8)]
            if len(hits) == 1:
                return str(hits[0].id)
            if not hits:
                raise ValueError(f"No existe {kind} con id corto '{raw}'. Probá: conciencia {kind} list")
            raise ValueError(f"El id corto '{raw}' es ambiguo ({len(hits)} coincidencias). Usá el UUID completo.")

    # corto sin prefijo NO se acepta (evita ambigüedad entre tipos)
    raise ValueError(f"ID inválido '{raw}'. Usá el UUID completo o el corto con prefijo, ej: M-6998bc52")


def _active_mission_or_pick(db):
    """§7 contexto: misión activa única, o lista de candidatas si hay varias/ninguna."""
    from app.models.mission import Mission

    actives = db.query(Mission).filter(Mission.status.in_(_ACTIVE_STATUSES)).order_by(Mission.created_at.desc()).all()
    if len(actives) == 1:
        return actives[0], None
    if not actives:
        return None, "No hay misiones activas. Creá una con: conciencia mission create \"objetivo\""
    recent = actives[:3]
    lines = "\n".join(f"  • {m.status}: {m.name} ({str(m.id)[:8]})" for m in recent)
    return None, f"Hay {len(actives)} misiones activas; elegí una explícitamente:\n{lines}\nEj: conciencia mission inspect {str(recent[0].id)[:8]}"


def _short_id(kind: str, full_id: str) -> str:
    """M-6998bc52 a partir del UUID canónico (para next-actions copiables)."""
    prefix = next((p for p, k in _SHORT_PREFIX.items() if k == kind), "X")
    return f"{prefix}-{full_id[:8]}"


def _mask_secret(key: str, value: str) -> str:
    """Enmascara valores de claves secretas (API keys, passwords, tokens).

    Devuelve los primeros 4 caracteres + '…' (nunca el valor completo).
    Las claves NO secretas se devuelven intactas.
    """
    if value and _SECRET_KEY_RE.search(key):
        return (value[:4] + "…" + f" ({len(value)} chars)") if len(value) > 4 else "•••"
    return value


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
    typer.echo(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def _agent_health(db, agent) -> dict:
    """Explain agent and runtime readiness without exposing agent config secrets."""
    from app.services.capability_readiness import runtime_readiness

    runtime = agent.runtime.value if hasattr(agent.runtime, "value") else str(agent.runtime)
    provider = agent.provider.value if hasattr(agent.provider, "value") else str(agent.provider)
    runtime_health = runtime_readiness(
        db,
        runtime,
        provider=provider if runtime == "generic" else None,
        model=agent.model if runtime == "generic" else None,
    )
    agent_status = agent.status.value if hasattr(agent.status, "value") else str(agent.status)
    health = agent.health_status or "unknown"
    if agent_status == "error":
        reason = "agent status is error; no persisted diagnostic is available"
    elif agent.availability != "available":
        reason = f"agent availability is {agent.availability}"
    elif not runtime_health["registered"] or not runtime_health["enabled"]:
        reason = f"runtime {runtime} is disabled or not configured"
    elif not runtime_health["ready"]:
        reason = f"runtime {runtime} unavailable: {runtime_health['reason']}"
    elif health == "unknown":
        reason = "agent has not reported a heartbeat"
    else:
        reason = f"agent health is {health}"
    return {
        "health_status": health,
        "availability": agent.availability,
        "last_heartbeat": agent.last_heartbeat,
        "health_reason": reason,
        "runtime_ready": runtime_health["ready"],
        "runtime_reason": runtime_health["reason"],
    }


@app.callback()
def root_dashboard(ctx: typer.Context) -> None:
    """Show an operational summary when conciencia is invoked without a command."""
    if ctx.invoked_subcommand is not None:
        return
    db = _make_session()
    try:
        from app.services.workspace_service import workspace_home

        home = workspace_home(db)
        table = Table(title=f"Conciencia · {home['workspace']}")
        table.add_column("Estado", style="cyan")
        table.add_column("Valor")
        current = home["current_project"]
        table.add_row("Proyecto actual", current["name"] if current else "ninguno")
        table.add_row("Misiones activas", str(home["active_missions"]))
        table.add_row("Aprobaciones pendientes", str(home["pending_approvals"]))
        table.add_row("Ejecución", home["execution"]["overall"])
        console.print(table)
        if home["recent_projects"]:
            console.print("\nProyectos recientes:")
            for project in home["recent_projects"]:
                console.print(f"  {project['status']:<10} {project['name']}")
        if home["recent_missions"]:
            console.print("\nMisiones recientes:")
            for mission in home["recent_missions"]:
                console.print(f"  {mission['id'][:8]}  {mission['status']:<18} {mission['name']}")
        console.print("\nAcciones: ask | mission list | approvals | runtime | onboard | doctor")
    except Exception as exc:  # noqa: BLE001 - dashboard must not hide the CLI
        console.print(f"Dashboard no disponible: {exc}", style="yellow")
        console.print(ctx.get_help())
    finally:
        db.close()


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
            # §23 empty state que enseña: filtros + sugerencias accionables
            total_local = db.query(Lead).count()
            filters = {
                "country": country, "region": region, "city": city,
                "category": category, "industry": industry, "segment": segment,
                "online": online, "min_score": min_score,
            }
            activos = " · ".join(f"{k}: {v}" for k, v in filters.items() if v) or "ninguno"
            console.print("Sin resultados.", style="yellow")
            console.print(f"\nHay [bold]{total_local}[/bold] leads en total; tu búsqueda no coincidió con los filtros:")
            console.print(f"  {activos}")
            console.print("\nProbá:")
            if online:
                console.print(f"  • quitar --online {online} (filtra por canal de contacto)")
            if query:
                console.print(f"  • buscar con menos términos: conciencia search \"{query.split()[0] if query.split() else query}\" --country PY")
            console.print("  • correr una caza nueva: conciencia hunt --industry <sector> --country PY")
            console.print("  • ver qué hay: conciencia leads list --limit 10")
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
            value = _mask_secret(real, value)  # nunca imprimir secrets completos
            if json_out:
                _json({key: value})
            else:
                console.print(f"[cyan]{key}[/cyan] = {value or '∅'}")
            return
        rows = db.query(Setting).order_by(Setting.key).all()
        if json_out:
            _json({r.key: _mask_secret(r.key, r.value) for r in rows})
            return
        table = Table(title="Settings")
        table.add_column("Key", style="cyan")
        table.add_column("Value")
        for r in rows:
            value = _mask_secret(r.key, r.value)
            table.add_row(r.key, value if len(value) < 60 else value[:57] + "...")
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
@agent_app.command("list")
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


# ---------------------------------------------------------------------------
# Missions (Fase B del master prompt: Mission = unidad central de trabajo)
# ---------------------------------------------------------------------------

@mission_app.command("create")
def mission_create(
    name: str = typer.Argument(..., help="Nombre de la misión"),
    objective: str = typer.Argument(..., help="Objetivo"),
    type: str = typer.Option("research", "--type", "-t", help="Tipo: " + ", ".join(MISSION_TYPES)),
    runtime: str = typer.Option("generic", "--runtime", help="Runtime: generic|claude_code|codex|opencode|openclaw|mcp"),
    agents: Optional[str] = typer.Option(None, "--agents", help="IDs de agentes separados por coma"),
    team: Optional[str] = typer.Option(None, "--team", help="ID del team (Fase F): runtime default + miembros"),
    harness: Optional[str] = typer.Option(None, "--harness", help="ID del harness activo (Fase G): contrato de ejecución"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Crea una misión (draft)."""
    db = _make_session()
    try:
        m = mission_service.create_mission(
            db,
            name=name,
            objective=objective,
            type=type,
            runtime=runtime,
            agent_ids=[a.strip() for a in agents.split(",") if a.strip()] if agents else None,
            team_id=team,
            harness_id=harness,
        )
        if json_out:
            _json(m.to_dict())
        else:
            console.print(f"✅ Misión creada: [cyan]{m.name}[/cyan] ({m.id})")
            console.print(f"   Tipo: {m.type} · Status: {m.status} · Runtime: {m.runtime}" + (f" · Team: {m.team_id}" if m.team_id else "") + (f" · Harness: {m.harness_id}" if m.harness_id else ""))
            console.print(f"   Siguiente: conciencia mission plan {m.id}")
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)
    finally:
        db.close()


@mission_app.command("list")
def mission_list(
    status: Optional[str] = typer.Option(None, "--status"),
    type: Optional[str] = typer.Option(None, "--type"),
    limit: int = typer.Option(20, "--limit", "-n", min=1, max=100),
    json_out: bool = typer.Option(False, "--json"),
):
    """Lista misiones."""
    db = _make_session()
    try:
        missions = mission_service.list_missions(db, status=status, type=type, limit=limit)
        if json_out:
            _json([m.to_dict() for m in missions])
            return
        if not missions:
            console.print("Sin misiones. Creá una con: conciencia mission create", style="yellow")
            return
        table = Table(title=f"Missions ({len(missions)})")
        for col in ("ID", "Nombre", "Tipo", "Status", "Runtime"):
            table.add_column(col, style="cyan" if col == "Nombre" else None)
        for m in missions:
            table.add_row(str(m.id)[:8], m.name, m.type, m.status, m.runtime)
        console.print(table)
    finally:
        db.close()


@mission_app.command("inspect")
def mission_inspect(
    mission_id: Optional[str] = typer.Argument(None, help="ID de la misión (UUID o corto M-6998bc52); vacío usa la única misión activa"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Muestra detalle de una misión."""
    db = _make_session()
    try:
        if not mission_id:
            mission, hint = _active_mission_or_pick(db)
            if mission is None:
                console.print(hint, style="yellow")
                raise typer.Exit(1)
            mission_id = str(mission.id)
        m = db.query(Mission).filter(Mission.id == uuid.UUID(_resolve_uuid(db, mission_id, "mission"))).first()
        if not m:
            console.print(f"Misión no encontrada: {mission_id}. Probá: conciencia mission list", style="red")
            raise typer.Exit(1)
        if json_out:
            _json(m.to_dict())
            return
        table = Table(title=m.name)
        table.add_column("Campo", style="cyan")
        table.add_column("Valor")
        for k, v in m.to_dict().items():
            table.add_row(k, str(v))
        console.print(table)
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)
    finally:
        db.close()


@mission_app.command("plan")
def mission_plan(
    mission_id: str = typer.Argument(..., help="ID de la misión (UUID o corto M-6998bc52)"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Genera el workflow por defecto para el tipo de misión."""
    db = _make_session()
    try:
        mid = _resolve_uuid(db, mission_id, "mission")
        m = db.query(Mission).filter(Mission.id == uuid.UUID(mid)).first()
        if not m:
            console.print(f"Misión no encontrada: {mission_id}. Probá: conciencia mission list", style="red")
            raise typer.Exit(1)
        m = mission_service.plan_mission(db, m)
        console.print(f"✅ Misión planeada: workflow [cyan]{m.workflow_id}[/cyan] · status={m.status}")
        console.print(f"   Siguiente: conciencia mission run {_short_id('mission', str(m.id))}")
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)
    finally:
        db.close()


@mission_app.command("run")
def mission_run(
    mission_id: str = typer.Argument(..., help="ID de la misión (UUID o corto M-6998bc52)"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Ejecuta la misión (crea MissionRun + corre el workflow)."""
    db = _make_session()
    try:
        mid = _resolve_uuid(db, mission_id, "mission")
        m = db.query(Mission).filter(Mission.id == uuid.UUID(mid)).first()
        if not m:
            console.print(f"Misión no encontrada: {mission_id}. Probá: conciencia mission list", style="red")
            raise typer.Exit(1)
        run = mission_service.run_mission(db, m)
        if json_out:
            _json(run.to_dict())
            return
        console.print(f"🏃 Misión ejecutada: {m.name}")
        console.print(f"   Run: {run.id} · Status: {run.status}")
        console.print(f"   Costo: {run.cost_usd.get('total', 0)}")
        if run.status == "waiting_approval":
            console.print("   ⏳ Esperando aprobación: conciencia approvals")
        elif run.status == "failed" and run.error:
            console.print(f"   ❌ Error: {run.error}", style="red")
    finally:
        db.close()


@run_app.command("list")
def run_list(
    mission_id: Optional[str] = typer.Option(None, "--mission", "-m"),
    limit: int = typer.Option(20, "--limit", "-n"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Lista runs de missions."""
    db = _make_session()
    try:
        q = db.query(MissionRun).order_by(MissionRun.started_at.desc())
        if mission_id:
            q = q.filter(MissionRun.mission_id == uuid.UUID(str(mission_id)))
        runs = q.limit(limit).all()
        if json_out:
            _json([r.to_dict() for r in runs])
            return
        if not runs:
            console.print("Sin runs.", style="yellow")
            return
        table = Table(title=f"Mission Runs ({len(runs)})")
        for col in ("ID", "Mission", "Status", "Costo", "Iniciado"):
            table.add_column(col, style="cyan")
        for r in runs:
            table.add_row(str(r.id)[:8], str(r.mission_id)[:8], r.status, str(r.cost_usd.get("total", 0)), (r.started_at or "").strftime("%m-%d %H:%M") if r.started_at else "")
        console.print(table)
    finally:
        db.close()


@run_app.command("inspect")
def run_inspect(
    run_id: str = typer.Argument(..., help="ID del run"),
    steps: bool = typer.Option(False, "--steps", "-s", help="Mostrar desglose por step (Fase H: observabilidad)"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Muestra detalle de un run (logs, costos, tokens, error).

    Con --steps muestra el desglose por step: status, agente, runtime,
    tokens, costo y duración (Fase H).
    """
    db = _make_session()
    try:
        rid = _resolve_uuid(db, run_id, "run")
        r = db.query(MissionRun).filter(MissionRun.id == uuid.UUID(rid)).first()
        if not r:
            console.print(f"Run no encontrado: {run_id}. Probá: conciencia run list", style="red")
            raise typer.Exit(1)
        if json_out:
            out = r.to_dict()
            if r.workflow_run_id:
                from app.models.workflow import WorkflowRun
                wr = db.query(WorkflowRun).filter(WorkflowRun.id == r.workflow_run_id).first()
                if wr:
                    out["step_results"] = wr.step_results or []
                    out["events"] = wr.events or []
            _json(out)
            return
        table = Table(title=f"Run {r.id}")
        table.add_column("Campo", style="cyan")
        table.add_column("Valor")
        d = r.to_dict()
        d.pop("logs", None)
        for k, v in d.items():
            table.add_row(k, str(v))
        console.print(table)

        if r.workflow_run_id:
            from app.models.workflow import WorkflowRun
            wr = db.query(WorkflowRun).filter(WorkflowRun.id == r.workflow_run_id).first()
            if wr and wr.step_results:
                console.print(f"\n[bold cyan]Steps ({len(wr.step_results)}):[/bold cyan]")
                stable = Table(title="Desglose por step")
                for col in ("Step", "Status", "Agente", "Runtime", "Tokens", "Costo", "ms"):
                    stable.add_column(col, style="cyan")
                for s in wr.step_results:
                    tok = (s.get("tokens") or {}).get("total", "-")
                    stable.add_row(
                        s.get("step_name", "?"),
                        s.get("status", "?"),
                        s.get("agent_name") or (f"⚡ {len(s.get('children') or [])} children" if s.get("parallel") else "-"),
                        s.get("runtime") or "-",
                        str(tok),
                        str(s.get("cost") or 0),
                        str(s.get("duration_ms") or "-"),
                    )
                console.print(stable)

        if steps and r.logs:
            console.print(f"\n[bold cyan]Timeline ({len(r.logs)} eventos):[/bold cyan]")
            for lg in r.logs:
                lvl = "red" if lg.get("level") == "error" else None
                console.print(f"  {lg.get('ts', '')[:23]} {lg.get('message', '')}", style=lvl, markup=False)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fase E — Mission Planning: conciencia ask (master prompt §9/§E)
# ---------------------------------------------------------------------------

@run_app.command("logs")
def run_logs(
    run_id: str = typer.Argument(..., help="ID del run"),
    limit: int = typer.Option(50, "--limit", "-n", min=1, max=500),
    json_out: bool = typer.Option(False, "--json"),
):
    """Show the persisted event timeline for a mission run."""
    db = _make_session()
    try:
        try:
            parsed_id = uuid.UUID(str(run_id))
        except ValueError:
            console.print(f"Run no encontrado: {run_id}", style="red")
            raise typer.Exit(1)
        run = db.query(MissionRun).filter(MissionRun.id == parsed_id).first()
        if not run:
            console.print(f"Run no encontrado: {run_id}", style="red")
            raise typer.Exit(1)
        logs = (run.logs or [])[-limit:]
        if json_out:
            _json(logs)
            return
        if not logs:
            console.print("Sin logs.", style="yellow")
            return
        for entry in logs:
            style = "red" if entry.get("level") == "error" else None
            console.print(
                f"{entry.get('ts', '')[:23]} {entry.get('level', 'info'):<5} {entry.get('message', '')}",
                style=style,
                markup=False,
            )
    finally:
        db.close()


@app.command("ask")
def ask_cmd(
    text: Optional[str] = typer.Argument(None, help="Texto natural: qué querés lograr"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirmar y crear sin preguntar"),
    json_out: bool = typer.Option(False, "--json", help="Mostrar la propuesta como JSON (no crea nada)"),
):
    """Texto natural → propuesta de misión. Confirma antes de crear."""
    from app.services import ask_service

    db = _make_session()
    try:
        if not text:
            text = typer.prompt("Qué querés lograr").strip()
        if not text:
            raise ValueError("El objetivo no puede estar vacío")
        proposal = ask_service.build_proposal(db, text)
        if json_out:
            _json(proposal)
            return

        console.print(f"[bold cyan]📋 Propuesta de misión[/bold cyan] — tipo: {proposal['mission_type']}")
        console.print(f"   Nombre: {proposal['name']}")
        console.print(f"   Runtime: {proposal['runtime']}")
        intent = proposal["intent"]
        alternative = f" · alternativa: {intent['alternative']}" if intent.get("alternative") else ""
        console.print(f"   Confianza de intent: {intent['confidence']:.0%}{alternative}")
        readiness = proposal["readiness"]
        console.print(f"   Workflow resoluble: {readiness['workflow']['resolvable']} ({readiness['workflow']['reason']})")
        execution_state = "READY" if readiness["runtime"]["ready"] else "BLOCKED"
        console.print(f"   Execution readiness: {execution_state} ({readiness['runtime']['reason']})")
        if readiness["runtime"].get("action"):
            console.print(f"   Acción requerida: {readiness['runtime']['action']}")
        cost = proposal["cost_estimate"]
        console.print(f"   Costo est.: ${cost['cost_usd']} · {cost['tokens_total']} tokens ({cost['model']})")
        if proposal.get("team"):
            t = proposal["team"]
            console.print(f"   👥 Team sugerido: {t['name']} ({t['coverage']}% match · {t['members_count']} miembros · runtime {t['default_runtime']})")
        if proposal["agents"]:
            console.print("   Agentes sugeridos:")
            for a in proposal["agents"]:
                console.print(f"     • {a['name']} ({a['role']}) — {a['coverage']}% match · score {a['score']} · {a['runtime']}/{a['model']}")
        else:
            console.print("   Agentes sugeridos: ninguno con match (revisá capabilities)", style="yellow")
        console.print("   Workflow:")
        for i, s in enumerate(proposal["workflow"]):
            gate = " 🔒 aprobación" if s["approval"] else ""
            par = " ⚡ paralelo" if s.get("parallel") else ""
            console.print(f"     {i}: {s['name']}{gate}{par}")
        console.print("   Criterios de éxito:")
        for c in proposal["success_criteria"]:
            console.print(f"     • {c}")

        if not yes and not typer.confirm("\n¿Crear la misión?", default=False):
            console.print("Cancelado.", style="yellow")
            raise typer.Exit(0)

        m = ask_service.create_from_proposal(db, proposal)
        short = _short_id("mission", str(m.id))
        console.print(f"✅ Misión creada: [cyan]{m.name}[/cyan] ({short})")
        console.print(f"   Tipo: {m.type} · Status: {m.status} · Runtime: {m.runtime}")
        console.print("   Next:")
        console.print(f"     conciencia mission plan {short}")
        console.print(f"     conciencia mission inspect {short}")
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)
    finally:
        db.close()


@app.command("approvals")
def approvals_list(json_out: bool = typer.Option(False, "--json")):
    """Lista misiones esperando aprobación."""
    db = _make_session()
    try:
        missions = mission_service.list_missions(db, status="waiting_approval")
        if json_out:
            _json([m.to_dict() for m in missions])
            return
        if not missions:
            console.print("Sin aprobaciones pendientes.", style="green")
            return
        table = Table(title="Aprobaciones pendientes")
        for col in ("Mission ID", "Nombre", "Tipo", "Workflow"):
            table.add_column(col, style="cyan")
        for m in missions:
            table.add_row(str(m.id), m.name, m.type, m.workflow_id or "-")
        console.print(table)
        console.print("\nPara aprobar: conciencia approve <mission_id> <step_index> [--reject]")
    finally:
        db.close()


@app.command("approve")
def approve(
    mission_id: str = typer.Argument(..., help="ID de la misión (UUID o corto M-6998bc52)"),
    step_index: int = typer.Argument(..., help="Índice del step a aprobar"),
    reject: bool = typer.Option(False, "--reject", help="Rechazar en vez de aprobar"),
):
    """Aprueba (o rechaza) el step de aprobación de una misión."""
    db = _make_session()
    try:
        mid = _resolve_uuid(db, mission_id, "mission")
        run = mission_service.approve_mission_step(db, mid, step_index, approved=not reject)
        console.print(f"{'❌ Rechazado' if reject else '✅ Aprobado'} step {step_index} de misión {_short_id('mission', mid)}")
        console.print(f"   Run status: {run.status}")
        if run.status == "waiting_approval":
            console.print("   ⏳ Siguiente step esperando aprobación")
        elif run.status == "completed":
            console.print("   🎉 Misión completada")
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)
    finally:
        db.close()


@app.command("reject")
def reject(
    mission_id: str = typer.Argument(..., help="ID de la misión (UUID o corto M-6998bc52)"),
    step_index: int = typer.Argument(..., help="Índice del step a rechazar"),
):
    """Rechaza el step de aprobación de una misión (alias de approve --reject)."""
    db = _make_session()
    try:
        mid = _resolve_uuid(db, mission_id, "mission")
        run = mission_service.approve_mission_step(db, mid, step_index, approved=False)
        console.print(f"❌ Rechazado step {step_index} de misión {_short_id('mission', mid)}")
        console.print(f"   Run status: {run.status}")
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)
    finally:
        db.close()


@app.command("status")
def status_cmd(json_out: bool = typer.Option(False, "--json")):
    """Resumen general (missions por estado, approvals pendientes, agents, knowledge).

    master-prompt-cli §25: overview accionable de mission control.
    """
    db = _make_session()
    try:
        from app.models.agent import Agent
        from app.modules.leadhunter.models import Lead
        from app.services.capability_readiness import execution_overview
        from app.modules.leadhunter.embeddings import embeddings_enabled, embedding_model

        missions = db.query(Mission).count()
        runs = db.query(MissionRun).count()
        leads = db.query(Lead).count()
        agents = db.query(Agent).count()
        awaiting = db.query(Mission).filter(Mission.status == "waiting_approval").count()
        running = db.query(Mission).filter(Mission.status == "running").count()
        planned = db.query(Mission).filter(Mission.status.in_(["planned", "ready"])).count()
        completed = db.query(Mission).filter(Mission.status == "completed").count()
        failed = db.query(Mission).filter(Mission.status == "failed").count()
        runtimes = execution_overview(db)
        emb_state = "enabled" if embeddings_enabled() else "disabled"
        emb_model = embedding_model()

        if json_out:
            _json({
                "missions": missions,
                "missions_by_status": {"running": running, "planned": planned,
                                       "waiting_approval": awaiting,
                                       "completed": completed, "failed": failed},
                "runs": runs,
                "agents": agents,
                "leads": leads,
                "approvals_pending": awaiting,
                "execution": runtimes.get("overall"),
                "runtimes_ready": len([r for r in runtimes.get("runtimes", []) if r.get("ready")]),
                "runtimes_total": len(runtimes.get("runtimes", [])),
                "embeddings": emb_state,
            })
            return

        console.print("[bold cyan]Conciencia status[/bold cyan]")
        table = Table(title="Misiones")
        table.add_column("Estado", style="cyan")
        table.add_column("Cantidad")
        for label, n in (("running", running), ("planned/ready", planned),
                         ("waiting_approval", awaiting), ("completed", completed),
                         ("failed", failed)):
            table.add_row(label, str(n))
        console.print(table)

        extra = Table(title="Sistema")
        extra.add_column("Componente", style="cyan")
        extra.add_column("Estado")
        extra.add_row("Total misiones", str(missions))
        extra.add_row("Runs", str(runs))
        extra.add_row("Agentes", str(agents))
        extra.add_row("Leads (knowledge)", str(leads))
        rt = runtimes.get("runtimes", [])
        extra.add_row("Runtimes", f"{len([r for r in rt if r.get('ready')])} / {len(rt)} listos")
        extra.add_row("Embeddings", emb_state + (f" ({emb_model})" if emb_state == "enabled" else ""))
        console.print(extra)

        if awaiting:
            console.print(f"\n[yellow]⚠ {awaiting} misión(es) espera(n) tu aprobación: conciencia approvals[/yellow]")
        else:
            console.print("\nSin aprobaciones pendientes.", style="green")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fase C — CLI Foundation: init, doctor, agent inspect/run, workflow, runtime/tool/model
# ---------------------------------------------------------------------------

@app.command("init")
def init_cmd(
    dir: str = typer.Argument(".", help="Directorio del proyecto a inicializar"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Detecta contexto del proyecto (git, stack, CI) y crea .conciencia/."""
    import subprocess
    from pathlib import Path

    root = Path(dir).resolve()
    if not root.is_dir():
        console.print(f"Directorio no encontrado: {root}", style="red")
        raise typer.Exit(1)

    info = {"path": str(root), "git": False, "branch": None, "remotes": [], "stack": [], "detected": []}

    # git
    if (root / ".git").exists():
        info["git"] = True
        try:
            branch = subprocess.run(["git", "-C", str(root), "branch", "--show-current"], capture_output=True, text=True, timeout=10)
            info["branch"] = branch.stdout.strip() or None
            rem = subprocess.run(["git", "-C", str(root), "remote", "-v"], capture_output=True, text=True, timeout=10)
            info["remotes"] = [l.split()[1] for l in rem.stdout.splitlines() if l.split()]
        except Exception:
            pass

    # stack markers
    markers = {
        "Python": ["pyproject.toml", "requirements.txt", "setup.py", "Pipfile"],
        "Node.js": ["package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"],
        "FastAPI": ["app/main.py"],
        "React": ["frontend/package.json", "vite.config.ts", "vite.config.js"],
        "Docker": ["Dockerfile", "docker-compose.yml", "compose.yaml"],
        "PostgreSQL": ["docker-compose.yml", "docker-compose.dev.yml"],
        "CI": [".github/workflows", ".gitlab-ci.yml"],
        "Tests": ["tests/", "pytest.ini", "pyproject.toml"],
    }
    for name, files in markers.items():
        if any((root / f).exists() for f in files):
            info["stack"].append(name)
            info["detected"].append(f"{name}: {', '.join(f for f in files if (root / f).exists())}")

    # crear .conciencia/
    conf_dir = root / ".conciencia"
    conf_dir.mkdir(exist_ok=True)
    (conf_dir / "project.yaml").write_text(
        f"# Generado por `conciencia init` — {datetime.utcnow().isoformat()}Z\n"
        f"name: {root.name}\n"
        f"path: {root}\n"
        f"git: {str(info['git']).lower()}\n"
        f"branch: {info['branch'] or 'none'}\n"
        f"stack:\n" + "".join(f"  - {s}\n" for s in info["stack"]),
        encoding="utf-8",
    )
    (conf_dir / "context.md").write_text(
        f"# Contexto del proyecto: {root.name}\n\n"
        f"- Git: {info['git']} ({info['branch'] or 'sin branch'})\n"
        f"- Remotes: {', '.join(info['remotes']) or 'ninguno'}\n"
        f"- Stack detectado: {', '.join(info['stack']) or 'no detectado'}\n",
        encoding="utf-8",
    )

    if json_out:
        _json(info)
        return
    console.print(f"✅ Proyecto inicializado: [cyan]{root.name}[/cyan]")
    console.print(f"   Git: {info['git']} · Branch: {info['branch'] or '-'} · Remotes: {len(info['remotes'])}")
    console.print(f"   Stack: {', '.join(info['stack']) or 'no detectado'}")
    console.print(f"   Creado: {conf_dir}/project.yaml + context.md")


@app.command("doctor")
def doctor_cmd(json_out: bool = typer.Option(False, "--json")):
    """Diagnóstico del sistema: DB, tablas, runtimes, embeddings, CLI."""
    import sqlalchemy
    from app.services.capability_readiness import execution_overview
    from app.modules.leadhunter.embeddings import embeddings_enabled, embedding_model

    core = []
    try:
        db = _make_session()
        db.execute(sqlalchemy.text("SELECT 1"))
        core.append({"name": "database", "state": "ready", "reason": "conexión ok"})
    except Exception as e:  # noqa: BLE001
        db = None
        core.append({"name": "database", "state": "blocked", "reason": str(e)})

    for table_name in ("missions", "mission_runs", "agents", "workflows"):
        try:
            exists = bool(db and sqlalchemy.inspect(db.get_bind()).has_table(table_name))
            core.append({
                "name": table_name,
                "state": "ready" if exists else "blocked",
                "reason": "tabla disponible" if exists else "tabla no disponible",
            })
        except Exception as e:  # noqa: BLE001
            core.append({"name": table_name, "state": "blocked", "reason": str(e)})

    execution = execution_overview(db) if db else {
        "overall": "BLOCKED FOR MISSION EXECUTION",
        "ready": False,
        "runtimes": [],
    }
    core_ready = all(item["state"] == "ready" for item in core)
    overall = execution["overall"] if core_ready else "BLOCKED"
    optional = {
        "embeddings": {
            "state": "ready" if embeddings_enabled() else "disabled",
            "reason": embedding_model(),
        }
    }
    report = {
        "overall": overall,
        "core": core,
        "execution": execution,
        "optional": optional,
    }

    if json_out:
        _json(report)
        if db:
            db.close()
        return
    table = Table(title="Conciencia doctor · Core")
    table.add_column("Capacidad", style="cyan")
    table.add_column("Estado")
    table.add_column("Razón")
    for item in core:
        table.add_row(item["name"], item["state"], item["reason"])
    console.print(table)

    runtime_table = Table(title="Mission execution")
    for column in ("Runtime", "Estado", "Detectado", "Habilitado", "Razón"):
        runtime_table.add_column(column, style="cyan" if column == "Runtime" else None)
    for runtime in execution["runtimes"]:
        runtime_table.add_row(
            runtime["name"],
            runtime["state"],
            str(runtime.get("detected", "-")),
            str(runtime["enabled"]),
            runtime["reason"],
        )
    console.print(runtime_table)
    console.print(f"\nOverall: [bold]{overall}[/bold]")
    if db:
        db.close()
    if overall in {"BLOCKED", "BLOCKED FOR MISSION EXECUTION"}:
        raise typer.Exit(1)


@app.command("tool")
def tool_list(json_out: bool = typer.Option(False, "--json")):
    """Lista tools/servidores MCP registrados."""
    db = _make_session()
    try:
        from app.models.setting import Setting
        from app.routers.mcp import MCP_SETTINGS_KEY, BUILTIN_EMAIL_SERVER
        from app.services.capability_readiness import tool_readiness
        row = db.query(Setting).filter(Setting.key == MCP_SETTINGS_KEY).first()
        servers = []
        if row and row.value:
            try:
                servers = json.loads(row.value)
            except Exception:
                servers = []
        if not any(s.get("name") == "email" for s in servers):
            servers.append(BUILTIN_EMAIL_SERVER)
        rows = [tool_readiness(server) for server in servers]
        if json_out:
            _json(rows)
            return
        table = Table(title="Tools / MCP servers")
        for col in ("Nombre", "Detectado", "Configurado", "Habilitado", "Estado", "Razón"):
            table.add_column(col, style="cyan")
        for row in rows:
            table.add_row(
                row["name"],
                str(row["detected"]),
                str(row["configured"]),
                str(row["enabled"]),
                row["state"],
                row["reason"],
            )
        console.print(table)
    finally:
        db.close()


@app.command("runtime")
def runtime_list(json_out: bool = typer.Option(False, "--json")):
    """Lista runtimes registrados + salud de cada binario."""
    db = _make_session()
    try:
        from app.core.agent_runtime import get_runtime_configs
        from app.services.capability_readiness import runtime_readiness

        rows = [runtime_readiness(db, cfg.name, config=cfg) for cfg in get_runtime_configs(db)]
        if json_out:
            _json(rows)
            return
        table = Table(title="Runtimes")
        for col in ("Nombre", "Tipo", "Detectado", "Habilitado", "Estado", "Razón"):
            table.add_column(col, style="cyan")
        for row in rows:
            table.add_row(
                row["name"],
                row["type"],
                str(row.get("detected", "-")),
                str(row["enabled"]),
                row["state"],
                row["reason"],
            )
        console.print(table)
    finally:
        db.close()


@app.command("runtime-inspect")
def runtime_inspect_cmd(
    runtime_name: str = typer.Argument(..., help="Nombre del runtime: generic|claude_code|codex|opencode|openclaw"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Detalle de un runtime: capabilities, binario, versión, salud y política (§14)."""
    db = _make_session()
    try:
        from app.core.agent_runtime import get_runtime_configs
        from app.services.capability_readiness import runtime_readiness

        cfg = next((c for c in get_runtime_configs(db) if c.name == runtime_name), None)
        if not cfg:
            console.print(f"Runtime no encontrado: {runtime_name}. Disponibles: "
                          + ", ".join(c.name for c in get_runtime_configs(db)), style="red")
            raise typer.Exit(1)
        row = runtime_readiness(db, cfg.name, config=cfg)
        if json_out:
            _json(row)
            return
        table = Table(title=f"Runtime: {cfg.name}")
        table.add_column("Campo", style="cyan")
        table.add_column("Valor")
        for k, v in row.items():
            if k not in ("meta",):
                table.add_row(k, str(v))
        console.print(table)
    finally:
        db.close()


@app.command("runtime-doctor")
def runtime_doctor_cmd(json_out: bool = typer.Option(False, "--json")):
    """Descubre runtimes instalados (PATH, PowerShell, Git Bash, WSL) y su salud (§15)."""
    db = _make_session()
    try:
        from app.core.agent_runtime import get_runtime_configs
        from app.services.capability_readiness import runtime_readiness

        rows = [runtime_readiness(db, cfg.name, config=cfg) for cfg in get_runtime_configs(db)]
        if json_out:
            _json(rows)
            return
        table = Table(title="Runtime discovery")
        for col in ("Runtime", "Detectado", "Estado", "Razón"):
            table.add_column(col, style="cyan")
        ready = 0
        for row in rows:
            mark = "✓" if row.get("detected") else "○"
            state = row["state"]
            if row.get("ready"):
                ready += 1
            table.add_row(f"{mark} {row['name']}", str(row.get("detected", "-")), state, row.get("reason", ""))
        console.print(table)
        console.print(f"\n{ready}/{len(rows)} runtimes listos")
        console.print("\nHabilitá uno con: conciencia onboard  (o Settings → Agents → Runtimes)")
    finally:
        db.close()


@app.command("onboard")
def onboard_cmd(
    yes: bool = typer.Option(False, "--yes", "-y", help="Habilitar runtimes detectados sin otra confirmación"),
    json_out: bool = typer.Option(False, "--json", help="Sólo mostrar detección; no modifica configuración"),
):
    """Detect and optionally enable external AI runtimes with explicit consent."""
    from app.core.agent_runtime import TYPE_CLI, get_runtime_configs, save_runtime_configs
    from app.services.capability_readiness import runtime_readiness

    db = _make_session()
    try:
        configs = get_runtime_configs(db)
        rows = [
            runtime_readiness(db, cfg.name, config=cfg)
            for cfg in configs
            if cfg.type == TYPE_CLI
        ]
        candidates = [row for row in rows if row["detected"] and not row["enabled"]]
        if json_out:
            _json({"runtimes": rows, "configurable": [row["name"] for row in candidates]})
            return
        table = Table(title="Detected AI runtimes")
        for column in ("Runtime", "Detectado", "Habilitado", "Estado"):
            table.add_column(column, style="cyan" if column == "Runtime" else None)
        for row in rows:
            table.add_row(row["name"], str(row["detected"]), str(row["enabled"]), row["state"])
        console.print(table)
        if not candidates:
            console.print("No hay runtimes detectados pendientes de configuración.")
            return
        names = ", ".join(row["name"] for row in candidates)
        console.print(f"\n{len(candidates)} runtime(s) detectados y deshabilitados: {names}")
        if not yes and not typer.confirm("¿Habilitarlos en Conciencia?", default=False):
            console.print("Sin cambios.", style="yellow")
            return
        candidate_names = {row["name"] for row in candidates}
        payload = [
            {**cfg.to_dict(), "enabled": True if cfg.name in candidate_names else cfg.enabled}
            for cfg in configs
        ]
        save_runtime_configs(db, payload)
        console.print(f"Habilitados: {names}", style="green")
        console.print("Ejecutá `conciencia doctor` para verificar readiness.")
    finally:
        db.close()


@agent_app.command("inspect")
def agent_inspect(
    agent_id: str = typer.Argument(..., help="ID o rol del agente (dev, ops, research…)"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Muestra detalle de un agente (SOUL, capabilities, runtime, permisos)."""
    import uuid as _uuid

    db = _make_session()
    try:
        from app.models.agent import Agent
        from app.services.agent_soul import load_agent_persona, AGENTS_DIR

        agent = None
        try:
            agent = db.query(Agent).filter(Agent.id == _uuid.UUID(str(agent_id))).first()
        except Exception:
            agent = None
        if not agent:
            agent = db.query(Agent).filter(Agent.role == agent_id.lower()).first()
        if not agent:
            from sqlalchemy import func

            agent = db.query(Agent).filter(func.lower(Agent.name) == agent_id.lower()).first()
        if not agent:
            console.print(f"Agente no encontrado: {agent_id}", style="red")
            raise typer.Exit(1)

        role = agent.role.value if hasattr(agent.role, "value") else str(agent.role)
        persona = load_agent_persona(role) or ""
        d = {
            "id": str(agent.id),
            "name": agent.name,
            "emoji": agent.emoji,
            "role": role,
            "runtime": agent.runtime.value if hasattr(agent.runtime, "value") else agent.runtime,
            "provider": agent.provider.value if hasattr(agent.provider, "value") else agent.provider,
            "model": agent.model,
            "status": agent.status.value if hasattr(agent.status, "value") else agent.status,
            "capabilities": agent.capabilities or [],
            "config": {"permissions": (agent.config or {}).get("permissions")},
            "soul": persona[:2000],
            **_agent_health(db, agent),
        }
        if json_out:
            _json(d)
            return
        table = Table(title=f"{agent.emoji or ''} {agent.name} ({role})")
        table.add_column("Campo", style="cyan")
        table.add_column("Valor")
        for k in ("id", "runtime", "provider", "model", "status", "health_status", "availability", "runtime_ready"):
            table.add_row(k, str(d[k]))
        table.add_row("health_reason", d["health_reason"])
        table.add_row("runtime_reason", d["runtime_reason"])
        table.add_row("capabilities", ", ".join(d["capabilities"]))
        if d.get("config", {}).get("permissions"):
            perm = d["config"]["permissions"]
            table.add_row("permissions", f"allow={perm.get('allow')} deny={perm.get('deny')}")
        console.print(table)
        if persona:
            console.print("\n[cyan]SOUL.md (primeros 600 chars):[/cyan]")
            console.print(persona[:600])
    finally:
        db.close()


@agent_app.command("run")
def agent_run(
    agent_id: str = typer.Argument(..., help="ID o rol del agente (dev, ops, research…)"),
    task: str = typer.Argument(..., help="Tarea a ejecutar"),
    runtime: Optional[str] = typer.Option(None, "--runtime", help="Override de runtime (codex, openclaw…)"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Ejecuta el agente con una tarea (adapter de su runtime)."""
    import uuid as _uuid
    from datetime import datetime as _dt

    db = _make_session()
    try:
        from app.models.agent import Agent
        from app.models.execution import AgentExecution, ExecutionStatus
        from app.adapters.registry import get_adapter
        from app.adapters.base import AgentIdentity
        from app.services.agent_soul import load_agent_persona

        agent = None
        try:
            agent = db.query(Agent).filter(Agent.id == _uuid.UUID(str(agent_id))).first()
        except Exception:
            agent = None
        if not agent:
            agent = db.query(Agent).filter(Agent.role == agent_id.lower()).first()
        if not agent:
            from sqlalchemy import func

            agent = db.query(Agent).filter(func.lower(Agent.name) == agent_id.lower()).first()
        if not agent:
            console.print(f"Agente no encontrado: {agent_id}", style="red")
            raise typer.Exit(1)

        runtime_name = (getattr(agent, "runtime", None) or "generic")
        runtime_name = runtime_name.value if hasattr(runtime_name, "value") else runtime_name
        if runtime:
            runtime_name = runtime.lower()

        provider_name = getattr(agent, "provider", None)
        provider_name = provider_name.value if hasattr(provider_name, "value") else (provider_name or "deepseek")
        role = agent.role.value if hasattr(agent.role, "value") else str(agent.role)
        system_prompt = load_agent_persona(role) or agent.system_prompt or agent.personality or ""

        identity = AgentIdentity(
            agent_id=str(agent.id), name=agent.name, role=role,
            runtime=runtime_name, provider=provider_name, model=agent.model,
            system_prompt=system_prompt, capabilities=agent.capabilities or [],
            config=agent.config or {},
        )

        execution = AgentExecution(agent_id=agent.id, status=ExecutionStatus.RUNNING, started_at=_dt.utcnow())
        db.add(execution)
        db.commit()
        db.refresh(execution)

        if runtime_name == "generic" or runtime_name == getattr(agent, "runtime", None):
            adapter = get_adapter(runtime_name)
            if not adapter:
                console.print(f"Runtime '{runtime_name}' sin adapter", style="red")
                raise typer.Exit(1)
            result = adapter.dispatch_task(identity, task, None)
        else:
            from app.core.agent_runtime import run_in_runtime
            from app.adapters.base import DispatchResult
            cli = run_in_runtime(db, runtime_name, task, None)
            result = DispatchResult(ok=cli.ok, status=cli.status, output=cli.output, error=cli.error, runtime=cli.runtime)

        if not result.ok or result.status == "failed":
            execution.status = ExecutionStatus.FAILED
            execution.error_message = result.error
            execution.completed_at = _dt.utcnow()
            db.commit()
            console.print(f"❌ {agent.name} falló: {result.error}", style="red")
            raise typer.Exit(1)

        execution.status = ExecutionStatus.COMPLETED
        execution.output = result.output
        execution.completed_at = _dt.utcnow()
        db.commit()

        if json_out:
            _json({"agent": agent.name, "status": "completed", "output": result.output, "execution_id": str(execution.id)})
            return
        console.print(f"✅ {agent.name} · runtime={result.runtime} · model={result.model or '-'}")
        console.print("---")
        console.print((result.output or "(sin output)")[:2000])
    finally:
        db.close()


@app.command("model")
def model_list(json_out: bool = typer.Option(False, "--json")):
    """Lista providers/modelos configurados del LLM Harness."""
    db = _make_session()
    try:
        from app.models.agent import Agent
        from app.services.capability_readiness import provider_readiness

        agents = db.query(Agent).order_by(Agent.name).all()
        seen = set()
        for a in agents:
            prov = getattr(a, "provider", None)
            prov_name = prov.value if hasattr(prov, "value") else (prov or "?")
            model = getattr(a, "model", None) or "default"
            seen.add((prov_name, model))
        active = provider_readiness()
        seen.add((active["provider"], active["model"]))
        rows = [provider_readiness(provider=provider, model=model) for provider, model in sorted(seen)]
        if json_out:
            _json(rows)
            return
        table = Table(title="Models / providers")
        for col in ("Provider", "Model", "Registrado", "Configurado", "Credenciales", "Estado"):
            table.add_column(col, style="cyan")
        for row in rows:
            table.add_row(
                row["provider"],
                row["model"],
                str(row["registered"]),
                str(row["configured"]),
                row["credentials"],
                row["state"],
            )
        console.print(table)
    finally:
        db.close()


@workflow_app.callback()
def workflow_root(
    ctx: typer.Context,
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Keep `conciencia workflow` as a legacy alias for workflow list."""
    if ctx.invoked_subcommand is None:
        workflow_list(json_out=json_out)


@workflow_app.command("list")
def workflow_list(json_out: bool = typer.Option(False, "--json")):
    """Lista workflows (declarativos, con estado)."""
    db = _make_session()
    try:
        from app.models.workflow import Workflow
        workflows = db.query(Workflow).order_by(Workflow.created_at.desc()).limit(50).all()
        if json_out:
            _json([w.to_dict() for w in workflows])
            return
        if not workflows:
            console.print("Sin workflows.", style="yellow")
            return
        table = Table(title=f"Workflows ({len(workflows)})")
        for col in ("ID", "Nombre", "Status", "Steps", "Misión"):
            table.add_column(col, style="cyan")
        for w in workflows:
            table.add_row(w.id[:12], w.name, w.status, str(len(w.definition or [])), w.project_id or "-")
        console.print(table)
    finally:
        db.close()


@workflow_app.command("inspect")
@app.command("workflow-inspect", hidden=True)
def workflow_inspect(workflow_id: str = typer.Argument(...)):
    """Muestra la definición de steps de un workflow."""
    db = _make_session()
    try:
        from app.models.workflow import Workflow
        wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not wf:
            console.print(f"Workflow no encontrado: {workflow_id}", style="red")
            raise typer.Exit(1)
        console.print(f"[cyan]{wf.name}[/cyan] · status={wf.status}")
        for i, step in enumerate(wf.definition or []):
            gate = "🔒 aprobación" if step.get("approval") else ""
            caps = ",".join(step.get("capabilities") or []) or "—"
            console.print(f"  {i}: [bold]{step.get('name', f'step_{i}')}[/bold] caps={caps} timeout={step.get('timeout', 0)}s retry={step.get('retry', 0)} {gate}")
    finally:
        db.close()


@workflow_app.command("run")
@app.command("workflow-run", hidden=True)
def workflow_run_cmd(workflow_id: str = typer.Argument(...), json_out: bool = typer.Option(False, "--json")):
    """Ejecuta un workflow directamente (workflow_engine)."""
    db = _make_session()
    try:
        from app.models.workflow import Workflow
        from app.services import workflow_engine
        wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not wf:
            console.print(f"Workflow no encontrado: {workflow_id}", style="red")
            raise typer.Exit(1)
        run = workflow_engine.execute_workflow(db, wf.id)
        if json_out:
            _json(run.to_dict())
            return
        console.print(f"🏃 Workflow {wf.name} · run={run.id[:12]} · status={run.status}")
        for step in (run.step_results or []):
            icon = "✅" if step.get("status") == "completed" else ("🔒" if step.get("status") == "waiting_approval" else "❌")
            console.print(f"  {icon} {step.get('step_name')} · {step.get('status')} · cost={step.get('cost', 0)}")
    finally:
        db.close()


@run_app.command("watch")
@app.command("run-watch", hidden=True)
def run_watch(
    run_id: str = typer.Argument(..., help="ID del MissionRun (UUID o corto R-xxxx)"),
    interval: float = typer.Option(2.0, "--interval", help="Segundos entre polls"),
    max_waits: int = typer.Option(30, "--max-waits", help="Máximo de polls antes de salir"),
):
    """Observa un run de misión en vivo (logs + estado + costo)."""
    db = _make_session()
    try:
        rid = _resolve_uuid(db, run_id, "run")
        r = db.query(MissionRun).filter(MissionRun.id == uuid.UUID(rid)).first()
        if not r:
            console.print(f"Run no encontrado: {run_id}. Probá: conciencia run list", style="red")
            raise typer.Exit(1)
        mission = db.query(Mission).filter(Mission.id == r.mission_id).first()
        _watch_mission_run(db, r, mission, interval=interval, max_waits=max_waits)
    finally:
        db.close()


@mission_app.command("watch")
def mission_watch(
    mission_id: Optional[str] = typer.Argument(None, help="ID de la misión (UUID o M-xxxx); vacío usa la única activa"),
    interval: float = typer.Option(2.0, "--interval", help="Segundos entre polls"),
    max_waits: int = typer.Option(30, "--max-waits", help="Máximo de polls antes de salir"),
):
    """Observa en vivo el último run de una misión (§21)."""
    db = _make_session()
    try:
        if not mission_id:
            mission, hint = _active_mission_or_pick(db)
            if mission is None:
                console.print(hint, style="yellow")
                raise typer.Exit(1)
        else:
            mid = _resolve_uuid(db, mission_id, "mission")
            mission = db.query(Mission).filter(Mission.id == uuid.UUID(mid)).first()
        if not mission:
            console.print(f"Misión no encontrada. Probá: conciencia mission list", style="red")
            raise typer.Exit(1)
        run = (db.query(MissionRun).filter(MissionRun.mission_id == mission.id)
               .order_by(MissionRun.started_at.desc()).first())
        if not run:
            console.print(f"La misión {_short_id('mission', str(mission.id))} aún no tiene runs. "
                          f"Ejecutala: conciencia mission run {_short_id('mission', str(mission.id))}", style="yellow")
            raise typer.Exit(1)
        _watch_mission_run(db, run, mission, interval=interval, max_waits=max_waits)
    finally:
        db.close()


def _watch_mission_run(db, r, mission, interval: float, max_waits: int) -> None:
    """Loop de observación en vivo compartido (run watch / mission watch)."""
    import time as _time

    from rich.live import Live
    from rich.panel import Panel

    def render() -> Panel:
        db.expire_all()
        rr = db.query(MissionRun).filter(MissionRun.id == r.id).first()
        lines = [
            f"Misión: {mission.name if mission else '?'} ({rr.mission_id})",
            f"Status: [bold]{rr.status}[/bold] · Run: {rr.id}",
            f"Costo: ${rr.cost_usd.get('total', 0)}"
            + f" · Tokens: {rr.tokens.get('total', 0)}"
            + f" (prompt {rr.tokens.get('prompt', 0)} + completion {rr.tokens.get('completion', 0)})",
            f"Iniciado: {rr.started_at} · Completado: {rr.completed_at or '—'}",
        ]
        if rr.error:
            lines.append(f"Error: {rr.error}")
        logs = rr.logs or []
        if logs:
            lines.append("")
            lines.append("Timeline (últimos):")
            for lg in logs[-8:]:
                lines.append(f"  {lg.get('ts', '')[:23]} {lg.get('message', '')}")
        return Panel("\n".join(lines), title=f"MISSION RUN {str(rr.id)[:8]}")

    with Live(render(), refresh_per_second=2, console=console) as live:
        for _ in range(max_waits):
            live.update(render())
            db.expire_all()
            rr = db.query(MissionRun).filter(MissionRun.id == r.id).first()
            if rr.status in ("completed", "failed", "cancelled"):
                live.update(render())
                break
            _time.sleep(interval)


# ---------------------------------------------------------------------------
# Fase F — Teams: agrupar agentes especializados (master prompt §F)
# ---------------------------------------------------------------------------

@team_app.command("create")
def team_create(
    name: str = typer.Argument(..., help="Nombre del team"),
    purpose: Optional[str] = typer.Option(None, "--purpose", help="Para qué se usa"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    emoji: str = typer.Option("👥", "--emoji"),
    members: Optional[str] = typer.Option(None, "--members", help="IDs de agentes separados por coma"),
    runtime: str = typer.Option("generic", "--runtime", help="Runtime default: generic|claude_code|codex|opencode|openclaw|mcp"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Crea un team de agentes."""
    from app.services import team_service

    db = _make_session()
    try:
        t = team_service.create_team(
            db,
            name=name,
            purpose=purpose,
            description=description,
            emoji=emoji,
            member_ids=[m.strip() for m in members.split(",") if m.strip()] if members else None,
            default_runtime=runtime,
        )
        if json_out:
            _json(t.to_dict())
        else:
            console.print(f"✅ Team creado: {t.emoji} [cyan]{t.name}[/cyan] ({t.id})")
            console.print(f"   Miembros: {len(t.member_ids or [])} · Runtime default: {t.default_runtime}")
            console.print(f"   Siguiente: conciencia team members-add {t.id} <agent_id>")
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)
    finally:
        db.close()


@team_app.command("list")
def team_list(
    status: Optional[str] = typer.Option(None, "--status", help="active|paused|archived"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Lista teams."""
    from app.services import team_service

    db = _make_session()
    try:
        teams = team_service.list_teams(db, status=status)
        if json_out:
            _json([t.to_dict() for t in teams])
            return
        if not teams:
            console.print("Sin teams. Creá uno con: conciencia team create", style="yellow")
            return
        table = Table(title=f"Teams ({len(teams)})")
        for col in ("ID", "Nombre", "Propósito", "Status", "Miembros", "Runtime"):
            table.add_column(col, style="cyan" if col == "Nombre" else None)
        for t in teams:
            table.add_row(str(t.id)[:8], f"{t.emoji or '👥'} {t.name}", t.purpose or "-", t.status, str(len(t.member_ids or [])), t.default_runtime)
        console.print(table)
    finally:
        db.close()


@team_app.command("inspect")
def team_inspect(
    team_id: str = typer.Argument(..., help="ID del team"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Muestra detalle de un team + miembros."""
    from app.services import team_service

    db = _make_session()
    try:
        t = team_service.get_team(db, team_id)
        if not t:
            console.print(f"Team no encontrado: {team_id}", style="red")
            raise typer.Exit(1)
        if json_out:
            out = t.to_dict()
            out["members"] = [
                {"id": str(a.id), "name": a.name, "role": a.role.value if hasattr(a.role, "value") else str(a.role),
                 "runtime": a.runtime.value if hasattr(a.runtime, "value") else str(a.runtime),
                 "capabilities": a.capabilities or []}
                for a in team_service.resolve_team_agents(db, t)
            ]
            _json(out)
            return
        table = Table(title=f"{t.emoji or '👥'} {t.name}")
        table.add_column("Campo", style="cyan")
        table.add_column("Valor")
        for k, v in t.to_dict().items():
            table.add_row(k, str(v))
        console.print(table)
        members = team_service.resolve_team_agents(db, t)
        if members:
            mtable = Table(title="Miembros")
            for col in ("ID", "Nombre", "Rol", "Runtime", "Capabilities"):
                mtable.add_column(col, style="cyan")
            for a in members:
                mtable.add_row(str(a.id)[:8], a.name, a.role.value if hasattr(a.role, "value") else str(a.role),
                               a.runtime.value if hasattr(a.runtime, "value") else str(a.runtime),
                               ", ".join(a.capabilities or []))
            console.print(mtable)
    finally:
        db.close()


@team_app.command("members-add")
def team_members_add(
    team_id: str = typer.Argument(..., help="ID del team"),
    agent_id: str = typer.Argument(..., help="ID del agente"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Agrega un agente al team."""
    from app.services import team_service

    db = _make_session()
    try:
        t = team_service.get_team(db, team_id)
        if not t:
            console.print(f"Team no encontrado: {team_id}", style="red")
            raise typer.Exit(1)
        t = team_service.add_member(db, t, agent_id)
        if json_out:
            _json(t.to_dict())
        else:
            console.print(f"✅ Agente {agent_id} agregado a {t.name} ({len(t.member_ids or [])} miembros)")
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)
    finally:
        db.close()


@team_app.command("members-remove")
def team_members_remove(
    team_id: str = typer.Argument(..., help="ID del team"),
    agent_id: str = typer.Argument(..., help="ID del agente"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Quita un agente del team."""
    from app.services import team_service

    db = _make_session()
    try:
        t = team_service.get_team(db, team_id)
        if not t:
            console.print(f"Team no encontrado: {team_id}", style="red")
            raise typer.Exit(1)
        t = team_service.remove_member(db, t, agent_id)
        if json_out:
            _json(t.to_dict())
        else:
            console.print(f"✅ Agente {agent_id} removido de {t.name} ({len(t.member_ids or [])} miembros)")
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)
    finally:
        db.close()


@team_app.command("match")
def team_match(
    capabilities: str = typer.Argument(..., help="Capabilities requeridas separadas por coma"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Teams que cubren las capabilities, ordenados por score."""
    from app.services import team_service

    db = _make_session()
    try:
        caps = [c.strip() for c in capabilities.split(",") if c.strip()]
        matches = team_service.match_teams(db, required_capabilities=caps)
        if json_out:
            _json(matches)
            return
        if not matches:
            console.print("Ningún team activo cubre esas capabilities.", style="yellow")
            return
        table = Table(title=f"Teams para: {', '.join(caps)}")
        for col in ("ID", "Nombre", "Coverage", "Score", "Miembros", "Runtime"):
            table.add_column(col, style="cyan")
        for m in matches:
            table.add_row(m["team_id"][:8], m["name"], f"{m['coverage']}%", str(m["score"]), str(m["members_count"]), m["default_runtime"])
        console.print(table)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fase G — Harnesses: contratos versionados de ejecución (master prompt §G)
# ---------------------------------------------------------------------------

@harness_app.command("create")
def harness_create(
    name: str = typer.Argument(..., help="Nombre del harness"),
    spec_file: Optional[str] = typer.Option(None, "--spec", "-f", help="Archivo JSON con el spec ({instructions, runtime.allowed, ...})"),
    version: str = typer.Option("1.0.0", "--version"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Crea un harness (draft). --spec apunta a un archivo JSON con el spec."""
    from app.services import harness_service

    spec = None
    if spec_file:
        import pathlib

        p = pathlib.Path(spec_file)
        if not p.is_file():
            console.print(f"Archivo de spec no encontrado: {spec_file}", style="red")
            raise typer.Exit(1)
        try:
            spec = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            console.print(f"Spec inválido (JSON): {e}", style="red")
            raise typer.Exit(1)

    db = _make_session()
    try:
        h = harness_service.create_harness(db, name=name, description=description, spec=spec, version=version)
        if json_out:
            _json(h.to_dict())
        else:
            console.print(f"✅ Harness creado: [cyan]{h.name}[/cyan] v{h.version} ({h.id})")
            console.print(f"   Status: {h.status} · Activalo con: conciencia harness activate {h.id}")
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)
    finally:
        db.close()


@harness_app.command("list")
def harness_list(
    status: Optional[str] = typer.Option(None, "--status", help="draft|active|archived"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Lista harnesses."""
    from app.services import harness_service

    db = _make_session()
    try:
        harnesses = harness_service.list_harnesses(db, status=status)
        if json_out:
            _json([h.to_dict() for h in harnesses])
            return
        if not harnesses:
            console.print("Sin harnesses. Creá uno con: conciencia harness create", style="yellow")
            return
        table = Table(title=f"Harnesses ({len(harnesses)})")
        for col in ("ID", "Nombre", "Versión", "Status", "Runtime allowed"):
            table.add_column(col, style="cyan" if col == "Nombre" else None)
        for h in harnesses:
            allowed = ", ".join((h.spec or {}).get("runtime", {}).get("allowed", [])) or "-"
            table.add_row(str(h.id)[:8], h.name, h.version, h.status, allowed)
        console.print(table)
    finally:
        db.close()


@harness_app.command("inspect")
def harness_inspect(
    harness_id: str = typer.Argument(..., help="ID del harness"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Muestra detalle de un harness (spec + historial de versiones)."""
    from app.services import harness_service

    db = _make_session()
    try:
        h = harness_service.get_harness(db, harness_id)
        if not h:
            console.print(f"Harness no encontrado: {harness_id}", style="red")
            raise typer.Exit(1)
        if json_out:
            _json(h.to_dict())
            return
        table = Table(title=f"{h.name} v{h.version}")
        table.add_column("Campo", style="cyan")
        table.add_column("Valor")
        for k, v in h.to_dict().items():
            table.add_row(k, json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v))
        console.print(table)
    finally:
        db.close()


@harness_app.command("activate")
def harness_activate(
    harness_id: str = typer.Argument(..., help="ID del harness"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Activa un harness (solo activos se pueden usar en misiones)."""
    from app.services import harness_service

    db = _make_session()
    try:
        h = harness_service.get_harness(db, harness_id)
        if not h:
            console.print(f"Harness no encontrado: {harness_id}", style="red")
            raise typer.Exit(1)
        h = harness_service.set_status(db, h, "active")
        if json_out:
            _json(h.to_dict())
        else:
            console.print(f"✅ Harness activado: [cyan]{h.name}[/cyan] v{h.version}")
    finally:
        db.close()


@harness_app.command("validate")
def harness_validate(
    harness_id: str = typer.Argument(..., help="ID del harness"),
    output: str = typer.Argument(..., help="Output real del agente a validar"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Prueba un output contra el output_contract del harness."""
    from app.services import harness_service

    db = _make_session()
    try:
        h = harness_service.get_harness(db, harness_id)
        if not h:
            console.print(f"Harness no encontrado: {harness_id}", style="red")
            raise typer.Exit(1)
        ok, errors = harness_service.validate_output(h, output)
        if json_out:
            _json({"ok": ok, "errors": errors})
        elif ok:
            console.print("✅ Output válido contra el contrato", style="green")
        else:
            console.print("❌ Output inválido:", style="red")
            for e in errors:
                console.print(f"   • {e}", style="red")
            raise typer.Exit(1)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fase I — Signals: hallazgos trazables con evidencia (master prompt §I)
# ---------------------------------------------------------------------------

@signal_app.command("list")
def signal_list(
    mission_id: Optional[str] = typer.Option(None, "--mission", "-m", help="Filtrar por misión"),
    type: Optional[str] = typer.Option(None, "--type", "-t", help="insight|risk|opportunity|decision|lead|finding"),
    status: Optional[str] = typer.Option(None, "--status", help="new|acknowledged|dismissed"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Lista signals (hallazgos de misiones)."""
    from app.services import signal_service

    db = _make_session()
    try:
        signals = signal_service.list_signals(db, mission_id=mission_id, type=type, status=status)
        if json_out:
            _json([s.to_dict() for s in signals])
            return
        if not signals:
            console.print("Sin signals.", style="yellow")
            return
        table = Table(title=f"Signals ({len(signals)})")
        for col in ("ID", "Tipo", "Título", "Status", "Misión", "Fuente"):
            table.add_column(col, style="cyan" if col == "Título" else None)
        for s in signals:
            table.add_row(str(s.id)[:8], s.type, s.title[:40], s.status, str(s.mission_id)[:8], s.source_step or "-")
        console.print(table)
    finally:
        db.close()


@signal_app.command("inspect")
def signal_inspect(
    signal_id: str = typer.Argument(..., help="ID de la signal"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Muestra detalle de una signal + evidencia."""
    from app.services import signal_service

    db = _make_session()
    try:
        s = signal_service.get_signal(db, signal_id)
        if not s:
            console.print(f"Signal no encontrada: {signal_id}", style="red")
            raise typer.Exit(1)
        if json_out:
            _json(s.to_dict())
            return
        table = Table(title=f"[{s.type}] {s.title}")
        table.add_column("Campo", style="cyan")
        table.add_column("Valor")
        d = s.to_dict()
        d.pop("evidence", None)
        for k, v in d.items():
            table.add_row(k, str(v))
        console.print(table)
        if s.evidences:
            console.print("\nEvidencia:")
            for e in s.evidences:
                console.print(f"  • [{e.kind}] {e.content[:200]}" + (f" ({e.source})" if e.source else ""))
    finally:
        db.close()


@signal_app.command("add")
def signal_add(
    mission_id: str = typer.Argument(..., help="ID de la misión"),
    title: str = typer.Argument(..., help="Título del hallazgo"),
    type: str = typer.Option("finding", "--type", "-t", help="insight|risk|opportunity|decision|lead|finding"),
    summary: Optional[str] = typer.Option(None, "--summary", "-s"),
    evidence: Optional[str] = typer.Option(None, "--evidence", "-e", help="Contenido de evidencia (quote)"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Registra una signal manualmente (con evidencia opcional)."""
    from app.services import signal_service

    db = _make_session()
    try:
        sig = signal_service.create_signal(
            db,
            mission_id=mission_id,
            title=title,
            type=type,
            summary=summary,
            evidences=[{"kind": "quote", "content": evidence}] if evidence else None,
        )
        if json_out:
            _json(sig.to_dict())
        else:
            console.print(f"✅ Signal [{sig.type}]: {sig.title} ({sig.id})")
            console.print(f"   Evidencia: {len(sig.evidences)} ítem(s) · Misión {mission_id}")
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)
    finally:
        db.close()


@signal_app.command("extract")
def signal_extract(
    mission_id: str = typer.Argument(..., help="ID de la misión"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Extrae signals desde los outputs de la misión (marcadores SIGNAL:/EVIDENCE:)."""
    from app.models.mission import Mission
    from app.services import signal_service

    db = _make_session()
    try:
        mission = db.query(Mission).filter(Mission.id == uuid.UUID(str(mission_id))).first()
        if not mission:
            console.print(f"Misión no encontrada: {mission_id}", style="red")
            raise typer.Exit(1)
        created = signal_service.extract_from_mission(db, mission)
        if json_out:
            _json([s.to_dict() for s in created])
        elif created:
            console.print(f"✅ {len(created)} signal(s) extraídas:")
            for s in created:
                console.print(f"  • [{s.type}] {s.title} — {len(s.evidences)} evidencia(s)")
        else:
            console.print("Sin marcadores SIGNAL: en los outputs (nada que extraer).", style="yellow")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fase J — Context packs: retrieval eficiente (master prompt §J)
# ---------------------------------------------------------------------------

@context_app.command("retrieve")
def context_retrieve(
    query: str = typer.Argument(..., help="Query / objetivo de la misión"),
    project_id: Optional[str] = typer.Option(None, "--project", "-p", help="Filtrar por proyecto"),
    limit: int = typer.Option(3, "--limit", "-n", min=1, max=10),
    json_out: bool = typer.Option(False, "--json"),
):
    """ContextPacks rankeados por relevancia al query (retrieval eficiente)."""
    from app.services import context_retrieval

    db = _make_session()
    try:
        packs = context_retrieval.retrieve_packs(db, query=query, project_id=project_id, limit=limit)
        if json_out:
            _json(packs)
            return
        if not packs:
            console.print("Ningún context pack relevante.", style="yellow")
            return
        table = Table(title=f"Context packs para: {query}")
        for col in ("ID", "Título", "Score", "Términos", "Proyecto"):
            table.add_column(col, style="cyan" if col == "Título" else None)
        for p in packs:
            table.add_row(p["pack_id"][:8], p["title"][:40], str(p["score"]),
                          ", ".join(p["matched_terms"][:4]), str(p.get("project_id") or "-")[:8])
        console.print(table)
    finally:
        db.close()


@context_app.command("assemble")
def context_assemble(
    query: str = typer.Argument(..., help="Query / objetivo de la misión"),
    project_id: Optional[str] = typer.Option(None, "--project", "-p"),
    limit: int = typer.Option(3, "--limit", "-n", min=1, max=10),
    max_chars: int = typer.Option(6000, "--max-chars", "-c"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Ensambla contexto acotado (solo lo que entra en max_chars)."""
    from app.services import context_retrieval

    db = _make_session()
    try:
        result = context_retrieval.assemble_context(
            db, query=query, project_id=project_id, limit=limit, max_chars=max_chars
        )
        if json_out:
            _json(result)
            return
        if not result["packs"]:
            console.print("Ningún context pack relevante.", style="yellow")
            return
        console.print(f"📦 {len(result['packs'])} pack(s) · {result['total_chars']} chars"
                      + (" · truncado" if result["truncated"] else ""))
        for p in result["packs"]:
            console.print(f"  • {p['title']} (score {p['score']})")
        console.print("\n--- contexto ---")
        console.print(result["context"][:2000])
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fase K — WebMCP: apps web WebMCP-enabled (master prompt §K)
# ---------------------------------------------------------------------------

@webmcp_app.command("run")
def webmcp_run(
    url: str = typer.Argument(..., help="Base URL de la app WebMCP-enabled"),
    actions: str = typer.Argument(..., help="Acciones separadas por coma: input:#name:Juan, click:#increment, submit, navigate:/x"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Ejecuta un script de acciones contra una app WebMCP-enabled (preserva evidencia)."""
    from app.services.webmcp import client as wm

    parsed = []
    for raw in [a.strip() for a in actions.split(",") if a.strip()]:
        parts = raw.split(":")
        atype = parts[0]
        if atype == "input":
            if len(parts) < 3:
                console.print(f"input necesita selector:valor → {raw}", style="red")
                raise typer.Exit(1)
            parsed.append({"type": "input", "selector": parts[1], "value": ":".join(parts[2:])})
        elif atype in ("click", "submit", "navigate"):
            action = {"type": atype}
            if len(parts) > 1:
                action["selector" if atype in ("click", "submit") else "url"] = parts[1]
            parsed.append(action)
        else:
            console.print(f"acción no soportada: {atype}", style="red")
            raise typer.Exit(1)

    try:
        result = wm.run_script(url, parsed)
    except wm.WebMCPError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)

    if json_out:
        _json(result)
        return
    console.print(f"🌐 WebMCP contra {result['url']} — {result['actions_count']} acción(es)")
    for a in result["action_log"]:
        mark = "✅" if a["ok"] else "❌"
        console.print(f"  {mark} {a['action']} → {a.get('result') or a.get('error')}")
    from app.services.webmcp import render_snapshot
    console.print(render_snapshot(result.get("snapshot") or {}))


@webmcp_app.command("demo")
def webmcp_demo(
    port: int = typer.Option(8765, "--port", "-p"),
):
    """Corre la demo app WebMCP-enabled (formulario + contador) para probar."""
    from app.services.webmcp.demo_app import create_demo_app
    import uvicorn

    console.print(f"🌐 WebMCP Demo App: http://127.0.0.1:{port}  (Ctrl+C para salir)")
    console.print("   Ejemplo: conciencia webmcp run http://127.0.0.1:8765 \"input:#name:Juan,input:#email:j@x.com,submit\"")
    uvicorn.run(create_demo_app(), host="127.0.0.1", port=port, log_level="warning")


# ---------------------------------------------------------------------------
# Fase L — Economics: economía de misiones inspeccionable (master prompt §L)
# ---------------------------------------------------------------------------

@economics_app.command("summary")
def economics_summary(
    days: int = typer.Option(30, "--days", "-d", help="Período en días"),
    mission_id: Optional[str] = typer.Option(None, "--mission", "-m", help="Economía de una misión específica"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Economía de plataforma (o de una misión): costos, tokens, modelos, outcomes."""
    from app.services import economics_service

    db = _make_session()
    try:
        if mission_id:
            data = economics_service.mission_economics(db, mission_id)
            title = f"Economía de misión: {data['mission_name']}"
        else:
            data = economics_service.platform_economics(db, days=days)
            title = f"Economía de plataforma (últimos {data['period_days']} días)"
        if json_out:
            _json(data)
            return
        console.print(f"[bold cyan]{title}[/bold cyan]")
        cost = data["cost_usd"]
        tok = data["tokens"]
        console.print(f"   Costo: ${cost['total']} (LLM ${cost['llm']} + tools ${cost['tools']})")
        console.print(f"   Tokens: {tok['total']} (prompt {tok['prompt']} + completion {tok['completion']})")
        if mission_id:
            console.print(f"   Runs: {data['runs_count']} · Status: {data['status']} · Outcomes: {data['outcomes']}")
        else:
            console.print(f"   Misiones: {data['missions_count']} · Runs: {data['runs_count']}")
            console.print(f"   Outcomes: {data['outcomes']}")
            if data.get("llm_cost_records"):
                console.print(f"   CostRecords LLM: ${data['llm_cost_records']} · {data['llm_tokens_records']} tokens")
        if data["cost_by_provider"]:
            console.print("   Por provider:")
            for p in data["cost_by_provider"]:
                console.print(f"     • {p['key']}: ${p['cost_usd']} · {p['tokens']} tokens · {p['calls']} llamada(s)")
        if data["cost_by_model"]:
            console.print("   Por modelo:")
            for m in data["cost_by_model"][:5]:
                console.print(f"     • {m['key']}: ${m['cost_usd']} · {m['tokens']} tokens")
        console.print(f"   Acciones: {data['actions_count']} · Tool calls: {data['tool_calls_count']} · Runtimes: {data.get('runtime_usage', {})}")
        if mission_id:
            console.print("   Runs:")
            for r in data["runs"]:
                ext = sum(e.get("cost_usd", 0) for e in r.get("external_costs") or [])
                console.print(f"     • {r['id'][:8]} {r['status']} · ${r['cost_usd'].get('total', 0)} · tokens {r['tokens'].get('total', 0)}" + (f" · ext ${ext}" if ext else ""))
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)
    finally:
        db.close()


@economics_app.command("record-external")
def economics_record_external(
    run_id: str = typer.Argument(..., help="ID del MissionRun"),
    tool: str = typer.Argument(..., help="Herramienta/servicio (ej: webmcp, scraper)"),
    cost_usd: float = typer.Argument(..., help="Costo en USD"),
    detail: Optional[str] = typer.Option(None, "--detail", "-d"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Registra un costo externo (tool/servicio) en un run."""
    from app.services import economics_service

    db = _make_session()
    try:
        entry = economics_service.record_external_cost(
            db, mission_run_id=run_id, tool=tool, cost_usd=cost_usd, detail=detail
        )
        if json_out:
            _json(entry)
        else:
            console.print(f"✅ Costo externo registrado: {tool} ${cost_usd} en run {run_id}")
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    app()

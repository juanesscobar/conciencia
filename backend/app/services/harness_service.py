"""HarnessService — CRUD versionado + aplicación de harness a agentes/misiones.

Fase G (master prompt): un Harness formaliza CÓMO ejecuta un agente
(instructions, context, tools, validation, guardrails, runtime, output_contract)
y es VERSIONADO + REUTILIZABLE entre misiones.

  apply_harness(harness, agent, mission_ctx) → (identity_patch, errors)
    - instructions → system_prompt (template renderizado)
    - context      → contexto ensamblado (template + objective/project/context_pack)
    - runtime      → guardrail: runtime del agente debe estar en spec.runtime.allowed
    - tools/guardrails/validation → identity.config["harness"]

  validate_output(harness, output) → (ok, errors)
    - output_contract: format json → parse + required_fields; min_length; etc.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.harness import Harness, HARNESS_STATUSES, DEFAULT_HARNESS_SPEC

log = logging.getLogger("harnesses")


# ---------------------------------------------------------------------------
# CRUD + versionado
# ---------------------------------------------------------------------------

def create_harness(
    db: Session,
    *,
    name: str,
    description: Optional[str] = None,
    spec: Optional[dict] = None,
    version: str = "1.0.0",
) -> Harness:
    if not name.strip():
        raise ValueError("Harness name requerido")
    cleaned = _merge_spec(spec or {})
    h = Harness(
        name=name.strip(),
        description=description,
        version=version or "1.0.0",
        spec=cleaned,
        status="draft",
        versions=[],
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    log.info("harness creado: %s v%s (%s)", h.name, h.version, h.id)
    return h


def list_harnesses(db: Session, status: Optional[str] = None, limit: int = 50) -> List[Harness]:
    q = db.query(Harness).order_by(Harness.created_at.desc())
    if status:
        if status not in HARNESS_STATUSES:
            raise ValueError(f"Status inválido: {status}. Válidos: {', '.join(HARNESS_STATUSES)}")
        q = q.filter(Harness.status == status)
    return q.limit(limit).all()


def get_harness(db: Session, harness_id: str) -> Optional[Harness]:
    return db.query(Harness).filter(Harness.id == uuid.UUID(str(harness_id))).first()


def update_harness(
    db: Session,
    harness: Harness,
    *,
    patch: dict,
    new_version: Optional[str] = None,
    changes: Optional[str] = None,
) -> Harness:
    """Actualiza spec/campos. Con new_version → versiona (snapshot a historial)."""
    allowed = {"name", "description", "spec", "status"}
    for k, v in patch.items():
        if k not in allowed:
            continue
        if k == "name" and (not v or not str(v).strip()):
            raise ValueError("Harness name requerido")
        if k == "status" and v not in HARNESS_STATUSES:
            raise ValueError(f"Status inválido: {v}")
        if k == "spec":
            v = _merge_spec(v or {})
        setattr(harness, k, v)

    if new_version:
        if new_version == harness.version:
            raise ValueError(f"La versión {new_version} ya es la actual")
        history = list(harness.versions or [])
        history.append({
            "version": harness.version,
            "changes": changes or "",
            "updated_at": datetime.utcnow().isoformat(),
            "snapshot": harness.to_dict(),
        })
        harness.versions = history
        harness.version = new_version

    db.commit()
    db.refresh(harness)
    return harness


def set_status(db: Session, harness: Harness, status: str) -> Harness:
    if status not in HARNESS_STATUSES:
        raise ValueError(f"Status inválido: {status}")
    harness.status = status
    db.commit()
    db.refresh(harness)
    return harness


def delete_harness(db: Session, harness: Harness) -> None:
    db.delete(harness)
    db.commit()


# ---------------------------------------------------------------------------
# Aplicación a un agente
# ---------------------------------------------------------------------------

def apply_harness(
    harness: Harness,
    agent: Any,
    *,
    mission_context: Optional[dict] = None,
) -> Tuple[dict, List[str]]:
    """Resuelve el harness sobre un agente.

    Devuelve (patch, errors) donde patch es un dict para ajustar la identidad:
      {system_prompt, context, config}
    errors no vacíos = el harness BLOQUEA la ejecución (guardrails de runtime).
    """
    spec = harness.spec or {}
    errors: List[str] = []

    # --- runtime guardrail ---
    runtime_allowed = (spec.get("runtime") or {}).get("allowed") or []
    agent_runtime = getattr(agent, "runtime", "generic")
    agent_runtime_name = agent_runtime.value if hasattr(agent_runtime, "value") else str(agent_runtime or "generic")
    if runtime_allowed and agent_runtime_name not in runtime_allowed:
        errors.append(
            f"runtime '{agent_runtime_name}' no permitido por harness '{harness.name}' "
            f"(allowed: {', '.join(runtime_allowed)})"
        )
        return {}, errors

    # --- instructions → system_prompt (template) ---
    instructions = (spec.get("instructions") or "").strip()
    system_prompt = None
    if instructions:
        system_prompt = _render_template(instructions, mission_context or {})

    # --- context ---
    context_spec = spec.get("context") or {}
    context = None
    ctx_template = (context_spec.get("template") or "").strip()
    if ctx_template:
        context = _render_template(ctx_template, mission_context or {})
    max_chars = int(context_spec.get("max_chars") or 6000)
    if context and len(context) > max_chars:
        context = context[:max_chars]

    # --- tools / guardrails / validation → config (contrato para adapters) ---
    config = dict(getattr(agent, "config", None) or {})
    config["harness"] = {
        "harness_id": str(harness.id),
        "harness_name": harness.name,
        "harness_version": harness.version,
        "tools": spec.get("tools") or {"allow": [], "deny": []},
        "guardrails": spec.get("guardrails") or [],
        "validation": spec.get("validation") or {},
        "output_contract": spec.get("output_contract") or {},
    }

    patch: dict = {"config": config}
    if system_prompt is not None:
        patch["system_prompt"] = system_prompt
    if context is not None:
        patch["context"] = context
    return patch, errors


def build_mission_context(
    db: Session,
    *,
    objective: Optional[str] = None,
    description: Optional[str] = None,
    project_name: Optional[str] = None,
    project_id: Optional[str] = None,
    context_pack_id: Optional[str] = None,
) -> dict:
    """Variables disponibles para los templates del harness.

    Fase J: el contexto del pack se resuelve con retrieval eficiente — pack
    explícito de la misión, o top-2 por relevancia al objetivo (nunca el
    proyecto entero).
    """
    ctx: Dict[str, Any] = {
        "objective": objective or "",
        "description": description or "",
        "project_name": project_name or "",
        "context_pack": "",
        "context_pack_title": "",
    }
    from app.services import context_retrieval

    pack_text, packs_used = context_retrieval.context_for_mission(
        db,
        objective=objective or "",
        project_id=project_id,
        context_pack_id=context_pack_id,
    )
    ctx["context_pack"] = pack_text
    if packs_used:
        ctx["context_pack_title"] = ", ".join(p["title"] for p in packs_used)
        ctx["context_packs"] = packs_used
    else:
        ctx["context_packs"] = []
    return ctx


def _get_context_pack(db: Session, context_pack_id: str):
    from app.models.context_pack import ContextPack
    return db.query(ContextPack).filter(ContextPack.id == context_pack_id).first()


# ---------------------------------------------------------------------------
# Validación de outputs (output contract)
# ---------------------------------------------------------------------------

def validate_output(harness: Harness, output: Optional[str]) -> Tuple[bool, List[str]]:
    """Valida el output contra el output_contract + reglas de validation.output.

    Devuelve (ok, errors). Si no hay contrato/reglas → (True, []).
    """
    spec = harness.spec or {}
    contract = spec.get("output_contract") or {}
    rules = (spec.get("validation") or {}).get("output") or {}
    if not contract and not rules:
        return True, []

    errors: List[str] = []
    text = (output or "").strip()
    fmt = contract.get("format", "text")

    if fmt == "json":
        data = None
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            errors.append("output no es JSON válido (output_contract.format=json)")
        if data is not None:
            for field in contract.get("required_fields") or []:
                if _dig(data, field) is None:
                    errors.append(f"campo requerido '{field}' ausente en output JSON")
    elif fmt == "markdown" and text and not any(tok in text for tok in ("#", "-", "*", "```")):
        errors.append("output no parece markdown (output_contract.format=markdown)")

    min_len = rules.get("min_length")
    if min_len and len(text) < int(min_len):
        errors.append(f"output demasiado corto (min_length={min_len}, len={len(text)})")
    if rules.get("required_substring"):
        sub = rules["required_substring"]
        if sub not in text:
            errors.append(f"output no contiene la subcadena requerida '{sub}'")

    return (not errors), errors


def _dig(data, path: str):
    """Acceso a campo anidado: 'a.b.c'."""
    cur = data
    for part in str(path).split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return None
    return cur


# ---------------------------------------------------------------------------
# helpers internos
# ---------------------------------------------------------------------------

def _merge_spec(spec: dict) -> dict:
    """Merge con el spec default (solo campos conocidos, deep por sección)."""
    merged = json.loads(json.dumps(DEFAULT_HARNESS_SPEC))
    for section, value in spec.items():
        if section not in merged:
            continue
        if isinstance(value, dict) and isinstance(merged[section], dict):
            merged[section].update({k: v for k, v in value.items() if k in merged[section]})
        else:
            merged[section] = value
    return merged


def _render_template(template: str, ctx: dict) -> str:
    """Reemplaza {placeholder} por valores del contexto (ignora los que falten)."""
    out = template
    for k, v in ctx.items():
        out = out.replace("{" + k + "}", str(v if v is not None else ""))
    return out

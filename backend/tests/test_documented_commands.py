"""§33 master-prompt-cli — los comandos documentados deben ser shell-safe.

Escanea los bloques ``` de README.md y docs/USAGE.md buscando líneas que empiecen
con `conciencia ` y valida que el árbol de comandos las resuelva (sin ejecutarlas).

Detecta pseudo-sintaxis documentada que rompe shells: `·`, `|`, `<id>` como parte
del comando, etc.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import typer
import pytest

from cli import app

REPO = Path(__file__).resolve().parents[2]
DOCS = [REPO / "README.md", REPO / "docs" / "USAGE.md"]

CMD_RE = re.compile(r"^\s*(conciencia\s+\S.*)$")

# patrones que rompen shells si se pegan tal cual (Tier A — falla en cualquier doc)
TIER_A = [" · ", "<cmd>"]
# placeholders crudos en bloques copiables (Tier B — solo README)
TIER_B = ["<id>", "<mission>", "<step>", "<id|rol>", "<mission_id>"]


def _fence_lines(path: Path):
    """Devuelve líneas dentro de bloques de código (``` ... ```)."""
    in_fence = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            yield raw


def _strip_comment(line: str) -> str:
    """Quita comentarios inline (' # comentario') para validar solo el comando."""
    idx = line.find("  #")
    return line[:idx] if idx > 0 else line


def _resolve_tree(typer_app, tokens):
    """Camina el árbol de comandos: devuelve (ok, razon)."""
    if not tokens:
        return True, "ok (línea sin subcomando → ayuda)"
    obj = typer_app
    for i, tok in enumerate(tokens):
        if tok.startswith("-"):
            return True, "ok (resto son opciones/valores)"
        if isinstance(obj, typer.Typer):
            groups = {c.name: c for c in obj.registered_groups}
            commands = {c.name: c for c in obj.registered_commands}
            if tok in commands:
                return True, "ok (comando final)"
            if tok in groups:
                obj = groups[tok].typer_instance
                continue
            return False, f"'{tok}' no es comando/subcomando de '{obj.info.name}'"
        else:
            return True, "ok (argumentos)"
    return True, "ok"


def _validate(doc: Path, tiers) -> list:
    bad = []
    for line in _fence_lines(doc):
        m = CMD_RE.match(line)
        if not m:
            continue
        cmdline = _strip_comment(m.group(1))
        offenders = TIER_A + (TIER_B if "TierB" in tiers else [])
        for offender in offenders:
            if offender in cmdline:
                bad.append(f"{line.strip()[:80]}  (contiene '{offender}')")
                break
        else:
            tokens = cmdline.replace("\\", " ").split()
            ok, why = _resolve_tree(app, tokens[1:])
            if not ok:
                bad.append(f"{line.strip()[:80]}  ({why})")
    return bad


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: p.name)
def test_comandos_documentados_resuelven(doc):
    if not doc.exists():
        pytest.skip(f"{doc.name} no existe")
    tiers = "TierB" if doc.name == "README.md" else ""
    bad = _validate(doc, tiers)
    assert not bad, f"{doc.name}: {len(bad)} ejemplo(s) no shell-safe:\n" + "\n".join(bad[:10])


def test_readme_no_tiene_separadores_pseudo_shell():
    readme = (REPO / "README.md").read_text(encoding="utf-8", errors="replace")
    for bad in ("conciencia agents ·", "create|plan|run", "status · conciencia doctor", "conciencia lead inspect <id>"):
        assert bad not in readme, f"README aún contiene pseudo-sintaxis: {bad}"

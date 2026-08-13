"""OpenClawAdapter — ejecuta tareas invocando el CLI de OpenClaw.

Runtime real: `openclaw run <prompt>` (o `openclaw agent run`) en un workspace.
Mission Control solo orquesta: no reimplementa el harness de OpenClaw.

NOTA: el adapter delega en el CLI. Si OPENCLAW_BIN no está disponible,
devuelve un resultado con estado claro (no simula silenciosamente).
"""

import shutil
import subprocess
import time
from typing import Optional

from .base import AgentAdapter, AgentIdentity, DispatchResult


class OpenClawAdapter(AgentAdapter):
    runtime_name = "openclaw"

    def get_capabilities(self) -> list:
        return ["cli_exec", "tool_use", "streaming_logs", "session_persistence"]

    def dispatch_task(self, identity: AgentIdentity, task: str, context: Optional[str] = None) -> DispatchResult:
        start = time.time()
        bin_path = identity.config.get("openclaw_bin") or shutil.which("openclaw")
        if not bin_path:
            return DispatchResult(
                ok=False,
                status="failed",
                error="OpenClaw CLI no encontrado. Instalalo o configurá openclaw_bin en el agente.",
                runtime=self.runtime_name,
                simulated=True,
                duration_ms=int((time.time() - start) * 1000),
                meta={"reason": "openclaw_not_installed"},
            )

        prompt = task
        if context:
            prompt = f"## CONTEXTO\n{context}\n\n## TAREA\n{task}"

        try:
            proc = subprocess.run(
                [bin_path, "run", "--agent", identity.role, prompt],
                capture_output=True,
                text=True,
                timeout=600,
                cwd=identity.workspace or None,
            )
            output = (proc.stdout or "").strip() or (proc.stderr or "").strip()
            ok = proc.returncode == 0
            return DispatchResult(
                ok=ok,
                status="completed" if ok else "failed",
                output=output,
                error=None if ok else (proc.stderr or proc.stdout or "")[:300],
                runtime=self.runtime_name,
                duration_ms=int((time.time() - start) * 1000),
                meta={"returncode": proc.returncode},
            )
        except subprocess.TimeoutExpired:
            return DispatchResult(
                ok=False,
                status="failed",
                error="Timeout: OpenClaw no respondió en 600s",
                runtime=self.runtime_name,
                duration_ms=int((time.time() - start) * 1000),
            )
        except Exception as e:  # noqa: BLE001
            return DispatchResult(
                ok=False,
                status="failed",
                error=str(e)[:300],
                runtime=self.runtime_name,
                duration_ms=int((time.time() - start) * 1000),
            )

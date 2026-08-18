"""Cliente MCP mínimo sobre stdio (JSON-RPC 2.0, newline-delimited).

Permite adjuntar cualquier MCP server (spawn via command/args) y
exponer sus tools al Control Plane (Tool Registry). Stdlib puro.
"""

import json
import logging
import subprocess
import threading
from typing import Any, Dict, List, Optional

log = logging.getLogger("mcp.client")

PROTOCOL_VERSION = "2024-11-05"


class MCPError(Exception):
    pass


class MCPClient:
    def __init__(self, name: str, command: str, args: Optional[List[str]] = None,
                 env: Optional[Dict[str, str]] = None, cwd: Optional[str] = None,
                 timeout: float = 30.0):
        self.name = name
        self._id = 0
        self._lock = threading.Lock()
        self._timeout = timeout
        self._proc: Optional[subprocess.Popen] = None
        self._env = env
        self._cwd = cwd
        self._command = command
        self._args = args or []
        self._initialized = False

    # ---- lifecycle ----

    def _ensure_proc(self):
        if self._proc is None or self._proc.poll() is not None:
            import os
            env = dict(os.environ)
            if self._env:
                env.update(self._env)
            self._proc = subprocess.Popen(
                [self._command] + self._args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                env=env,
                cwd=self._cwd,
            )
            self._initialized = False

    def connect(self):
        self._ensure_proc()
        if not self._initialized:
            self._request("initialize", {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "conciencia-control-plane", "version": "2.0"},
            })
            self._send_notification("notifications/initialized", {})
            self._initialized = True

    def close(self):
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:  # noqa: BLE001
                try:
                    self._proc.kill()
                except Exception:  # noqa: BLE001
                    pass
        self._proc = None

    # ---- protocol ----

    def _send_notification(self, method: str, params: dict):
        self._ensure_proc()
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()

    def _request(self, method: str, params: dict) -> Any:
        self._ensure_proc()
        with self._lock:
            self._id += 1
            msg = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}
            self._proc.stdin.write(json.dumps(msg) + "\n")
            self._proc.stdin.flush()
            line = self._proc.stdout.readline()
            if not line:
                raise MCPError(f"MCP server '{self.name}' cerró stdout sin respuesta")
            try:
                resp = json.loads(line)
            except json.JSONDecodeError as e:
                raise MCPError(f"MCP server '{self.name}' respuesta inválida: {line[:200]}") from e
            if resp.get("error"):
                raise MCPError(f"MCP error {resp['error'].get('code')}: {resp['error'].get('message')}")
            return resp.get("result")

    # ---- tools ----

    def list_tools(self) -> List[dict]:
        self.connect()
        result = self._request("tools/list", {}) or {}
        return result.get("tools", [])

    def call_tool(self, tool_name: str, arguments: Optional[dict] = None) -> Any:
        self.connect()
        result = self._request("tools/call", {
            "name": tool_name,
            "arguments": arguments or {},
        }) or {}
        # MCP devuelve contenido estructurado: extraer texto
        return self._extract_content(result)

    @staticmethod
    def _extract_content(result: dict) -> Any:
        if "content" in result and isinstance(result["content"], list):
            texts = []
            for item in result["content"]:
                if isinstance(item, dict) and item.get("type") == "text":
                    texts.append(item.get("text", ""))
            if len(texts) == 1:
                return texts[0]
            return texts
        return result

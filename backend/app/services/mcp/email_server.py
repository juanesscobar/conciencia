"""Servidor MCP de email - expone tools de email al Control Plane.

Corre como proceso hijo del backend (stdio):
    python -m app.services.mcp.email_server

Lee las cuentas desde la misma DB (settings) y expone:
  - email_list_accounts
  - email_send(account_id, to, subject, body)
  - email_inbox(account_id, limit)
  - email_test(account_id)
"""

import json
import sys


def _read_line() -> str:
    line = sys.stdin.readline()
    return line


def _write(obj) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _accounts() -> list:
    from app.database import SessionLocal
    from app.modules.email.models import EmailAccount

    db = SessionLocal()
    try:
        return [a.to_dict() for a in db.query(EmailAccount).all()]
    finally:
        db.close()


def _load_account(account_id: str) -> dict:
    for acc in _accounts():
        if acc["id"] == account_id:
            return acc
    raise ValueError(f"cuenta {account_id} no encontrada")


TOOLS = [
    {
        "name": "email_list_accounts",
        "description": "Lista las cuentas de email configuradas (id, nombre, proveedor, email).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "email_send",
        "description": "Envía un email por SMTP desde una cuenta configurada.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "ID de la cuenta (email_list_accounts)"},
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["account_id", "to", "subject", "body"],
            "additionalProperties": False,
        },
    },
    {
        "name": "email_inbox",
        "description": "Lista los últimos emails del inbox (IMAP) de una cuenta.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "limit": {"type": "integer", "description": "Máx. emails (default 20, máx 50)"},
            },
            "required": ["account_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "email_test",
        "description": "Prueba conexión IMAP y SMTP de una cuenta.",
        "inputSchema": {
            "type": "object",
            "properties": {"account_id": {"type": "string"}},
            "required": ["account_id"],
            "additionalProperties": False,
        },
    },
]


def _call(name: str, args: dict):
    from app.modules.email import service

    if name == "email_list_accounts":
        accs = _accounts()
        return {"accounts": [{k: v for k, v in a.items() if k != "password"} for a in accs]}
    if name == "email_send":
        acc = _load_account(args["account_id"])
        return service.send_email(acc, args["to"], args["subject"], args["body"])
    if name == "email_inbox":
        acc = _load_account(args["account_id"])
        return {"messages": service.list_inbox(acc, limit=min(int(args.get("limit", 20)), 50))}
    if name == "email_test":
        acc = _load_account(args["account_id"])
        return service.test_connection(acc)
    raise ValueError(f"tool desconocida: {name}")


def main():
    while True:
        line = _read_line()
        if not line:
            break
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("method") == "initialize":
            _write({"jsonrpc": "2.0", "id": msg.get("id"), "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "conciencia-email-mcp", "version": "1.0"},
            }})
        elif msg.get("method") == "notifications/initialized":
            pass
        elif msg.get("method") == "tools/list":
            _write({"jsonrpc": "2.0", "id": msg.get("id"), "result": {"tools": TOOLS}})
        elif msg.get("method") == "tools/call":
            params = msg.get("params") or {}
            name = params.get("name")
            args = params.get("arguments") or {}
            try:
                result = _call(name, args)
                _write({"jsonrpc": "2.0", "id": msg.get("id"), "result": {
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                }})
            except Exception as e:  # noqa: BLE001
                _write({"jsonrpc": "2.0", "id": msg.get("id"), "result": {
                    "content": [{"type": "text", "text": json.dumps({"error": str(e)}, ensure_ascii=False)}],
                    "isError": True,
                }})
        else:
            _write({"jsonrpc": "2.0", "id": msg.get("id"), "error": {
                "code": -32601, "message": f"método no soportado: {msg.get('method')}",
            }})


if __name__ == "__main__":
    main()

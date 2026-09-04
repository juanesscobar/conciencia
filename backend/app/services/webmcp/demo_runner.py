"""Runner de la demo app WebMCP (Fase K) — `python -m app.services.webmcp.demo_runner [--port N]`.

Lee PORT del entorno si existe (deploy en Render/Railway/Fly).
"""

import argparse
import os
import uvicorn

from app.services.webmcp.demo_app import create_demo_app


def main() -> None:
    parser = argparse.ArgumentParser(description="WebMCP Demo App (Fase K)")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8765")))
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    args = parser.parse_args()
    print(f"WebMCP Demo App: http://{args.host}:{args.port}  (bridge en /api/webmcp/*)")
    uvicorn.run(create_demo_app(), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()

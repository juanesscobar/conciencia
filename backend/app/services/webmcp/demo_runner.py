"""Runner de la demo app WebMCP (Fase K) — `python -m app.services.webmcp.demo_runner --port 8765`."""

import argparse
import uvicorn

from app.services.webmcp.demo_app import create_demo_app


def main() -> None:
    parser = argparse.ArgumentParser(description="WebMCP Demo App (Fase K)")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    print(f"WebMCP Demo App: http://{args.host}:{args.port}  (bridge en /api/webmcp/*)")
    uvicorn.run(create_demo_app(), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()

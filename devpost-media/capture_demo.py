"""Captura screenshots reales de la demo WebMCP (para Devpost).

Usa playwright con el Chrome instalado (channel='chrome', headless).
El estado de la demo arranca limpio (reset) y se documenta el flujo humano.
"""
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(r"C:\Users\juane\.openclaw\workspace\mission-control\devpost-media")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://127.0.0.1:8765"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 820}, device_scale_factor=1.5)
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(1200)

        # 1. estado limpio
        page.screenshot(path=str(OUT / "01-demo-app-clean.png"))
        time.sleep(1)

        # 2. llenar el formulario (como humano)
        page.fill("#name", "María López")
        page.fill("#email", "maria@logistik.com.py")
        page.fill("#message", "Quiero cotizar flete refrigerado Asunción–CDE")
        page.wait_for_timeout(900)
        page.screenshot(path=str(OUT / "02-form-filled.png"))

        # 3. enviar
        page.click("#submit")
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / "03-submitted.png"))

        # 4. contador
        page.click("#increment")
        page.click("#increment")
        page.wait_for_timeout(900)
        page.screenshot(path=str(OUT / "04-counter.png"))

        # 5. reset + una segunda interacción (agente)
        page.click("#reset")
        page.wait_for_timeout(600)
        page.fill("#name", "Agente Conciencia")
        page.fill("#email", "bot@conciencia.dev")
        page.click("#submit")
        page.wait_for_timeout(1100)
        page.screenshot(path=str(OUT / "05-agent-submit.png"))

        browser.close()
        print("screenshots OK:", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()

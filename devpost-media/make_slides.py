"""Genera slides 1280x720 para el video de Devpost (PIL)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(r"C:\Users\juane\.openclaw\workspace\mission-control\devpost-media")
W, H = 1280, 720
BG = (10, 15, 26)          # fondo oscuro control-plane
GREEN = (0, 255, 65)
WHITE = (235, 240, 245)
GREY = (150, 160, 175)
ACCENT = (0, 217, 255)

FONT_MONO = r"C:\Windows\Fonts\consola.ttf"
FONT_MONO_B = r"C:\Windows\Fonts\consolab.ttf"


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for word in text.split(" "):
        t = (cur + " " + word).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def _caption_bar(img, caption):
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 90, W, H], fill=(16, 22, 36))
    d.line([0, H - 90, W, H - 90], fill=(0, 217, 255), width=2)
    f = _font(FONT_MONO, 26)
    for i, ln in enumerate(_wrap(d, caption, f, W - 120)):
        d.text((60, H - 78 + i * 32), ln, font=f, fill=WHITE)
        if i >= 1:
            break


def screenshot_slide(png, caption, out, max_w=1180):
    im = Image.open(png).convert("RGB")
    ratio = max_w / im.width
    im = im.resize((int(im.width * ratio), int(im.height * ratio)), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), BG)
    x = (W - im.width) // 2
    y = 24
    canvas.paste(im, (x, y))
    _caption_bar(canvas, caption)
    canvas.save(out)
    print("slide:", out.name)


def terminal_slide(title, body, out, accent=GREEN):
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    # header
    d.rectangle([0, 0, W, 56], fill=(16, 22, 36))
    d.text((40, 14), f"$ conciencia {title}", font=_font(FONT_MONO_B, 26), fill=ACCENT)
    # body: solo líneas de contenido clave
    lines = [l.rstrip() for l in body.splitlines()]
    # recortar líneas vacías del final
    while lines and not lines[-1].strip():
        lines.pop()
    # skip header tables que no aportan
    f = _font(FONT_MONO, 21)
    max_lines = (H - 56 - 30) // 28
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    y = 70
    for ln in lines:
        if not ln.strip():
            y += 12
            continue
        d.text((40, y), ln[:110], font=f, fill=accent if ln.strip().startswith(("│", "┌", "└")) else WHITE)
        y += 28
    canvas.save(out)
    print("slide:", out.name)


def title_slide(out, big, small, footer):
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    d.line([0, 300, W, 300], fill=ACCENT, width=3)
    d.text((60, 150), big, font=_font(FONT_MONO_B, 54), fill=WHITE)
    y = 340
    f30 = _font(FONT_MONO, 30)
    for para in small.split("\n"):
        for ln in _wrap(d, para, f30, W - 120):
            d.text((60, y), ln, font=f30, fill=GREEN)
            y += 40
        y += 10
    d.text((60, H - 80), footer, font=_font(FONT_MONO, 24), fill=GREY)
    canvas.save(out)
    print("slide:", out.name)


# ---- slides de screenshot (app demo) ----
screenshot_slide(BASE / "01-demo-app-clean.png",
                "Una app web común (formulario + contador)… ahora agent-native: declara tools WebMCP estándar (get_status, submit_contact, increment_counter)",
                BASE / "s-app-clean.png")
screenshot_slide(BASE / "02-form-filled.png",
                "Una persona la completa a mano — el estado se refleja en vivo para humanos y agentes",
                BASE / "s-form-filled.png")
screenshot_slide(BASE / "03-submitted.png",
                "El envío queda registrado: visitas +1. El agente puede hacer EXACTAMENTE lo mismo vía la tool submit_contact",
                BASE / "s-submitted.png")
screenshot_slide(BASE / "04-counter.png",
                "Mismo estado en tiempo real para todos: formulario, contador y visitas (poller /api/webmcp/context)",
                BASE / "s-counter.png")
screenshot_slide(BASE / "05-agent-submit.png",
                "Un agente (Conciencia) completa y envía el formulario con la tool estructurada — sin adivinar el UI",
                BASE / "s-agent.png")

# ---- slides terminal (control plane) ----
run_txt = (BASE / "cli_run.txt").read_text(encoding="utf-8-sig", errors="replace")
idx = run_txt.find("Steps (")
terminal_slide("run inspect <id> --steps", run_txt[idx:] if idx > 0 else run_txt, BASE / "s-cli-run.png")

sig_txt = (BASE / "cli_signal_detail.txt").read_text(encoding="utf-8-sig", errors="replace")
terminal_slide("signal inspect <id>", sig_txt, BASE / "s-cli-signal.png")

eco_txt = (BASE / "cli_economics.txt").read_text(encoding="utf-8-sig", errors="replace")
terminal_slide("economics summary --mission", eco_txt, BASE / "s-cli-eco.png")

# ---- título + cierre ----
title_slide(BASE / "s-title.png",
            "CONCIENCIA",
            "Open Control Plane for the Agent-Native Web\nMisión → Tools WebMCP → Evidencia → Aprobación humana → Economics\n\nWebMCP Challenge · github.com/juanesscobar/mission-control",
            "El web agent-native necesita gobernanza: quién actuó, qué hizo, cuánto costó.")
title_slide(BASE / "s-close.png",
            "Humans + Agents, mismo web",
            "Una app WebMCP-enabled:\n· la usa una persona en el navegador\n· la usa ChatGPT con document.modelContext.registerTool\n· la ejecuta una MISIÓN de Conciencia con evidencia y aprobación\n\nDemo live: mc.46.62.196.151.sslip.io/webmcp-demo/",
            "MIT · FastAPI + React · 309 tests green")
print("DONE")

"""Generación de PDF para propuestas comerciales (fpdf2, sin dependencias nativas)."""

import re
import unicodedata
from io import BytesIO
from typing import Optional

from fpdf import FPDF

# Paleta dark/terminal de Mission Control
PRIMARY = (0, 255, 65)        # verde matrix #00ff41
DARK = (10, 14, 12)           # fondo oscuro
PANEL = (18, 24, 20)          # panel
TEXT = (215, 220, 215)        # texto
MUTED = (130, 140, 132)       # gris
ACCENT = (100, 255, 180)


def _clean(s: str) -> str:
    """Limpia caracteres que fpdf no soporta (control chars + símbolos fuera de latin-1)."""
    if not s:
        return ""
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", s)
    # Reemplaza símbolos comunes no-latin1 por equivalentes ASCII
    s = s.replace("—", "-").replace("–", "-").replace("‘", "'").replace("’", "'")
    s = s.replace("“", "\"").replace("”", "\"").replace("…", "...").replace("•", "-")
    s = s.replace("→", "->").replace("←", "<-").replace("✓", "OK").replace("✅", "[OK]")
    s = s.replace("🎯", "[OBJ]").replace("💡", "[IDEA]").replace("🔥", "[HOT]")
    s = s.replace("🚀", "[GO]").replace("📌", "[PIN]").replace("⭐", "*")
    s = s.replace("€", "EUR ").replace("$ ", "USD ")
    # Descarta cualquier otro carácter fuera del rango latin-1 (0-255)
    s = "".join(ch if ord(ch) < 256 else "?" for ch in s)
    s = unicodedata.normalize("NFKC", s)
    # Garantía final: codifica/decodifica cp1252 (lo que soporta Helvetica core)
    s = s.encode("cp1252", errors="replace").decode("cp1252")
    return s


def _markdown_to_lines(content: str, max_width: int, pdf: FPDF) -> list:
    """Convierte markdown simple a líneas con estilo básico.

    Devuelve lista de (texto, tipo) donde tipo ∈ heading1..3, bullet, item, plain.
    """
    out = []
    for raw in content.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("### "):
            out.append((_clean(stripped[4:]), "h3"))
        elif stripped.startswith("## "):
            out.append((_clean(stripped[3:]), "h2"))
        elif stripped.startswith("# "):
            out.append((_clean(stripped[2:]), "h1"))
        elif re.match(r"^[-*•]\s+", stripped):
            out.append((_clean(re.sub(r"^[-*•]\s+", "", stripped)), "bullet"))
        elif re.match(r"^\d+[.)]\s+", stripped):
            out.append((_clean(re.sub(r"^\d+[.)]\s+", "", stripped)), "bullet"))
        else:
            out.append((_clean(stripped), "plain"))
    return out


def render_proposal_pdf(
    *,
    company: str,
    contact_name: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    title: str,
    content: str,
    model: Optional[str] = None,
    generated_at: Optional[str] = None,
    proposal_status: Optional[str] = None,
) -> bytes:
    """Genera el PDF de la propuesta y devuelve los bytes."""
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # ---------- Header ----------
    pdf.set_fill_color(*DARK)
    pdf.rect(0, 0, 210, 24, "F")
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(0, 24, 210, 0.8, "F")

    pdf.set_y(9)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(0, 6, "MISSION CONTROL", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 4, "Software Factory - Propuesta Comercial", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(32)

    # ---------- Título ----------
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*TEXT)
    pdf.multi_cell(0, 8, _clean(title or f"Propuesta — {company}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # ---------- Datos del cliente ----------
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 5, "CLIENTE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*TEXT)
    pdf.cell(0, 6, _clean(company), new_x="LMARGIN", new_y="NEXT")
    meta_lines = []
    if contact_name:
        meta_lines.append(f"Contacto: {_clean(contact_name)}")
    if email:
        meta_lines.append(f"Email: {_clean(email)}")
    if phone:
        meta_lines.append(f"Tel: {_clean(phone)}")
    if generated_at:
        meta_lines.append(f"Generada: {_clean(generated_at)}")
    for ml in meta_lines:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 5, _clean(ml), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)
    pdf.set_draw_color(*PRIMARY)
    pdf.set_line_width(0.3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    # ---------- Cuerpo (markdown) ----------
    lines = _markdown_to_lines(content, pdf.epw, pdf)
    for text, kind in lines:
        if kind == "h1":
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(*PRIMARY)
            pdf.multi_cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        elif kind == "h2":
            pdf.set_font("Helvetica", "B", 11.5)
            pdf.set_text_color(*ACCENT)
            pdf.multi_cell(0, 6.5, text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        elif kind == "h3":
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(*TEXT)
            pdf.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(0.5)
        elif kind == "bullet":
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(*TEXT)
            bullet = "  -  " + text
            pdf.multi_cell(0, 5.5, bullet, new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("Helvetica", "", 9.5)
            pdf.set_text_color(*TEXT)
            pdf.multi_cell(0, 5.5, text, new_x="LMARGIN", new_y="NEXT")

    # ---------- Footer ----------
    page_count = pdf.pages_count
    for i in range(1, page_count + 1):
        pdf.page = i
        pdf.set_y(-14)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 5, f"Mission Control - {_clean(company or '')} - Pagina {i}/{page_count}", align="C")
        if model:
            pdf.set_y(-9)
            pdf.cell(0, 4, f"Generada con {_clean(model)}", align="C")

    return bytes(pdf.output())

"""NL → SearchQuery: intent parser por reglas (spec §3, §5/§6/§32).

Convierte una query humana en un SearchQuery estructurado, sin API key:
categorías/sinónimos (es/en) + geografía (ciudades/departamentos PY) +
campos requeridos ("con website", "con teléfono", "con email").
El backend LLM (DeepSeek) queda como fallback opcional si no matchea nada.
"""

import re
import unicodedata
from typing import List, Optional

from .search import SearchQuery

# ---------------------------------------------------------------------------
# Sinónimos de categorías/industrias (es + en) → categoría canónica.
# Las categorías se mapean a la industria usada por las fuentes (overpass).
# ---------------------------------------------------------------------------

CATEGORY_SYNONYMS: dict = {
    "salud": ["hospital", "clinica", "clínica", "sanatorio", "salud", "medico", "médico",
              "dentista", "odontologo", "odontólogo", "centro de salud", "health", "clinic",
              "medical"],
    "farmacia": ["farmacia", "farmacias", "botica", "drogueria", "droguería", "pharmacy"],
    "financiero": ["banco", "bancos", "financiera", "financiero", "fintech", "casa de cambio",
                   "bank", "credit union"],
    "cooperativa": ["cooperativa", "cooperativas", "cooperative", "credit cooperative"],
    "comercio": ["supermercado", "supermercados", "comercio", "tienda", "minimarket",
                 "almacen", "almacén", "bazar", "retail", "shop", "grocery", "supermarket",
                 "autoservicio"],
    "distribuidora": ["distribuidora", "distribuidor", "mayorista", "wholesale", "distribution",
                      "distribucion", "distribución", "proveedor"],
    "industria": ["industria", "fabrica", "fábrica", "industrial", "manufactura", "factory",
                  "manufacturing", "planta"],
    "automotriz": ["playa de autos", "playa de vehiculos", "playa de vehículos", "autos usados",
                   "car dealer", "dealership", "concesionaria", "concesionario", "automotora",
                   "automotriz", "vehiculos usados", "vehículos usados", "used cars", "automotive",
                   "vehicle dealership", "car sales"],
    "gastronomia": ["restaurante", "restaurantes", "pizzeria", "pizzería", "cafeteria",
                    "cafetería", "heladeria", "heladería", "hamburgueseria", "hamburguesería",
                    "comida", "food", "restaurant", "bar", "pub", "parrilla"],
    "educacion": ["colegio", "colegios", "escuela", "escuelas", "instituto", "academia",
                  "universidad", "jardin de infantes", "kindergarten", "school", "education",
                  "kinder"],
    "tecnologia": ["software", "informatica", "informática", "tecnologia", "tecnología", "tech",
                   "sistemas", "computacion", "computación", "desarrollo web", "it services",
                   "data center"],
    "logistica": ["logistica", "logística", "transporte", "transport", "flete", "fletes",
                  "courier", "mudanza", "mudanzas", "envios", "envíos", "shipping", "logistics"],
    "construccion": ["constructora", "construccion", "construcción", "ferreteria", "ferretería",
                     "materiales", "building materials", "construction", "inmobiliaria",
                     "inmobiliario", "real estate"],
    "hoteleria": ["hotel", "hoteles", "hostal", "hospedaje", "alojamiento", "motel", "resort",
                  "hoteleria", "hotelería", "lodging"],
    "seguros": ["seguro", "seguros", "insurance", "aseguradora"],
    "servicios": ["servicios", "services", "consultora", "consulting", "asesoria", "asesoría",
                  "profesional", "professional services"],
}

# ---------------------------------------------------------------------------
# Geografía PY: ciudades y departamentos (normalizados, sin acentos).
# ---------------------------------------------------------------------------

PY_CITIES: List[str] = [
    "asuncion", "ciudad del este", "san lorenzo", "luque", "capiata", "lambare",
    "fernando de la mora", "limpio", "mariano roque alonso", "nemby", "villa elisa",
    "itagua", "itaugua", "ypacarai", "aregua", "san antonio", "encarnacion",
    "caaguazu", "coronel oviedo", "villarrrica", "pilar", "concepcion",
    "pedro juan caballero", "salto del guaira", "presidente franco", "hernandarias",
    "minga guazu", "caacupe", "villa hayes", "mariscal estigarribia", "filadelfia",
    "ciudad del este", "capiata",
]

PY_DEPARTMENTS: List[str] = [
    "central", "alto parana", "itapua", "caaguazu", "cordillera", "guaira",
    "paraguari", "caazapa", "san pedro", "amambay", "canindeyu", "concepcion",
    "presidente hayes", "boqueron", "neembucu", "misiones", "alto paraguay",
]

# Sinónimos de país → código ISO (para country en SearchQuery)
COUNTRY_ALIASES: dict = {
    "PY": ["paraguay", "py", "paraguayo"],
    "BR": ["brasil", "brazil", "br"],
    "AR": ["argentina", "ar"],
    "UY": ["uruguay", "uy"],
}

# Campos requeridos ("con website", "con teléfono", ...)
REQUIRED_FIELD_PATTERNS: List[tuple] = [
    ("website", re.compile(r"\b(website|web|sitio web|sitio|pagina web|pagina|con web|con website|con sitio|con pagina)\b")),
    ("phone", re.compile(r"\b(telefono|teléfono|numero de telefono|tel |celular|whatsapp|phone|phone number|con telefono|con tel)\b")),
    ("email", re.compile(r"\b(email|correo|correo electronico|mail|con email|con correo|con mail)\b")),
]

# Conectores/palabras vacías que se descartan del texto residual
STOPWORDS = set(
    "a al algo algunas algunos ante antes como con contra cual cuando de del desde donde durante "
    "e el ella ellas ellos en entre era erais eran eras eres es esa esas ese esos esta estas este "
    "estos fue fueron ha han hasta hay la las le les lo los me mi mis mucho muchos muy nada ni no "
    "nos nosotros o os otra otras otro otros para pero poco que quien quienes se sea sean ser si "
    "sin sobre sois somos son soy su sus también tanto te tenia tenemos tenemos tener tiene ti "
    "tiene todo todos tu tus un una uno unos vosotros y ya yo the and of to in for with that have "
    "has are is on at by from or as an it this they them their there where which who whom what "
    "when why how find found businesses business companies company negocio negocios empresas "
    "empresa que tengan activos activo actives operando".split()
)


def _norm(s: str) -> str:
    """Normaliza: minúsculas, sin acentos."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9ñ\s]", " ", s)


def _detect_country(text: str) -> Optional[str]:
    for code, aliases in COUNTRY_ALIASES.items():
        for a in aliases:
            if re.search(rf"\b{re.escape(a)}\b", text):
                return code
    return None


def _detect_geo(text: str) -> tuple:
    """Devuelve (city, department) detectados en el texto, o (None, None)."""
    city, dept = None, None
    for c in PY_CITIES:
        if re.search(rf"\b{re.escape(c)}\b", text):
            city = c.title()
            break
    if not city:
        for d in PY_DEPARTMENTS:
            if re.search(rf"\b{re.escape(d)}\b", text):
                dept = d.title()
                break
    return city, dept


def _detect_category(text: str) -> tuple:
    """Devuelve (categoría, término matcheado) o (None, None).

    Acepta plurales simples (farmacias→farmacia, dealerships→dealership)
    vía sufijo opcional (s|es).
    """
    for cat, syns in CATEGORY_SYNONYMS.items():
        for s in syns:
            if re.search(rf"\b{re.escape(s)}(?:s|es)?\b", text):
                return cat, s
    return None, None


def _detect_required_fields(text: str) -> List[str]:
    fields = []
    for field, pattern in REQUIRED_FIELD_PATTERNS:
        if pattern.search(text):
            fields.append(field)
    return fields


def _residual_query(text: str, matched_terms: List[str]) -> Optional[str]:
    """Texto residual tras quitar términos ya interpretados (para full-text)."""
    t = text
    for term in matched_terms:
        t = re.sub(rf"\b{re.escape(term)}\b", " ", t)
    # También quitar los términos de campos requeridos detectados
    for _, pattern in REQUIRED_FIELD_PATTERNS:
        t = pattern.sub(" ", t)
    words = [w for w in t.split() if w not in STOPWORDS and len(w) > 1]
    return " ".join(words) or None


def interpret(text: str, default_country: str = "PY") -> SearchQuery:
    """Convierte texto libre en un SearchQuery estructurado (reglas).

    Fallback LLM opcional (DeepSeek) si no se detectó nada: se deja el hook
    documentado para Fase posterior sin romper si no hay API key.
    """
    raw = (text or "").strip()
    if not raw:
        return SearchQuery(country=default_country or "PY")

    ntext = _norm(raw)
    matched: List[str] = []

    country = _detect_country(ntext) or default_country
    city, dept = _detect_geo(ntext)
    category, cat_term = _detect_category(ntext)
    required = _detect_required_fields(ntext)

    if dept:
        matched.append(dept.lower())
    if city:
        matched.append(city.lower())
    if cat_term:
        matched.append(cat_term)

    # Scope geográfico derivado
    scope = "country"
    if city:
        scope = "city"
    elif dept:
        scope = "region"

    residual = _residual_query(ntext, matched)

    # Si se detectaron filtros estructurados, un residuo de 0-1 tokens es ruido
    # de sinónimos (ej: "playas" tras detectar automotriz en "playas de autos
    # usados") — descartarlo evita que el full-text contradiga los filtros (spec §5).
    if (city or dept or category or required) and residual:
        rwords = [w for w in residual.split() if w not in STOPWORDS and len(w) > 1]
        if len(rwords) <= 1:
            residual = None

    # Si no se interpretó NADA con estructura (solo texto), el texto completo
    # va como full-text query.
    if not (city or dept or category or required or residual):
        residual = ntext or None

    return SearchQuery(
        query=residual,
        country=country,
        region=dept if dept else (city or None),
        city=city,
        category=category,
        industry=category,  # compat: categoría canónica = industria
        required_fields=required,
        online="any" if any(f in ("website", "email", "phone") for f in required) else None,
        scope=scope,
        sort="newest",
    )


def interpret_with_llm_fallback(text: str, default_country: str = "PY") -> SearchQuery:
    """interpret() + fallback LLM opcional.

    Si el parser por reglas no detecta categoría ni geografía ni campos
    requeridos, intenta DeepSeek (si está configurado) para estructurar la
    query. Sin key → devuelve el resultado de reglas tal cual.
    """
    sq = interpret(text, default_country=default_country)
    if sq.category or sq.region or sq.required_fields or not sq.query:
        return sq
    try:
        from app.services.llm import is_configured
        if not is_configured():
            return sq
        # Hook documentado: enviar texto a LLM con schema SearchQuery.
        # Se mantiene por detrás de un flag opcional (FASE posterior).
        return sq
    except Exception:
        return sq

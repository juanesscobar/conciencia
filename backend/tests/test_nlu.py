"""Tests NL parser: queries benchmark de spec §40 + reglas de interpretación."""

import pytest

from app.modules.leadhunter.nlu import interpret, _norm


class TestNluInterpret:
    def test_playa_de_autos_ciudad_del_este(self):
        """'playas de autos usados en Ciudad del Este' → automotriz + región."""
        sq = interpret("playas de autos usados en Ciudad del Este")
        assert sq.category == "automotriz"
        assert sq.industry == "automotriz"
        assert sq.country == "PY"
        assert sq.region is not None
        assert "ciudad del este" in _norm(sq.region)

    def test_farmacias_asuncion(self):
        sq = interpret("farmacias en Asunción")
        assert sq.category == "farmacia"
        assert "asuncion" in _norm(sq.region or "")

    def test_english_dealerships_high_parana(self):
        """Query EN: vehicle dealerships in Alto Paraná → automotriz + región."""
        sq = interpret("Find vehicle dealerships in Alto Parana that have a website, phone number and appear to be active businesses")
        assert sq.category == "automotriz"
        assert "alto parana" in _norm(sq.region or "")
        assert "website" in sq.required_fields
        assert "phone" in sq.required_fields

    def test_distribuidoras_con_email(self):
        sq = interpret("distribuidoras mayoristas con email en Central")
        assert sq.category == "distribuidora"
        assert "email" in sq.required_fields
        assert "central" in _norm(sq.region or "")

    def test_default_country(self):
        sq = interpret("empresas de software")
        assert sq.country == "PY"
        sq2 = interpret("empresas de software", default_country="BR")
        assert sq2.country == "BR"

    def test_empty_text(self):
        sq = interpret("")
        assert sq.country == "PY"
        assert sq.query is None

    def test_required_fields_detection(self):
        sq = interpret("hoteles con website y telefono en Luque")
        assert sq.category == "hoteleria"
        assert "website" in sq.required_fields
        assert "phone" in sq.required_fields

    def test_scope_derivation(self):
        sq = interpret("farmacias en Asuncion")
        assert sq.scope in ("city", "region")
        sq2 = interpret("bancos")
        assert sq2.scope == "country"


class TestNorm:
    def test_acentos(self):
        assert _norm("Asunción") == "asuncion"
        assert _norm("Ciudad del Este") == "ciudad del este"

"""Tests unitarios para discovery: dedupe, scoring, normalize."""

import pytest
from app.modules.leadhunter.discovery import normalize_company, domain_of
from app.modules.leadhunter.service import compute_score


class TestNormalizeCompany:
    def test_basic(self):
        assert normalize_company("Cooperativa Ypacarai") == "cooperativa ypacarai"

    def test_quita_acentos(self):
        assert normalize_company("Asunción") == "asuncion"

    def test_quita_sufijos_legales(self):
        assert normalize_company("Empresa S.A.") == "empresa"
        assert normalize_company("Empresa S.R.L.") == "empresa"
        assert "empresa" in normalize_company("Empresa S.A.C.I.")

    def test_quita_puntuacion(self):
        result = normalize_company("Empresa, S.A.")
        assert "empresa" in result

    def test_vacio(self):
        assert normalize_company("") == ""
        assert normalize_company(None) == ""

    def test_espacios_multiples(self):
        assert normalize_company("  Empresa   S.A.  ") == "empresa"


class TestDomainOf:
    def test_basic(self):
        assert domain_of("https://example.com") == "example.com"
        assert domain_of("https://www.example.com") == "example.com"
        assert domain_of("http://example.com/path") == "example.com"

    def test_none(self):
        assert domain_of(None) is None
        assert domain_of("") is None


class TestComputeScore:
    def test_cooperativa_alto_score(self):
        score = compute_score(
            company="Cooperativa Test",
            industry="cooperativa",
            source="overpass",
            email="test@test.com",
            phone="+595981123456",
        )
        assert score >= 50

    def test_hospital_alto_score(self):
        score = compute_score(
            company="Hospital Test",
            industry="salud",
            source="overpass",
            email="test@test.com",
        )
        assert score >= 40

    def test_sin_contacto_bajo_score(self):
        score = compute_score(
            company="Empresa Sin Datos",
            industry="comercio",
            source="overpass",
        )
        assert score < 30

    def test_con_email_suma_puntos(self):
        sin_email = compute_score(company="Test", industry="comercio", source="overpass")
        con_email = compute_score(company="Test", industry="comercio", source="overpass", email="test@test.com")
        assert con_email > sin_email

    def test_con_phone_suma_puntos(self):
        sin_phone = compute_score(company="Test", industry="comercio", source="overpass")
        con_phone = compute_score(company="Test", industry="comercio", source="overpass", phone="+595981123456")
        assert con_phone > sin_phone

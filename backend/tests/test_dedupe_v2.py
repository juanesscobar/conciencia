"""Tests dedupe v2: normalización + entity resolution indexado (spec §12)."""

from app.modules.leadhunter.normalization import (
    normalize_company,
    domain_of,
    norm_phone,
    norm_email,
)
from app.modules.leadhunter.entity import is_duplicate, find_duplicates, apply_normalization
from app.modules.leadhunter.models import Lead


class TestNormalization:
    def test_company_legal_suffixes(self):
        assert normalize_company("Cooperativa Ypacarai S.A.") == "cooperativa ypacarai"
        assert normalize_company("Distribuidora Norte S.R.L.") == "distribuidora norte"
        assert normalize_company("Ferreteria El Clavo SAC") == "ferreteria el clavo"

    def test_company_accents_and_case(self):
        assert normalize_company("FARMACIA SAN ROQUÉ") == "farmacia san roque"
        assert normalize_company("Asunción Motors") == "asuncion motors"

    def test_company_generic_words_removed(self):
        # "empresa"/"servicios" no discriminan entre duplicados
        assert normalize_company("Empresa San Blas") == "san blas"
        assert normalize_company("Servicios San Blas") == "san blas"

    def test_domain(self):
        assert domain_of("https://www.example.com.py/x/y") == "example.com.py"
        assert domain_of("http://Example.COM") == "example.com"
        assert domain_of(None) is None

    def test_phone(self):
        assert norm_phone("(+595) 21 123-4567") == "11234567"
        assert norm_phone("021 123 456") == "21123456"
        assert norm_phone("") == ""

    def test_email(self):
        assert norm_email("  INFO@Ejemplo.COM ") == "info@ejemplo.com"


def _seed(db, company="Empresa X", website=None, phone=None, email=None):
    lead = Lead(company=company, website=website, phone=phone, email=email, source="test")
    apply_normalization(lead)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


class TestEntityResolution:
    def test_duplicate_by_normalized_name(self, db):
        _seed(db, company="Distribuidora Norte S.R.L.")
        assert is_duplicate(db, company="Distribuidora Norte SRL") is True
        assert is_duplicate(db, company="Otra Empresa") is False

    def test_duplicate_by_domain(self, db):
        _seed(db, website="https://www.example.com.py")
        assert is_duplicate(db, website="https://example.com.py") is True

    def test_duplicate_by_phone(self, db):
        _seed(db, phone="021 123-4567")
        assert is_duplicate(db, phone="+595211234567") is True

    def test_duplicate_by_email(self, db):
        _seed(db, email="ventas@ejemplo.com")
        assert is_duplicate(db, email="VENTAS@Ejemplo.COM") is True

    def test_no_false_positive(self, db):
        _seed(db, company="Farmacia San Roque", phone="021123456")
        assert is_duplicate(db, company="Farmacia San Blas", phone="0987654321") is False

    def test_exclude_id(self, db):
        lead = _seed(db, company="Misma Empresa")
        assert is_duplicate(db, company="Misma Empresa", exclude_id=lead.id) is False

    def test_find_duplicates_returns_leads(self, db):
        existing = _seed(db, company="Cooperativa 1 S.A.")
        dupes = find_duplicates(db, company="Cooperativa 1 SA")
        assert len(dupes) == 1
        assert dupes[0].id == existing.id

    def test_apply_normalization_populates_columns(self, db):
        lead = _seed(db, company="FARMACIA SAN ROQUÉ", website="https://www.fsr.com.py", phone="021 123 4567")
        assert lead.normalized_name == "farmacia san roque"
        assert lead.normalized_domain == "fsr.com.py"
        assert lead.normalized_phone == "11234567"

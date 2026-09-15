"""Tests de geografía first-class (spec §7-9): scope default PY, allowlist, global explícito."""

import pytest
from unittest.mock import patch, MagicMock

from app.modules.leadhunter.geo import (
    GeographicScope,
    GeoScopeError,
    build_geo_context,
    get_geo_provider,
    COUNTRY_AREAS,
)
from app.modules.leadhunter.models import Lead


class TestGeographicScope:
    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("SEARCH_DEFAULT_COUNTRY", raising=False)
        monkeypatch.delenv("SEARCH_ALLOWED_COUNTRIES", raising=False)
        monkeypatch.delenv("SEARCH_SCOPE", raising=False)
        monkeypatch.delenv("LEADHUNTER_SCOPE", raising=False)
        s = GeographicScope.from_env()
        assert s.default_country == "PY"
        assert "PY" in s.allowed_countries
        assert s.scope == "country"

    def test_from_env_custom(self, monkeypatch):
        monkeypatch.setenv("SEARCH_DEFAULT_COUNTRY", "BR")
        monkeypatch.setenv("SEARCH_ALLOWED_COUNTRIES", "BR,AR")
        monkeypatch.setenv("SEARCH_SCOPE", "region")
        monkeypatch.setenv("SEARCH_DEFAULT_REGION", "São Paulo")
        s = GeographicScope.from_env()
        assert s.default_country == "BR"
        assert s.allowed_countries == ["BR", "AR"]
        assert s.scope == "region"
        assert s.default_region == "São Paulo"

    def test_legacy_bbox_scope_maps_to_region(self, monkeypatch):
        monkeypatch.delenv("SEARCH_SCOPE", raising=False)
        monkeypatch.setenv("LEADHUNTER_SCOPE", "bbox")
        s = GeographicScope.from_env()
        assert s.scope == "region"

    def test_effective_applies_default_country(self):
        s = GeographicScope(default_country="PY", allowed_countries=["PY"])
        eff = s.effective()
        assert eff.default_country == "PY"

    def test_effective_global_requires_allow_global(self):
        s = GeographicScope(default_country="PY", allowed_countries=["PY"], scope="global")
        with pytest.raises(GeoScopeError):
            s.effective()
        eff = s.effective(allow_global=True)
        assert eff.scope == "global"

    def test_effective_rejects_country_outside_allowlist(self):
        s = GeographicScope(default_country="PY", allowed_countries=["PY", "BR"])
        with pytest.raises(GeoScopeError):
            s.effective(country="XX")

    def test_effective_city_upgrades_scope(self):
        s = GeographicScope(default_country="PY", allowed_countries=["PY"], scope="country")
        eff = s.effective(city="Ciudad del Este")
        assert eff.scope == "city"
        assert eff.default_city == "Ciudad del Este"


class TestBuildGeoContext:
    def test_default_country_py_area(self, monkeypatch):
        monkeypatch.delenv("SEARCH_SCOPE", raising=False)
        monkeypatch.delenv("LEADHUNTER_SCOPE", raising=False)
        ctx = build_geo_context()
        assert ctx["country"] == "PY"
        assert ctx["is_global"] is False
        assert ctx["area_id"] == COUNTRY_AREAS["PY"]

    def test_global_requires_flag(self, monkeypatch):
        monkeypatch.setenv("SEARCH_SCOPE", "global")
        with pytest.raises(GeoScopeError):
            build_geo_context()
        ctx = build_geo_context(allow_global=True)
        assert ctx["is_global"] is True

    def test_region_resolves_bbox(self, monkeypatch):
        monkeypatch.setenv("SEARCH_SCOPE", "region")
        monkeypatch.delenv("SEARCH_DEFAULT_REGION", raising=False)
        monkeypatch.setenv("SEARCH_DEFAULT_REGION", "Alto Paraná")
        with patch.object(
            get_geo_provider(), "bounding_box_for", return_value=(-25.5, -55.1, -24.9, -54.6)
        ) as mock_bb:
            ctx = build_geo_context()
            mock_bb.assert_called_once()
            assert ctx["bbox"] == (-25.5, -55.1, -24.9, -54.6)

    def test_region_fallback_env_bbox(self, monkeypatch):
        monkeypatch.setenv("SEARCH_SCOPE", "region")
        monkeypatch.delenv("SEARCH_DEFAULT_REGION", raising=False)
        monkeypatch.setenv("LEADHUNTER_BBOX", "-25.55,-57.75,-25.15,-57.40")
        with patch.object(get_geo_provider(), "bounding_box_for", return_value=None):
            ctx = build_geo_context()
            assert ctx["bbox"] == (-25.55, -57.75, -25.15, -57.40)

    def test_provider_factory_unknown(self):
        with pytest.raises(GeoScopeError):
            get_geo_provider("googlemaps-no-existe")


class TestGeoScopeAPI:
    def test_geo_scope_endpoint(self, client, auth_headers):
        res = client.get("/api/v1/leads/geo/scope", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["country"] == "PY"
        assert data["is_global"] is False
        assert data["scope_dict"]["default_country"] == "PY"

    def test_hunt_run_applies_scope(self, client, auth_headers, db):
        """Cazar sin filtros usa el scope default (PY) y no toca la red real."""
        mock_items = [
            {"company": "Farmacia Test CDE", "industry": "farmacia", "segment": "pyme",
             "region": "Ciudad del Este", "phone": "+595981123456"},
        ]
        with patch("app.modules.leadhunter.sources.overpass.OverpassSource.fetch", return_value=mock_items) as mock_fetch:
            res = client.post("/api/v1/leads/hunt/run", headers=auth_headers)
            assert res.status_code == 200
            data = res.json()
            assert data["total_added"] == 1
            # el fetch recibe geo context (nunca None → scope efectivo aplicado)
            _, kwargs = mock_fetch.call_args
            assert kwargs.get("geo") is not None
            assert kwargs["geo"]["country"] == "PY"

    def test_hunt_run_city_filter(self, client, auth_headers, db):
        mock_items = [
            {"company": "Playas del Este", "industry": "comercio", "segment": "pyme",
             "region": "Ciudad del Este", "phone": "+595981123456"},
        ]
        with patch("app.modules.leadhunter.sources.overpass.OverpassSource.fetch", return_value=mock_items):
            res = client.post(
                "/api/v1/leads/hunt/run",
                params={"city": "Ciudad del Este"},
                headers=auth_headers,
            )
            assert res.status_code == 200
            data = res.json()
            assert data["total_added"] == 1
            leads = db.query(Lead).all()
            assert leads[0].region == "Ciudad del Este"

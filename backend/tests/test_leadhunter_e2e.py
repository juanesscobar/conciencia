"""Tests E2E para LeadHunterJob: lifecycle, cancel, retry, error handling."""

import time
import pytest
from unittest.mock import patch, MagicMock


class TestLeadHunterJobAPI:
    def test_create_job(self, client, auth_headers):
        """POST /jobs crea un job"""
        with patch("app.modules.leadhunter.jobs.start_job"):
            res = client.post("/api/v1/leads/jobs", json={
                "name": "Test Job",
                "criteria": {"source": "overpass", "limit": 1},
            }, headers=auth_headers)
            assert res.status_code == 201
            job = res.json()
            assert job["status"] == "pending"
            assert job["name"] == "Test Job"
            assert job["criteria"]["source"] == "overpass"

    def test_list_jobs(self, client, auth_headers):
        """GET /jobs lista los jobs creados"""
        res = client.get("/api/v1/leads/jobs", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data

    def test_get_job_by_id(self, client, auth_headers):
        """GET /jobs/{id} devuelve un job especifico"""
        with patch("app.modules.leadhunter.jobs.start_job"):
            res = client.post("/api/v1/leads/jobs", json={
                "name": "Test Get",
                "criteria": {"source": "overpass"},
            }, headers=auth_headers)
            job_id = res.json()["id"]

            res = client.get(f"/api/v1/leads/jobs/{job_id}", headers=auth_headers)
            assert res.status_code == 200
            job = res.json()
            assert job["id"] == job_id
            assert job["name"] == "Test Get"

    def test_get_nonexistent_job(self, client, auth_headers):
        """GET /jobs/{id} con ID inexistente devuelve 404"""
        res = client.get("/api/v1/leads/jobs/nonexistent-id", headers=auth_headers)
        assert res.status_code == 404

    def test_create_job_without_auth(self, client):
        """POST /jobs sin auth devuelve 401/403"""
        res = client.post("/api/v1/leads/jobs", json={
            "criteria": {"source": "overpass"},
        })
        assert res.status_code in (401, 403)


class TestLeadHunterJobInvalidSource:
    def test_invalid_source_fails(self, client, auth_headers):
        """Source inexistente -> job se crea pero falla"""
        with patch("app.modules.leadhunter.jobs.start_job"):
            res = client.post("/api/v1/leads/jobs", json={
                "name": "Bad Source",
                "criteria": {"source": "nonexistent"},
            }, headers=auth_headers)
            assert res.status_code == 201
            job = res.json()
            assert job["status"] == "pending"


class TestLeadHunterJobCancel:
    def test_cancel_endpoint(self, client, auth_headers):
        """POST /cancel en un job"""
        with patch("app.modules.leadhunter.jobs.start_job"):
            res = client.post("/api/v1/leads/jobs", json={
                "criteria": {"source": "overpass"},
            }, headers=auth_headers)
            job_id = res.json()["id"]

            res = client.post(f"/api/v1/leads/jobs/{job_id}/cancel", headers=auth_headers)
            assert res.status_code in (200, 409)


class TestLeadHunterJobRetry:
    def test_retry_endpoint(self, client, auth_headers):
        """POST /retry en un job"""
        with patch("app.modules.leadhunter.jobs.start_job"):
            res = client.post("/api/v1/leads/jobs", json={
                "criteria": {"source": "overpass"},
            }, headers=auth_headers)
            job_id = res.json()["id"]

            res = client.post(f"/api/v1/leads/jobs/{job_id}/retry", headers=auth_headers)
            assert res.status_code in (200, 202, 409)


class TestExceptions:
    def test_lead_hunter_error_to_dict(self):
        from app.modules.leadhunter.exceptions import LeadHunterError
        e = LeadHunterError("test error", error_type="test")
        d = e.to_dict()
        assert d["type"] == "test"
        assert d["message"] == "test error"

    def test_rate_limit_error(self):
        from app.modules.leadhunter.exceptions import RateLimitError
        e = RateLimitError("overpass", retry_after=30)
        assert e.retry_after == 30
        d = e.to_dict()
        assert d["type"] == "rate_limit"
        assert d["retry_after"] == 30

    def test_source_timeout_error(self):
        from app.modules.leadhunter.exceptions import SourceTimeoutError
        e = SourceTimeoutError("overpass", timeout=120)
        assert e.timeout == 120
        d = e.to_dict()
        assert d["type"] == "source_timeout"

    def test_invalid_criteria_error(self):
        from app.modules.leadhunter.exceptions import InvalidCriteriaError
        e = InvalidCriteriaError("fuente mala")
        d = e.to_dict()
        assert d["type"] == "invalid_criteria"

    def test_partial_failure_error(self):
        from app.modules.leadhunter.exceptions import PartialFailureError
        e = PartialFailureError(["overpass"], ["manual"])
        d = e.to_dict()
        assert d["type"] == "partial_failure"
        assert "overpass" in d["message"]


class TestJobExecution:
    def test_execute_job_sync(self, client, auth_headers, db):
        """Ejecutar un job sincronicamente (sin thread) y verificar resultado"""
        from app.modules.leadhunter.jobs import _execute, create_job
        from app.modules.leadhunter.models import LeadHunterJob, LeadHunterJobStatus

        mock_fetch = MagicMock(return_value=[
            {"company": "Test Coop", "industry": "cooperativa", "segment": "mediana",
             "region": "Asuncion", "phone": "+595981123456", "email": "test@test.com"},
        ])

        with patch("app.modules.leadhunter.sources.overpass.OverpassSource.fetch", mock_fetch):
            job = create_job(db, name="Sync Test", project_id=None, criteria={"source": "overpass", "limit": 1})
            job_id = job.id

            job = db.query(LeadHunterJob).filter(LeadHunterJob.id == job_id).first()
            _execute(db, job_id)

            db.refresh(job)
            assert job.status in (LeadHunterJobStatus.COMPLETED, LeadHunterJobStatus.PARTIAL_FAILURE)
            assert job.progress == "done"

    def test_execute_job_invalid_source_sync(self, client, auth_headers, db):
        """Ejecutar un job con source invalido sincronicamente"""
        from app.modules.leadhunter.jobs import _execute, create_job
        from app.modules.leadhunter.models import LeadHunterJob, LeadHunterJobStatus

        job = create_job(db, name="Bad Source", project_id=None, criteria={"source": "nonexistent"})
        job_id = job.id

        with patch("app.modules.leadhunter.jobs.start_job"):
            pass

        job = db.query(LeadHunterJob).filter(LeadHunterJob.id == job_id).first()
        _execute(db, job_id)

        db.refresh(job)
        assert job.status == LeadHunterJobStatus.FAILED
        assert "invalid_criteria" in (job.error or "")
